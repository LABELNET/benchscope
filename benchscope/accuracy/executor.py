"""精度评测执行器（Serving / Native / Mock 统一推理接口 + run_eval 编排）。

本模块即内置命令 `benchscope eval` 的实现体，CLI 与 Web 任务（EvalTaskManager）
双入口共用同一评测核心：

    run_eval(cfg, payload, callbacks) → (meta, sample_results, result)

流程：数据集加载 → Prompt 构建 → 批量推理（完整回答 + usage Token 采集 +
失败重试 → invalid + stop 中断 + 进度回调）→ 判分（scorers 注册表）→ 指标汇总。

Serving：aiohttp 异步调用 OpenAI 兼容 API（非流式为主，可选流式），
         usage 逐条采集，缺失时按 chars/4 近似（仅精度统计用途）。
Native  ：transformers 本地推理（native_runner，惰性导入，缺依赖抛明确错误）。
Mock    ：按样本返回可控伪输出（mock_correct_rate 控制正确率），mock 环境全链路联调。
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import aiohttp

from benchscope.accuracy import metrics as acc_metrics
from benchscope.accuracy.datasets import build_prompt, load_samples
from benchscope.accuracy.engines import eval_capability, get_eval_engine
from benchscope.accuracy.scorers import get_scorer
from benchscope.accuracy.scorers.base import clean_output
from benchscope.accuracy.scorers.code import compiles
from benchscope.accuracy.scorers.judge import judge_turn

log = logging.getLogger("benchscope.accuracy.executor")

DEFAULT_TIMEOUT = 300.0
DEFAULT_CONCURRENCY = 4
DEFAULT_RETRIES = 1  # 失败重试次数（重试仍失败 → invalid）


# ---------------------------------------------------------------------------
# 选项与结果结构
# ---------------------------------------------------------------------------


@dataclass
class InferOptions:
    """一次精度评测的推理选项（由 payload + Provider 配置映射）。"""

    capability: str = "serving"        # serving | native | mock
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    endpoint: str = "/v1/chat/completions"
    backend: str = "openai-chat"       # openai-chat | openai
    lora_name: str = ""                # Serving：服务端已注册的 adapter 名（请求侧 model）
    lora_path: str = ""                # Native：peft adapter 路径
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 512
    seed: int = 0
    concurrency: int = DEFAULT_CONCURRENCY
    timeout: float = DEFAULT_TIMEOUT
    extra_headers: dict = field(default_factory=dict)
    stream: bool = False
    judge_model: str = ""              # MT-Bench 评审模型（空 = 与被测模型相同）
    mock_correct_rate: float = 0.7     # mock 引擎可控正确率


@dataclass
class InferResult:
    """单样本推理结果。"""

    index: int = 0
    output: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    error: str = ""
    turns: list = field(default_factory=list)  # MT-Bench 两轮问答 [{question, answer}]


def _approx_tokens(text: str) -> int:
    return max(1, round(len(text or "") / 4.0))


# ---------------------------------------------------------------------------
# Serving：aiohttp 异步批量推理
# ---------------------------------------------------------------------------


def _messages_for(sample: dict, prompt: str) -> list[dict]:
    return [{"role": "user", "content": prompt}]


def _chat_body(opts: InferOptions, messages: list[dict]) -> dict:
    model = opts.lora_name or opts.model
    return {
        "model": model,
        "messages": messages,
        "max_tokens": int(opts.max_tokens),
        "temperature": float(opts.temperature),
        "top_p": float(opts.top_p),
        "stream": bool(opts.stream),
    }


def _completion_body(opts: InferOptions, prompt: str) -> dict:
    model = opts.lora_name or opts.model
    return {
        "model": model,
        "prompt": prompt,
        "max_tokens": int(opts.max_tokens),
        "temperature": float(opts.temperature),
        "top_p": float(opts.top_p),
        "stream": bool(opts.stream),
    }


def _extract_text(payload: dict, is_chat: bool) -> str:
    choices = payload.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return ""
    if is_chat:
        msg = choices[0].get("message") or {}
        return str(msg.get("content") or msg.get("reasoning_content") or "")
    return str(choices[0].get("text") or "")


def _headers(opts: InferOptions) -> dict:
    headers = {"Content-Type": "application/json"}
    if opts.api_key:
        headers["Authorization"] = f"Bearer {opts.api_key}"
    headers.update(opts.extra_headers or {})
    return headers


def _endpoint_url(opts: InferOptions) -> str:
    base = (opts.base_url or "").rstrip("/")
    ep = opts.endpoint if opts.endpoint.startswith("/") else "/" + opts.endpoint
    return base + ep


async def _infer_once(session, opts: InferOptions, messages: list[dict], prompt: str,
                      t_start: float) -> InferResult:
    """执行一次推理请求（SSE / 非流式双模式），返回完整回答与 usage。"""
    is_chat = "chat/completions" in opts.endpoint
    body = _chat_body(opts, messages) if is_chat else _completion_body(opts, prompt)
    rec = InferResult(index=-1)
    t0 = time.perf_counter()
    try:
        timeout = aiohttp.ClientTimeout(total=opts.timeout)
        async with session.post(_endpoint_url(opts), json=body, headers=_headers(opts), timeout=timeout) as resp:
            if resp.status != 200:
                text = await resp.text()
                rec.error = f"HTTP {resp.status}: {text[:200]}"
                rec.latency_ms = (time.perf_counter() - t0) * 1000
                return rec
            if opts.stream:
                output_parts: list[str] = []
                usage: dict = {}
                async for raw in resp.content:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    usage = chunk.get("usage") or usage
                    piece = _extract_text(chunk, is_chat)
                    if piece:
                        output_parts.append(piece)
                rec.output = "".join(output_parts)
                rec.prompt_tokens = int((usage or {}).get("prompt_tokens") or 0)
                rec.completion_tokens = int((usage or {}).get("completion_tokens") or 0)
            else:
                payload = await resp.json(content_type=None)
                rec.output = _extract_text(payload, is_chat)
                usage = payload.get("usage") or {}
                rec.prompt_tokens = int(usage.get("prompt_tokens") or 0)
                rec.completion_tokens = int(usage.get("completion_tokens") or 0)
            rec.latency_ms = (time.perf_counter() - t0) * 1000
            # usage 缺失 → chars/4 近似（仅精度统计用途，非性能口径）
            if rec.prompt_tokens <= 0:
                rec.prompt_tokens = _approx_tokens(prompt)
            if rec.completion_tokens <= 0:
                rec.completion_tokens = _approx_tokens(rec.output)
            return rec
    except asyncio.CancelledError:
        rec.error = "cancelled"
        return rec
    except Exception as e:  # noqa: BLE001
        rec.error = f"{type(e).__name__}: {e}"[:300]
        rec.latency_ms = (time.perf_counter() - t0) * 1000
        return rec


async def _run_serving_async(opts: InferOptions, message_tasks: list[tuple[int, list[dict], str]],
                             stop_event: asyncio.Event,
                             progress_cb: Optional[Callable[[int, int], None]]) -> list[InferResult]:
    """并发批量推理：concurrency 个信号量槽位 + 逐样本失败重试。"""
    total = len(message_tasks)
    results: dict[int, InferResult] = {}
    lock = asyncio.Lock()
    done = {"n": 0}
    sem = asyncio.Semaphore(max(1, int(opts.concurrency)))
    connector = aiohttp.TCPConnector(limit=0, ssl=False)
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=opts.timeout)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        async def worker(index: int, messages: list[dict], prompt: str):
            async with sem:
                if stop_event.is_set():
                    results[index] = InferResult(index=index, error="stopped")
                    return
                rec = InferResult(index=index, error="retry-exhausted")
                for _ in range(DEFAULT_RETRIES + 1):
                    if stop_event.is_set():
                        rec = InferResult(index=index, error="stopped")
                        break
                    rec = await _infer_once(session, opts, messages, prompt, time.perf_counter())
                    if not rec.error:
                        break
                rec.index = index
                results[index] = rec
                async with lock:
                    done["n"] += 1
                    if progress_cb:
                        progress_cb(done["n"], total)

        await asyncio.gather(*(worker(i, m, p) for i, m, p in message_tasks))

    return [results[i] for i in range(total) if i in results]


def run_serving_inference(opts: InferOptions, message_tasks: list[tuple[int, list[dict], str]],
                          stop_flag=None, progress_cb: Optional[Callable[[int, int], None]] = None) -> list[InferResult]:
    """同步入口：Serving 批量推理（线程内新开事件循环，桥接 threading 停止信号）。"""
    loop = asyncio.new_event_loop()
    stop_event = asyncio.Event()
    try:
        asyncio.set_event_loop(loop)
        if stop_flag is not None:
            async def _poll_stop():
                while not stop_event.is_set():
                    if stop_flag.is_set():
                        stop_event.set()
                        return
                    await asyncio.sleep(0.1)

            loop.create_task(_poll_stop())
        return loop.run_until_complete(_run_serving_async(opts, message_tasks, stop_event, progress_cb))
    finally:
        try:
            loop.close()
        except Exception:
            pass
        asyncio.set_event_loop(None)


# ---------------------------------------------------------------------------
# Mock：可控正确率伪输出（mock 环境定位，联调与测试）
# ---------------------------------------------------------------------------


def _mock_output(sample: dict, prompt: str, scorer: str, rate: float, seed: int, index: int,
                 n_choices: int) -> str:
    """按样本确定性生成伪输出：rate 概率给正确答案，否则给错误答案。"""
    rng = random.Random(f"mock-{seed}-{index}")
    correct = rng.random() < rate
    letters = "ABCDEFGH"[: max(2, min(n_choices, 8))]

    if scorer == "choice":
        answer = str(sample.get("answer") or "").strip().upper()
        if correct and answer in letters:
            letter = answer
        elif answer in letters:
            others = [ch for ch in letters if ch != answer]
            letter = rng.choice(others) if others else answer
        else:
            letter = rng.choice(letters)
        return f"{sample.get('question') or ''}\n答案是 {letter}"

    answer = str(sample.get("answer") or "").strip()
    num = None
    try:
        num = float(answer.replace(",", ""))
    except (TypeError, ValueError):
        num = None
    if num is not None:
        wrong = num + (rng.choice([-2, -1, 1, 2]) or 1)
        value = num if correct else wrong
        value = int(value) if float(value).is_integer() else round(value, 4)
        return f"逐步推理……最终答案是 {value}"
    return f"推理过程……答案是 {answer if correct else answer + 'x'}"


def run_mock_inference(opts: InferOptions, samples: list[dict], prompts: list[str],
                       scorer: str) -> list[InferResult]:
    """mock 批量推理：确定性伪输出 + 近似 Token 计数。"""
    out = []
    for sample, prompt in zip(samples, prompts):
        index = int(sample.get("index", 0))
        n_choices = len(sample.get("choices") or []) or 4
        text = _mock_output(sample, prompt, scorer, opts.mock_correct_rate, opts.seed, index, n_choices)
        out.append(InferResult(
            index=index,
            output=text,
            prompt_tokens=_approx_tokens(prompt),
            completion_tokens=_approx_tokens(text),
            latency_ms=1.0,
        ))
    return out


# ---------------------------------------------------------------------------
# 评测编排：数据集 → Prompt → 推理 → 判分 → 汇总
# ---------------------------------------------------------------------------


def _native_messages(opts: InferOptions, message_tasks: list[tuple[int, list[dict], str]],
                     stop_flag, progress_cb) -> list[InferResult]:
    """Native 推理（transformers 本地权重，惰性导入；缺依赖抛明确错误）。"""
    try:
        from benchscope.accuracy.native_runner import generate_native
    except ImportError as e:  # pragma: no cover - 仅缺依赖时触发
        raise RuntimeError(
            "Native 精度评测需要 transformers/torch 环境：pip install 'benchscope[accuracy-native]'"
        ) from e
    return generate_native(opts, message_tasks, stop_flag=stop_flag, progress_cb=progress_cb)


def run_eval(cfg, payload: dict, *, log_cb: Optional[Callable[[str], None]] = None,
             sample_cb: Optional[Callable[[dict], None]] = None,
             progress_cb: Optional[Callable[[int, int], None]] = None,
             stop_flag=None) -> tuple[dict, list[dict], dict, bool]:
    """执行一次精度评测（`benchscope eval` 与 EvalTaskManager 共用核心）。

    payload：{engine_id, model, lora_name, lora_path, dataset{id|path}, limit, seed,
              temperature, top_p, max_tokens, concurrency, judge_model,
              mock_correct_rate, use_mock_env, api{base_url,endpoint,api_key,extra_headers}}
    返回：(meta, sample_results, result, stopped)
      - sample_results：逐样本溯源记录（samples.jsonl 行内容）
      - result：汇总指标（不含 benchmark，由调用方补充对标）
    """
    def log(line: str):
        if log_cb:
            log_cb(line + "\n")

    engine_id = payload.get("engine_id") or ""
    engine = get_eval_engine(engine_id)
    if not engine:
        raise ValueError(f"精度引擎无效或不支持精度评测: {engine_id or '（未指定）'}")
    capability = eval_capability(engine)
    mode = "native" if capability == "native" else "serving"

    api = dict(payload.get("api") or cfg.api or {})
    opts = InferOptions(
        capability=capability,
        base_url=api.get("base_url") or "",
        api_key=api.get("api_key") or "",
        endpoint=api.get("endpoint") or "/v1/chat/completions",
        backend=payload.get("backend") or "openai-chat",
        model=payload.get("model") or "",
        lora_name=payload.get("lora_name") or "",
        lora_path=payload.get("lora_path") or "",
        temperature=float(payload.get("temperature") or 0.0),
        top_p=float(payload.get("top_p") or 1.0),
        max_tokens=int(payload.get("max_tokens") or 512),
        seed=int(payload.get("seed") or 0),
        concurrency=int(payload.get("concurrency") or DEFAULT_CONCURRENCY),
        judge_model=payload.get("judge_model") or "",
        mock_correct_rate=float(payload["mock_correct_rate"]) if payload.get("mock_correct_rate") is not None else 0.7,
        stream=bool(payload.get("stream") or False),
    )
    opts.extra_headers = dict(api.get("extra_headers") or {})

    dataset_ref = payload.get("dataset") or {}
    meta, samples = load_samples(cfg, dataset_ref, limit=payload.get("limit") or 0, seed=opts.seed)
    scorer_name = (meta.get("eval") or {}).get("scorer") or "choice"
    scorer = get_scorer(scorer_name)
    total = len(samples)
    log(f"[accuracy] dataset={meta['id']} samples={total} engine={engine_id} capability={capability}")
    if total == 0:
        raise RuntimeError(f"数据集 {meta['id']} 中没有可评测样本（请检查数据集内容或判分器配置）")

    # ---- 推理 ----
    prompts = [build_prompt(meta, s) for s in samples]
    stopped = False
    if capability == "mock":
        recs = run_mock_inference(opts, samples, prompts, scorer_name)
        if progress_cb:
            progress_cb(total, total)
    else:
        message_tasks = [(int(s.get("index", i)), _messages_for(s, prompts[i]), prompts[i])
                         for i, s in enumerate(samples)]

        def _progress(done: int, done_total: int):
            if progress_cb:
                progress_cb(done, done_total)

        if capability == "native":
            recs = _native_messages(opts, message_tasks, stop_flag, _progress)
        else:
            recs = run_serving_inference(opts, message_tasks, stop_flag=stop_flag, progress_cb=_progress)
        if stop_flag is not None and stop_flag.is_set():
            stopped = True

    # judge 数据集：两轮对话生成 + 评审模型打分（逐样本）
    if scorer_name == "judge" and capability == "native":
        raise RuntimeError("MT-Bench 评审模型需经 Serving 链路调用，Native 模式暂不支持 judge 数据集")
    judge_inputs: dict[int, dict] = {}
    if scorer_name == "judge" and not stopped:
        for sample, prompt, rec in zip(samples, prompts, recs):
            if rec.error:
                continue
            turns_q = [str(t) for t in (sample.get("turns") or [prompt])]
            q2 = turns_q[1] if len(turns_q) > 1 else ""
            turn1 = rec.output
            turn2 = ""
            if q2:
                messages = [
                    {"role": "user", "content": turns_q[0]},
                    {"role": "assistant", "content": turn1},
                    {"role": "user", "content": q2},
                ]
                # 第二轮生成使用被测模型（opts），评审模型仅用于打分
                if capability == "mock":
                    second = run_mock_inference(opts, [sample], [q2], "chat")[0]
                else:
                    second = run_serving_inference(opts, [(rec.index, messages, q2)])[0]
                turn2 = second.output
            judge_inputs[rec.index] = {"turns": [
                {"question": turns_q[0], "answer": turn1},
                {"question": q2, "answer": turn2},
            ]}

    # ---- 判分 + 汇总 ----
    results: list[dict] = []
    judge_model_opts = InferOptions(**{**opts.__dict__, "model": opts.judge_model or opts.model}) \
        if (scorer_name == "judge" and capability == "serving") else None
    for sample, prompt, rec in zip(samples, prompts, recs):
        index = int(sample.get("index", 0))
        record: dict = {
            "index": index,
            "sample_id": sample.get("sample_id") or f"{meta['id']}-{index}",
            "subject": sample.get("subject") or "",
            "prompt": prompt,
            "output": rec.output,
            "answer": sample.get("answer") if scorer_name != "judge" else "",
            "tokens": {"prompt_tokens": rec.prompt_tokens, "completion_tokens": rec.completion_tokens},
            "latency_ms": round(rec.latency_ms, 1),
            "status": "invalid",
            "error_tag": "",
            "error_detail": "",
            "dataset_metrics": {},
        }
        if rec.error:
            record["status"] = "invalid"
            record["error_tag"] = "输出格式错误"
            record["error_detail"] = rec.error if rec.error != "stopped" else "任务已停止"
            if rec.error == "stopped":
                stopped = True
        elif scorer_name == "judge":
            turns_info = judge_inputs.get(index) or {"turns": [{"question": prompt, "answer": rec.output}, {"question": "", "answer": ""}]}
            record["turns"] = turns_info["turns"]
            record["answer"] = ""
            scores = []
            dims = []
            for turn in turns_info["turns"]:
                if not turn.get("answer"):
                    scores.append(None)
                    continue
                if capability == "mock":
                    rng = random.Random(f"judge-{opts.seed}-{index}")
                    good = rng.random() < opts.mock_correct_rate
                    base = 8.0 if good else 4.0
                    parsed = {"score": base, "helpfulness": base, "truthfulness": base, "harmlessness": base}
                else:
                    parsed = judge_turn(lambda q: _judge_call(cfg, judge_model_opts, q), turn["question"], turn["answer"])
                scores.append(parsed)
            first = scores[0]["score"] if scores and scores[0] else None
            second = scores[1]["score"] if len(scores) > 1 and scores[1] else None
            record["dataset_metrics"] = {
                "first_turn": first,
                "second_turn": second,
                "dimensions": {
                    "helpfulness": _mean([s.get("helpfulness") for s in scores if s]),
                    "truthfulness": _mean([s.get("truthfulness") for s in scores if s]),
                    "harmlessness": _mean([s.get("harmlessness") for s in scores if s]),
                },
            }
            sample["judge_result"] = {"scores": scores, "dimensions": record["dataset_metrics"]["dimensions"]}
            verdict = scorer.score(sample, rec.output)
            record.update({
                "extracted": verdict["extracted"], "status": verdict["status"],
                "error_tag": verdict["error_tag"], "error_detail": verdict["detail"],
            })
        else:
            verdict = scorer.score(sample, rec.output)
            record["extracted"] = verdict["extracted"]
            record["status"] = verdict["status"]
            record["error_tag"] = verdict["error_tag"]
            record["error_detail"] = verdict["detail"]
            if scorer_name == "math":
                record["dataset_metrics"] = {"exact_match": verdict["status"] == "correct"}
            elif scorer_name == "code":
                code = verdict["extracted"] if isinstance(verdict["extracted"], str) else ""
                record["dataset_metrics"] = {"compiled": bool(code) and compiles(code)}
        results.append(record)
        if sample_cb:
            sample_cb(record)

    result = acc_metrics.aggregate(meta, results, mode)
    result["mode"] = mode
    result["engine_id"] = engine_id
    return meta, results, result, stopped


def _mean(values: list) -> float | None:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def _judge_call(cfg, opts: InferOptions | None, prompt: str) -> str:
    """评审模型单次调用（非流式），失败返回空串（由 judge_turn 重评/标记异常）。"""
    if opts is None or not opts.base_url:
        return ""
    try:
        recs = run_serving_inference(opts, [(0, [{"role": "user", "content": prompt}], prompt)])
        return recs[0].output if recs else ""
    except Exception:
        log.exception("judge 调用失败")
        return ""

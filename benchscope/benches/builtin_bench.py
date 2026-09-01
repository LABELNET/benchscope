"""自研 bench 引擎（benchscope builtin）：基于 OpenAI 兼容 API 的异步流式负载生成器。

设计要点
--------
1. **不依赖本地框架环境**：只依赖 aiohttp，pip 装完即可对本地/远程任意 OpenAI 兼容服务压测。
2. **流式采集**：走 SSE 流式，记录单请求时间线 `t0 → t_first → t_i → t_end`，
   这是准确测量 TTFT / ITL 的前提（非流式只能拿到 E2E）。
3. **口径对齐 vLLM bench**（保证与原生引擎结果可比）：
   - `Output token throughput = 总 completion_tokens / benchmark_duration`
   - `Total token throughput = (总 prompt_tokens + 总 completion_tokens) / duration`
   - `Request throughput = 成功请求数 / duration`
   - `TTFT` 首 token 延迟（mean / median / p99）
   - `TPOT = (E2E - TTFT) / (completion_tokens - 1)`（mean / median / p99）
   - `ITL` 相邻 chunk 间隔（mean / median / p99）
4. **输出 token 计数**：优先服务端 `usage.completion_tokens`
   （请求带 `stream_options.include_usage: true`），服务端未提供时回退按 chunk 数估算。
5. **input 长度近似构造**：按字符/token 比（默认 4 字符≈1 token）构造 prompt，零额外依赖。

子系统：LoadGenerator（负载生成） → Requester（SSE 执行） → MetricsCollector（指标计算）。
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import statistics
import time

import aiohttp
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

log = logging.getLogger("benchscope.builtin_bench")

# 字符 / token 近似比（用于构造目标输入长度的 prompt）
DEFAULT_CHARS_PER_TOKEN = 4.0

# 单请求默认超时（秒）
DEFAULT_TIMEOUT = 600.0

# 构造 prompt 用的填充词表（随机组合，避免服务端 prompt 缓存影响）
_FILLER_WORDS = (
    "benchscope performance test random prompt filler content token "
    "latency throughput inference serving model benchmark data sample text"
).split()


# ---------------------------------------------------------------------------
# Bench CLI 参数清单（configs/benchscope-default.yaml）
#
# 说明与可选值见 configs/bench-params.yaml 的 benchscope 段；此处为缺省值，
# 未出现在参数清单中的键回退这些默认值。
# ---------------------------------------------------------------------------
BUILTIN_PARAM_DEFAULTS = {
    "backend": "openai-chat",
    "endpoint": "/v1/chat/completions",
    "request-rate": "inf",
    "num-prompts": "0",
    "num-warmups": "0",
    "chars-per-token": "4",
    "timeout": "600",
    "temperature": "0.0",
    "seed": "0",
}


def _as_float(value, default: float) -> float:
    try:
        v = float(str(value).strip())
    except (TypeError, ValueError):
        return default
    return v if v == v else default  # 过滤 NaN


def _as_int(value, default: int) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def params_from_yaml(content: str) -> dict:
    """解析引擎参数清单文本（configs/<params_key>-default.yaml）为 {key: value}。"""
    params: dict = {}
    for ln in (content or "").splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        k, v = s.split(":", 1)
        k = k.strip()
        if k == "version":
            continue
        params[k] = v.strip()
    return params


def build_options(
    params: dict,
    *,
    base_url: str,
    model: str,
    dataset: dict,
    concurrency: int,
    api_key: str = "",
) -> "BuiltinOptions":
    """由「引擎参数清单」构造一次执行的选项（参数随引擎，不与其他引擎混淆）。

    params：解析自 configs/<params_key>-default.yaml 的 {key: value}（key 为连字符形式）。
    """
    p = {**BUILTIN_PARAM_DEFAULTS, **(params or {})}

    rate_raw = str(p.get("request-rate", "inf")).strip().lower()
    if rate_raw in ("inf", "", "none", "infinite"):
        rate = float("inf")
    else:
        rate = _as_float(rate_raw, float("inf"))

    num_prompts = _as_int(p.get("num-prompts"), 0)
    if num_prompts <= 0:
        num_prompts = int(concurrency)
    seed = _as_int(p.get("seed"), 0)

    return BuiltinOptions(
        base_url=base_url,
        api_key=api_key,
        model=model,
        endpoint=str(p.get("endpoint") or "/v1/chat/completions"),
        backend=str(p.get("backend") or "openai-chat"),
        dataset=dataset or {},
        concurrency=int(concurrency),
        num_prompts=num_prompts,
        request_rate=rate,
        timeout=_as_float(p.get("timeout"), DEFAULT_TIMEOUT),
        warmups=_as_int(p.get("num-warmups"), 0),
        chars_per_token=_as_float(p.get("chars-per-token"), DEFAULT_CHARS_PER_TOKEN),
        seed=seed or None,
        extra_body={"temperature": _as_float(p.get("temperature"), 0.0)},
    )


def build_command(opts: "BuiltinOptions", engine_id: str = "benchscope") -> list[str]:
    """构建 Bench CLI 的等效命令（Step3 预览 / 日志留档 / 可直接复制执行）。

    与 `benchscope perf` 子命令参数一致（见 benchscope/cli.py）。
    """
    ds = opts.dataset or {}
    rate = "inf" if opts.request_rate == float("inf") else f"{opts.request_rate:g}"
    cmd = [
        "benchscope", "perf",
        "--engine", engine_id,
        "--model", opts.model or "<model>",
        "--base-url", opts.base_url or "<base-url>",
        "--backend", opts.backend,
        "--endpoint", opts.endpoint,
        "--concurrency", str(int(opts.concurrency)),
        "--num-prompts", str(int(opts.num_prompts)),
        "--input-len", str(ds.get("input_len") or 0),
        "--output-len", str(ds.get("output_len") or 0),
        "--request-rate", rate,
        "--num-warmups", str(int(opts.warmups)),
        "--chars-per-token", f"{opts.chars_per_token:g}",
        "--timeout", f"{opts.timeout:g}",
        "--temperature", f"{_as_float((opts.extra_body or {}).get('temperature'), 0.0):g}",
        "--seed", str(int(opts.seed or 0)),
    ]
    # 阈值模式：命令体现真实执行的阈值探测参数（与 CLI --mode threshold 一致，见 cli._perf_threshold）
    if opts.mode == "threshold":
        cmd += [
            "--mode", "threshold",
            "--ttft-threshold-ms", f"{_as_float(opts.ttft_threshold_ms, 0.0):g}",
            "--tpot-threshold-ms", f"{_as_float(opts.tpot_threshold_ms, 0.0):g}",
            "--output-threshold", f"{_as_float(opts.output_throughput_threshold, 0.0):g}",
            "--max-requests", str(int(opts.max_requests or 4096)),
        ]
    return cmd


@dataclass
class RequestRecord:
    """单个请求的采集结果。"""

    ok: bool
    start: float                  # t0（相对 benchmark 起点的秒）
    first_token: Optional[float] = None   # t_first
    end: Optional[float] = None           # t_end
    itls: list = field(default_factory=list)      # 相邻 chunk 间隔（ms）
    output_events: list = field(default_factory=list)  # (t, tokens)：逐 chunk 产出 token 时间序列（peak 滑窗用）
    completion_tokens: int = 0
    prompt_tokens: int = 0
    error: str = ""
    server_error: bool = False    # 服务端返回错误（4xx/5xx），区别于客户端异常


@dataclass
class BuiltinOptions:
    """自研引擎一次执行所需的选项（由 BenchOptions / task payload 映射而来）。"""

    base_url: str                 # 如 http://127.0.0.1:8000
    api_key: str = ""
    model: str = ""
    endpoint: str = "/v1/chat/completions"   # /v1/chat/completions | /v1/completions
    backend: str = "openai-chat"             # openai-chat | openai
    dataset: dict = field(default_factory=dict)   # {type, input_len, output_len, path}
    concurrency: int = 1
    num_prompts: int = 0
    request_rate: float = float("inf")
    timeout: float = DEFAULT_TIMEOUT
    warmups: int = 0
    extra_headers: dict = field(default_factory=dict)
    extra_body: dict = field(default_factory=dict)
    chars_per_token: float = DEFAULT_CHARS_PER_TOKEN
    seed: Optional[int] = None
    mode: str = "concurrency"                 # concurrency | threshold（仅用于命令展示，执行策略由上层决定）
    max_requests: int = 4096                  # 阈值模式：请求数上限（强制结束）
    ttft_threshold_ms: float = 0.0            # 阈值模式：TTFT 阈值（0 = 不判定）
    tpot_threshold_ms: float = 100.0          # 阈值模式：TPOT 阈值（0 = 不判定）
    output_throughput_threshold: float = 0.0  # 阈值模式：输出吞吐阈值（0 = 不判定）


# ---------------------------------------------------------------------------
# ① 负载生成：构造 prompt
# ---------------------------------------------------------------------------


def build_prompt(input_len: int, chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
                 rng: Optional[random.Random] = None) -> str:
    """按目标输入 token 数构造 prompt（近似：chars_per_token 字符 ≈ 1 token）。"""
    target_chars = max(1, int(input_len * chars_per_token))
    r = rng or random.Random()
    words: list[str] = []
    total = 0
    while total < target_chars:
        w = r.choice(_FILLER_WORDS)
        words.append(w)
        total += len(w) + 1
    return " ".join(words)[:target_chars]


# ---------------------------------------------------------------------------
# ② 请求执行：SSE 流式 + 时间线采集
# ---------------------------------------------------------------------------


def _endpoint_url(opts: BuiltinOptions) -> str:
    base = opts.base_url.rstrip("/")
    ep = opts.endpoint if opts.endpoint.startswith("/") else "/" + opts.endpoint
    if ep in ("/v1/chat/completions", "/v1/completions"):
        return base + ep
    return base + ep


async def _request_once(
    session,
    opts: BuiltinOptions,
    prompt: str,
    t_start: float,
    semaphore: asyncio.Semaphore,
    stop_event: asyncio.Event,
) -> RequestRecord:
    """执行一次流式请求并采集时间线（相对 t_start 的秒）。"""
    is_chat = opts.endpoint.endswith("chat/completions")
    if is_chat:
        body: dict[str, Any] = {
            "model": opts.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": int(opts.dataset.get("output_len") or 128),
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": 0.0,
        }
    else:
        body = {
            "model": opts.model,
            "prompt": prompt,
            "max_tokens": int(opts.dataset.get("output_len") or 128),
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": 0.0,
        }
    body.update(opts.extra_body or {})

    headers = {"Content-Type": "application/json"}
    if opts.api_key:
        headers["Authorization"] = f"Bearer {opts.api_key}"
    headers.update(opts.extra_headers or {})

    t0 = time.perf_counter() - t_start
    rec = RequestRecord(ok=False, start=t0)

    async with semaphore:
        if stop_event.is_set():
            rec.error = "stopped"
            return rec
        try:
            timeout = aiohttp.ClientTimeout(total=opts.timeout)
            async with session.post(_endpoint_url(opts), json=body, headers=headers, timeout=timeout) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    rec.error = f"HTTP {resp.status}: {text[:200]}"
                    rec.server_error = True
                    rec.end = time.perf_counter() - t_start
                    return rec

                prev: Optional[float] = None
                chunks = 0
                async for raw in resp.content:
                    if stop_event.is_set():
                        rec.error = "stopped"
                        return rec
                    line = raw.decode("utf-8", "replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        payload = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    now = time.perf_counter() - t_start

                    # usage 块（stream_options.include_usage）：只有 usage 没有 choices
                    usage = payload.get("usage")
                    if usage and not payload.get("choices"):
                        rec.completion_tokens = int(usage.get("completion_tokens") or 0)
                        rec.prompt_tokens = int(usage.get("prompt_tokens") or 0)
                        continue

                    choices = payload.get("choices") or []
                    if not choices:
                        continue
                    ch = choices[0] if isinstance(choices[0], dict) else {}
                    delta = ch.get("delta") if is_chat else ch
                    if not isinstance(delta, dict):
                        delta = {}
                    text_piece = delta.get("content") or delta.get("reasoning_content") or delta.get("text") or ""
                    if not text_piece:
                        continue

                    chunks += 1
                    if rec.first_token is None:
                        rec.first_token = now
                    else:
                        assert prev is not None
                        rec.itls.append((now - prev) * 1000.0)
                    prev = now

                    # 逐 chunk 产出 token 时间序列（peak output 滑窗）：优先 usage 增量，否则文本长度/4 估算
                    chunk_tokens = max(1, int(len(text_piece) / 4))
                    if usage:
                        cur_compl = int(usage.get("completion_tokens") or 0)
                        if cur_compl > rec.completion_tokens:
                            chunk_tokens = cur_compl - rec.completion_tokens
                        rec.completion_tokens = cur_compl
                        rec.prompt_tokens = int(usage.get("prompt_tokens") or 0)
                    rec.output_events.append((now, chunk_tokens))

                rec.end = time.perf_counter() - t_start
                rec.ok = True
                # 服务端未提供 usage → 回退按 chunk 数估算输出 token
                if rec.completion_tokens <= 0:
                    rec.completion_tokens = chunks
                if rec.prompt_tokens <= 0:
                    rec.prompt_tokens = max(1, int(len(prompt) / max(opts.chars_per_token, 0.1)))
                return rec
        except asyncio.CancelledError:
            rec.error = "cancelled"
            return rec
        except Exception as e:  # noqa: BLE001 - 单请求异常不影响整体
            rec.error = f"{type(e).__name__}: {e}"[:300]
            rec.end = time.perf_counter() - t_start
            return rec


# ---------------------------------------------------------------------------
# ③ 指标计算（口径对齐 vLLM bench）
# ---------------------------------------------------------------------------


def _percentile(values: list[float], pct: float) -> float:
    """最近秩分位数（nearest-rank，pct 取 0-100）。

    样本数 < 2 时直接返回唯一值（statistics.quantiles 会抛错）。
    采用最近秩而非插值，与 numpy/vLLM 的 percentile 语义一致。
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = max(1, int(round((pct / 100.0) * len(ordered))))
    return float(ordered[min(rank, len(ordered)) - 1])


def _stats(values: list[float]) -> dict:
    """mean / median / p99 三元组。"""
    if not values:
        return {"mean": 0.0, "median": 0.0, "p99": 0.0}
    return {
        "mean": float(statistics.fmean(values)),
        "median": float(statistics.median(values)),
        "p99": _percentile(values, 99),
    }


def compute_metrics(records: list[RequestRecord], duration: float, concurrency: int) -> dict:
    """由请求记录计算指标（口径对齐 vLLM bench）。

    返回结构与 `benchscope.parser.parse_metrics` 兼容：
    output_mean / total_mean / req_per_s / ttft_{mean,median,p99} /
    tpot_{mean,median,p99} / itl_{mean,median,p99} / successful_requests / ...
    """
    oks = [r for r in records if r.ok and r.first_token is not None and r.end is not None]
    failed = len(records) - len(oks)
    duration = max(duration, 1e-9)

    ttft = [(r.first_token - r.start) * 1000.0 for r in oks]
    e2e = [(r.end - r.start) * 1000.0 for r in oks]
    # TPOT = (E2E - TTFT) / (completion_tokens - 1)，与 vLLM bench 一致
    tpot: list[float] = []
    for r in oks:
        n = max(int(r.completion_tokens or 0), 1)
        denom = max(n - 1, 1)
        tpot.append((((r.end - r.first_token) * 1000.0) / denom) if n > 1 else 0.0)
    itl = [v for r in oks for v in r.itls]

    total_completion = sum(int(r.completion_tokens or 0) for r in oks)
    total_prompt = sum(int(r.prompt_tokens or 0) for r in oks)

    ttft_s, tpot_s, itl_s = _stats(ttft), _stats(tpot), _stats(itl)
    e2e_s = _stats(e2e)

    metrics = {
        "concurrency": concurrency,
        "successful_requests": len(oks),
        "failed_requests": failed,
        "benchmark_duration": round(duration, 4),
        "total_input_tokens": total_prompt,
        "total_generated_tokens": total_completion,
        # 吞吐（tok/s）
        "output_mean": round(total_completion / duration, 4),
        "total_mean": round((total_prompt + total_completion) / duration, 4),
        # 请求吞吐（req/s）
        "req_per_s": round(len(oks) / duration, 4),
        # 延迟（ms）
        "ttft_mean": round(ttft_s["mean"], 4),
        "ttft_median": round(ttft_s["median"], 4),
        "ttft_p99": round(ttft_s["p99"], 4),
        "tpot_mean": round(tpot_s["mean"], 4),
        "tpot_median": round(tpot_s["median"], 4),
        "tpot_p99": round(tpot_s["p99"], 4),
        "itl_mean": round(itl_s["mean"], 4),
        "itl_median": round(itl_s["median"], 4),
        "itl_p99": round(itl_s["p99"], 4),
        "e2e_mean": round(e2e_s["mean"], 4),
        "e2e_median": round(e2e_s["median"], 4),
        "e2e_p99": round(e2e_s["p99"], 4),
    }
    # peak output throughput：并发窗口内的峰值吞吐（按请求完成时间滑窗估算）
    metrics["peakoutput_mean"] = _peak_output_throughput(oks, duration)
    # 单用户 QPS = 1000 / tpot_mean（与 parser.py 一致）
    if metrics["tpot_mean"] > 0:
        metrics["single_user"] = round(1000.0 / metrics["tpot_mean"], 2)
    return metrics


def _peak_output_throughput(oks: list[RequestRecord], duration: float) -> float:
    """峰值输出吞吐（vLLM 语义）：1 秒滑窗内**实际产出**的最大 token 数。

    与 vLLM 一致：基于每个输出 token / chunk 的**产出时刻**做滑动窗口统计，
    反映窗口内真实产出速率（而非在请求结束时刻一次性记入整段 token）。
    回退：请求无逐 chunk 产出记录时，用请求完成时刻整段 token 估算。
    """
    if not oks or duration <= 0:
        return 0.0
    window = 1.0
    # 逐 chunk 产出事件（含跨请求）：(t, tokens)
    events = sorted(
        (t, max(int(tok), 0)) for r in oks if r.end is not None for t, tok in (r.output_events or [])
    )
    if not events:
        # 回退：按请求完成时刻整段 token（旧口径）
        events = sorted((r.end, int(r.completion_tokens or 0)) for r in oks if r.end is not None)
    best = 0
    j = 0
    prefix = [0]
    for _, tok in events:
        prefix.append(prefix[-1] + tok)
    for i, (t, _) in enumerate(events):
        while j < len(events) and events[j][0] - t <= window:
            j += 1
        best = max(best, prefix[j] - prefix[i])
    return round(float(best) / window, 4)


# ---------------------------------------------------------------------------
# 主入口：执行一轮 bench（并发模型 + 总量控制 + 速率控制）
# ---------------------------------------------------------------------------


async def _run_async(
    opts: BuiltinOptions,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    stop_event: Optional[asyncio.Event] = None,
) -> tuple[list[RequestRecord], float]:
    """异步执行一轮：concurrency 个 worker 持续发请求直到完成 num_prompts。"""
    stop_event = stop_event or asyncio.Event()
    rng = random.Random(opts.seed if opts.seed is not None else None)
    input_len = int(opts.dataset.get("input_len") or 1024)
    num_prompts = int(opts.num_prompts or opts.concurrency)
    concurrency = max(1, int(opts.concurrency))

    # 预热请求不计入指标
    warmups = max(0, int(opts.warmups or 0))

    connector = aiohttp.TCPConnector(limit=0, limit_per_host=0, ssl=False)
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=60, sock_read=opts.timeout)
    records: list[RequestRecord] = []

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        t_start = time.perf_counter()

        # ---- 预热 ----
        if warmups:
            sem = asyncio.Semaphore(concurrency)
            tasks = [
                _request_once(session, opts, build_prompt(input_len, opts.chars_per_token, rng), t_start, sem, stop_event)
                for _ in range(warmups)
            ]
            await asyncio.gather(*tasks)

        # ---- 正式压测 ----
        t_start = time.perf_counter()
        sem = asyncio.Semaphore(concurrency)
        counter = {"done": 0}
        lock = asyncio.Lock()

        async def worker():
            while True:
                if stop_event.is_set():
                    return
                async with lock:
                    if counter["done"] >= num_prompts:
                        return
                    counter["done"] += 1
                    idx = counter["done"]
                rec = await _request_once(
                    session, opts, build_prompt(input_len, opts.chars_per_token, rng), t_start, sem, stop_event
                )
                if rec.error == "stopped":
                    async with lock:
                        counter["done"] = idx - 1
                    return
                records.append(rec)
                if progress_cb:
                    progress_cb(len(records), num_prompts)
                # 速率控制：非 inf 时按泊松到达间隔休眠
                rate = opts.request_rate
                if rate and rate != float("inf") and rate > 0:
                    await asyncio.sleep(rng.expovariate(rate) / concurrency)

        workers = [asyncio.create_task(worker()) for _ in range(concurrency)]
        await asyncio.gather(*workers)
        duration = time.perf_counter() - t_start

    return records, duration


def run_builtin_bench(
    opts: BuiltinOptions,
    stream_cb: Optional[Callable[[str], None]] = None,
    stop_flag=None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> dict:
    """同步入口：执行自研 bench 并返回与 parse_metrics 兼容的指标字典。

    stop_flag：threading.Event（来自 BenchRunner），设置后中断执行并抛 StopRequested。
    stream_cb：输出行回调（用于终端日志与前端 Console 展示）。
    """
    import threading

    from benchscope.benches.runner import StopRequested

    def emit(line: str):
        if stream_cb:
            stream_cb(line)

    emit(f"$ benchscope perf --backend={opts.backend} --base-url={opts.base_url} "
         f"--model={opts.model} --concurrency={opts.concurrency} --num-prompts={opts.num_prompts or opts.concurrency}\n")

    loop = asyncio.new_event_loop()
    stop_event = asyncio.Event()
    result: dict = {"records": [], "duration": 0.0, "error": ""}

    try:
        asyncio.set_event_loop(loop)

        # 桥接 threading.Event（停止信号）→ asyncio.Event
        poll_task = None
        if stop_flag is not None:
            async def _poll_stop():
                while not stop_event.is_set():
                    if stop_flag.is_set():
                        stop_event.set()
                        return
                    await asyncio.sleep(0.1)

            poll_task = loop.create_task(_poll_stop())

        def _progress(done: int, total: int):
            emit(f"  progress: {done}/{total}\n")

        cb = progress_cb or _progress
        records, duration = loop.run_until_complete(_run_async(opts, cb, stop_event))
        result["records"], result["duration"] = records, duration
    except Exception as e:  # noqa: BLE001
        result["error"] = f"{type(e).__name__}: {e}"
        log.exception("自研 bench 执行失败")
    finally:
        try:
            loop.close()
        except Exception:
            pass
        asyncio.set_event_loop(None)

    if result["error"]:
        raise RuntimeError(f"自研 bench 执行失败：{result['error']}")

    records = result["records"]
    if stop_flag is not None and stop_flag.is_set() and not records:
        raise StopRequested("测试已被停止")

    if not records:
        raise RuntimeError("自研 bench 未采集到任何请求结果")

    metrics = compute_metrics(records, result["duration"], opts.concurrency)
    # 全部请求失败：视为执行失败（避免返回全 0 指标被误判为测试成功）
    if metrics.get("successful_requests", 0) <= 0:
        first_err = next((r.error for r in records if r.error), "未知错误")
        raise RuntimeError(
            f"自研 bench 执行失败：{len(records)} 个请求全部失败"
            f"（如 {first_err}）。请检查推理服务地址、模型名与网络连通性。"
        )
    metrics["raw"] = _format_output(opts, metrics)
    emit(metrics["raw"])
    return metrics


def _format_output(opts: BuiltinOptions, metrics: dict) -> str:
    """格式化为 vLLM bench 风格输出（便于日志查看与人工比对）。"""
    lines = [
        "============ Serving Benchmark Result (benchscope builtin) ============",
        f"Backend:                                 {opts.backend}",
        f"Model:                                   {opts.model}",
        f"Base URL:                                {opts.base_url}",
        f"Successful requests:                     {metrics['successful_requests']}",
        f"Failed requests:                         {metrics['failed_requests']}",
        f"Maximum request concurrency:             {metrics['concurrency']}",
        f"Benchmark duration (s):                  {metrics['benchmark_duration']:.2f}",
        f"Total input tokens:                      {metrics['total_input_tokens']}",
        f"Total generated tokens:                  {metrics['total_generated_tokens']}",
        f"Request throughput (req/s):              {metrics['req_per_s']:.2f}",
        f"Output token throughput (tok/s):         {metrics['output_mean']:.2f}",
        f"Peak output token throughput (tok/s):    {metrics.get('peakoutput_mean', 0):.2f}",
        f"Total token throughput (tok/s):          {metrics['total_mean']:.2f}",
        "-------------------- Time to First Token --------------------",
        f"Mean TTFT (ms):                          {metrics['ttft_mean']:.2f}",
        f"Median TTFT (ms):                        {metrics['ttft_median']:.2f}",
        f"P99 TTFT (ms):                           {metrics['ttft_p99']:.2f}",
        "-------------------- Time per Output Token --------------------",
        f"Mean TPOT (ms):                          {metrics['tpot_mean']:.2f}",
        f"Median TPOT (ms):                        {metrics['tpot_median']:.2f}",
        f"P99 TPOT (ms):                           {metrics['tpot_p99']:.2f}",
        "-------------------- Inter-token Latency --------------------",
        f"Mean ITL (ms):                           {metrics['itl_mean']:.2f}",
        f"Median ITL (ms):                         {metrics['itl_median']:.2f}",
        f"P99 ITL (ms):                            {metrics['itl_p99']:.2f}",
        "==============================================================",
    ]
    return "\n".join(lines) + "\n"

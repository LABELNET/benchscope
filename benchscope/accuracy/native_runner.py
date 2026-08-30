"""Native 推理运行器：transformers 本地加载模型权重推理（kind=native 引擎执行实现）。

- 依赖策略：torch / transformers / peft 为可选依赖（extras `benchscope[accuracy-native]`），
  未安装时抛出明确 RuntimeError（不污染平台必装依赖）。
- 模型：本地权重路径或 HF id；dtype / device_map 自动（有 CUDA 用 auto+bfloat16，否则 CPU float32）。
- LoRA 微调增量模型：`lora_path` 配置 adapter 路径，经 peft PeftModel 合并加载（微调效果验收）。
- 可复现：固定 seed（torch.manual_seed / torch.cuda.manual_seed_all）。
- 同一模型进程内缓存（多次评测复用加载结果）。
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from benchscope.accuracy.executor import InferOptions, InferResult

log = logging.getLogger("benchscope.accuracy.native_runner")

# 进程内模型缓存：{model_key: (model, tokenizer)}
_MODEL_CACHE: dict = {}


def _require_deps():
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "Native 精度评测需要 torch + transformers 环境："
            "pip install 'benchscope[accuracy-native]'"
        ) from e


def _load_model(opts: InferOptions):
    """加载（并缓存）模型与 tokenizer；配置 LoRA 时经 peft 挂载增量权重。"""
    _require_deps()
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    key = f"{opts.model}|{opts.lora_path or ''}"
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]

    device_map = "auto" if torch.cuda.is_available() else None
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    kwargs = {"trust_remote_code": True}
    if device_map:
        kwargs["device_map"] = device_map
        kwargs["torch_dtype"] = dtype

    log.info("[native] 加载模型 %s（lora=%s）", opts.model, opts.lora_path or "-")
    model = AutoModelForCausalLM.from_pretrained(opts.model, **kwargs)
    if opts.lora_path:
        try:
            from peft import PeftModel
        except ImportError as e:
            raise RuntimeError(
                "配置 LoRA 增量模型路径需要 peft：pip install 'benchscope[accuracy-native]'"
            ) from e
        model = PeftModel.from_pretrained(model, opts.lora_path)
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(
        opts.lora_path or opts.model, trust_remote_code=True
    )
    _MODEL_CACHE[key] = (model, tokenizer)
    return model, tokenizer


def generate_native(opts: InferOptions,
                    message_tasks: list[tuple[int, list[dict], str]],
                    stop_flag=None,
                    progress_cb: Optional[Callable[[int, int], None]] = None) -> list[InferResult]:
    """批量本地推理：chat 模板（对话模型）/ 原始 prompt（补全模型）+ generate。"""
    _require_deps()
    import torch

    model, tokenizer = _load_model(opts)
    device = next(model.parameters()).device
    if opts.seed:
        torch.manual_seed(opts.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(opts.seed)

    total = len(message_tasks)
    results: list[InferResult] = []
    for i, (index, messages, prompt) in enumerate(message_tasks):
        if stop_flag is not None and stop_flag.is_set():
            results.append(InferResult(index=index, error="stopped"))
            continue
        try:
            if getattr(tokenizer, "chat_template", None) and messages and messages[0].get("role") == "user":
                text = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True)
            else:
                text = prompt
            inputs = tokenizer(text, return_tensors="pt").to(device)
            generate_kwargs = {
                "max_new_tokens": int(opts.max_tokens),
                "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
            }
            if opts.temperature and opts.temperature > 0:
                generate_kwargs.update({"do_sample": True, "temperature": opts.temperature,
                                        "top_p": opts.top_p})
            else:
                generate_kwargs["do_sample"] = False
            t0 = time.perf_counter()
            with torch.no_grad():
                out_ids = model.generate(**inputs, **generate_kwargs)
            new_ids = out_ids[0][inputs["input_ids"].shape[1]:]
            output = tokenizer.decode(new_ids, skip_special_tokens=True)
            latency = (time.perf_counter() - t0) * 1000
            results.append(InferResult(
                index=index,
                output=output,
                prompt_tokens=int(inputs["input_ids"].shape[1]),
                completion_tokens=int(new_ids.shape[0]),
                latency_ms=latency,
            ))
        except Exception as e:  # noqa: BLE001
            log.exception("Native 推理失败（index=%s）", index)
            results.append(InferResult(index=index, error=f"{type(e).__name__}: {e}"[:300]))
        if progress_cb:
            progress_cb(i + 1, total)
    return results


def unload_cache() -> None:
    """清空模型缓存（释放显存）。"""
    _MODEL_CACHE.clear()

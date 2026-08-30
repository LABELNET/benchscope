"""精度引擎适配：从 bench 引擎注册表（configs/benchs.yaml）过滤 eval 引擎。

引擎条目通过 `eval` 能力字段声明精度评测能力：
  - benchscope: eval: serving（Serving 链路精度，OpenAI 兼容 API）
  - native-hf : eval: native （Native 原生精度，transformers 本地权重）
  - mock      : eval: mock   （mock 伪输出，联调与测试）

引擎注册表属 1.0.7 引擎抽象的公共基础设施；本模块只做精度侧的过滤与
环境校验适配（native 追加 CUDA 检测），不复制注册表逻辑。
"""
from __future__ import annotations

import logging
from typing import Optional

from benchscope.benchs import check_env, engine_summary, get_engine, load_bench_engines

log = logging.getLogger("benchscope.accuracy.engines")

EVAL_CAPABILITIES = ("serving", "native", "mock")


def eval_capability(engine: dict) -> str:
    """引擎的精度评测能力：serving | native | mock（无 eval 字段 = 不支持）。"""
    value = (engine.get("eval") or "").strip().lower()
    return value if value in EVAL_CAPABILITIES else ""


def list_eval_engines(with_env: bool = True) -> list[dict]:
    """具备精度评测能力的引擎清单（含 eval 能力字段）。"""
    out = []
    for engine in load_bench_engines():
        capability = eval_capability(engine)
        if not capability:
            continue
        summary = engine_summary(engine, with_env)
        summary["eval"] = capability
        out.append(summary)
    return out


def get_eval_engine(engine_id: str) -> Optional[dict]:
    """按 id 获取 eval 引擎（不支持精度评测的引擎返回 None）。"""
    engine = get_engine(engine_id)
    if not engine or not eval_capability(engine):
        return None
    return engine


def default_eval_engine_id() -> str:
    """默认精度引擎：优先 serving（benchscope），否则第一个 eval 引擎。"""
    engines = list_eval_engines(with_env=False)
    for engine in engines:
        if engine.get("eval") == "serving":
            return engine["id"]
    return engines[0]["id"] if engines else "benchscope"


def _cuda_available() -> bool:
    """torch.cuda.is_available()，torch 未安装返回 False。"""
    try:
        import torch  # type: ignore

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def check_eval_env(engine_id: str) -> dict:
    """精度引擎环境校验：通用 requires 校验 + native 追加 CUDA 检测。

    返回 {engine_id, eval, ok, checks: [{name, required, installed, ok, hint}]}。
    """
    engine = get_eval_engine(engine_id)
    if not engine:
        raise KeyError(f"精度评测引擎不存在或不支持精度评测: {engine_id}")

    result = check_env(engine)
    result["engine_id"] = engine_id
    result["eval"] = eval_capability(engine)

    if result["eval"] == "native":
        cuda_ok = _cuda_available()
        result["checks"].append({
            "name": "cuda",
            "required": "CUDA 可用",
            "installed": "可用" if cuda_ok else "不可用",
            "ok": cuda_ok,
            "hint": "" if cuda_ok else "未检测到可用 CUDA 设备（torch.cuda.is_available()=False），Native 精度评测需要 GPU",
        })
        if not cuda_ok:
            result["ok"] = False
    return result

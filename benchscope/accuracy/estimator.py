"""Token 消耗预估（Serving 链路精度评测前置提醒 + 任务结束偏差对比）。

预估优先级：
  1. 数据集实测统计（datasets_dir 缓存的实测 prompt token 均值，来自历史任务 / stats 探测）
  2. 内置常量表（configs/token_estimates.yaml，需求附件固化的工业界通用均值）
  3. 自定义数据集字符估算（chars/4 近似 token，与自研 bench 的 chars-per-token 语义一致）

输出：{prompt_tokens, completion_tokens, total_tokens, est_seconds, source}；
耗时估算按 12 tok/s 单流保守输出速率近似（仅作提醒参考，不计入任何性能指标口径）。
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

log = logging.getLogger("benchscope.accuracy.estimator")

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"
ESTIMATES_YAML = CONFIGS_DIR / "token_estimates.yaml"

# 保守输出速率（tok/s）：仅用于「预估耗时」提醒，非性能指标
AVG_OUTPUT_TOKENS_PER_SECOND = 12.0
# 字符 / token 近似比（自定义数据集兜底估算）
CHARS_PER_TOKEN = 4.0

_SOURCE_LABELS = {
    "measured": "数据集实测统计",
    "builtin": "内置常量表",
    "chars": "字符估算（自定义数据集）",
}


def load_builtin_estimates() -> dict:
    try:
        data = yaml.safe_load(ESTIMATES_YAML.read_text(encoding="utf-8")) or {}
        return data.get("estimates") or {}
    except Exception:
        log.exception("读取 token_estimates.yaml 失败")
        return {}


def _measured_avg(cfg, dataset_ref: dict) -> dict | None:
    """数据集实测统计（dataset_stats 的 prompt 字符均值 → token 近似 + 常量输出均值）。"""
    try:
        from benchscope.accuracy.datasets import dataset_stats

        stats = dataset_stats(cfg, dataset_ref)
    except Exception:
        return None
    if not stats.get("avg_prompt_chars"):
        return None
    return {
        "prompt_tokens": max(1, round(stats["avg_prompt_chars"] / CHARS_PER_TOKEN)),
        "completion_tokens": None,  # 实测仅覆盖输入侧；输出侧回退常量 / 默认
        "total": stats.get("total") or 0,
    }


def estimate(cfg, dataset_ref: dict, limit: int = 0, mode: str = "serving",
             max_tokens: int = 512) -> dict:
    """预估一次评测的 Token 开销（mode=native 恒为 0：无线上链路消耗）。"""
    total_samples = 0
    declared = 0
    if mode != "serving":
        return {
            "mode": mode, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
            "est_seconds": 0.0, "source": "native", "source_label": "Native 模式无 Token 消耗",
            "total_samples": 0,
        }

    dataset_id = str((dataset_ref or {}).get("id") or "")
    is_custom = bool((dataset_ref or {}).get("path")) or dataset_id.startswith("custom")

    prompt_avg = None
    completion_avg = None
    source = "builtin"

    # ① 实测统计（仅非自定义数据集；自定义数据集样本可直接读取，见 ③）
    measured = None
    if not is_custom:
        measured = _measured_avg(cfg, dataset_ref)
    if measured:
        prompt_avg = measured["prompt_tokens"]
        source = "measured"

    # ② 内置常量表
    if prompt_avg is None:
        builtin = load_builtin_estimates().get(dataset_id) or {}
        if builtin:
            prompt_avg = int(builtin.get("prompt_tokens") or 0) or None
            completion_avg = int(builtin.get("completion_tokens") or 0) or None
            declared = int(builtin.get("total_samples") or 0)

    # ③ 自定义 / 无常量数据集：直接统计样本字符均值做字符估算
    total_samples = 0
    if prompt_avg is None or is_custom:
        try:
            from benchscope.accuracy.datasets import dataset_stats, resolve_dataset

            stats = dataset_stats(cfg, dataset_ref)
            total_samples = stats.get("total") or 0
            if stats.get("avg_prompt_chars"):
                prompt_avg = max(1, round(stats["avg_prompt_chars"] / CHARS_PER_TOKEN))
                source = "chars"
            elif prompt_avg is None:
                prompt_avg = 256  # 空数据集兜底
        except Exception:
            if prompt_avg is None:
                prompt_avg = 256

    if not total_samples:
        try:
            from benchscope.accuracy.datasets import resolve_dataset, standardize_samples, filter_samples

            _, path = resolve_dataset(cfg, dataset_ref)
            meta_holder = {"id": dataset_id, "name": dataset_id, "eval": {"scorer": "math"}, "source": "custom", "path": str(path)}
            total_samples = len(filter_samples(meta_holder, standardize_samples(meta_holder, path)))
        except Exception:
            total_samples = declared or 0

    # 输出侧：实测无输出统计 → 常量表 → max_tokens/2 兜底
    if completion_avg is None:
        builtin = load_builtin_estimates().get(dataset_id) or {}
        completion_avg = int(builtin.get("completion_tokens") or 0) or max(8, min(max_tokens // 2, 256))

    n = int(limit or 0) or (total_samples or declared or 0)
    prompt_total = int(prompt_avg or 0) * n
    completion_total = int(completion_avg or 0) * n
    return {
        "mode": mode,
        "total_samples": n,
        "prompt_tokens": prompt_total,
        "completion_tokens": completion_total,
        "total_tokens": prompt_total + completion_total,
        "est_seconds": round(completion_total / AVG_OUTPUT_TOKENS_PER_SECOND, 1) if n else 0.0,
        "source": source,
        "source_label": _SOURCE_LABELS.get(source, source),
        "declared_total": declared,
    }


def estimate_vs_actual(estimate: dict | None, result: dict | None) -> dict | None:
    """任务结束：预估 vs 实际消耗对比（偏差百分比 = (实际 - 预估) / 预估）。"""
    if not estimate or not result:
        return None
    tokens = (result or {}).get("tokens") or None
    if not tokens:
        return None

    def _dev(est, act):
        if not est:
            return None
        return round(((act or 0) - est) / est * 100.0, 2)

    return {
        "estimate_total": estimate.get("total_tokens") or 0,
        "actual_total": tokens.get("total_tokens") or 0,
        "deviation_pct": _dev(estimate.get("total_tokens"), tokens.get("total_tokens")),
        "estimate_prompt": estimate.get("prompt_tokens") or 0,
        "actual_prompt": tokens.get("prompt_tokens_total") or 0,
        "prompt_deviation_pct": _dev(estimate.get("prompt_tokens"), tokens.get("prompt_tokens_total")),
        "estimate_completion": estimate.get("completion_tokens") or 0,
        "actual_completion": tokens.get("completion_tokens_total") or 0,
        "completion_deviation_pct": _dev(estimate.get("completion_tokens"), tokens.get("completion_tokens_total")),
    }

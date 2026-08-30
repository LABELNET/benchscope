"""开源模型基准对标（平台核心新增能力）。

每次评测结束后自动横向对标内置基线池（configs/baselines.yaml，静态固化公开测评
分数 + 来源标注），生成：
  1. 同数据集差值百分点（当前模型 vs 最接近尺寸基线 / 最优基线）
  2. 能力档位评级 S / A / B / C（相对最优基线：≥0 → S；≥-5pp → A；≥-15pp → B；否则 C）
  3. 同尺寸段排名百分比（段内基线中被当前模型超越的比例）
  4. 能力雷达（知识 / 数学 / 代码 / 对话维度，单数据集任务取该维度得分）
  5. 自动结论：优于同尺寸开源基线 / 持平基线 / 明显劣于基线（风险预警）
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

log = logging.getLogger("benchscope.accuracy.baselines")

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"
BASELINES_YAML = CONFIGS_DIR / "baselines.yaml"

# 同尺寸段划分（B）：[0, 4) / [4, 15) / [15, 40) / [40, +∞)
_SIZE_SEGMENTS = ((0, 4), (4, 15), (15, 40), (40, float("inf")))

# 档位阈值（相对最优基线差值，百分点）
_GRADE_RULES = (
    (0.0, "S"),
    (-5.0, "A"),
    (-15.0, "B"),
)

RADAR_DIMS = ("知识", "数学", "代码", "对话")
_DIM_BY_CATEGORY = {
    "accuracy-knowledge": "知识",
    "accuracy-math": "数学",
    "accuracy-code": "代码",
    "accuracy-chat": "对话",
    "accuracy-mix": "综合",
}


def load_baselines() -> dict:
    """读取基线库（原文 + 解析结果，供 API 展示与更新）。"""
    content = BASELINES_YAML.read_text(encoding="utf-8") if BASELINES_YAML.exists() else ""
    try:
        data = yaml.safe_load(content) or {}
    except Exception:
        log.exception("解析 baselines.yaml 失败")
        data = {}
    return {
        "version": data.get("version") or "",
        "models": data.get("models") or [],
        "content": content,
    }


def save_baselines(content: str) -> dict:
    """管理员更新基线库（YAML 校验后写盘）。"""
    data = yaml.safe_load(content or "")
    if not isinstance(data, dict) or not isinstance(data.get("models"), list) or not data["models"]:
        raise ValueError("基线库必须是含非空 models 列表的对象")
    for m in data["models"]:
        if not isinstance(m, dict) or not m.get("name") or not isinstance(m.get("scores"), dict):
            raise ValueError("基线模型必须含 name 与 scores 字典")
    BASELINES_YAML.write_text(content, encoding="utf-8")
    return load_baselines()


def _segment(params_b: float) -> int:
    for i, (lo, hi) in enumerate(_SIZE_SEGMENTS):
        if lo <= params_b < hi:
            return i
    return len(_SIZE_SEGMENTS) - 1


def _grade(diff_vs_best: float) -> str:
    for threshold, grade in _GRADE_RULES:
        if diff_vs_best >= threshold:
            return grade
    return "C"


def _conclusion(diff_vs_segment: float) -> str:
    if diff_vs_segment >= 0:
        return "优于同尺寸开源基线"
    if diff_vs_segment >= -5.0:
        return "持平基线"
    return "明显劣于基线（风险预警）"


def compute_benchmark(meta: dict, result: dict) -> dict | None:
    """由数据集元数据与评测结果计算基线对标。

    返回 None 表示该数据集无任何基线分数可对标。
    """
    dataset_id = meta.get("id") or ""
    library = load_baselines()
    models = [m for m in library["models"] if isinstance(m.get("scores"), dict)]

    # 当前模型该数据集主指标（百分制）
    main_metric = (meta.get("eval") or {}).get("metrics") or "accuracy"
    score = None
    if main_metric == "accuracy":
        score = result.get("accuracy")
    elif main_metric == "exact_match":
        score = (result.get("dataset_metrics") or {}).get("exact_match")
    elif main_metric == "pass@1":
        score = (result.get("dataset_metrics") or {}).get("pass_at_1")
    elif main_metric == "mt_bench":
        score = (result.get("dataset_metrics") or {}).get("mt_bench_score")
    if score is None:
        return None

    scored = [
        {"name": m.get("name"), "params_b": float(m.get("params_b") or 0),
         "group": m.get("group") or "general", "source": m.get("source") or "",
         "score": float(m["scores"][dataset_id])}
        for m in models if dataset_id in m["scores"]
    ]
    if not scored:
        return None

    best = max(scored, key=lambda m: m["score"])
    # 尺寸最接近的基线（参数量差最小）
    nearest = min(scored, key=lambda m: abs(m["params_b"] - float(result.get("_params_b") or 0) or 0))
    current_seg = _segment(nearest["params_b"])
    segment_models = [m for m in scored if _segment(m["params_b"]) == current_seg]
    seg_best = max(segment_models, key=lambda m: m["score"])
    better_count = sum(1 for m in segment_models if score >= m["score"])

    diff_best = round(score - best["score"], 2)
    diff_nearest = round(score - nearest["score"], 2)
    diff_segment = round(score - seg_best["score"], 2)

    # 能力雷达：单数据集任务仅该维度有值（综合类全维空）
    dim = _DIM_BY_CATEGORY.get(meta.get("category") or "")
    radar = {d: None for d in RADAR_DIMS}
    if dim in radar:
        radar[dim] = round(float(score), 2)

    return {
        "dataset_id": dataset_id,
        "metric": main_metric,
        "score": round(float(score), 2),
        "baselines": scored,
        "baseline_used": {"name": nearest["name"], "score": nearest["score"], "params_b": nearest["params_b"],
                          "source": nearest["source"]},
        "diff_pp": diff_nearest,
        "diff_vs_best_pp": diff_best,
        "best_baseline": {"name": best["name"], "score": best["score"]},
        "grade": _grade(diff_best),
        "rank_pct": round(better_count / len(segment_models) * 100.0, 1) if segment_models else None,
        "segment": {"range_b": [segment_models[0]["params_b"], segment_models[-1]["params_b"]] if segment_models else [],
                    "count": len(segment_models), "best": seg_best["name"], "best_score": seg_best["score"]},
        "diff_vs_segment_pp": diff_segment,
        "radar": radar,
        "conclusion": _conclusion(diff_segment),
        "baseline_version": library.get("version") or "",
    }

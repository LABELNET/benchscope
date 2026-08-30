"""多任务对比 / Native vs Serving 训推一致性差值（P15）。

对比口径：
  - 横向对比：多任务按「模型+数据集」分组，逐指标（accuracy / exact_match / pass@1 /
    mt_bench_score）列出；
  - 一致性：同组内同时存在 native 与 serving 任务时计算逐指标差值
    （|diff| ≤ 2pp 训推一致；≤ 5pp 存在偏差；> 5pp 显著偏差）。
"""
from __future__ import annotations

CONSISTENT = "训推一致"
DEVIATED = "存在偏差"
SIGNIFICANT = "显著偏差"

# 参与对比的主指标（按数据集判分器取值）
_MAIN_METRICS = (
    ("accuracy", "accuracy"),
    ("exact_match", "dataset_metrics.exact_match"),
    ("pass@1", "dataset_metrics.pass_at_1"),
    ("mt_bench_score", "dataset_metrics.mt_bench_score"),
)


def _main_metric(result: dict | None) -> tuple[str, float | None]:
    """任务的主指标取值（按数据集判分器选择）。"""
    if not result:
        return "accuracy", None
    dm = result.get("dataset_metrics") or {}
    if dm.get("pass_at_1") is not None:
        return "pass@1", dm.get("pass_at_1")
    if dm.get("exact_match") is not None:
        return "exact_match", dm.get("exact_match")
    if dm.get("mt_bench_score") is not None:
        return "mt_bench_score", dm.get("mt_bench_score")
    return "accuracy", result.get("accuracy")


def _deviation_label(diff_pp: float) -> str:
    diff = abs(diff_pp)
    if diff <= 2.0:
        return CONSISTENT
    if diff <= 5.0:
        return DEVIATED
    return SIGNIFICANT


def compare_tasks(task_snapshots: list[dict]) -> dict:
    """对比多任务结果。

    task_snapshots：[{task_id, name, mode, model, lora_name/lora_path, dataset_id,
                      dataset_name, engine_id, result}]
    返回 {items, groups}：items 为任务主指标表，groups 按「模型+数据集」分组，
    组内含 native vs serving 一致性差值。
    """
    items = []
    for t in task_snapshots:
        result = t.get("result") or {}
        metric_name, metric_value = _main_metric(result)
        items.append({
            "task_id": t.get("task_id"),
            "name": t.get("name") or t.get("task_id"),
            "mode": t.get("mode"),
            "engine_id": t.get("engine_id"),
            "model": t.get("model"),
            "lora_name": t.get("lora_name") or "",
            "lora_path": t.get("lora_path") or "",
            "dataset_id": t.get("dataset_id"),
            "dataset_name": t.get("dataset_name"),
            "status": t.get("status"),
            "metric": metric_name,
            "metric_value": metric_value,
            "total_samples": result.get("total_samples"),
            "correct_samples": result.get("correct_samples"),
            "invalid_samples": result.get("invalid_samples"),
            "pass_rate": result.get("pass_rate"),
            "conclusion": result.get("conclusion"),
        })

    # 按「模型 + 数据集」分组，组内做模式对比
    groups: dict[str, list[dict]] = {}
    for item in items:
        key = f"{item.get('model')}|{item.get('lora_path') or ''}|{item.get('dataset_id')}"
        groups.setdefault(key, []).append(item)

    group_outputs = []
    for key, members in groups.items():
        native = next((m for m in members if m.get("mode") == "native"), None)
        serving = next((m for m in members if m.get("mode") == "serving"), None)
        consistency = None
        if native and serving and native.get("metric_value") is not None and serving.get("metric_value") is not None:
            diff = round(float(native["metric_value"]) - float(serving["metric_value"]), 2)
            consistency = {
                "native_task_id": native["task_id"],
                "serving_task_id": serving["task_id"],
                "metric": native["metric"],
                "native_value": native["metric_value"],
                "serving_value": serving["metric_value"],
                "diff_pp": diff,
                "conclusion": _deviation_label(diff),
            }
        group_outputs.append({
            "key": key,
            "model": members[0].get("model"),
            "lora_path": members[0].get("lora_path") or "",
            "dataset_id": members[0].get("dataset_id"),
            "tasks": [m["task_id"] for m in members],
            "items": members,
            "consistency": consistency,
        })

    group_outputs.sort(key=lambda g: g["key"])
    return {"items": items, "groups": group_outputs}

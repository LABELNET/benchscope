"""精度指标汇总：样本计数 / accuracy / pass_rate / 分学科 / Token 统计 / 数据集专属指标 / 结论。

口径（需求附件）：
  - accuracy          = correct_samples / total_samples（核心主指标）
  - pass_rate         = (total - invalid) / total（有效可解析样本占比）
  - tokens（Serving） = prompt_tokens_total / completion_tokens_total / total_tokens /
                        avg_prompt_tokens_per_sample / avg_completion_tokens_per_sample
  - 数据集专属         exact_match / math_accuracy（数学）；pass@1 / compile_rate / case_pass_rate（代码）；
                       mt_bench_score 首轮 / 二轮 / 分项（对话）
结论规则：invalid 占比 > 0.2 或 total = 0 → 异常；基线主指标差值 < -5pp → 精度下跌；否则 → 合格。
"""
from __future__ import annotations

CONCLUSION_OK = "合格"
CONCLUSION_DROP = "精度下跌"
CONCLUSION_ABNORMAL = "异常"

# 数据集类别 → 能力雷达维度
RADAR_DIMENSIONS = {
    "accuracy-knowledge": "知识",
    "accuracy-math": "数学",
    "accuracy-code": "代码",
    "accuracy-chat": "对话",
    "accuracy-mix": "综合",
}


def _pct(v: float) -> float:
    return round(v * 100.0, 2)


def aggregate(meta: dict, results: list[dict], mode: str) -> dict:
    """由逐样本判分结果汇总精度指标。

    results：[{status, error_tag, tokens{prompt,completion}, latency_ms, subject,
               dataset_metrics: {...}（可选，代码/对话类逐样本补充）}]
    """
    total = len(results)
    correct = sum(1 for r in results if r.get("status") == "correct")
    wrong = sum(1 for r in results if r.get("status") == "wrong")
    invalid = sum(1 for r in results if r.get("status") == "invalid")

    out: dict = {
        "total_samples": total,
        "correct_samples": correct,
        "wrong_samples": wrong,
        "invalid_samples": invalid,
        "accuracy": _pct(correct / total) if total else 0.0,
        "pass_rate": _pct((total - invalid) / total) if total else 0.0,
        "subjects": _subjects(results),
        "dataset_metrics": _dataset_metrics(meta, results),
        "error_tag_summary": _tag_summary(results),
    }

    if mode == "serving":
        prompt_tokens = [int((r.get("tokens") or {}).get("prompt_tokens") or 0) for r in results]
        completion_tokens = [int((r.get("tokens") or {}).get("completion_tokens") or 0) for r in results]
        pt, ct = sum(prompt_tokens), sum(completion_tokens)
        out["tokens"] = {
            "prompt_tokens_total": pt,
            "completion_tokens_total": ct,
            "total_tokens": pt + ct,
            "avg_prompt_tokens_per_sample": round(pt / total, 1) if total else 0.0,
            "avg_completion_tokens_per_sample": round(ct / total, 1) if total else 0.0,
        }
    else:
        out["tokens"] = None  # Native 模式无 Token 统计（能力边界）
    return out


def _subjects(results: list[dict]) -> list[dict]:
    """分学科准确率（subject 为空的样本不参与）。"""
    by: dict[str, dict] = {}
    for r in results:
        subject = str(r.get("subject") or "").strip()
        if not subject:
            continue
        stat = by.setdefault(subject, {"subject": subject, "total": 0, "correct": 0})
        stat["total"] += 1
        if r.get("status") == "correct":
            stat["correct"] += 1
    for stat in by.values():
        stat["accuracy"] = _pct(stat["correct"] / stat["total"]) if stat["total"] else 0.0
    return sorted(by.values(), key=lambda x: x["subject"])


def _tag_summary(results: list[dict]) -> dict:
    """错因标签分布（错误样本归因）。"""
    summary: dict[str, int] = {}
    for r in results:
        tag = r.get("error_tag") or ""
        if tag:
            summary[tag] = summary.get(tag, 0) + 1
    return summary


def _dataset_metrics(meta: dict, results: list[dict]) -> dict:
    """数据集专属指标（按判分器类型汇总）。"""
    scorer = (meta.get("eval") or {}).get("scorer") or "choice"
    total = len(results)
    out: dict = {}

    if scorer == "math":
        matched = [r for r in results if r.get("dataset_metrics", {}).get("exact_match") is not None]
        em = sum(1 for r in results if r.get("dataset_metrics", {}).get("exact_match") is True)
        out["exact_match"] = _pct(em / total) if total else 0.0
        out["math_accuracy"] = out["exact_match"]
        parsed = sum(1 for r in results if r.get("status") != "invalid")
        out["answer_parse_rate"] = _pct(parsed / total) if total else 0.0

    elif scorer == "code":
        passed = sum(1 for r in results if r.get("status") == "correct")
        compiled = sum(1 for r in results if r.get("dataset_metrics", {}).get("compiled"))
        case_total, case_passed = 0, 0
        for r in results:
            dm = r.get("dataset_metrics") or {}
            case_total += int(dm.get("cases_total") or 0)
            case_passed += int(dm.get("cases_passed") or 0)
        out["pass_at_1"] = _pct(passed / total) if total else 0.0
        out["compile_rate"] = _pct(compiled / total) if total else 0.0
        out["case_pass_rate"] = _pct(case_passed / case_total) if case_total else None

    elif scorer == "judge":
        first = [r["dataset_metrics"]["first_turn"] for r in results
                 if (r.get("dataset_metrics") or {}).get("first_turn") is not None]
        second = [r["dataset_metrics"]["second_turn"] for r in results
                  if (r.get("dataset_metrics") or {}).get("second_turn") is not None]
        dims = ("helpfulness", "truthfulness", "harmlessness")
        out["mt_bench_score"] = round(
            (sum(first) / len(first) if first else 0.0) * 0.5
            + (sum(second) / len(second) if second else 0.0) * 0.5, 2)
        out["first_turn_score"] = round(sum(first) / len(first), 2) if first else None
        out["second_turn_score"] = round(sum(second) / len(second), 2) if second else None
        for dim in dims:
            vals = [r["dataset_metrics"]["dimensions"][dim] for r in results
                    if (r.get("dataset_metrics") or {}).get("dimensions", {}).get(dim) is not None]
            out[f"dim_{dim}"] = round(sum(vals) / len(vals), 2) if vals else None

    return out


def conclusion(result: dict, benchmark: dict | None = None) -> str:
    """最终评测结论：合格 / 精度下跌 / 异常。"""
    total = result.get("total_samples") or 0
    invalid = result.get("invalid_samples") or 0
    if total == 0 or (invalid / total) > 0.2:
        return CONCLUSION_ABNORMAL
    if benchmark:
        main = (benchmark.get("diff_pp") if isinstance(benchmark, dict) else None)
        if main is not None and main < -5.0:
            return CONCLUSION_DROP
    return CONCLUSION_OK

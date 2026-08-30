"""API 测试：Token 预估（/api/accuracy/estimate）+ 基线对标（/baselines、/benchmark）+ 多任务对比（/compare）。"""

from __future__ import annotations

import json
import time

from benchscope.accuracy import baselines as acc_baselines
from benchscope.accuracy import compare as acc_compare
from benchscope.accuracy import estimator as acc_estimator


# ---------------------------------------------------------------------------
# Token 预估
# ---------------------------------------------------------------------------


def test_builtin_estimates_loaded():
    """内置常量表固化需求附件数值。"""
    est = acc_estimator.load_builtin_estimates()
    assert est["mmlu"]["prompt_tokens"] == 180 and est["mmlu"]["completion_tokens"] == 8
    assert est["cmmlu"]["total_samples"] == 11960
    assert est["mt-bench"]["completion_tokens"] == 350
    assert est["gaokao-bench"]["prompt_tokens"] == 400


def test_estimate_api_builtin_dataset(client, base_url):
    """/estimate：内置数据集返回常量表口径预估（source=builtin 或 measured）。"""
    r = client.get(f"{base_url}/api/accuracy/estimate",
                   params={"dataset_id": "mmlu", "limit": 100}, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["mode"] == "serving"
    assert data["total_samples"] == 100
    assert data["total_tokens"] > 0
    assert data["source"] in ("builtin", "measured")
    assert data["source_label"]


def test_estimate_api_native_mode_zero():
    """Native 模式无 Token 消耗（能力边界）。"""
    est = acc_estimator.estimate(None, {"id": "mmlu"}, mode="native")
    assert est["total_tokens"] == 0 and est["source"] == "native"


def test_estimate_api_requires_dataset(client, base_url):
    r = client.get(f"{base_url}/api/accuracy/estimate", timeout=10)
    assert r.status_code == 400


def test_estimate_vs_actual_deviation():
    ev = acc_estimator.estimate_vs_actual(
        {"total_tokens": 200, "prompt_tokens": 160, "completion_tokens": 40},
        {"tokens": {"total_tokens": 150, "prompt_tokens_total": 120, "completion_tokens_total": 30}})
    assert ev["deviation_pct"] == -25.0 and ev["prompt_deviation_pct"] == -25.0


# ---------------------------------------------------------------------------
# 基线对标
# ---------------------------------------------------------------------------


def test_baselines_api_roundtrip(client, base_url):
    """/baselines 读取内置基线池；PUT 更新（校验失败 400）。"""
    r = client.get(f"{base_url}/api/accuracy/baselines", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    names = {m["name"] for m in data["models"]}
    assert {"Llama-3-8B", "Qwen2-7B", "InternLM2-7B", "Mistral-7B"} <= names
    assert any(m.get("group") == "chinese" for m in data["models"])  # 中文专项基线
    assert all(m.get("source") for m in data["models"])  # 来源标注

    r = client.put(f"{base_url}/api/accuracy/baselines", json={"content": "models: []"}, timeout=10)
    assert r.status_code == 400  # 空基线池拒绝


def test_compute_benchmark_grades_and_conclusion():
    library = acc_baselines.load_baselines()
    assert library["models"], "内置基线池不应为空"

    meta = {"id": "mmlu", "category": "accuracy-knowledge", "eval": {"scorer": "choice", "metrics": "accuracy"}}
    result = {"accuracy": 100.0}
    b = acc_baselines.compute_benchmark(meta, result)
    assert b and b["score"] == 100.0
    assert b["grade"] == "S" and b["conclusion"] == "优于同尺寸开源基线"
    assert b["rank_pct"] is not None and b["radar"]["知识"] == 100.0

    result_low = {"accuracy": 20.0}
    b_low = acc_baselines.compute_benchmark(meta, result_low)
    assert b_low["grade"] == "C" and "风险预警" in b_low["conclusion"]

    # 无基线分数的数据集 → None
    meta_unknown = {**meta, "id": "no-baseline-ds"}
    assert acc_baselines.compute_benchmark(meta_unknown, {"accuracy": 50.0}) is None


def test_task_benchmark_api(client, base_url, tmp_path):
    """任务结束自动生成对标：上传自定义数据集 + 管理员更新基线库（含该数据集分数）→ benchmark 生成。

    全程不触发内置数据集下载（测试隔离）；结束后恢复基线库原文。
    """
    lines = [json.dumps({"question": f"q{i}", "choices": ["甲", "乙", "丙", "丁"],
                         "answer": "ABCD"[i % 4], "subject": "s"}, ensure_ascii=False)
             for i in range(4)]
    r = client.post(f"{base_url}/api/accuracy/datasets/import?name=bench-ds",
                    files={"file": ("bench_ds.jsonl", "\n".join(lines).encode("utf-8"),
                                    "application/octet-stream")}, timeout=10)
    ds_id = r.json()["dataset"]["id"]

    original = client.get(f"{base_url}/api/accuracy/baselines", timeout=10).json()["content"]
    updated = original + (
        "  - name: TestBaseline-7B\n"
        "    params_b: 7\n"
        f"    scores: {{ \"{ds_id}\": 50.0 }}\n"
        "    source: test\n"
    )
    r = client.put(f"{base_url}/api/accuracy/baselines", json={"content": updated}, timeout=10)
    assert r.status_code == 200, r.text
    try:
        r = client.post(f"{base_url}/api/accuracy/tasks",
                        json={"engine_id": "mock", "model": "m", "dataset": {"id": ds_id},
                              "mock_correct_rate": 1.0,
                              "api": {"base_url": "http://mock.invalid"}}, timeout=15)
        task = r.json()["task"]
        task_id = task["task_id"]

        deadline = time.time() + 30
        while time.time() < deadline:
            t = client.get(f"{base_url}/api/accuracy/tasks/{task_id}", timeout=10).json()["task"]
            if t["status"] in ("done", "stopped", "error"):
                break
            time.sleep(0.2)
        assert t["status"] == "done", t.get("error")
        benchmark = t["result"]["benchmark"]
        assert benchmark["dataset_id"] == ds_id
        assert benchmark["score"] == 100.0 and benchmark["grade"] == "S"
        assert t["result"]["conclusion"] in ("合格", "精度下跌", "异常")

        r = client.get(f"{base_url}/api/accuracy/tasks/{task_id}/benchmark", timeout=10)
        assert r.status_code == 200 and r.json()["benchmark"]["dataset_id"] == ds_id
    finally:
        client.put(f"{base_url}/api/accuracy/baselines", json={"content": original}, timeout=10)
        client.delete(f"{base_url}/api/accuracy/tasks/{task_id}", timeout=10)


# ---------------------------------------------------------------------------
# 多任务对比 / Native vs Serving 一致性
# ---------------------------------------------------------------------------


def test_compare_tasks_native_vs_serving_unit():
    """一致性差值（纯函数级）：native vs serving 逐指标差值与结论。"""
    data = acc_compare.compare_tasks([
        {"task_id": "t1", "mode": "native", "model": "M", "dataset_id": "mmlu", "result": {"accuracy": 70.0}},
        {"task_id": "t2", "mode": "serving", "model": "M", "dataset_id": "mmlu", "result": {"accuracy": 68.0}},
        {"task_id": "t3", "mode": "serving", "model": "M", "dataset_id": "gsm8k", "result": {"accuracy": 80.0}},
    ])
    group = next(g for g in data["groups"] if g["dataset_id"] == "mmlu")
    assert group["consistency"]["diff_pp"] == 2.0
    assert group["consistency"]["conclusion"] == "训推一致"
    assert not next(g for g in data["groups"] if g["dataset_id"] == "gsm8k")["consistency"]


def test_compare_api(client, base_url, tmp_path):
    """POST /compare：横向对比 items + 分组；同模式任务无一致性差值（None）。"""
    lines = [json.dumps({"question": f"q{i}", "choices": ["甲", "乙", "丙", "丁"],
                         "answer": "ABCD"[i % 4], "subject": "s"}, ensure_ascii=False)
             for i in range(4)]
    ds = tmp_path / "cmp_ds.jsonl"
    ds.write_text("\n".join(lines) + "\n", encoding="utf-8")

    task_ids = []
    for rate in (1.0, 0.0):
        r = client.post(f"{base_url}/api/accuracy/tasks",
                        json={"engine_id": "mock", "model": "cmp-model", "dataset": {"path": str(ds)},
                              "mock_correct_rate": rate, "name": f"cmp-{rate}",
                              "api": {"base_url": "http://mock.invalid"}}, timeout=15)
        task_ids.append(r.json()["task"]["task_id"])
    for task_id in task_ids:
        deadline = time.time() + 30
        while time.time() < deadline:
            t = client.get(f"{base_url}/api/accuracy/tasks/{task_id}", timeout=10).json()["task"]
            if t["status"] in ("done", "stopped", "error"):
                break
            time.sleep(0.2)

    r = client.post(f"{base_url}/api/accuracy/compare", json={"task_ids": task_ids}, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["items"]) == 2
    group = data["groups"][0]
    assert group["consistency"] is None  # 双任务同为 serving（mock 引擎），无跨模式差值
    values = {i["task_id"]: i["metric_value"] for i in data["items"]}
    assert values[task_ids[0]] == 100.0 and values[task_ids[1]] == 0.0

    for task_id in task_ids:
        client.delete(f"{base_url}/api/accuracy/tasks/{task_id}", timeout=10)

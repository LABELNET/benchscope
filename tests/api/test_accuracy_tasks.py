"""API 测试：精度任务全链路（/api/accuracy/tasks*）——创建 / 运行 / 溯源 / 停止 / 删除。

全链路使用 mock 引擎（mock_correct_rate 可控正确率）+ 本地路径自定义数据集，
无 GPU、无真实推理服务即可验证：落库三件套 / 指标汇总 / 分学科 / 结论 / 错题集导出。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest


def _make_dataset(tmp_path, n=10):
    """构造 mock 引擎可判定正确率的四选一数据集（标准格式）。"""
    lines = []
    for i in range(n):
        answer = "ABCD"[i % 4]
        lines.append(json.dumps({
            "question": f"第 {i} 题",
            "choices": ["甲", "乙", "丙", "丁"],
            "answer": answer,
            "subject": f"学科{i % 2}",
        }, ensure_ascii=False))
    p = tmp_path / "acc_mock_ds.jsonl"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _create_task(client, base_url, ds_path, **overrides):
    payload = {
        "name": "精度任务单测",
        "engine_id": "mock",
        "mode": "serving",
        "model": "mock-model",
        "dataset": {"path": str(ds_path)},
        "limit": 0,
        "seed": 42,
        "mock_correct_rate": 1.0,  # 全对 → accuracy=100
        "api": {"base_url": "http://mock.invalid", "endpoint": "/v1/chat/completions"},
    }
    payload.update(overrides)
    r = client.post(f"{base_url}/api/accuracy/tasks", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["task"]


def _wait_done(client, base_url, task_id, timeout=30) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = client.get(f"{base_url}/api/accuracy/tasks/{task_id}", timeout=10).json()["task"]
        if task["status"] in ("done", "stopped", "error"):
            return task
        time.sleep(0.2)
    raise AssertionError(f"任务超时未结束: {task_id}")


def test_create_and_run_mock_task_full_pipeline(client, base_url, tmp_path):
    """mock 引擎全链路：任务状态 / result 三件套 / accuracy / 分学科 / 结论 / 预估对比。"""
    ds = _make_dataset(tmp_path, n=10)
    task = _create_task(client, base_url, ds)
    task_id = task["task_id"]
    assert task_id.startswith("eval-")
    assert task["status"] in ("running", "done")

    task = _wait_done(client, base_url, task_id)
    assert task["status"] == "done", task.get("error")
    assert task["progress"] == {"done": 10, "total": 10}

    result = task["result"]
    assert result["total_samples"] == 10
    assert result["correct_samples"] == 10
    assert result["wrong_samples"] == 0 and result["invalid_samples"] == 0
    assert result["accuracy"] == 100.0 and result["pass_rate"] == 100.0
    assert {s["subject"]: s["accuracy"] for s in result["subjects"]} == {"学科0": 100.0, "学科1": 100.0}
    assert result["tokens"] and result["tokens"]["total_tokens"] > 0
    assert result["conclusion"] == "合格"

    # 任务列表含该任务
    r = client.get(f"{base_url}/api/accuracy/tasks", timeout=10)
    assert task_id in {t["task_id"] for t in r.json()["tasks"]}


def test_task_artifacts_persisted(client, base_url, tmp_path):
    """落库三件套：task.json / result.json / samples.jsonl 均存在且结构完整。"""
    ds = _make_dataset(tmp_path, n=6)
    task = _create_task(client, base_url, ds, mock_correct_rate=0.5)
    task_id = task["task_id"]
    task = _wait_done(client, base_url, task_id)
    assert task["status"] == "done"

    task_dir = Path(task["task_dir"])
    for name in ("task.json", "result.json", "samples.jsonl"):
        assert (task_dir / name).exists(), name

    r = client.get(f"{base_url}/api/accuracy/tasks/{task_id}/samples?filter=all&limit=100", timeout=10)
    data = r.json()
    assert data["total"] == 6
    sample = data["samples"][0]
    for key in ("prompt", "output", "answer", "status", "tokens", "sample_id"):
        assert key in sample, key
    # mock_correct_rate=0.5 → 有对有错
    statuses = {s["status"] for s in data["samples"]}
    assert statuses <= {"correct", "wrong", "invalid"}

    r = client.get(f"{base_url}/api/accuracy/tasks/{task_id}/samples?filter=wrong", timeout=10)
    assert all(s["status"] == "wrong" for s in r.json()["samples"])


def test_export_wrong_samples(client, base_url, tmp_path):
    """错题集导出（filter=wrong 的 JSONL 下载）。"""
    ds = _make_dataset(tmp_path, n=8)
    task = _create_task(client, base_url, ds, mock_correct_rate=0.0)  # 全错
    task_id = task["task_id"]
    _wait_done(client, base_url, task_id)
    r = client.get(f"{base_url}/api/accuracy/tasks/{task_id}/export-samples?filter=wrong", timeout=10)
    assert r.status_code == 200, r.text
    lines = [ln for ln in r.text.splitlines() if ln.strip()]
    assert len(lines) == 8
    assert all(json.loads(ln)["status"] == "wrong" for ln in lines)


def test_stop_and_delete_task(client, base_url, tmp_path):
    """任务停止与删除（目录一并清理）。"""
    lines = []
    for i in range(2000):  # 足够大，确保运行中可停止
        lines.append(json.dumps({"question": f"q{i}", "choices": ["甲", "乙", "丙", "丁"],
                                 "answer": "ABCD"[i % 4], "subject": "s"}, ensure_ascii=False))
    ds = tmp_path / "big_ds.jsonl"
    ds.write_text("\n".join(lines) + "\n", encoding="utf-8")
    task = _create_task(client, base_url, ds)
    task_id = task["task_id"]

    r = client.post(f"{base_url}/api/accuracy/tasks/{task_id}/stop", timeout=10)
    assert r.status_code == 200
    task = _wait_done(client, base_url, task_id, timeout=60)
    assert task["status"] in ("stopped", "done")

    r = client.delete(f"{base_url}/api/accuracy/tasks/{task_id}", timeout=10)
    assert r.status_code == 200
    r = client.get(f"{base_url}/api/accuracy/tasks/{task_id}", timeout=10)
    assert r.status_code == 404


def test_create_task_validation(client, base_url, tmp_path):
    """参数校验：缺模型 / 缺数据集 / 非法数据集路径。"""
    ds = _make_dataset(tmp_path, n=2)
    r = client.post(f"{base_url}/api/accuracy/tasks",
                    json={"engine_id": "mock", "dataset": {"path": str(ds)}}, timeout=10)
    assert r.status_code == 400  # 缺模型
    r = client.post(f"{base_url}/api/accuracy/tasks",
                    json={"engine_id": "mock", "model": "m"}, timeout=10)
    assert r.status_code == 400  # 缺数据集
    r = client.post(f"{base_url}/api/accuracy/tasks",
                    json={"engine_id": "mock", "model": "m", "dataset": {"path": "/no/such/file.jsonl"}}, timeout=15)
    assert r.status_code in (400, 500)  # 文件不存在（创建即启动，执行线程报错或创建校验拒绝）


def test_create_task_error_status_propagates(client, base_url, tmp_path):
    """执行期错误（数据集为空）→ 任务 error 状态 + error 信息。"""
    empty = tmp_path / "empty.jsonl"
    empty.write_text('{"foo": "bar"}\n', encoding="utf-8")  # 无可评测样本
    task = _create_task(client, base_url, empty)
    task = _wait_done(client, base_url, task["task_id"])
    assert task["status"] == "error"
    assert task["error"]


def test_unknown_task_404(client, base_url):
    r = client.get(f"{base_url}/api/accuracy/tasks/eval-not-exist", timeout=10)
    assert r.status_code == 404

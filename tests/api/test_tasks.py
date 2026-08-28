"""API 测试：性能任务（/api/tasks*）。"""

from __future__ import annotations

import pytest

import tests.helpers as helpers
from tests.helpers import DEFAULT_PAYLOAD


def test_preview(client, base_url):
    r = client.post(f"{base_url}/api/tasks/preview", json=DEFAULT_PAYLOAD, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "commands" in data
    assert len(data["commands"]) > 0
    cmd = data["commands"][0]
    assert isinstance(cmd, dict)
    assert cmd["case"] and cmd["concurrency"] > 0 and cmd["cmd"]


def test_preview_threshold_mode(client, base_url):
    payload = {**DEFAULT_PAYLOAD, "mode": "threshold"}
    r = client.post(f"{base_url}/api/tasks/preview", json=payload, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "commands" in data
    assert len(data["commands"]) > 0


def test_task_crud(client, base_url):
    """创建 -> 列表可见 -> 读取 -> 删除 -> 列表消失 / 读取 404。"""
    task_id = helpers.create_task(client, base_url)

    r = client.get(f"{base_url}/api/tasks", timeout=10)
    assert r.status_code == 200, r.text
    tasks = r.json()["tasks"]
    assert any(t["task_id"] == task_id for t in tasks)

    r = client.get(f"{base_url}/api/tasks/{task_id}", timeout=10)
    assert r.status_code == 200, r.text
    snap = r.json()
    assert snap["task_id"] == task_id
    assert snap["status"] == "pending"
    assert isinstance(snap.get("rows"), list)

    r = client.delete(f"{base_url}/api/tasks/{task_id}", timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    r = client.get(f"{base_url}/api/tasks/{task_id}", timeout=10)
    assert r.status_code == 404

    r = client.get(f"{base_url}/api/tasks", timeout=10)
    assert not any(t["task_id"] == task_id for t in r.json()["tasks"])


def test_task_run_lifecycle(client, base_url):
    """创建 -> 启动 -> 等待完成 -> 数据/日志/阈值/导出 -> 删除。"""
    task_id = helpers.create_task(client, base_url)

    r = client.post(f"{base_url}/api/tasks/{task_id}/start", timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    assert r.json()["task"]["status"] == "running"

    snap = helpers.wait_task_terminal(client, base_url, task_id, timeout=120)
    assert snap["status"] == "done", snap.get("error")

    # 结果数据
    assert isinstance(snap.get("rows"), list)
    assert len(snap["rows"]) > 0
    row = snap["rows"][0]
    assert "metrics" in row
    assert row["metrics"].get("tpot_mean") is not None

    # 日志
    r = client.get(f"{base_url}/api/tasks/{task_id}/logs", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["task_id"] == task_id
    assert isinstance(data["lines"], list)
    assert len(data["lines"]) > 0

    # 阈值更新（返回任务 snapshot）
    r = client.patch(f"{base_url}/api/tasks/{task_id}/threshold", json={"tpot_threshold_ms": 150}, timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["tpot_threshold_ms"] == 150

    # 导出 Excel
    r = client.post(f"{base_url}/api/tasks/{task_id}/export", json={"data": snap.get("rows", [])}, timeout=15)
    assert r.status_code == 200, r.text
    assert len(r.content) > 0
    assert r.headers.get("content-type", "").startswith(("application", "text"))

    # 删除
    r = client.delete(f"{base_url}/api/tasks/{task_id}", timeout=10)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


def test_task_unknown_404(client, base_url):
    r = client.get(f"{base_url}/api/tasks/task-nonexistent", timeout=10)
    assert r.status_code == 404
    r = client.delete(f"{base_url}/api/tasks/task-nonexistent", timeout=10)
    assert r.status_code == 200  # delete 幂等


@pytest.mark.parametrize("kind", ["perf", "eval"])
def test_preview_kinds(client, base_url, kind):
    payload = {**DEFAULT_PAYLOAD, "kind": kind}
    r = client.post(f"{base_url}/api/tasks/preview", json=payload, timeout=10)
    assert r.status_code == 200, r.text
    assert len(r.json()["commands"]) > 0

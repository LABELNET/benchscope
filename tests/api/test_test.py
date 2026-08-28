"""API 测试：精度任务（/api/test*），FAKE 模式下秒级完成。"""

from __future__ import annotations

import tests.helpers as helpers

TEST_PAYLOAD = {
    "framework": "vllm",
    "model": "Qwen2.5-7B-Instruct",
    "tokenizer": "",
    "dataset": {"type": "random", "length_pairs": [[64, 64, "用例A", "case-a"]]},
    "concurrency_list": [1],
    "gpu": {},
    "request_rate": "inf",
    "precision": "",
    "curated": {},
}


def test_preview(client, base_url):
    r = client.post(f"{base_url}/api/test/preview", json=TEST_PAYLOAD, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["count"] > 0
    assert len(data["commands"]) == data["count"]


def test_run_flow(client, base_url):
    """start -> 运行中 -> 等待结束 -> status 复位。"""
    client.post(f"{base_url}/api/test/stop", timeout=10)

    r = client.post(f"{base_url}/api/test/start", json=TEST_PAYLOAD, timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    run_id = data["run_id"]
    assert run_id

    # 运行中（刚启动，FAKE 也有短暂 running 窗口，轮询容忍）
    helpers.wait_until(
        lambda: client.get(f"{base_url}/api/test/status", timeout=5).json().get("running") is True,
        timeout=15, msg="精度任务未进入 running",
    )

    # 等待结束
    helpers.wait_until(
        lambda: client.get(f"{base_url}/api/test/status", timeout=5).json().get("running") is False,
        timeout=120, msg="精度任务未结束",
    )
    status = client.get(f"{base_url}/api/test/status", timeout=10).json()
    assert status["run"] is not None
    assert status["run"]["run_id"] == run_id
    assert status["run"]["status"] in ("done", "stopped", "error"), status["run"]

    # stop 幂等
    r = client.post(f"{base_url}/api/test/stop", timeout=10)
    assert r.status_code == 200 and r.json()["ok"] is True

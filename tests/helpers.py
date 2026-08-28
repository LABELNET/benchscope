"""benchscope 测试公共工具。

仅依赖标准库与 requests（不依赖 mocks/ 或 benchscope 包内部），
通过 HTTP API 驱动被测服务（进程级黑盒测试）。
"""

from __future__ import annotations

import os
import time

# FAKE bench 下任务终止态
TASK_TERMINAL = {"done", "stopped", "error"}

# mock 推理服务地址（FAKE bench / test-connection / sessions chat 共用）
MOCK_URL = os.environ.get("BS_MOCK_URL", "http://127.0.0.1:8001")

# 并发模式默认任务 payload（短小快速，FAKE bench 秒级完成）
DEFAULT_PAYLOAD: dict = {
    "framework": "vllm",
    "model": "Qwen2.5-7B-Instruct",
    "tokenizer": "",
    "dataset": {"type": "random", "length_pairs": [[64, 64, "用例A", "case-a"]]},
    "concurrency_list": [1, 4],
    "gpu": {},
    "request_rate": "inf",
    "tpot_threshold_ms": 100,
    "mode": "concurrency",
}


def wait_until(cond, timeout: float = 30, interval: float = 0.5, msg: str = "条件未满足"):
    """轮询等待 cond() 返回真值；超时抛出 AssertionError。"""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            if cond():
                return True
        except Exception as e:  # noqa: BLE001 - 轮询期间任何异常都视为未就绪
            last = e
        time.sleep(interval)
    raise AssertionError(f"{msg}（超时 {timeout:.0f}s，最后异常: {last!r}）")


def wait_task_terminal(client, base_url: str, task_id: str, timeout: float = 90) -> dict:
    """轮询任务直到进入终止态（done/stopped/error），返回最终 snapshot。"""

    def terminal():
        r = client.get(f"{base_url}/api/tasks/{task_id}", timeout=5)
        if r.status_code != 200:
            return False
        snap = r.json()
        return snap.get("status") in TASK_TERMINAL

    wait_until(terminal, timeout=timeout, msg=f"任务 {task_id} 未进入终止态")

    r = client.get(f"{base_url}/api/tasks/{task_id}", timeout=5)
    assert r.status_code == 200, r.text
    return r.json()


def create_task(client, base_url: str, payload: dict | None = None) -> str:
    """创建 perf 任务，返回 task_id。

    内部 sleep 1.1s 保证 task_id/run_id 唯一（task_id 为秒级时间戳，
    同一秒创建的多个任务会共用同一 run_id 目录）。
    """
    time.sleep(1.1)
    body = {**DEFAULT_PAYLOAD, **(payload or {})}
    r = client.post(f"{base_url}/api/tasks", json=body, timeout=10)
    assert r.status_code == 200, f"创建任务失败: {r.status_code} {r.text}"
    return r.json()["task_id"]


def start_task(client, base_url: str, task_id: str):
    r = client.post(f"{base_url}/api/tasks/{task_id}/start", timeout=10)
    assert r.status_code == 200, f"启动任务失败: {r.status_code} {r.text}"


def run_id_of(task_id: str) -> str:
    """由 task_id 推导 run_id（task-MMDD-HHMMSS -> MMDD-HHMMSS）。"""
    return task_id.removeprefix("task-")


def create_and_run_task(client, base_url: str, payload: dict | None = None, timeout: float = 90) -> dict:
    """创建 perf 任务 -> start -> 等待终止态。

    返回最终任务 snapshot（含 task_id / status / rows）。
    """
    task_id = create_task(client, base_url, payload)
    start_task(client, base_url, task_id)
    snap = wait_task_terminal(client, base_url, task_id, timeout=timeout)
    assert snap.get("status") == "done", f"任务未成功完成: status={snap.get('status')} error={snap.get('error')}"
    return snap

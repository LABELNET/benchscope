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


def test_preview_builtin_threshold_command(client, base_url):
    """自研引擎阈值模式预览命令：应体现真实阈值探测（--mode threshold + 阈值参数），
    与前端 previewConditions 展示的阈值条件一致。"""
    payload = {
        **DEFAULT_PAYLOAD,
        "engine_id": "benchscope",
        "mode": "threshold",
        "concurrency_list": [1],
        "max_requests": 4096,
        "dataset": {"type": "random", "length_pairs": [[64, 64, "用例A", "case-a", {
            "ttft_statistic": "median", "ttft_threshold_ms": 50,
            "tpot_statistic": "p99", "tpot_threshold_ms": 120,
            "output_throughput_threshold": 200,
        }]]},
    }
    r = client.post(f"{base_url}/api/tasks/preview", json=payload, timeout=10)
    assert r.status_code == 200, r.text
    cmd = r.json()["commands"][0]["cmd"]
    assert "--engine benchscope" in cmd
    assert "--mode threshold" in cmd, f"阈值模式预览命令应含 --mode threshold: {cmd}"
    assert "--ttft-threshold-ms 50" in cmd, cmd
    assert "--tpot-threshold-ms 120" in cmd, cmd
    assert "--output-threshold 200" in cmd, cmd
    assert "--max-requests 4096" in cmd, cmd


def test_create_task_threshold_ttft_fields(client, base_url):
    """阈值模式创建：TTFT/TPOT 统计量（mean/median/p99）与阈值字段透传并持久化。
    阈值信息在每组请求配置（length_pairs 第 5 元素）中，透传到每个 case；任务级字段保留（向后兼容）。"""
    group_thr = {
        "ttft_statistic": "median", "ttft_threshold_ms": 50,
        "tpot_statistic": "p99", "tpot_threshold_ms": 120,
        "output_throughput_threshold": 200,
    }
    payload = {
        **DEFAULT_PAYLOAD,
        "mode": "threshold",
        "dataset": {"type": "random", "length_pairs": [[64, 64, "用例A", "case-a", group_thr]]},
        "tpot_threshold_ms": 120,
        "ttft_threshold_ms": 50,
        "ttft_statistic": "median",
        "tpot_statistic": "p99",
        "output_throughput_threshold": 200,
    }
    r = client.post(f"{base_url}/api/tasks", json=payload, timeout=10)
    assert r.status_code == 200, r.text
    snap = r.json()["task"]
    task_id = snap["task_id"]
    assert snap["mode"] == "threshold"
    assert snap["tpot_threshold_ms"] == 120
    assert snap["ttft_threshold_ms"] == 50
    assert snap["ttft_statistic"] == "median"
    assert snap["tpot_statistic"] == "p99"
    assert snap["output_throughput_threshold"] == 200

    # 每组（case）阈值透传：阈值信息跟随 Groups 数据，不跟随主任务
    cases = snap.get("cases") or []
    assert cases and cases[0]["case_id"] == "case-a"
    c0 = cases[0]
    assert c0["ttft_statistic"] == "median"
    assert c0["ttft_threshold_ms"] == 50
    assert c0["tpot_statistic"] == "p99"
    assert c0["tpot_threshold_ms"] == 120
    assert c0["output_throughput_threshold"] == 200

    # 重新读取（持久化）仍保留
    r = client.get(f"{base_url}/api/tasks/{task_id}", timeout=10)
    assert r.status_code == 200, r.text
    snap = r.json()
    assert snap["ttft_threshold_ms"] == 50
    assert snap["ttft_statistic"] == "median"
    assert snap["tpot_statistic"] == "p99"
    cases = snap.get("cases") or []
    assert cases and cases[0]["ttft_threshold_ms"] == 50
    assert cases[0]["tpot_threshold_ms"] == 120
    assert cases[0]["output_throughput_threshold"] == 200

    client.delete(f"{base_url}/api/tasks/{task_id}", timeout=10)


def test_build_cases_parses_per_group_thresholds():
    """build_cases：length_pairs 第 5 元素阈值解析到每组 case（阈值跟随 Groups，不跟随主任务）。"""
    from benchscope.task_manager import build_cases

    dataset = {
        "type": "random",
        "length_pairs": [
            [64, 64, "用例A", "case-a", {
                "ttft_statistic": "median", "ttft_threshold_ms": 50,
                "tpot_statistic": "p99", "tpot_threshold_ms": 120,
                "output_throughput_threshold": 200,
            }],
            [128, 128, "用例B", "case-b", {
                "ttft_statistic": "p99", "ttft_threshold_ms": 30,
                "tpot_statistic": "mean", "tpot_threshold_ms": 90,
                "output_throughput_threshold": 0,
            }],
            # 旧格式：无第 5 元素 → 默认统计量 mean、阈值为 0（不参与判定）
            [256, 256, "用例C", "case-c"],
        ],
    }
    cases = build_cases(dataset, "test-model")
    assert len(cases) == 3
    a, b, c = cases
    assert a["case_id"] == "case-a"
    assert a["ttft_statistic"] == "median" and a["ttft_threshold_ms"] == 50
    assert a["tpot_statistic"] == "p99" and a["tpot_threshold_ms"] == 120
    assert a["output_throughput_threshold"] == 200
    assert b["ttft_statistic"] == "p99" and b["ttft_threshold_ms"] == 30
    assert b["tpot_statistic"] == "mean" and b["tpot_threshold_ms"] == 90
    assert b["output_throughput_threshold"] == 0
    assert c["case_id"] == "case-c"
    assert c["ttft_statistic"] == "mean" and c["ttft_threshold_ms"] == 0
    assert c["tpot_statistic"] == "mean" and c["tpot_threshold_ms"] == 0
    assert c["output_throughput_threshold"] == 0


def test_annotate_best_per_group_statistic():
    """_annotate_best：按每组 case 的 tpot 阈值与 statistic 独立标注最佳并发（xlsx 用）。"""
    import tempfile
    from pathlib import Path

    from benchscope.task_manager import Task, TaskManager

    task = Task(
        task_id="t-best", run_dir=Path(tempfile.mkdtemp()),
        payload={"tpot_statistic": "mean", "tpot_threshold_ms": 200},
        framework="sglang", model="m", gpu={},
        cases=[
            {"label": "A", "case_id": "a", "tpot_statistic": "median", "tpot_threshold_ms": 150},
            {"label": "B", "case_id": "b", "tpot_statistic": "p99", "tpot_threshold_ms": 300},
        ],
    )
    rows = [
        {"case_id": "a", "concurrency": 1, "metrics": {"tpot_median": 60}},
        {"case_id": "a", "concurrency": 2, "metrics": {"tpot_median": 120}},
        {"case_id": "a", "concurrency": 4, "metrics": {"tpot_median": 160}},   # >150 超阈值
        {"case_id": "b", "concurrency": 1, "metrics": {"tpot_p99": 280}},
        {"case_id": "b", "concurrency": 2, "metrics": {"tpot_p99": 350}},      # >300 超阈值
    ]
    out = TaskManager.__new__(TaskManager)._annotate_best(rows, task)
    best = {r["case_id"]: r for r in out if r.get("best")}
    # 组 A 用 tpot_median：满足 <150 的并发中最大（2，tpot=120）
    assert best["a"]["concurrency"] == 2
    assert best["a"].get("best_tpot") == 120
    # 组 B 用 tpot_p99：无 <300 的行 → 取最小（1，tpot=280）
    assert best["b"]["concurrency"] == 1
    assert best["b"].get("best_tpot") == 280
    # 未配置阈值的组（无）不被标注


def test_threshold_per_group_execution(client, base_url):
    """阈值模式执行：每组独立阈值判定（跟随 Groups，不跟随主任务）。
    组 A 阈值极高 → 搜索到上限 max_concurrency_search；组 B 阈值极低 → 1 并发即违规。"""
    payload = {
        "mode": "threshold",
        "max_concurrency_search": 8,
        "dataset": {"type": "random", "length_pairs": [
            [64, 64, "用例A", "case-a", {
                "ttft_statistic": "mean", "ttft_threshold_ms": 100000,
                "tpot_statistic": "mean", "tpot_threshold_ms": 100000,
                "output_throughput_threshold": 0,
            }],
            [64, 64, "用例B", "case-b", {
                "ttft_statistic": "mean", "ttft_threshold_ms": 0,
                "tpot_statistic": "mean", "tpot_threshold_ms": 1,
                "output_throughput_threshold": 0,
            }],
        ]},
    }
    snap = helpers.create_and_run_task(client, base_url, payload, timeout=120)
    rows = snap.get("rows") or []
    assert rows, "阈值模式执行应产生 rows"
    by_case: dict = {}
    for row in rows:
        by_case.setdefault(row.get("case_id"), []).append(row)
    assert set(by_case) >= {"case-a", "case-b"}
    conc_a = max(int(r["concurrency"]) for r in by_case["case-a"])
    conc_b = max(int(r["concurrency"]) for r in by_case["case-b"])
    assert conc_a == 8, f"组 A 应搜索到上限 8，实际 {conc_a}"
    assert conc_b == 1, f"组 B 应在 1 并发即违规，实际 {conc_b}"
    # 全条件判断所需 metrics 键完整（TTFT/TPOT statistic 键 + output_mean）
    m = by_case["case-a"][0].get("metrics") or {}
    assert "ttft_mean" in m and "tpot_mean" in m and "output_mean" in m
    # 每组阈值随存储保留
    cases = snap.get("cases") or []
    by_cid = {c["case_id"]: c for c in cases}
    assert by_cid["case-a"]["tpot_threshold_ms"] == 100000
    assert by_cid["case-b"]["tpot_threshold_ms"] == 1


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


# ---------------- 阈值模式 Max Requests 强制结束 + mocks 环境（1.0.7） ----------------


def test_threshold_max_requests_forced_finish(client, base_url):
    """阈值模式 max_requests：下一次执行请求数超过上限 → 任务强制结束并标记 Finish。

    max_requests=3：探测 1 → 2（2<=3 执行）→ 下一次 4 > 3 → 强制结束；
    快照 forced_finish=True（前端显示 Finish 而非 Done），且不再探测 4。
    阈值给极大值（永不违反）确保走满递增路径。
    """
    payload = {
        **DEFAULT_PAYLOAD,
        "mode": "threshold",
        "engine_id": "benchscope",
        "max_requests": 3,
        "tpot_threshold_ms": 100000,  # 永不违反 → 持续倍增直到超限
        "ttft_threshold_ms": 0,
        "output_throughput_threshold": 0,
    }
    task_id = helpers.create_task(client, base_url, payload)
    helpers.start_task(client, base_url, task_id)
    snap = helpers.wait_task_terminal(client, base_url, task_id, timeout=120)

    assert snap["status"] == "done", f"任务应正常结束: {snap['status']} {snap.get('error')}"
    assert snap.get("forced_finish") is True, "下一次执行请求数超上限应标记 forced_finish（Finish）"
    concs = [r.get("concurrency") for r in snap.get("rows", []) if r.get("concurrency")]
    assert concs, "应至少执行了并发 1"
    assert max(concs) <= 3, f"执行过的并发不应超过 max_requests=3: {concs}"
    assert all(c not in concs for c in (4, 8)), f"超限并发不应被执行: {concs}"
    client.delete(f"{base_url}/api/tasks/{task_id}", timeout=10)


def test_native_engine_with_mock_env(client, base_url):
    """原生引擎 + use_mock_env：无本地 vllm 环境也可用 mocks 仿真输出完成测试。"""
    payload = {
        **DEFAULT_PAYLOAD,
        "engine_id": "vllm-0.23",
        "use_mock_env": True,
    }
    task_id = helpers.create_task(client, base_url, payload)
    helpers.start_task(client, base_url, task_id)
    snap = helpers.wait_task_terminal(client, base_url, task_id, timeout=120)

    assert snap["status"] == "done", f"mocks 环境下任务应完成: {snap['status']} {snap.get('error')}"
    rows = [r for r in snap.get("rows", []) if r.get("metrics")]
    assert rows, f"FAKE 输出应解析出指标行: {snap.get('rows', [])[:2]}"
    assert snap.get("use_mock_env") is True, "快照应透出 use_mock_env=True（Mock 标识）"
    client.delete(f"{base_url}/api/tasks/{task_id}", timeout=10)


def test_native_engine_engine_mocks_config(client, base_url):
    """引擎 mock 开关（config.engine_mocks，按 engine_id）→ 任务走 mocks 仿真，无需 use_mock_env。"""
    # 先通过 config 打开 vllm-0.23 的 mock 开关
    r = client.post(f"{base_url}/api/config",
                    json={"engine_mocks": {"vllm-0.23": True}}, timeout=10)
    assert r.status_code == 200, r.text
    try:
        payload = {**DEFAULT_PAYLOAD, "engine_id": "vllm-0.23"}  # 不传 use_mock_env
        task_id = helpers.create_task(client, base_url, payload)
        helpers.start_task(client, base_url, task_id)
        snap = helpers.wait_task_terminal(client, base_url, task_id, timeout=120)
        assert snap["status"] == "done", \
            f"开启引擎 mock 开关后任务应完成: {snap['status']} {snap.get('error')}"
        rows = [r for r in snap.get("rows", []) if r.get("metrics")]
        assert rows, f"engine_mocks 开关应触发 FAKE 仿真并解析出指标: {snap.get('rows', [])[:2]}"
    finally:
        # 复原
        client.post(f"{base_url}/api/config", json={"engine_mocks": {}}, timeout=10)
    client.delete(f"{base_url}/api/tasks/{task_id}", timeout=10)


def test_task_payload_api_overrides_global(client, base_url):
    """任务 payload.api（创建时选择的 Provider 配置）优先于全局 api：
    命令中的 base-url 应取 payload 值，而非回退全局 mock 地址。"""
    payload = {
        **DEFAULT_PAYLOAD,
        "framework": "vllm",
        "api": {"base_url": "http://127.0.0.1:9", "endpoint": "/v1/chat/completions"},
    }
    task_id = helpers.create_task(client, base_url, payload)
    helpers.start_task(client, base_url, task_id)
    snap = helpers.wait_task_terminal(client, base_url, task_id, timeout=120)

    assert snap["status"] == "done", f"任务应完成: {snap['status']} {snap.get('error')}"
    cmds = [r.get("cmd", "") for r in snap.get("rows", []) if isinstance(r, dict)]
    assert cmds, "任务应产出含 cmd 的结果行"
    assert any("--port 9" in c for c in cmds), f"payload.api 的 base_url 未进入命令: {cmds}"
    assert all("--port 8001" not in c for c in cmds), f"不应回退全局 mock 地址: {cmds}"
    client.delete(f"{base_url}/api/tasks/{task_id}", timeout=10)

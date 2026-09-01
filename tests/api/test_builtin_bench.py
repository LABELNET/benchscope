"""API 测试：自研 bench 引擎（builtin）——指标计算、mock 服务集成、任务级集成。

自研引擎不依赖本地 vllm/sglang 环境，通过 HTTP 直接压测被测服务；
测试环境被测服务的推理地址已由 conftest 指向 mock（:8001），因此可对 mock 真实发压。
"""
from __future__ import annotations

import pytest

import tests.helpers as helpers
from benchscope.benches.builtin_bench import (
    BuiltinOptions,
    RequestRecord,
    _percentile,
    build_prompt,
    compute_metrics,
    run_builtin_bench,
)


# ---------------- 纯函数：分位数与统计 ----------------


def test_percentile_edge_cases():
    """分位数：空列表 / 单样本 / 多样本（最近秩语义）。"""
    assert _percentile([], 99) == 0.0
    assert _percentile([5.0], 99) == 5.0, "单样本不应抛错，直接返回该值"
    vals = list(range(1, 101))  # 1..100
    assert _percentile(vals, 50) == 50
    assert _percentile(vals, 99) == 99
    assert _percentile(vals, 1) == 1


def test_compute_metrics_tpot_definition():
    """TPOT 口径对齐 vLLM：(E2E - TTFT) / (completion_tokens - 1)。"""
    # 单请求：t0=0, t_first=0.1(100ms), t_end=1.1 → E2E=1100ms，TTFT=100ms
    # completion_tokens=11 → TPOT = (1100-100)/(11-1) = 100ms
    rec = RequestRecord(ok=True, start=0.0, first_token=0.1, end=1.1,
                        itls=[100.0] * 10, completion_tokens=11, prompt_tokens=8)
    m = compute_metrics([rec], duration=1.1, concurrency=1)
    assert m["ttft_mean"] == pytest.approx(100.0, abs=1)
    assert m["tpot_mean"] == pytest.approx(100.0, abs=1)
    assert m["itl_mean"] == pytest.approx(100.0, abs=1)
    # 吞吐：11 tokens / 1.1s = 10 tok/s；总吞吐 (8+11)/1.1
    assert m["output_mean"] == pytest.approx(10.0, abs=0.5)
    assert m["total_mean"] == pytest.approx(19 / 1.1, abs=0.5)
    assert m["successful_requests"] == 1
    assert m["failed_requests"] == 0


def test_compute_metrics_throughput_and_failed():
    """吞吐与失败计数：失败请求不计入成功数与 token 统计。"""
    oks = [
        RequestRecord(ok=True, start=0.0, first_token=0.05, end=0.5, completion_tokens=10, prompt_tokens=5),
        RequestRecord(ok=True, start=0.0, first_token=0.05, end=0.5, completion_tokens=10, prompt_tokens=5),
    ]
    bad = RequestRecord(ok=False, start=0.0, end=0.2, error="HTTP 500")
    m = compute_metrics(oks + [bad], duration=1.0, concurrency=2)
    assert m["successful_requests"] == 2
    assert m["failed_requests"] == 1
    assert m["output_mean"] == pytest.approx(20.0, abs=0.5)   # 20 tokens / 1s
    assert m["req_per_s"] == pytest.approx(2.0, abs=0.1)
    assert m["total_generated_tokens"] == 20
    assert m["total_input_tokens"] == 10
    # mean/median/p99 三套指标齐全
    for metric in ("ttft", "tpot", "itl"):
        for kind in ("mean", "median", "p99"):
            assert f"{metric}_{kind}" in m


def test_build_prompt_approx_length():
    """prompt 按字符/token 比近似构造（默认 4 字符 ≈ 1 token）。"""
    p = build_prompt(64, 4.0)
    assert 200 <= len(p) <= 260, f"64 tokens 应约 256 字符，实际 {len(p)}"
    p2 = build_prompt(16, 4.0)
    assert len(p2) < len(p), "更短的目标长度应生成更短 prompt"


# ---------------- 峰值输出吞吐（vLLM 语义：按请求完成时刻 1s 滑窗） ----------------


def test_peak_output_throughput_sliding_window():
    """peak output：vLLM 语义——按请求**完成时刻**整段 token 的 1s 滑窗（非逐 chunk 产出）。

    两个请求完成时刻 t=0.3 / t=0.9，各 8 tokens → 落在同一 1s 窗内 → 峰值 16 tok/s。
    """
    from benchscope.benches.builtin_bench import _peak_output_throughput

    # 请求1：t=0.3 完成，8 tokens；请求2：t=0.9 完成，8 tokens（同窗内）
    r1 = RequestRecord(ok=True, start=0.0, first_token=0.0, end=0.3,
                       output_events=[(0.0, 8)], completion_tokens=8, prompt_tokens=0)
    r2 = RequestRecord(ok=True, start=0.0, first_token=0.6, end=0.9,
                       output_events=[(0.6, 8)], completion_tokens=8, prompt_tokens=0)
    peak = _peak_output_throughput([r1, r2], duration=1.0)
    assert peak == pytest.approx(16.0, abs=0.5), f"1s 窗内两请求合计应为 16 tok/s: {peak}"

    # 完成时刻相隔 > 1s：峰值 = 单个请求的整段 token（不同时落在 1s 窗内）
    r3 = RequestRecord(ok=True, start=0.0, first_token=0.0, end=0.5, completion_tokens=10, prompt_tokens=0)
    r4 = RequestRecord(ok=True, start=0.0, first_token=0.0, end=2.5, completion_tokens=10, prompt_tokens=0)
    peak_fb = _peak_output_throughput([r3, r4], duration=2.6)
    assert peak_fb == pytest.approx(10.0, abs=0.5), f"相隔超 1s 应取单个完成请求 10 tok/s: {peak_fb}"


def test_compute_metrics_has_peakoutput():
    """compute_metrics 输出 peakoutput_mean 键（实时面板 Peak output 列读取）。"""
    rec = RequestRecord(ok=True, start=0.0, first_token=0.0, end=0.5,
                        output_events=[(0.0, 2), (0.1, 2), (0.2, 2), (0.3, 2), (0.4, 2)],
                        completion_tokens=10, prompt_tokens=0)
    m = compute_metrics([rec], duration=0.5, concurrency=1)
    assert "peakoutput_mean" in m
    assert m["peakoutput_mean"] == pytest.approx(10.0, abs=0.5)


# ---------------- 引擎执行（对 mock 服务真实发压） ----------------


@pytest.fixture()
def engine_opts(mock_url) -> BuiltinOptions:
    """自研引擎选项：指向 mock 推理服务（:8001）。"""
    return BuiltinOptions(
        base_url=mock_url,
        model="mock-vllm-model",
        endpoint="/v1/chat/completions",
        dataset={"type": "random", "input_len": 64, "output_len": 32},
        concurrency=2,
        num_prompts=2,
    )


def test_builtin_bench_against_mock(engine_opts):
    """对 mock 服务执行自研 bench：请求全部成功，指标完整且合理。"""
    m = run_builtin_bench(engine_opts, stream_cb=lambda l: None)

    assert m["successful_requests"] == 2, m
    assert m["failed_requests"] == 0, m
    assert m["concurrency"] == 2
    # 指标键齐全（口径对齐 parse_metrics）
    for key in ("output_mean", "total_mean", "req_per_s", "ttft_mean", "ttft_median",
                "ttft_p99", "tpot_mean", "tpot_median", "tpot_p99",
                "itl_mean", "itl_median", "itl_p99",
                "successful_requests", "benchmark_duration",
                "total_input_tokens", "total_generated_tokens"):
        assert key in m, f"缺少指标 {key}"
    # 服务端 usage 生效：输出 token 数 = 请求数 × max_tokens(32)
    assert m["total_generated_tokens"] == 64, f"usage 计数异常: {m['total_generated_tokens']}"
    assert m["output_mean"] > 0
    assert m["ttft_mean"] > 0
    # 输出含 vLLM 风格文本（便于日志查看）
    assert "Output token throughput" in m["raw"]


def test_builtin_bench_concurrency_scaling(mock_url):
    """并发提升 → 输出吞吐上升（负载生成器并发模型有效）。"""
    results = {}
    for conc in (1, 4):
        opts = BuiltinOptions(
            base_url=mock_url, model="mock-vllm-model",
            dataset={"type": "random", "input_len": 32, "output_len": 16},
            concurrency=conc, num_prompts=conc,
        )
        m = run_builtin_bench(opts, stream_cb=lambda l: None)
        assert m["successful_requests"] == conc
        results[conc] = m["output_mean"]
    assert results[4] > results[1], f"并发提升吞吐未上升: {results}"


def test_builtin_bench_unreachable_endpoint():
    """服务不可达：全部请求失败，抛出明确错误（不静默返回 0）。"""
    opts = BuiltinOptions(
        base_url="http://127.0.0.1:59999", model="m",
        dataset={"type": "random", "input_len": 16, "output_len": 8},
        concurrency=1, num_prompts=1, timeout=5,
    )
    with pytest.raises(RuntimeError) as exc:
        run_builtin_bench(opts, stream_cb=lambda l: None)
    assert "自研 bench" in str(exc.value)


# ---------------- 任务级集成（engine_id=benchscope 走自研引擎） ----------------


def test_task_with_builtin_engine(client, base_url, mock_url):
    """创建并发任务时指定 engine_id=benchscope：走自研引擎，真实产出指标行。"""
    payload = {
        "framework": "vllm",
        "engine_id": "benchscope",
        "model": "mock-vllm-model",
        "dataset": {"type": "random", "length_pairs": [[32, 16, "用例A", "case-a"]]},
        "concurrency_list": [1, 2],
        "gpu": {},
        "request_rate": "inf",
        "mode": "concurrency",
    }
    snap = helpers.create_and_run_task(client, base_url, payload, timeout=180)

    assert snap["status"] == "done", snap.get("error")
    rows = snap.get("rows") or []
    assert len(rows) == 2, f"应有 2 行结果（并发 1/2），实际 {len(rows)}: {rows}"

    for row in rows:
        assert "error" not in row, f"行执行出错: {row.get('error')}"
        m = row.get("metrics") or {}
        # 自研引擎指标（含 usage 精确计数）
        assert m.get("output_mean", 0) > 0, f"输出吞吐应 > 0: {m}"
        assert m.get("ttft_mean") is not None and m.get("tpot_mean") is not None
        assert m.get("successful_requests", 0) >= 1
        # 命令标记为自研引擎（不经子进程 CLI）
        assert "builtin" in (row.get("cmd") or ""), row.get("cmd")

    # 并发 2 的输出吞吐应高于并发 1
    by_conc = {int(r["concurrency"]): r["metrics"]["output_mean"] for r in rows}
    assert by_conc[2] > by_conc[1], f"并发提升吞吐未上升: {by_conc}"


def test_task_without_engine_id_uses_native_path(client, base_url):
    """未指定 engine_id：回退原生引擎链路（FAKE bench 子进程），保持旧行为兼容。"""
    payload = {
        "framework": "vllm",
        "model": "Qwen2.5-7B-Instruct",
        "dataset": {"type": "random", "length_pairs": [[64, 64, "用例A", "case-a"]]},
        "concurrency_list": [1],
        "gpu": {},
        "request_rate": "inf",
        "mode": "concurrency",
    }
    snap = helpers.create_and_run_task(client, base_url, payload, timeout=120)
    rows = snap.get("rows") or []
    assert len(rows) == 1
    m = rows[0].get("metrics") or {}
    assert m.get("output_mean", 0) > 0
    # 原生链路：命令为 vllm bench serve（FAKE 模式由 runner 仿真）
    assert "builtin" not in (rows[0].get("cmd") or ""), rows[0].get("cmd")

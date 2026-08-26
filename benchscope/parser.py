"""bench 输出解析：同时解析 mean 与 P99 两套指标。

兼容 vLLM `vllm bench serve` 与 SGLang `sglang.bench_serving` 两种输出格式。
"""
from __future__ import annotations

import re
from typing import Optional

# 指标键（统一命名）
METRIC_KEYS = [
    "output",
    "peakoutput",
    "total",
    "ttft",
    "itl",
    "tpot",
]

# 每个指标在输出中的可能标签（vllm / sglang 写法不同）
_PATTERNS: list[tuple[str, str, re.Pattern]] = []


def _add(kind: str, metric: str, regex: str):
    _PATTERNS.append((kind, metric, re.compile(regex, re.IGNORECASE)))


# ---- vLLM bench serve ----
_add("mean", "output", r"Output token throughput \(tok/s\):\s+([\d.]+)")
_add("mean", "peakoutput", r"Peak output token throughput \(tok/s\):\s+([\d.]+)")
_add("mean", "total", r"Total token throughput \(tok/s\):\s+([\d.]+)")
_add("mean", "ttft", r"Mean TTFT \(ms\):\s+([\d.]+)")
_add("median", "ttft", r"Median TTFT \(ms\):\s+([\d.]+)")
_add("p99", "ttft", r"P99 TTFT \(ms\):\s+([\d.]+)")
_add("mean", "tpot", r"Mean TPOT \(ms\):\s+([\d.]+)")
_add("median", "tpot", r"Median TPOT \(ms\):\s+([\d.]+)")
_add("p99", "tpot", r"P99 TPOT \(ms\):\s+([\d.]+)")
_add("mean", "itl", r"Mean ITL \(ms\):\s+([\d.]+)")
_add("median", "itl", r"Median ITL \(ms\):\s+([\d.]+)")
_add("p99", "itl", r"P99 ITL \(ms\):\s+([\d.]+)")
_add("scalar", "concurrency", r"Maximum request concurrency:\s+(\d+)")
_add("scalar", "successful_requests", r"Successful requests:\s+(\d+)")
_add("scalar", "failed_requests", r"Failed requests:\s+(\d+)")
_add("scalar", "benchmark_duration", r"Benchmark duration \(s\):\s+([\d.]+)")
_add("scalar", "total_input_tokens", r"Total input tokens:\s+(\d+)")
_add("scalar", "total_generated_tokens", r"Total generated tokens:\s+(\d+)")
_add("scalar", "peak_concurrent", r"Peak concurrent requests:\s+([\d.]+)")

# ---- SGLang bench_serving ----
_add("mean", "output", r"Output token throughput \(tok/s\):\s+([\d.]+)")
_add("mean", "total", r"Total token throughput \(tok/s\):\s+([\d.]+)")
_add("mean", "ttft", r"Time to first token \(TTFT\) mean \(ms\):\s+([\d.]+)")
_add("median", "ttft", r"Time to first token \(TTFT\) median \(ms\):\s+([\d.]+)")
_add("p99", "ttft", r"Time to first token \(TTFT\) p99 \(ms\):\s+([\d.]+)")
_add("mean", "tpot", r"Time per output token \(TPOT\) mean \(ms\):\s+([\d.]+)")
_add("median", "tpot", r"Time per output token \(TPOT\) median \(ms\):\s+([\d.]+)")
_add("p99", "tpot", r"Time per output token \(TPOT\) p99 \(ms\):\s+([\d.]+)")
_add("mean", "itl", r"Inter-token latency \(ITL\) mean \(ms\):\s+([\d.]+)")
_add("median", "itl", r"Inter-token latency \(ITL\) median \(ms\):\s+([\d.]+)")
_add("p99", "itl", r"Inter-token latency \(ITL\) p99 \(ms\):\s+([\d.]+)")
_add("scalar", "successful_requests", r"Successful requests:\s+(\d+)")
_add("scalar", "benchmark_duration", r"Duration:\s+([\d.]+)\s*s")
_add("scalar", "total_input_tokens", r"Total input tokens:\s+(\d+)")
_add("scalar", "total_generated_tokens", r"Total generated tokens:\s+(\d+)")

# 请求吞吐（req/s），sglang/vllm 均输出
_add("scalar", "req_per_s", r"Request throughput \(req/s\):\s+([\d.]+)")


def parse_metrics(output: str) -> dict:
    """解析 bench 输出，返回统一指标字典。

    返回结构:
    {
      "concurrency": int,
      "output": float, "peakoutput": float, "total": float,
      "ttft_mean": float, "tpot_mean": float, "itl_mean": float,
      "ttft_p99": float, "tpot_p99": float, "itl_p99": float,
      "req_per_s": float, "raw": str(完整原始输出)
    }
    """
    metrics: dict = {}
    for kind, metric, pattern in _PATTERNS:
        m = pattern.search(output)
        if m:
            # scalar 与 concurrency 类均不带后缀（如 successful_requests、concurrency）
            key = metric if kind in ("scalar", "concurrency") else f"{metric}_{kind}"
            try:
                value = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
            except ValueError:
                value = float(m.group(1))
            metrics[key] = value

    # 兼容只有 mean 没有 p99/median 的情况：缺省回退 mean
    for metric in ("ttft", "tpot", "itl"):
        mean_key = f"{metric}_mean"
        p99_key = f"{metric}_p99"
        median_key = f"{metric}_median"
        if mean_key in metrics:
            if p99_key not in metrics:
                metrics[p99_key] = metrics[mean_key]
            if median_key not in metrics:
                metrics[median_key] = metrics[mean_key]

    # 单用户 QPS = 1000 / tpot_mean（README 定义）
    if "tpot_mean" in metrics and metrics["tpot_mean"] > 0:
        metrics["single_user"] = round(1000.0 / metrics["tpot_mean"], 2)
    metrics["raw"] = output
    return metrics


def has_result_block(output: str) -> bool:
    """判断输出中是否包含结果块（可能成功或失败）。"""
    return "Serving Benchmark Result" in output or "Benchmark Result" in output

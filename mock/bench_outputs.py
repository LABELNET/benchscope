"""生成 vLLM / SGLang bench 结果的仿真输出。

输出文本与 ``benchscope/parser.py`` 中的解析正则严格对齐：

- **vLLM 风格**（``vllm bench serve``）::

    ============ Serving Benchmark Result ============
    Successful requests:                     32
    Maximum request concurrency:             32
    ...
    Output token throughput (tok/s):         1771.23
    ...
    Mean TTFT (ms):                          348.12
    P99 TTFT (ms):                           410.88
    ...

- **SGLang 风格**（``sglang.bench_serving``）::

    ============ Serving Benchmark Result ============
    ...
    Time to first token (TTFT) mean (ms):    348.12
    Time per output token (TPOT) p99 (ms):   22.87
    Inter-token latency (ITL) mean (ms):     18.01
    ...

所有指标随并发度 / 输入输出长度做**符合直觉的缩放**（并发越高吞吐越高、
时延越大），并支持 ``seed`` 复现。可被 ``BENCHSCOPE_FAKE_BENCH=1`` 的
FAKE 模式与 ``mock/cli.py`` 共同复用，是 mock 数据的唯一来源。
"""
from __future__ import annotations

import random
from typing import Optional

# ---------------------------------------------------------------- 基础统计模型

# 基准吞吐（并发=1 时的 output tok/s）与并发指数的经验参考值
_BASE_OUTPUT_TPS = 45.0
_CONC_EXP = 0.62          # 吞吐随并发的亚线性增长
_TTFT_BASE_MS = 55.0      # 并发=1 时 TTFT 基数
_TTFT_PER_CONC = 8.5      # 每增加 1 并发 TTFT 增长量
_TPOT_BASE_MS = 16.5      # 并发=1 时 TPOT 基数
_TPOT_PER_CONC = 0.5      # 每增加 1 并发 TPOT 增长量


def _scale_stats(
    concurrency: int,
    input_len: int,
    output_len: int,
    rng: random.Random,
) -> dict:
    """按并发/长度生成一组自洽的指标。"""
    c = max(int(concurrency), 1)
    input_len = max(int(input_len), 1)
    output_len = max(int(output_len), 1)

    out_tps = round(_BASE_OUTPUT_TPS * c**_CONC_EXP * rng.uniform(0.95, 1.05), 2)
    total = round(out_tps * (input_len + output_len) / output_len, 2)
    req_per_s = round(rng.uniform(0.05, c * 0.9) + 0.01, 2)
    ttft = round(_TTFT_BASE_MS + _TTFT_PER_CONC * c + rng.uniform(0, 15), 2)
    tpot = round(_TPOT_BASE_MS + _TPOT_PER_CONC * c + rng.uniform(0, 3), 2)
    itl = round(tpot * rng.uniform(0.97, 1.02), 2)
    duration = round(rng.uniform(5, 30) + c * 0.5, 2)

    def p99(v: float) -> float:
        return round(v * rng.uniform(1.05, 1.35), 2)

    def median(v: float) -> float:
        return round(v * rng.uniform(0.96, 0.99), 2)

    return {
        "concurrency": c,
        "num_prompts": c,
        "input_len": input_len,
        "output_len": output_len,
        "successful": c,
        "failed": 0,
        "duration": duration,
        "total_input_tokens": input_len * c,
        "total_generated_tokens": output_len * c,
        "req_per_s": req_per_s,
        "output": out_tps,
        "peakoutput": round(out_tps * rng.uniform(1.01, 1.05), 2),
        "total": total,
        "ttft_mean": ttft,
        "ttft_median": median(ttft),
        "ttft_p99": p99(ttft),
        "tpot_mean": tpot,
        "tpot_median": median(tpot),
        "tpot_p99": p99(tpot),
        "itl_mean": itl,
        "itl_median": median(itl),
        "itl_p99": p99(itl),
    }


# ---------------------------------------------------------------- vLLM 风格

def generate_vllm_output(
    concurrency: int = 1,
    input_len: int = 1024,
    output_len: int = 1024,
    request_rate: str | float = "inf",
    seed: Optional[int] = None,
    include_progress: bool = True,
    num_prompts: Optional[int] = None,
) -> str:
    """生成 ``vllm bench serve`` 风格的完整终端输出。"""
    rng = random.Random(seed)
    s = _scale_stats(concurrency, input_len, output_len, rng)
    prompts = num_prompts if num_prompts is not None else s["num_prompts"]

    lines: list[str] = []
    if include_progress:
        lines += _progress_lines(rng, prompts)

    lines += [
        "============ Serving Benchmark Result ============",
        "Successful requests:                     %d" % s["successful"],
        "Failed requests:                         %d" % s["failed"],
        "Maximum request concurrency:             %d" % s["concurrency"],
        "Benchmark duration (s):                  %.2f" % s["duration"],
        "Total input tokens:                      %d" % s["total_input_tokens"],
        "Total generated tokens:                  %d" % s["total_generated_tokens"],
        "Request throughput (req/s):              %.2f" % s["req_per_s"],
        "Output token throughput (tok/s):         %s" % s["output"],
        "Peak output token throughput (tok/s):    %s" % s["peakoutput"],
        "Peak concurrent requests:                %.2f" % s["concurrency"],
        "Total token throughput (tok/s):          %s" % s["total"],
        "---------------Time to First Token----------------",
        "Mean TTFT (ms):                          %s" % s["ttft_mean"],
        "Median TTFT (ms):                        %s" % s["ttft_median"],
        "P99 TTFT (ms):                           %s" % s["ttft_p99"],
        "-----Time per Output Token (excl. 1st token)------",
        "Mean TPOT (ms):                          %s" % s["tpot_mean"],
        "Median TPOT (ms):                        %s" % s["tpot_median"],
        "P99 TPOT (ms):                           %s" % s["tpot_p99"],
        "---------------Inter-token Latency----------------",
        "Mean ITL (ms):                           %s" % s["itl_mean"],
        "Median ITL (ms):                         %s" % s["itl_median"],
        "P99 ITL (ms):                            %s" % s["itl_p99"],
        "==================================================",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- SGLang 风格

def generate_sglang_output(
    concurrency: int = 1,
    input_len: int = 1024,
    output_len: int = 1024,
    request_rate: str | float = "inf",
    seed: Optional[int] = None,
    include_progress: bool = True,
    num_prompts: Optional[int] = None,
    backend: str = "openai",
) -> str:
    """生成 ``sglang.bench_serving`` 风格的完整终端输出。

    标签写法与 vLLM 不同（TTFT/TPOT/ITL 用 ``Time to first token (TTFT) mean (ms)``
    等），与 ``benchscope.parser`` 中 SGLang 的解析正则对齐；额外输出
    ``Maximum request concurrency`` 行以便解析出并发度。
    """
    rng = random.Random(seed)
    s = _scale_stats(concurrency, input_len, output_len, rng)
    prompts = num_prompts if num_prompts is not None else s["num_prompts"]

    lines: list[str] = []
    if include_progress:
        lines += _progress_lines(rng, prompts, sglang=True)

    lines += [
        "============ Serving Benchmark Result ============",
        "Backend:                                 %s" % backend,
        "Traffic request rate:                    %s" % request_rate,
        "Max concurrency:                         %d" % s["concurrency"],
        "Maximum request concurrency:             %d" % s["concurrency"],
        "Successful requests:                     %d" % s["successful"],
        "Duration:                                %.2f s" % s["duration"],
        "Total input tokens:                      %d" % s["total_input_tokens"],
        "Total generated tokens:                  %d" % s["total_generated_tokens"],
        "Request throughput (req/s):              %.2f" % s["req_per_s"],
        "Output token throughput (tok/s):         %s" % s["output"],
        "Total token throughput (tok/s):          %s" % s["total"],
        "---------------Time to First Token----------------",
        "Time to first token (TTFT) mean (ms):    %s" % s["ttft_mean"],
        "Time to first token (TTFT) median (ms):  %s" % s["ttft_median"],
        "Time to first token (TTFT) p99 (ms):     %s" % s["ttft_p99"],
        "---------------Time per Output Token----------------",
        "Time per output token (TPOT) mean (ms):  %s" % s["tpot_mean"],
        "Time per output token (TPOT) median (ms):%s" % s["tpot_median"],
        "Time per output token (TPOT) p99 (ms):   %s" % s["tpot_p99"],
        "---------------Inter-token Latency----------------",
        "Inter-token latency (ITL) mean (ms):     %s" % s["itl_mean"],
        "Inter-token latency (ITL) median (ms):   %s" % s["itl_median"],
        "Inter-token latency (ITL) p99 (ms):      %s" % s["itl_p99"],
        "==================================================",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- 公共入口

def generate_output(framework: str, **kwargs) -> str:
    """按框架名生成对应风格的 bench 输出。framework: "vllm" | "sglang"。"""
    if framework and "sglang" in str(framework).lower():
        return generate_sglang_output(**kwargs)
    return generate_vllm_output(**kwargs)


# ---------------------------------------------------------------- 进度行

def _progress_lines(rng: random.Random, num_prompts: int, sglang: bool = False) -> list[str]:
    """模拟 bench 运行中的进度/预热日志（纯展示，不影响解析）。"""
    if sglang:
        return [
            "[INFO] Benchmarks will be run on the server: http://127.0.0.1:8000",
            "[INFO] Warming up ...",
            "[INFO] Warmed up. Starting benchmarking for %d requests ..." % num_prompts,
        ]
    return [
        "INFO 01-01 00:00:00 benchmark_serving.py:1xx] Starting serving benchmark on http://127.0.0.1:8000",
        "INFO 01-01 00:00:01 benchmark_serving.py:1xx] Warming up...",
        "INFO 01-01 00:00:03 benchmark_serving.py:1xx] Warmup done. Starting benchmark for %d requests" % num_prompts,
        "100%%|████████████████████████████████████████| %d/%d" % (num_prompts, num_prompts),
    ]

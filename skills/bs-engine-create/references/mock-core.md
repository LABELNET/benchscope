# Mock 核心逻辑方法与介绍

> 适用：benchscope ≥ 1.0.7  
> 铁律：**mock 仿真代码唯一归属 `mocks/` 目录，`tests/` 不携带 mock 代码**

## 一、Mock 的定位

Mock 解决两类「无真实环境也能跑通全链路」的需求：

1. **无推理服务**：`mocks/openai_server.py` 提供 OpenAI 兼容服务（含 SSE 流式与 usage 统计），
   使自研引擎可在无 GPU、无框架的环境下端到端验证。
2. **无框架 bench CLI**：`mocks/cli.py` + `mocks/bench_outputs.py` 仿真 `vllm bench serve` /
   `sglang.bench_serving` 的输出文本，供原生引擎链路（子进程 → 输出解析）在 FAKE 模式下验证。
   启用方式：`BENCHSCOPE_FAKE_BENCH=1 python -m benchscope`。

## 二、核心方法清单

### 2.1 `mocks/bench_outputs.py` — 指标仿真（mock 数据唯一来源）

| 方法 | 签名 | 作用 |
| --- | --- | --- |
| `_scale_stats` | `(concurrency, input_len, output_len, rng) -> dict` | 生成一组**自洽**的指标（吞吐/时延随并发缩放），返回 20+ 字段字典 |
| `generate_vllm_output` | `(concurrency=1, ...) -> str` | 生成 **vLLM 风格**输出文本（对齐 `parser.py` 正则） |
| `generate_sglang_output` | `(concurrency=1, ...) -> str` | 生成 **SGLang 风格**输出文本（对齐 `parser.py` 正则） |
| `generate_output` | `(framework, **kwargs) -> str` | 按框架分发，是 mock 数据的**统一入口** |
| `_progress_lines` | `(rng, num_prompts, sglang=False) -> list[str]` | 生成进度条输出行 |

**缩放模型（保证数据符合直觉）**：

```python
_BASE_OUTPUT_TPS = 45.0   # 并发=1 时基准吞吐
_CONC_EXP   = 0.62        # 吞吐随并发亚线性增长
_TTFT_BASE_MS = 55.0      # 并发=1 TTFT 基数
_TTFT_PER_CONC = 8.5      # 每增 1 并发 TTFT 增量
_TPOT_BASE_MS = 16.5      # 并发=1 TPOT 基数
_TPOT_PER_CONC = 0.5      # 每增 1 并发 TPOT 增量
```

- `out_tps = BASE * concurrency^0.62 * U(0.95, 1.05)`
- `ttft = TTFT_BASE + 8.5 * concurrency + U(0, 15)`
- `p99 = value * U(1.05, 1.35)`，`median = value * U(0.96, 0.99)`
- 支持 `seed` 复现（同一 seed 输出一致）

### 2.2 `mocks/cli.py` — FAKE bench 命令行

| 方法 | 签名 | 作用 |
| --- | --- | --- |
| `_parse_bench_args` | `(argv) -> (dict, dict)` | 解析 bench CLI 参数为 `(parsed_args, stats_kwargs)` |
| `_detect_framework` | `(argv, explicit) -> str` | 从 argv 推断框架（vllm / sglang） |
| `main` | `(argv=None) -> int` | FAKE CLI 入口，输出仿真结果 |

### 2.3 `mocks/openai_server.py` — OpenAI 兼容 mock 服务

| 方法 | 签名 | 作用 |
| --- | --- | --- |
| `list_models` | `() -> JSON` | `GET /v1/models` |
| `chat` | `(req) -> Response` | `POST /v1/chat/completions`，支持流式与非流式 |
| `_sse_stream` | `(model, reply, thinking, include_usage, prompt_tokens, completion_tokens) -> AsyncGenerator` | SSE 增量输出；`include_usage=True` 时在 `[DONE]` 前追加只含 usage 的 chunk |
| `_mock_reply` | `(question, model, max_tokens) -> str` | 生成 mock 回复内容 |
| `_count_tokens` | `(text) -> int` | 粗略 token 计数（≈4 字符 1 token） |
| `_fill_to_tokens` | `(seed, target_tokens) -> str` | 将文本补齐到目标 token 数 |
| `main` | `(argv=None) -> int` | 服务启动入口 |

启动：`python -m mocks.openai_server --port 8001`（或 `mocks/run_mock.sh`）。

## 三、两条硬性规则（生成 mock 时必须遵守）

### 规则 1：输出文本必须匹配 `benchscope/parser.py` 的正则

vLLM 风格（注意对齐的冒号与空格）：

```
=================== Serving Benchmark Result ===================
Successful requests:                     32
Maximum request concurrency:             32
Output token throughput (tok/s):         1771.23
Total token throughput (tok/s):          3542.46
Mean TTFT (ms):                          348.12
Median TTFT (ms):                        320.10
P99 TTFT (ms):                           410.88
Mean TPOT (ms):                          22.10
P99 TPOT (ms):                           28.30
Mean ITL (ms):                           18.01
P99 ITL (ms):                            24.15
```

SGLang 风格：

```
=================== Serving Benchmark Result ===================
Request throughput (req/s):              1.79
Output token throughput (tok/s):         1771.23
Time to first token (TTFT) mean (ms):    348.12
Time to first token (TTFT) p99 (ms):     410.88
Time per output token (TPOT) mean (ms):  22.10
Time per output token (TPOT) p99 (ms):   28.30
Inter-token latency (ITL) mean (ms):     18.01
Inter-token latency (ITL) p99 (ms):      24.15
```

**不匹配则指标全部解析为 0** —— 这是 mock 输出最常见的问题。

### 规则 2：指标必须随并发「符合直觉」地缩放

- 并发↑ → 吞吐↑（亚线性）、TTFT↑、TPOT↑、ITL 与 TPOT 接近
- 复用 `_scale_stats()` 保证各指标自洽，不要各自独立随机
- 支持 `seed` 以便复现与回归测试

## 四、自研引擎与 mock 的协作

自研引擎（`benchscope/benches/builtin_bench.py`）**依赖 mock 服务返回 usage**：

- 请求带 `stream_options: {"include_usage": true}`
- mock 在流末返回独立 usage chunk（choices 为空），携带 `prompt_tokens` / `completion_tokens`
- 自研引擎优先取服务端 usage，缺失时回退按 chunk 数估算

因此为自研引擎新增/修改 mock 时，**必须保证 usage 逻辑正确**，否则输出吞吐会偏差或为 0。

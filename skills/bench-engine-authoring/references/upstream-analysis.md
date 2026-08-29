# 上游 Bench 核心逻辑分析（源码实证）

> **分析对象**：vLLM **v0.23.0** · SGLang **v0.5.10**（实际拉取源码分析，行号为对应版本文件内行号）  
> **用途**：自定义引擎实现时，复用上游经过验证的核心逻辑，保持指标口径一致  
> **完整版**：[docs/rules/BenchUpstream.md](../../../docs/rules/BenchUpstream.md)

---

## 一、源码获取（链接已验证可用）

### vLLM v0.23.0

| 项 | 值 |
| --- | --- |
| 版本 | `v0.23.0` |
| commit | `0fc695fc6d1d82e9a5ac6835ac8e4e1c83703665` |
| Git | https://github.com/vllm-project/vllm |
| **Zip** | https://github.com/vllm-project/vllm/archive/refs/tags/v0.23.0.zip |
| bench 入口 | `vllm/benchmarks/serve.py`（2052 行） |
| 请求函数 | `vllm/benchmarks/lib/endpoint_request_func.py`（861 行） |

```bash
git clone --depth 1 --branch v0.23.0 https://github.com/vllm-project/vllm
curl -L -o vllm-0.23.0.zip https://github.com/vllm-project/vllm/archive/refs/tags/v0.23.0.zip
```

### SGLang v0.5.10

| 项 | 值 |
| --- | --- |
| 版本 | `v0.5.10` |
| commit | `1519acf37c23f2189adb93f57ca9cd2db1bebf18` |
| Git | https://github.com/sgl-project/sglang |
| **Zip** | https://github.com/sgl-project/sglang/archive/refs/tags/v0.5.10.zip |
| bench 入口 | `python/sglang/bench_serving.py`（2352 行） |

```bash
git clone --depth 1 --branch v0.5.10 https://github.com/sgl-project/sglang
curl -L -o sglang-0.5.10.zip https://github.com/sgl-project/sglang/archive/refs/tags/v0.5.10.zip
```

**通用模板**（替换 `<VERSION>` / `<REPO>` 即可取任意版本）：

| 框架 | bench 入口 pinned 链接 |
| --- | --- |
| vLLM | `https://github.com/vllm-project/vllm/blob/v<VERSION>/vllm/benchmarks/serve.py` |
| SGLang | `https://github.com/sgl-project/sglang/blob/v<VERSION>/python/sglang/bench_serving.py` |

---

## 二、核心逻辑（可复制）

### 2.1 时间线采集（必须流式）

vLLM `endpoint_request_func.py:193-253`：

```python
st = time.perf_counter()              # t0
most_recent_timestamp = st
async for chunk in response.content:
    timestamp = time.perf_counter()
    if ttft == 0.0:                   # 首个 chunk
        ttft = timestamp - st         # → TTFT
        output.ttft = ttft
    else:                             # 后续 chunk
        output.itl.append(timestamp - most_recent_timestamp)   # → ITL
    most_recent_timestamp = timestamp
    output.output_tokens = usage.get("completion_tokens")
output.latency = most_recent_timestamp - st                    # → E2E
```

SGLang `bench_serving.py:180-206`：**同一模型**。

> 非流式只有一个 chunk → ITL / TTFT 无从测量，因此压测**必须 `stream=True`**。

### 2.2 指标公式（两引擎一致）

```python
# TPOT —— 分母是 output_len - 1（首 token 已计入 TTFT）
if output_len > 1:
    tpot = (latency - ttft) / (output_len - 1)
else:
    tpot = 0                          # vLLM: serve.py:463 明确记 0

# 吞吐（dur_s = 墙钟时间）
output_throughput = sum(output_lens) / dur_s
total_throughput  = (total_input + sum(output_lens)) / dur_s
request_throughput = completed / dur_s

# duration 定义
benchmark_start_time = time.perf_counter()
...  # 全部请求
benchmark_duration = time.perf_counter() - benchmark_start_time
```

| 指标 | vLLM | SGLang |
| --- | --- | --- |
| TPOT | `serve.py:460-461` | `bench_serving.py:993` |
| Output throughput | `serve.py:584` | `bench_serving.py:1095` |
| Total throughput | `serve.py:585` | `bench_serving.py:1097` |
| Request throughput | `serve.py:582` | `bench_serving.py:1093` |
| duration | `serve.py:819,887` | `bench_serving.py:1426` |

### 2.3 并发模型（semaphore + 预生成请求列表）

```python
semaphore = asyncio.Semaphore(max_concurrency)          # serve.py:807
async def limited_request_func(...):
    async with semaphore:
        return await request_func(...)

benchmark_start_time = time.perf_counter()              # serve.py:819
for request in get_request(input_requests, request_rate, ...):
    tasks.append(asyncio.create_task(limited_request_func(...)))
outputs = await asyncio.gather(*tasks)                  # serve.py:882
benchmark_duration = time.perf_counter() - benchmark_start_time   # serve.py:887
```

- 按 `num_prompts` **预生成请求列表**（每个请求有确定 prompt 与长度），semaphore 限流；
- 预生成的好处：可精确控制长度分布、支持 trace 回放与 ramp-up。

### 2.4 速率控制（gamma + 归一化补偿）

vLLM `serve.py:317-339`：

```python
theta = 1.0 / (current_request_rate * burstiness)
delay_ts.append(np.random.gamma(shape=burstiness, scale=theta))
# burstiness=1 → gamma(shape=1) ≡ 指数分布（泊松到达）
# burstiness<1 更突发；>1 更均匀

# 归一化：消除 gamma 累加和与目标总时长的 1-2% 偏差
target_total_delay_s = total_requests / request_rate
normalize_factor = target_total_delay_s / delay_ts[-1]
delay_ts = [d * normalize_factor for d in delay_ts]
```

### 2.5 输出 token 计数

| 引擎 | 方式 |
| --- | --- |
| vLLM | 服务端 `usage.completion_tokens`（`endpoint_request_func.py:241`）；为 0 时回退 tokenizer（`serve.py:442-455`） |
| SGLang (OpenAI) | `usage.completion_tokens`（`bench_serving.py:449`） |
| SGLang (原生) | `data["meta_info"]["completion_tokens"]`（`bench_serving.py:666`） |

→ **优先服务端 usage，缺失回退**（自研引擎回退为 chunk 数）。

---

## 三、实现自定义引擎：复制 + 契约适配

**推荐路径**：复用上游核心逻辑（经官方验证），只适配 benchscope 的入口 / 出口 / mock 契约。

| 契约段 | 要求 |
| --- | --- |
| **入口 Input** | 接收 `BuiltinOptions`（base_url / model / endpoint / backend / dataset / concurrency / num_prompts / request_rate / timeout / warmups / seed / extra_body） |
| **核心 Core** | **复制**上游的时间线采集 + 指标公式 + 并发与速率控制（保持口径一致） |
| **出口 Output** | 返回与 `parser.parse_metrics` 兼容的 dict：`output_mean` `total_mean` `req_per_s` `ttft_{mean,median,p99}` `tpot_{mean,median,p99}` `itl_{mean,median,p99}` `successful_requests` `failed_requests` `benchmark_duration` `total_input_tokens` `total_generated_tokens`；并提供 `raw` 文本（vLLM 风格输出，供日志与人工比对） |
| **Mock** | 在 `mocks/` 实现仿真，输出文本**必须匹配 `parser.py` 正则**（详见 [mock-core.md](mock-core.md)） |

**代码骨架**（自研引擎 `benchscope/benches/builtin_bench.py` 即按此实现，可直接参考）：

```
BuiltinOptions（入口）
   ↓
_run_async：预生成 prompt → semaphore 限流 → 并发发请求
   ↓
_request_once：SSE 流式，记录 t0/t_first/t_i/t_end + usage
   ↓
compute_metrics：按上游公式计算（TPOT 分母 n-1，duration 用墙钟）
   ↓
_format_output：vLLM 风格文本（raw）
   ↓
返回 dict → task_manager._record_row → summary → 前端展示
```

---

## 四、差异与注意事项

| 项 | 上游 | benchscope 自研 | 建议 |
| --- | --- | --- | --- |
| 速率分布 | gamma(burstiness) + 归一化 | 指数（泊松），无归一化 | 复现对比场景建议补 burstiness 与归一化 |
| 并发实现 | 预生成列表 + semaphore | worker 循环 | 语义等价；需精确长度分布时改用预生成 |
| 分位数 | `np.percentile`（linear 插值） | 最近秩（nearest-rank） | 差异极小，文档已标注 |
| 输入长度 | tokenizer 精确分词 | 近似（4 字符≈1 token） | 追求精确时可接 tokenizer（可选依赖） |
| 输出长度 | 由 max_tokens / EOS 决定 | 同 | 一致 |

**最重要**：无论怎么实现，**指标口径必须与上游一致**（尤其 TPOT 分母与 duration 定义），
否则结果无法与原生引擎对比，工具就失去作为统一评测入口的意义。

# 上游 Bench 核心逻辑分析 — BenchUpstream

> **最后更新**：2026-08-29  
> **目的**：存档 vLLM / SGLang **官方 bench 的性能测试核心逻辑**（实际拉取源码分析，含行号引用），
> 作为自研引擎与自定义引擎实现的**事实依据**。  
> **关联**：[BenchCore.md](./BenchCore.md)（自研引擎核心实现）· [BenchEngine.md](./BenchEngine.md)（引擎架构）·
> [skills/bs-engine-create](../skills/bs-engine-create/SKILL.md)（自定义引擎技能）

---

## 一、版本与源码获取（已验证可用）

### 1.1 vLLM v0.23.0

| 项 | 值 |
| --- | --- |
| **具体版本** | `v0.23.0` |
| **commit** | `0fc695fc6d1d82e9a5ac6835ac8e4e1c83703665` |
| **发布日期** | 2026-06-15 |
| **Git 仓库** | https://github.com/vllm-project/vllm |
| **Zip 下载** | https://github.com/vllm-project/vllm/archive/refs/tags/v0.23.0.zip |
| **Tarball** | https://api.github.com/repos/vllm-project/vllm/tarball/v0.23.0 |
| **bench 入口** | `vllm bench serve` → `vllm/benchmarks/serve.py`（2052 行） |
| **请求函数** | `vllm/benchmarks/lib/endpoint_request_func.py`（861 行） |
| **Pinned 链接** | `https://github.com/vllm-project/vllm/blob/v0.23.0/vllm/benchmarks/serve.py` |

```bash
# 获取方式（任选）
git clone --depth 1 --branch v0.23.0 https://github.com/vllm-project/vllm
curl -L -o vllm-0.23.0.zip https://github.com/vllm-project/vllm/archive/refs/tags/v0.23.0.zip
# 或只取单个文件（GitHub API）
curl -sL "https://api.github.com/repos/vllm-project/vllm/contents/vllm/benchmarks/serve.py?ref=v0.23.0"
```

### 1.2 SGLang v0.5.10

| 项 | 值 |
| --- | --- |
| **具体版本** | `v0.5.10` |
| **commit** | `1519acf37c23f2189adb93f57ca9cd2db1bebf18` |
| **发布日期** | 2026-04-05 |
| **Git 仓库** | https://github.com/sgl-project/sglang |
| **Zip 下载** | https://github.com/sgl-project/sglang/archive/refs/tags/v0.5.10.zip |
| **Tarball** | https://api.github.com/repos/sgl-project/sglang/tarball/v0.5.10 |
| **bench 入口** | `python -m sglang.bench_serving` → `python/sglang/bench_serving.py`（2352 行） |
| **Pinned 链接** | `https://github.com/sgl-project/sglang/blob/v0.5.10/python/sglang/bench_serving.py` |

```bash
git clone --depth 1 --branch v0.5.10 https://github.com/sgl-project/sglang
curl -L -o sglang-0.5.10.zip https://github.com/sgl-project/sglang/archive/refs/tags/v0.5.10.zip
```

---

## 二、核心逻辑（源码实证）

> 以下均取自上述版本源码，**行号为该版本文件内行号**。

### 2.1 时间线采集（TTFT / ITL / E2E）

**vLLM**（`lib/endpoint_request_func.py:193-253`）：

```python
st = time.perf_counter()              # L193  t0
most_recent_timestamp = st            # L195
...
async for chunk in response.content:
    timestamp = time.perf_counter()
    if ttft == 0.0:                   # L231-232 首个 chunk
        ttft = timestamp - st         #   → TTFT
        output.ttft = ttft
    else:                             # L236 后续 chunk
        output.itl.append(timestamp - most_recent_timestamp)   # → ITL
    most_recent_timestamp = timestamp # L238
    output.output_tokens = usage.get("completion_tokens")      # L241
output.latency = most_recent_timestamp - st                    # L253 → E2E
```

**SGLang**（`bench_serving.py:180-206`）：

```python
st = time.perf_counter()
most_recent_timestamp = st
async for chunk_bytes in response.content:
    timestamp = time.perf_counter()
    if ttft == 0.0:                         # 首个 chunk → TTFT
        ttft = timestamp - st
        output.ttft = ttft
    else:                                   # 后续 chunk → ITL
        output.itl.append(timestamp - most_recent_timestamp)
    most_recent_timestamp = timestamp
output.latency = most_recent_timestamp - st  # E2E
```

**结论**：两者**完全同一模型**——`t0 → t_first → t_i → t_end`，且**必须流式**（非流式只有一个 chunk，ITL/TTFT 无从测量）。

### 2.2 指标公式

| 指标 | vLLM | SGLang | 一致 |
| --- | --- | --- | --- |
| **TPOT** | `(latency - ttft) / (output_len - 1)`<br>`serve.py:460-461` | `(outputs[i].latency - outputs[i].ttft) / (output_len - 1)`<br>`bench_serving.py:993` | ✅ |
| **Output throughput** | `sum(actual_output_lens) / dur_s`<br>`serve.py:584` | `sum(output_lens) / dur_s`<br>`bench_serving.py:1095` | ✅ |
| **Total throughput** | `(total_input + sum(output_lens)) / dur_s`<br>`serve.py:585` | `(total_input + sum(output_lens)) / dur_s`<br>`bench_serving.py:1097` | ✅ |
| **Request throughput** | `completed / dur_s`<br>`serve.py:582` | `completed / dur_s`<br>`bench_serving.py:1093` | ✅ |
| **TTFT / ITL / E2E** | 直接统计（mean/median/p99） | 同 | ✅ |
| **duration** | `time.perf_counter() - benchmark_start_time`<br>`serve.py:819,887` | `time.perf_counter() - benchmark_start_time`<br>`bench_serving.py:1426` | ✅ |

**两个关键共识**（与自研引擎实现一致，见 BenchCore.md）：

1. **TPOT 分母是 `output_len - 1`** —— 首 token 已计入 TTFT，剩余间隔数为 N-1。
   vLLM 注释明确：`if output_len > 1: tpot = latency_minus_ttft / (output_len - 1)`，
   `output_len <= 1` 时 tpot 记 0（`serve.py:458-464`）。
2. **`duration` 是墙钟时间**（从第一个请求发出前到全部完成），非「各请求耗时之和 ÷ 并发」。

### 2.3 输出 token 计数

| 引擎 | 方式 | 源码 |
| --- | --- | --- |
| vLLM | **服务端 `usage.completion_tokens`**（流末 usage 块）；为 0 时回退 tokenizer 计数 | `endpoint_request_func.py:241`、`serve.py:442-455` |
| SGLang (OpenAI 后端) | `usage.completion_tokens` | `bench_serving.py:449` |
| SGLang (原生后端) | `data["meta_info"]["completion_tokens"]` | `bench_serving.py:666` |

> 与自研引擎策略一致：**优先服务端 usage，缺失回退估算**（自研回退为 chunk 数）。

### 2.4 并发模型

两者相同（`serve.py:807-882`、`bench_serving.py:1207`）：

```python
semaphore = asyncio.Semaphore(max_concurrency)
async def limited_request_func(...):
    async with semaphore:
        return await request_func(...)

benchmark_start_time = time.perf_counter()
for request in get_request(input_requests, request_rate, ...):   # 按速率产出请求
    tasks.append(asyncio.create_task(limited_request_func(...)))
outputs = await asyncio.gather(*tasks)
benchmark_duration = time.perf_counter() - benchmark_start_time
```

- **按 num_prompts 预生成请求列表**（每个请求有确定的 prompt/output 长度），用 semaphore 限流；
- 自研引擎用 **worker 循环**模型（c 个 worker 各自循环取任务），语义等价（并发上限 c、总量 n），
  但上游方式能精确控制每个请求的 prompt 与长度分布。

### 2.5 速率控制（vLLM 更精细）

vLLM `get_request()`（`serve.py:247-355`）：

```python
theta = 1.0 / (current_request_rate * burstiness)
delay_ts.append(np.random.gamma(shape=burstiness, scale=theta))   # L321
# burstiness=1 → gamma(shape=1) 即指数分布（泊松到达）
...
target_total_delay_s = total_requests / request_rate              # L337
normalize_factor = target_total_delay_s / delay_ts[-1]            # L338
delay_ts = [delay * normalize_factor for delay in delay_ts]       # L339
```

- 分布：**gamma(shape=burstiness, scale=1/(rate×burstiness))**；`burstiness=1` 退化为泊松；
  `<1` 更突发、`>1` 更均匀。
- **归一化补偿**：gamma 随机累加和与目标总时长有 1-2% 偏差，vLLM 用归一化因子消除
  （注释明写 "close the gap for stabilizing the throughput data from different random seeds"）。

> **与自研引擎的差异**：自研用 `random.expovariate(rate)`（等价于 burstiness=1 的泊松），
> 但**缺少归一化补偿**，也**未暴露 burstiness 参数**。→ 记录为后续优化项（见 §四）。

---

## 三、自研引擎 vs 上游：对齐情况

| 维度 | vLLM v0.23.0 | SGLang v0.5.10 | 自研 benchscope | 结论 |
| --- | --- | --- | --- | --- |
| 流式采集 | SSE | SSE | SSE（aiohttp） | ✅ 一致 |
| 时间线模型 | t0/t_first/t_i/t_end | 同 | 同 | ✅ 一致 |
| TTFT 定义 | 首 chunk - t0 | 同 | 同 | ✅ |
| ITL 定义 | t_i - t_{i-1} | 同 | 同 | ✅ |
| TPOT 定义 | (lat-ttft)/(n-1) | 同 | 同 | ✅ |
| duration | 墙钟 | 墙钟 | 墙钟 | ✅ |
| Output throughput | tokens/duration | 同 | 同 | ✅ |
| token 计数 | usage 优先 | usage 优先 | usage 优先（回退 chunk 数） | ✅ |
| 并发模型 | semaphore + 预生成列表 | 同 | worker 循环 | ⚠️ 语义等价，实现不同 |
| 速率分布 | gamma(burstiness) + 归一化 | 同（多数参数一致） | 指数（泊松），无归一化 | ⚠️ 缺 burstiness / 归一化 |
| 分位数 | `np.percentile`（linear 插值） | 同 | 最近秩（nearest-rank） | ⚠️ 有细微差异 |
| output_len<=1 时 TPOT | 记 0 | — | 记 0 | ✅ |

**结论**：**核心指标口径完全对齐**，自研引擎与原生引擎结果可直接对比。
差异集中在「非口径性细节」（速率分布精度、分位数插值方式、并发实现形式），不影响可比性。

---

## 四、后续优化项（基于上游分析）

| # | 优化 | 依据 | 优先级 |
| --- | --- | --- | --- |
| 1 | 速率控制改为 **gamma(burstiness)** + **归一化补偿**，并暴露 `burstiness` 参数 | vLLM `serve.py:317-339` | 中 |
| 2 | 并发模型改为「**预生成请求列表 + semaphore**」，支持每个请求独立 prompt/长度分布 | vLLM `serve.py:807-882` | 中 |
| 3 | 分位数改为 `np.percentile` **linear 插值**（或说明差异） | 两者均用 numpy | 低 |
| 4 | `output_len <= 1` 时 TPOT 记 0（自研已实现） | vLLM `serve.py:463` | ✅ 已对齐 |
| 5 | 支持 `output_throughput_retokenized`（SGLang 有本地重分词口径） | `bench_serving.py:1096` | 低 |

---

## 五、自定义引擎实现方法（复制上游代码 + 契约适配）

用户新增引擎版本（如 vllm 0.24）时，推荐实现路径：

1. **拉取目标版本源码**（见 §1 命令），定位 bench 入口文件；
2. **复用其核心逻辑**：时间线采集、指标公式、并发与速率控制（这些是通用且经过验证的）；
3. **适配 benchscope 的三段契约**：

| 契约 | 要求 |
| --- | --- |
| **入口（Input）** | 读取 `BuiltinOptions` / payload（base_url、model、endpoint、backend、dataset、concurrency、num_prompts、request_rate、timeout、warmups…） |
| **处理（Core）** | 复制上游的负载生成 + 时间线采集 + 指标计算，保持口径一致 |
| **出口（Output）** | 返回与 `parser.parse_metrics` 兼容的 dict（output_mean / total_mean / req_per_s / ttft_* / tpot_* / itl_* / successful_requests…），并提供 `raw` 文本（vLLM 风格，供日志与展示） |
| **Mock** | 在 `mocks/` 实现仿真输出，文本必须匹配 `parser.py` 正则（见 [mock-core.md](../skills/bs-engine-create/references/mock-core.md)） |

4. **校验导入**：`POST /api/benchs/import`（dry_run）或 `scripts/validate.sh`，全部通过方可导入。

> 详见技能文档 [bs-engine-create](../skills/bs-engine-create/SKILL.md) 与其
> [import-checklist.md](../skills/bs-engine-create/references/import-checklist.md)。

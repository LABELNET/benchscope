# 自研 Bench 引擎核心实现总结 — BenchCore

> **版本**：v1.0.7 · **最后更新**：2026-08-28 22:30:00  
> **定位**：本文是**自研 bench 引擎（benchscope builtin）的核心实现总结与存档**，回答「自研 bench 的核心是什么、怎么实现的、为什么这样设计」。  
> **关联**：[BenchEngine.md](./BenchEngine.md)（整体引擎架构）· [Architecture.md](./Architecture.md) · 源码 `benchscope/benches/builtin_bench.py`

---

## 一、核心结论（一句话）

> **自研 bench 的核心 = 「基于 OpenAI 兼容 API 的异步流式负载生成器」+「与 vLLM bench 严格对齐的指标口径」。**

前者决定**能不能测**（不装框架、远程可测、高并发），后者决定**测得准不准、能不能和原生引擎对比**。

**为什么这两点才是核心**（而非"再造一个压测工具"）：
1. 若只做负载生成而不对齐口径，自研测出的数无法与 `vllm bench` / `sglang.bench_serving` 对比，工具就失去了作为统一评测入口的意义；
2. 若只对齐口径而不能用（要装 vLLM 才能跑），就退化成原生引擎的复刻，失去"pip 装完即可测任意服务"的价值。

---

## 二、为什么必须「流式」

压测指标中，只有走 SSE 流式才能拿到**真正的**首 token 与 token 间隔：

| 方式 | 可测量 | 不可测量 |
| --- | --- | --- |
| 非流式（等完整响应） | E2E 延迟、总吞吐 | **TTFT、ITL、TPOT 均不可测** |
| **流式（SSE）** | TTFT、ITL、TPOT、E2E、全部吞吐 | — |

因此自研引擎**强制 `stream: true`**，在收到每个 chunk 时打点，构成单请求时间线：

```
t0        发出请求
t_first   首个内容 chunk 到达   → TTFT = t_first - t0
t_i       第 i 个 chunk 到达    → ITL_i = t_i - t_{i-1}
t_end     流结束（[DONE]）      → E2E  = t_end - t0
N         输出 token 数         → 服务端 usage.completion_tokens
```

---

## 三、四个子系统的实现

### ① LoadGenerator — 负载生成

| 设计点 | 实现 | 为什么 |
| --- | --- | --- |
| 并发模型 | `concurrency` 个 worker 持续发请求，直到累计完成 `num_prompts` | 与 vLLM bench 语义一致，结果可比 |
| 速率控制 | `request_rate=inf` 全速；数值 → `expovariate(rate)` 泊松到达 | 泊松到达贴近真实流量分布 |
| 停止机制 | `threading.Event`（来自 BenchRunner）→ `asyncio.Event` 轮询桥接 | 复用既有停止通道，用户点停止可即时中断 |
| 预热 | `num_warmups` 个请求先跑，不计入指标 | 消除冷启动（编译 / 权重加载）对 TTFT 的污染 |
| prompt 构造 | 按 `chars_per_token`（默认 4）反推字符数随机组词 | 零 tokenizer 依赖，可控制目标输入长度 |

### ② Requester — SSE 执行与采集

- **技术栈**：`aiohttp`（`TCPConnector(limit=0)` 不限制并发）
- **端点**：`/v1/chat/completions`（`backend=openai-chat`）/ `/v1/completions`（`backend=openai`）
- **token 计数**：请求带 `stream_options.include_usage: true`，从流末的 usage chunk 取 `completion_tokens`；服务端不返回时**回退按 chunk 数估算**
- **单请求异常隔离**：连接错误 / 超时 / HTTP 非 200 均记为失败请求，**不影响其他 worker**（try/except 包在单个请求内）

### ③ MetricsCollector — 指标计算（**核心中的核心**）

严格对齐 vLLM bench 定义：

| 指标 | 计算口径 |
| --- | --- |
| `output_mean` | `总 completion_tokens / benchmark_duration` |
| `total_mean` | `(总 prompt_tokens + 总 completion_tokens) / duration` |
| `req_per_s` | `成功请求数 / duration` |
| `ttft_{mean,median,p99}` | 首 token 延迟（ms） |
| **`tpot_{mean,median,p99}`** | **`(E2E - TTFT) / (completion_tokens - 1)`**（ms） |
| `itl_{mean,median,p99}` | 相邻 chunk 间隔 `t_i - t_{i-1}`（ms） |
| `e2e_{mean,median,p99}` | `t_end - t0`（ms） |
| `peakoutput_mean` | 1 秒滑窗内最大完成 token 数 |
| `single_user` | 用户 QPS = `1000 / tpot_mean` |
| `successful/failed_requests` | 成功 / 失败计数 |

**两个易错点（实现中已处理）**：
1. **TPOT 分母是 `tokens - 1` 而非 `tokens`**：首 token 已计入 TTFT，剩余间隔数为 N-1。用错分母会让长输出场景的 TPOT 系统性偏低。
2. **`benchmark_duration` 必须是墙钟时间**（所有 worker 从开始到最后一个请求完成），这是 throughput 可比的关键；用"各请求耗时之和 / 并发"会严重高估吞吐。

**分位数实现**：最近秩（nearest-rank，`ordered[ceil(p*n)-1]`），与 numpy / vLLM 语义一致；**单样本时直接返回该值**（`statistics.quantiles` 在 n=1 时会抛错，已规避）。

### ④ ResultSink — 结果集成

自研引擎直接返回 metrics dict → 复用既有链路：`task_manager._record_row` → `summary`（CSV/xlsx）→ 前端 Realtime / Perf Datas 展示。

**同时输出 vLLM 风格文本**（`============ Serving Benchmark Result ============`），便于终端日志查看与人工比对。

---

## 四、与原生引擎的执行链路对比

```
                    自研引擎（builtin）              原生引擎（vllm / sglang）
参数来源            curated + dataset                curated + dataset
命令构建            ❌ 不需要                         ✅ build_command() → CLI
执行方式            ✅ 进程内 asyncio.run             ✅ 子进程 bash -lic
输出解析            ❌ 不需要（结构化直出）           ✅ parser 正则解析
环境依赖            ❌ 无（仅 aiohttp）               ✅ torch + vllm/sglang（需校验）
远程服务测试        ✅ 天然支持                       ⚠️ 需本地装框架工具
指标口径            对齐 vLLM                         原生口径
```

判定与分支在 `task_manager._builtin_engine()` + `_run_one()`，未指定 `engine_id` 的旧任务**回退原生链路**（向后兼容）。

---

## 五、关键设计决策与取舍

| 决策 | 选择 | 理由 | 代价 |
| --- | --- | --- | --- |
| 异步 HTTP | **aiohttp** | 成熟高并发、SSE 友好 | 新增一个依赖 |
| 输出 token 计数 | **服务端 usage**，缺失回退 chunk 数 | 精确，且不引入分词依赖 | 依赖服务端支持（多数现代服务支持） |
| 输入长度控制 | **近似构造**（字符/token 比） | 零依赖 | 长度不精确到 token |
| 分位数 | **最近秩**（纯 Python） | 与 numpy 语义一致，零依赖 | 非插值（与 numpy linear 略有差异，可接受） |
| 全部请求失败 | **抛错**而非返回全 0 | 避免全 0 指标被误判为"测试成功" | — |
| 单请求异常 | **隔离**，记为失败请求 | 一个请求失败不拖垮整轮 | — |

---

## 六、验证结果（对 mock 服务实测）

```
conc= 1  out_tps=  64.9  req/s= 2.03  ttft=2.43ms  tpot=15.83ms  ok=1
conc= 2  out_tps= 130.5  req/s= 4.08  ttft=2.17ms  tpot=15.73ms  ok=2
conc= 4  out_tps= 260.2  req/s= 8.13  ttft=2.06ms  tpot=15.79ms  ok=4
conc= 8  out_tps= 517.8  req/s=16.18  ttft=2.92ms  tpot=15.83ms  ok=8
```

**结论**：
- 吞吐随并发**线性增长**（64.9 → 130.5 → 260.2 → 517.8，近似翻倍）→ 负载生成器并发模型有效；
- TPOT 稳定 ≈15.8ms、TTFT 稳定 ≈2-3ms → 指标采集口径正确（未随并发漂移）；
- usage 精确计数生效（32 token/请求，与 mock 配置一致）。

---

## 七、已知限制与后续优化

| 限制 | 说明 | 可能的优化 |
| --- | --- | --- |
| 输入长度近似 | 按字符/token 比构造，不精确到 token | 可选接入 tokenizer（transformers / tiktoken）精确分词 |
| 输出长度依赖服务端 | 由 `max_tokens` 与 EOS 决定，客户端不强制 | 可增加"强制生成到 N token"模式（ignore_eos 语义） |
| 数据集仅 random | 当前实现 random 分布；sharegpt / custom 未在自研引擎落地 | 复用既有 sharegpt 数据集加载逻辑 |
| 多轮对话未支持 | 单轮请求 | 可扩展多轮会话序列 |
| peak throughput 为估算 | 1 秒滑窗近似 | 可对齐 vLLM 的精确窗口算法 |

---

## 八、代码地图

| 文件 | 职责 |
| --- | --- |
| `benchscope/benches/builtin_bench.py` | **自研引擎全部实现**：`BuiltinOptions` / `RequestRecord` / `_request_once`（SSE 采集）/ `_run_async`（负载编排）/ `compute_metrics`（指标口径）/ `run_builtin_bench`（同步入口） |
| `benchscope/task_manager.py` | `_builtin_engine()` 判定、`_builtin_options()` 映射、`_run_one()` 分支 |
| `benchscope/benchs.py` | 引擎注册表 + 环境校验（`check_env` / `_match_spec`） |
| `benchscope/bench_params.py` | 参数描述与下拉选项加载（**注意**：不可命名为 `benchs`，与 `benchs.py` 模块同名会冲突） |
| `benchscope/configs/benchs.yaml` | 引擎定义（扩展点） |
| `benchscope/configs/bench-params.yaml` | 参数描述与选项（扩展点） |
| `mocks/openai_server.py` | mock 服务（支持 `stream_options.include_usage`，供自研引擎联调） |
| `tests/api/test_builtin_bench.py` | 自研引擎测试（口径 / 并发扩展 / 任务级集成） |

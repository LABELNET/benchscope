# Performance-Create（创建任务页）— 功能与约束说明

> **版本**：v1.0.6  
> **最后更新**：2026-08-28  
> **文档状态**：Performance 创建任务子页面（`/performance/create`）的三步表单、双模式与约束说明  
> **关联文档**：[Performance.md](./Performance.md)（任务执行页双模式核心逻辑）

---

## 0. 总览

创建任务页为独立路由 `/performance/create`，通过 `?mode=concurrency|threshold` 区分两种执行模式（由 Performance 默认页的两个入口按钮进入）。三步表单：**Step 1 性能条件 → Step 2 性能参数 → Step 3 启动测试**。

---

## 1. Step 1 性能条件

### 1.0 测试引擎选择（BenchPicker，1.0.7）

- 位于 Step1 顶部：下拉选择**测试引擎**（**Bench CLI** 自研 `benchscope` / 原生 `vllm-0.23` / `sglang-0.5.10`），引擎定义来自 `GET /api/benchs`（`benchscope/configs/benchs.yaml`，可用户扩展）
- 选中后展示引擎介绍文案；原生引擎展示**环境校验明细**（要求版本 / 已安装 / OK-FAIL / 安装提示）
- **环境校验约定（强制）**：原生引擎（vllm / sglang）必须校验 `torch` 与目标框架安装版本（+ CLI 可用性），**不满足则点击「下一步」被阻断**并提示 `benchEnvBlocked`；**Bench CLI 自研引擎无框架环境依赖，恒可用**（pip 安装即可远程测 OpenAI 兼容服务）
- 引擎 id 随 payload 提交（`engine_id` 字段）
- **引擎决定后续步骤（1.0.7）**：切换引擎时同步刷新「参数定义（paramSpecs）」与「引擎参数清单（params-yaml）」，Step2 与 Step3 均跟随当前引擎变化（见 §2 / §3）

### 1.1 环境面板（BaseEnvPanel）

- 展示：框架（vLLM / SGLang）、模型选择（来自 `/v1/models`，可刷新）、Base URL、推理服务在线状态
- 「去设置」按钮 → 跳转 Settings 页

### 1.2 条件组（ConditionPanel）

- 支持**多组条件**（每组一个「输入长度 × 输出长度」条件 + 数据集 + 请求速率 + 阈值条件）
- 每组有唯一 `id`（自增），用于生成 `case_id`（**多组相同条件不叠加**的关键，见 Performance.md §2.1）
- **并发模式**：每组显示「请求数条件」多选（默认 1,4,8,16,32,40,64,128，可编辑）；请求速率 Inf / Follow
- **阈值模式**：每组显示三行阈值条件（均可编辑）：
  - `TTFT`：统计量选择（**Mean / Median / P99**，默认 Mean）+ 阈值 ≤ X ms（默认 0）
  - `TPOT`：统计量选择（**Mean / Median / P99**，默认 Mean）+ 阈值 ≤ X ms（默认 100）
  - `Output token throughput`：阈值 ≤ Y tok/s（默认 0）

### 1.3 校验（validateStep1）

| 项 | 规则 |
| --- | --- |
| 模型 | 必选，否则提示「请选择模型」 |
| 条件组 | 至少一组，否则提示 |
| 请求数（并发模式） | 至少一个正整数值，自动去重升序 |
| TTFT / TPOT / Output 阈值（阈值模式） | 均必须为非负整数 |
| 阈值三者非全零（阈值模式） | **每组独立校验**：TTFT、TPOT、Output 三者阈值不能同时为 0，否则提示「TTFT / TPOT / Output token throughput 阈值不能同时为 0，请至少设置一项」，且不能进入下一步 |

---

## 2. Step 2 性能参数（跟随引擎，1.0.7）

- **取消双框架 Tab（vLLM / SGLang）**，改为**单参数面板**：只显示 Step1 所选引擎的参数（前面选什么引擎，后面就显示什么参数，不需要全部显示）
- 面板顶部展示当前引擎标识（名称 + 版本）与说明文案（`paramsEngineHint`）
- 参数来源：`GET /api/benchs/{id}/params-yaml` → `benchscope/configs/{params_key}-default.yaml`
  - Bench CLI（自研）→ `benchscope-default.yaml`
  - vLLM 原生 → `vllm-default.yaml`；SGLang 原生 → `sglang-default.yaml`
- 参数说明与下拉可选值来自 `benchscope/configs/bench-params.yaml` 中该引擎的 `params_key` 段（每个 option 必须带 `description`）
- **参数表单仅内存修改（syncEngineParams），不写入文件**；修改结果用于后续命令生成与任务执行

**Bench CLI 参数配置清单**（`benchscope-default.yaml`，与 `bench-params.yaml` 的 `benchscope` 段一一对应）：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `backend` | `openai-chat` | 接口协议：`openai-chat`（/v1/chat/completions） / `openai`（/v1/completions） |
| `endpoint` | `/v1/chat/completions` | 被测服务接口路径 |
| `request-rate` | `inf` | 请求速率 req/s；`inf` 为全速（测最大吞吐） |
| `num-prompts` | `0` | 请求总数；`0` = 跟随并发数 |
| `num-warmups` | `0` | 预热请求数（不计入指标），消除冷启动影响 |
| `chars-per-token` | `4` | 字符 / token 近似换算比（英文 4，中文 2） |
| `timeout` | `600` | 单请求超时（秒），超时计为失败 |
| `temperature` | `0.0` | 采样温度，压测建议固定 0 保证可复现 |
| `seed` | `0` | 随机种子，`0` = 不固定 |

---

## 3. Step 3 启动测试

- 预览**任务条件**（测试引擎 / 框架 / 模型 / Base URL / 数据集组 / 模式相关参数）
- 预览**命令**（`/api/tasks/preview` 生成的首条命令），**命令随引擎变化**（1.0.7）：
  - **Bench CLI（自研，`kind=builtin`）** → `benchscope perf --model ... --concurrency ...`，
    标题行展示引擎标签与「复制」按钮，附说明 `commandHintBuiltin`
  - **原生引擎（vllm / sglang）** → 对应 CLI 命令（`vllm bench serve` / `python -m sglang.bench_serving`），
    Step2 编辑的引擎参数以 `--key=value` 附加
- Bench CLI 预览命令**可直接复制到终端执行**（新增 `benchscope perf` 子命令，见 [rules/BenchEngine.md](../rules/BenchEngine.md)）
- 「启动」→ Modal 确认 → `createTask` + `startTask` + 设为当前任务 → 跳回 `/performance` 任务执行页

---

## 4. Payload 构建（buildPayload）

```text
framework: 框架，由所选引擎的 framework 字段决定（Environment 不再单独配置框架）
model / tokenizer
engine_id: 测试引擎 id（benchscope / vllm-0.23 / sglang-0.5.10，决定命令与参数）
engine_params_yaml: 当前引擎的参数清单（Step2 内存编辑后的序列化文本，随引擎切换）
  # 自研引擎：据此构造执行选项与预览命令（build_options / build_command）
  # 原生引擎：据此以 --key=value 附加到 CLI 命令（merge_extra_args）
params_yaml: { vllm, sglang }（保留为空字符串，向后兼容字段，已被 engine_params_yaml 取代）
dataset: { type: random, length_pairs: [[inputLen, outputLen, "IxO", case_id, {阈值}], ...] }
  # 第 4 元素为唯一组 id（相同条件多组不叠加）；第 5 元素为该组阈值 dict——阈值信息跟随每组请求配置，不跟随主任务：
  #   { ttft_statistic, ttft_threshold_ms, tpot_statistic, tpot_threshold_ms, output_throughput_threshold }
  #   （并发模式：全为 0 / mean；阈值模式：取每组各自的统计量与阈值，0 表示该指标不参与判定）
concurrency_list: 并发模式 = 首组请求数；阈值模式 = [1]
request_rate: inf | follow
ttft_threshold_ms / ttft_statistic（保留：取第一组值，向后兼容旧逻辑/旧数据回退）
tpot_threshold_ms / tpot_statistic（保留：取第一组值，向后兼容旧逻辑/旧数据回退）
output_throughput_threshold（保留：取第一组值，向后兼容旧逻辑/旧数据回退）
mode: concurrency | threshold
```

---

## 5. 约束与边界

| 项 | 约束 |
| --- | --- |
| 模式判定 | 仅由路由 `?mode=` 决定，进入后不可切换 |
| 请求数条件 | 并发模式仅取**第一组**的请求数作为 `concurrency_list`；多组条件下其余组的请求数不参与执行（仅展示） |
| 阈值模式 | `concurrency_list` 恒为 `[1]`，实际并发由执行页阈值策略动态探测 |
| 参数 YAML | 修改仅存内存，刷新页面丢失；不写回配置文件 |
| 引擎联动 | Step2 参数面板与 Step3 命令预览均跟随 Step1 所选引擎；切换引擎会重新拉取参数清单，未保存的内存修改随之丢弃 |
| 页面宽度 | 居中窄栏（max 760px），紧凑显示 |

## 6. 相关文档约定

> **约定**：后续对该子页面的设计/界面修改、逻辑与策略调整、UI 调整，均需同步更新本文档。

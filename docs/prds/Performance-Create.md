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

## 2. Step 2 性能参数

- 双框架 Tab（vLLM / SGLang），当前框架 Tab 可编辑，另一框架只读
- 参数按组展示（server / sampling / resource / benchmark / other），来源为后端 YAML 配置（`/api/config/params-yaml/{fw}`，`benchscope/configs/{fw}-default.yaml`）
- **参数表单仅内存修改（syncParams），不写入文件**；修改结果用于后续命令生成

---

## 3. Step 3 启动测试

- 预览**任务条件**（框架 / 模型 / Base URL / 数据集组 / 模式相关参数）
- 预览**命令**（`/api/tasks/preview` 生成的首条命令）
- 「启动」→ Modal 确认 → `createTask` + `startTask` + 设为当前任务 → 跳回 `/performance` 任务执行页

---

## 4. Payload 构建（buildPayload）

```text
framework / model / tokenizer
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
params_yaml: { vllm, sglang }（内存参数序列化）
```

---

## 5. 约束与边界

| 项 | 约束 |
| --- | --- |
| 模式判定 | 仅由路由 `?mode=` 决定，进入后不可切换 |
| 请求数条件 | 并发模式仅取**第一组**的请求数作为 `concurrency_list`；多组条件下其余组的请求数不参与执行（仅展示） |
| 阈值模式 | `concurrency_list` 恒为 `[1]`，实际并发由执行页阈值策略动态探测 |
| 参数 YAML | 修改仅存内存，刷新页面丢失；不写回配置文件 |
| 页面宽度 | 居中窄栏（max 760px），紧凑显示 |

## 6. 相关文档约定

> **约定**：后续对该子页面的设计/界面修改、逻辑与策略调整、UI 调整，均需同步更新本文档。

·# benchscope Accuracy 页面 — 功能与约束说明

> **版本**：v1.0.8
> **最后更新**：2026-08-31
> **文档状态**：Accuracy（独立精度测试模块）页面功能、实现策略与约束说明
> **关联文档**：[Performance.md](./Performance.md) · [Dashboard.md](./Dashboard.md) · [Datas.md](./Datas.md) · [../rules/AccuracyEngine.md](../rules/AccuracyEngine.md)

---

## 0. 总览

Accuracy 页面为**独立精度测试模块**的主页面（1.0.8 落地，替换原 v5.0 占位页）：Native 原生精度 / Serving 链路精度双模式评测，与性能模块彻底解耦。顶部导航第 3 项「Accuracy」进入；创建任务走 `/accuracy/create` 三步向导。

后端独立包 `benchscope/accuracy/`（架构详见 [rules/AccuracyEngine.md](../rules/AccuracyEngine.md)）：
- `EvalTaskManager` 独立调度（`pending → running → done|stopped|error`），落库三件套 `evals/<task_id>/task.json + result.json + samples.jsonl`（另写 `run.json` 接入 Datas 记录体系）；
- `run_eval` 评测核心（CLI `benchscope eval` 与 Web 任务共用）：数据集加载 → Prompt 构建 → 批量推理（Serving aiohttp / Native transformers / Mock 可控伪输出）→ 判分（choice / math / code / judge）→ 指标汇总 → 基线对标；
- WS 消息族 `eval_task_*`（快照回放 / started / log / progress / result / done / error）。

## 1. 任务列表（无任务 → 介绍页）

- **无任务（1.0.8 对齐 Performance）**：介绍页与 Performance 默认页结构/样式一致——`.perf-intro` + `.planned-card` + `a-result`（标题「精度测试」/描述一句话/主色图标 `FundOutlined`（与主导航 Accuracy 项一致）/CTA「创建精度任务」）+ `.features` 三张特性卡（**模型链路精度测评 / 离线模型精度测评 / 模型精度基准对比**，各 ≤2 行说明，居中、`text-align:center`、antd 语义色）。
- **有任务**：任务表格（任务 ID / 模型（LoRA 标签）/ 模式（Native|Serving）/ 数据集 / 状态 / accuracy 或运行进度 / 停止 / 删除）+ 点击行进入详情；「刷新」「创建精度任务」按钮。

## 2. 创建任务（/accuracy/create 三步向导）

### Step1 数据集（沿用 Settings → Datasets 体系）

- 来源单选：**内置评测数据集**（`configs/datasets.yaml` 带 eval 元数据的 9 个：MMLU / CMMLU / C-Eval / GSM8K / MATH / HumanEval / MBPP / MT-Bench / GAOKAO-Bench，显示类别 / 判分器 / 样本量 / 下载缓存状态）/ **本地路径 JSONL**（免上传直接引用，标准字段 `question / answer`，可选 `choices / subject`；判分器按字段自动探测）。
- 预览按钮 → 前 5 条样本（题干 / prompt / 标准答案）。
- 样本抽样上限（0 = 全量；固定种子抽样可复现）。

### Step2 模式与模型

- **模式**：Serving 链路（OpenAI 兼容服务）/ Native 原生（本地权重；说明环境要求与无 Token 统计边界）。
- **评测引擎**（`GET /api/accuracy/engines`）：`benchscope`（serving）/ `native-hf`（native）/ `mock`（联调）；选中后展示环境校验明细（`env-check`），native 不满足（torch / transformers / CUDA）**阻断下一步**。
- **Provider**（Serving）：复用 Settings → Providers（激活项默认）。
- **模型**：沿用 Settings → Models 厂商目录（下拉搜索）/ 自定义（模型名或 Native 本地权重路径）。
- **LoRA 微调增量模型**：`lora_path`（peft adapter 路径，Native 经 peft 合并加载；Serving 请求服务端已注册 adapter，`lora_name`）——微调前后的精度与性能均可对比。
- 推理参数：全局种子 / 温度 / top_p / max_tokens / 并发推理数（Serving）；MT-Bench 数据集需填评审模型（judge）。

### Step3 预览与启动（Token 强提醒）

- payload 摘要 + **等效 CLI 命令**（`benchscope eval ...`，可复制执行）。
- **Serving 模式强提醒弹窗**（固定文案，`Modal.confirm`）：数据集 / 预估总 Token（含输入 / 输出拆分、样本数与预估口径）/「该消耗会计入线上推理资源计费/负载」/ 确认启动。预估接口 `GET /api/accuracy/estimate`（优先级：数据集实测统计 > 内置常量表 `configs/token_estimates.yaml` > 字符估算）。
- 确认后 `POST /api/accuracy/tasks`（创建即启动）→ 跳回 Accuracy 页。

## 3. 任务详情（实时 + 报表）

| 区块 | 内容 |
| --- | --- |
| 头部 | 任务名 / 模式标签 / 状态 / 运行进度条（done/total）/ 停止按钮 |
| 核心指标 | 六指标卡：accuracy / pass_rate / 总样本 / 正确 / 错误 / 无效；数据集专属指标标签（exact_match / pass@1 / mt_bench_score 等）；评测结论（合格 / 精度下跌 / 异常）+ 错因标签分布 |
| Token 统计（Serving） | 输入 / 输出 / 总消耗 / 单样本均值；**预估 vs 实际**偏差 |
| 基线对标 | 档位标签（S/A/B/C）/ 对标基线与差值 pp / 同尺寸排名 / 自动结论（优于 / 持平 / 明显劣于-风险预警） |
| 分学科准确率 | 学科 / 正确 / 总数 / accuracy（知识类） |
| 评测日志 | 实时终端（WS `eval_task_log`，自动滚动） |
| 单样本溯源 | 表格（# / 学科 / Prompt / 输出 / 标准答案 / Token(入/出) / 判定+错因），筛选全部 / 答错 / 无效；**导出错题集**（JSONL 下载） |

## 4. Datas/evals 与 Dashboard 联动

- **Datas → Evals**：精度记录列表（来自既有 `listRuns` 扫描 evals_dir，`run.json` kind=eval），摘要列显示 accuracy；勾选 2 条 →「对比」面板（横向主指标表 + **Native vs Serving 一致性差值**：|diff|≤2pp 训推一致 / ≤5pp 存在偏差 / >5pp 显著偏差）；详情跳 Accuracy、日志下载。
- **Dashboard**：Overview 六宫格 Total/Max Acc Records 实数；Eval Records 表格（Run ID / Model / Accuracy / Status / Time / 详情）接通真实数据。

## 5. 约束与边界

| 项 | 约束 |
| --- | --- |
| 解耦 | `accuracy/` 不 import 性能模块代码；不承载任何性能指标（QPS / 延迟 / 吞吐） |
| 双模式边界 | Native 模式无 Token 统计（`result.tokens = null`）；judge（MT-Bench）仅 Serving / Mock 支持 |
| LoRA | Serving 需服务端已启用 LoRA（vLLM `--enable-lora --lora-modules`，`model` 用 adapter 注册名）；Native 需 peft（extras `benchscope[accuracy-native]`） |
| 代码沙箱 | HumanEval / MBPP 判分在受限子进程执行（`-I` 隔离 + 超时 + 临时目录），属预期行为 |
| 数据集 | 内置数据集启动评测时自动下载（ModelScope 优先，缓存 `datasets_dir/<id>/`）；GAOKAO-Bench 自动判分取客观题子集 |
| i18n | 全部文案走 zh/en 词典（`acc*` / `evals*` 键），`npm run check:i18n` 校验 |
| 主题 | antd 变量（亮/暗自适应），组件复用 antd 表格 / 卡片 / 步骤条范式 |

## 6. 相关文档约定

> **约定**：后续对 Accuracy 页面的设计/界面修改、逻辑与策略调整、UI 调整，均需同步更新本文档。

# VERSION 1.0.8 — 版本修订记录

> **版本**：1.0.8  
> **状态**：开发中（In Development）  
> **发布时间**：待定  
> **文档状态**：当前开发版本——**未特别说明版本号时，项目内容所有变更均迭代在此版本**（显示 `v1.0.8-dev`），按时间顺序追加到本文档；仅当明确「迭代下一个版本」才切换  
> **目录**：页面级行为细则见 `docs/prds/`；版本路线见 `docs/Roadmap.md`

---

## 1. 版本概述

1.0.8 为 1.0.7 发布后的**迭代开发版本**，主目标：**独立精度测试模块（Accuracy）落地**——在完全脱离性能模块的前提下，建成「Native 原生精度 + Serving 链路精度」双模式评测闭环：标准精度指标全覆盖（知识 / 数学 / 代码 / 对话 / 中文专项 9 数据集）、开源模型基准对标（基线库 + 档位评级 + 能力雷达图）、Serving 模式 Token 消耗预估算 + 强提醒，全量数据落库可溯源、可对比、可基线。

规划功能见 [docs/Roadmap.md](../Roadmap.md) 1.0.8 小节，逐项落地后在此按时间顺序记录迭代明细。

---

## 2. 版本规划目标（用户确认版）

### 主目标：独立精度测试模块（Accuracy）

规划来源：《BenchScope 独立精度测试模块完整功能规划》（2026-08-30 需求附件，七大模块：独立任务管理 / 数据集管理 / 精度打分引擎 / Token 预估与统计 / 开源基线对比 / 精度对比报表 / 错误样本溯源）。经用户确认两项范围决策：

1. **Native 模式采用引擎抽象**（对齐 1.0.7 bench 引擎模式）：不引入 `torch` / `transformers` 必装依赖，仅检测运行环境已安装的相关依赖（版本不满足则阻断选择）；开发与测试使用 mock 环境全链路验证。
2. **9 个专项数据集全部实现**：含 HumanEval / MBPP 代码沙箱 `pass@1` 与 MT-Bench LLM-as-judge。
3. **精度测试提供内置命令 `benchscope eval`**（对齐 `benchscope perf` 模式，2026-08-30 补充确认）；**bench engines 体系增加精度相关测试内容**——精度引擎注册并入 `configs/benchs.yaml` 引擎体系（引擎清单 / 对比表 / 引擎介绍纳入精度评测能力），精度任务管理 / 结果落库 / 报表仍与性能模块完全独立。
4. **模型与数据集沿用设置界面内容，支持自定义路径；被测对象包含 LoRA 微调训练的增量模型（精度 + 性能推理测试）**（2026-08-30 补充确认）：模型沿用 Settings → Models 厂商目录（`configs/models.yaml`）、数据集沿用 Settings → Datasets 内置数据集体系（`configs/datasets.yaml` 下载缓存）；新增自定义路径模型（本地权重路径 / 自定义模型名）与自定义路径数据集（本地 JSONL 免上传）；**LoRA 微调训练产出的增量模型（adapter 路径）作为被测模型**——精度测试与性能测试均可对其进行推理测试（精度：Native 经 peft 加载 / Serving 请求服务端已注册 adapter；性能：压测请求 adapter 注册名）。

#### 硬性约束（强制）

1. **完全独立拆分**：精度模块与压测 / 性能模块彻底解耦，不复用任何性能代码、调度、报表、指标，自成一套闭环系统（独立任务表 / 结果表 / 报表 / 调度队列，Job 逻辑完全独立）。
2. **双模式独立运行**：Native 原生精度、Serving 链路精度互不依赖，可单独执行。
3. **不承载性能指标**：精度模块不含 QPS、延迟、并发、吞吐量等任何性能指标。
4. **全量数据可落库、可溯源、可对比、可基线**。

#### 双模式定义与能力边界

| 模式 | 定义 | 用途 | 核心能力 | 边界 |
| --- | --- | --- | --- | --- |
| **Native 原生精度（离线）** | 引擎抽象 `native-hf`：本地加载模型权重推理（transformers，环境校验已有依赖，不满足阻断） | 模型固有能力打分、版本迭代回归、微调效果验收、模型海选 | 纯模型固有精度打分、固定种子 100% 可复现、版本回归对比、开源基线对标 | **无 Token 统计、无线上链路消耗** |
| **Serving 链路精度（在线）** | 引擎抽象 `serving`：调用推理服务 API（vLLM / SGLang 等 OpenAI 兼容服务）真实链路推理 | 训推一致性校验、上线前验收、真实业务精度核验、Token 消耗统计 | 真实服务链路精度、训推一致性对比（native vs serving 差值）、**全量 Token 消耗预估 + 强提醒 + 实统计** | 依赖可用 Provider / 推理服务 |

#### 核心指标体系（必存、必展示、必参与对比）

| 指标 | 含义 | 级别 |
| --- | --- | --- |
| `accuracy` 准确率 | 客观题正确样本 / 总样本 | 核心主指标 |
| `total_samples` / `correct_samples` / `wrong_samples` | 总样本 / 正确 / 错误数 | 溯源必备 |
| `invalid_samples` / `pass_rate` | 无效样本数（输出异常、解析失败、截断空输出）/ 有效可解析样本占比 | 质量与链路稳定性 |
| `prompt_tokens_total` / `completion_tokens_total` / `total_tokens` / `avg_prompt_tokens_per_sample` / `avg_completion_tokens_per_sample` | Serving 专属 Token 统计（总输入 / 总输出 / 总消耗 / 单样本均值） | Serving 专属 |
| 分学科准确率、学科最优 / 最差 | MMLU / CMMLU / C-Eval / GAOKAO-Bench 分学科能力分布 | 知识类专项 |
| `exact_match` / `math_accuracy` / `step_valid_rate`（可选） | 最终答案精准匹配率 / 数学专项准确率 / 步骤合规率 | 数学类专项 |
| 单轮得分、多轮平均分、分项得分（有用性 / 真实性 / 无害性）、`mt_bench_score`（0–10） | MT-Bench 行业标准分 | 对话类专项 |
| `pass@1`、编译通过率、用例通过率 | 代码单次通过率 | 代码类专项 |
| 基线差值百分点、S / A / B / C 档位、同尺寸排名百分比 | 当前模型 vs 主流开源基线横向对比 | 对标专项 |

#### 实施路径（P1–P16）

| # | 阶段 | 目标 | 说明 |
| --- | --- | --- | --- |
| P1 | 地基 | 架构方案与数据模型定型 | 新建 `docs/rules/AccuracyEngine.md`；定型落库三件套字段与判分器接口 |
| P2 | 地基 | 独立任务管理器 + API 骨架 | `EvalTaskManager` + `/api/accuracy/tasks*` + WS `eval_task_*` |
| P3 | 地基 | 评测引擎抽象 + `benchscope eval` 内置命令 | bench engines 体系并入精度内容（benchs.yaml 精度引擎条目 / 对比维度 / 介绍）+ `benchscope eval` CLI 子命令 + 环境校验 + mock 引擎 |
| P4 | 数据 | 评测数据集体系（沿用 Settings → Datasets） | 评测数据集并入 `configs/datasets.yaml` 体系 / 9 数据集注册 / 下载 / 标准化 / 预览 / 统计 + 自定义路径与上传 JSONL |
| P5 | 推理 | Serving 推理执行器 | aiohttp 批量推理、完整答案收集、usage 逐条采集、中断 / 重试 / 进度 |
| P6 | 判分 | 判分框架 + 客观题 | MMLU / CMMLU / C-Eval / GAOKAO：选项抽取、分学科、错因打标 |
| P7 | 判分 | 数学判分 | GSM8K / MATH：答案抽取 + 规范化等价、`exact_match` |
| P8 | 判分 | 代码判分 | HumanEval / MBPP：受限子进程沙箱、`pass@1` / 编译率 / 用例率 |
| P9 | 判分 | MT-Bench judge | judge 模型评分、单 / 多轮、分项分、`mt_bench_score` |
| P10 | 亮点 | Token 预估与强提醒 | 常量表 + 实测统计预估、创建前置强提醒弹窗、预估 vs 实际偏差 |
| P11 | 亮点 | 开源基线对标 | 内置基线库、差值 / S-A-B-C 档位 / 同尺寸排名 / 雷达图 / 自动结论 |
| P12 | 前端 | Accuracy 页落地 | 三步创建向导 + 强提醒、任务列表 / 实时详情 / 全套报表 / 错题导出 |
| P13 | 前端 | Datas/Evals + Dashboard 联动 | 精度记录页落地、Dashboard Eval Records 接通 |
| P14 | Native | Native 引擎 | transformers 本地推理（可选依赖 + 环境校验 + GPU 检测 + LoRA 增量加载）+ mock 联调 |
| P15 | 对比 | 一致性对比与多任务对比 | Native vs Serving 差值报告、多版本模型精度对比 |
| P16 | 收口 | 测试与文档收口 | API + WebUI 全量测试、docs 全量同步、Release Notes |

#### 次要候选（主目标完成后评估）

| # | 候选项 | 说明 |
| --- | --- | --- |
| A | 错题集回流为自定义数据集 | 错误样本导出 → 一键转为定制训练 / 回归数据集 |
| B | 模型海选批量评测队列 | 多模型 × 多数据集批量排队评测 |
| C | 报告 PNG 分享 | html2canvas 截图分享（对齐 Datas/Perfs 模式） |
| D | 自定义判分器插件 | 用户扩展判分逻辑（对齐引擎扩展模式） |

### 架构蓝图（摘要，详案见 P1 产出的 `docs/rules/AccuracyEngine.md`）

- **独立包 `benchscope/accuracy/`**：`engines.py`（精度引擎适配：从 bench 引擎注册表过滤 eval 引擎、native CUDA 校验）、`task_manager.py`（`EvalTaskManager`：线程执行 / `stop_event` 终止 / 重启恢复 / WS 推送，写入 `evals_dir`）、`executor.py`（Serving / Native 统一推理执行接口，即 `benchscope eval` 命令实现体）、`datasets.py`（数据集加载与标准化）、`scorers/`（判分器注册表：base + choice + math + code + judge）、`estimator.py`（Token 预估）、`baselines.py`（基线对标）。**不 import 任何性能模块代码**（`task_manager.py` / `benches/`），仅共享 `ConfigManager` / `WebSocketHub` / 目录基础设施等公共服务。
- **内置命令 `benchscope eval` + bench engines 精度内容**：精度评测核心以内置命令 `benchscope eval` 提供（对齐 `benchscope perf` 模式：CLI 参数 / 终端打印精度指标 / 产物落盘 `evals/` 目录供 Datas/evals 打包导入），CLI 与 Web 任务双入口共用同一评测核心；精度引擎注册并入 `configs/benchs.yaml` 引擎体系——`benchscope` 引擎增加 `benchscope eval` serving 精度评测能力与介绍、新增 `native-hf` 引擎条目（requires torch + transformers，本地权重精度）、`mock` 引擎条目，对比表新增「Eval Support / 精度评测」维度；`benchs.py` 注册表增加 eval 能力字段，Settings → Bench 引擎栏同步展示精度评测内容。引擎注册表为 1.0.7 引擎抽象的**公共基础设施**（用户指定并入），精度任务调度 / 结果 / 报表仍完全独立。
- **落库三件套**（无数据库，文件持久化对齐「accuracy_task / accuracy_result / 单样本溯源」三表）：`evals/<task_id>/task.json`（任务主表：任务 ID / 名称 / 评测模式 / 模型名称 / 模型版本 / LoRA 名称与增量模型路径（`lora_name` / `lora_path`）/ 数据集名称+版本 / 任务状态 / 创建与结束时间 / 全局种子 / 温度 / top_p / max_tokens / 引擎 / 基线版本 ID）、`result.json`（总准确率 / 各细分指标 / 样本计数 / Token 统计 / 异常样本 ID 列表 / 最终评测结论（合格 / 精度下跌 / 异常）/ 预估 vs 实际偏差）、`samples.jsonl`（单样本溯源：Prompt / 模型输出 / 标准答案 / 判定结果 / 单条 Token 消耗 / 错因标签（知识错误 / 推理错误 / 输出格式错误））。
- **模型与数据集来源（沿用设置界面 + 自定义路径 + LoRA）**：模型沿用 Settings → Models 厂商目录（`configs/models.yaml`，41 厂商模型清单）作为选择来源，并支持自定义——自定义模型名（Serving 模式任意 OpenAI 兼容服务模型）或本地权重路径（Native 模式）；数据集沿用 Settings → Datasets 内置数据集体系（`configs/datasets.yaml`：分类 / 下载源 / `datasets_dir` 缓存 / 上传），精度评测数据集（MMLU / CMMLU / C-Eval / GSM8K / MATH / HumanEval / MBPP / MT-Bench / GAOKAO-Bench 共 9 个，样本量与元数据明细见 TODO P4）并入该注册表并扩展精度元数据（prompt 模板 / 判分器绑定 / 分学科字段），Settings → Datasets 同步展示；支持自定义本地路径数据集（直接引用 JSONL 路径，免上传）与上传导入；**LoRA 微调训练的增量模型作为被测模型（精度 + 性能推理测试）**：增量模型以 adapter 路径 `lora_path`（可选注册名 `lora_name`）配置——精度测试：Native 模式经 peft 加载（base 模型 + adapter 合并推理）、Serving 模式请求服务端已注册 adapter（服务端需启用 LoRA，如 vLLM `--enable-lora --lora-modules`，文档标注前置条件）；性能测试：Performance 压测请求 adapter 注册名（沿用现有 model 字符串能力，创建页模型选择统一支持输入/选择增量模型），微调前后的精度与性能变化均可量化对比；task.json / run.json 记录 base 模型与 LoRA 路径实现微调效果溯源（base vs base+LoRA）。
- **Token 预估** `configs/token_estimates.yaml`：固化内置常量表（单样本输入 / 输出 Token 均值，附件工业界通用均值）；预估优先级 = 数据集实测统计 > 内置常量 > 自定义数据集字符估算；Serving 创建前置预估弹窗（固定文案强提醒：数据集 / 预估总 Token / 计入计费负载 / 确认启动），确认后方可执行；任务结束记录预估 vs 实际对比偏差。
- **基线库** `configs/baselines.yaml`：静态固化权威公开测评分数（通用基线：Llama3-8B / 70B、Qwen2-7B / 14B / 72B、InternLM2、Mistral-7B；中文专项：Qwen2-Chinese、Llama3-CN、Zephyr；标注来源），支持管理员手动更新最新行业基线。
- **API / WS**：`server/api_accuracy.py`（prefix `/api/accuracy`：tasks CRUD / start / stop / samples、datasets、estimate、engines、env-check、baselines、benchmark、compare）；WS 复用 `WebSocketHub` 新增 `eval_task_*` 消息族（快照回放模式对齐 `task_*` 语义）。
- **边界与遗留**：旧 `/api/test`（`server/api_test.py` + `test_manager.py`，实为旧版性能压测遗留，命名易混淆）本版本不动、不纳入精度体系；`torch` / `transformers` 为可选依赖（extras），mock 引擎保证无 GPU 全链路可测。

---

## 3. 迭代记录（按时间顺序）

### 迭代 1（2026-08-31）：开启 1.0.8 开发

**功能概述**：
- 版本号升级：`benchscope/__init__.py __version__`、`pyproject.toml`、`web/package.json` 均升为 `1.0.8.dev0`
- 创建本版本文档 `docs/versions/VERSION_1_0_8.md`，迭代记录归口到本版本
- 后续开发内容（未特别说明版本号）全部迭代到本版本

**变更内容**：
1. 开启 1.0.8 开发（版本号 + 文档初始化）

### 迭代 2（2026-08-30 10:54:47）：1.0.8 开发计划确认（主目标：独立精度测试模块）

**背景**：用户提供《BenchScope 独立精度测试模块完整功能规划》需求附件（前置核心原则：完全独立拆分 / 双模式独立运行 / 核心三件套 / 全量落库可溯源；功能模块：独立精度任务管理、数据集管理、精度打分引擎、Token 开销预估与统计、开源模型基准对比、精度对比报表、错误样本溯源），要求据此制定 1.0.8 开发计划并尽可能详细分解任务。

**范围决策（用户确认）**：
- Native 原生模式做成与 bench engines 同类的**引擎抽象**：不引入 `torch` / `transformers` 必装依赖，仅检测安装环境已有的相关依赖（不满足则阻断选择）；开发 / 测试使用 mock 环境全链路验证
- **9 个专项数据集全部实现**：MMLU / CMMLU / C-Eval / GSM8K / MATH / HumanEval / MBPP / MT-Bench / GAOKAO-Bench（含代码沙箱 `pass@1` 与 MT-Bench judge）

**产出**：
- `VERSION_1_0_8.md`：新增「2. 版本规划目标（用户确认版）」（硬性约束 / 双模式边界 / 核心指标体系 / P1–P16 实施路径 / 次要候选 / 架构蓝图摘要）+ §4 TODO 清单 P1–P16 详细任务分解
- `docs/Roadmap.md`：1.0.8 小节同步主目标与目标要点；v5.0 精度表述去重（基础精度能力改由 1.0.8 落地）

**TODO 状态**：
- [x] 规划 — 1.0.8 开发计划确认（规划目标 + P1–P16 任务分解 + Roadmap 同步）

### 迭代 3（2026-08-30 11:14:33）：开发计划修订——内置命令 `benchscope eval` + bench engines 精度内容并入

**背景**：用户补充两项规划要求：① 精度测试提供**内置命令 `benchscope eval`**；② **bench engines 体系增加精度相关测试内容**。

**变更内容**：
- 范围决策新增第 3 项（用户确认）：内置命令 `benchscope eval` + bench engines 体系并入精度内容
- 实施路径 P3 调整为「评测引擎抽象 + `benchscope eval` 内置命令」：精度引擎注册**并入 `configs/benchs.yaml` 引擎体系**（新增 `native-hf` / `mock` 引擎条目、`benchscope` 引擎增加精度评测能力介绍、对比表新增「Eval Support / 精度评测」维度），不再新建独立 `accuracy_engines.yaml`；引擎注册表定位为 1.0.7 引擎抽象的公共基础设施，精度任务调度 / 结果 / 报表仍与性能模块完全独立
- 内置命令 `benchscope eval`（对齐 `benchscope perf`）：CLI 参数体系 / 终端精度指标输出 / `evals/` 产物落盘供 Datas/evals 打包导入；CLI 与 Web 任务双入口共用同一评测核心（P5 executor 即命令实现体）
- 架构蓝图、TODO 清单（P3 / P5 / P12 / P14）、`docs/Roadmap.md` 1.0.8 小节同步修订

**TODO 状态**：
- [x] 规划 — 开发计划修订（`benchscope eval` 内置命令 + bench engines 精度内容并入）

### 迭代 4（2026-08-30 11:19:35）：开发计划修订——模型 / 数据集沿用设置界面 + 自定义路径 + LoRA 微调支持

**背景**：用户补充规划要求：① 精度测试的**模型和数据集沿用设置界面内容**（Settings → Models 厂商目录 / Settings → Datasets 内置数据集体系）；② **增加自定义路径的模型和数据集**；③ **支持 LoRA 微调：可配置增量模型路径**。

**变更内容**：
- 范围决策新增第 4 项（用户确认）：模型沿用 `configs/models.yaml` 厂商目录、数据集沿用 `configs/datasets.yaml` 体系（下载缓存 / 上传 / 分类展示），精度评测数据集并入该注册表（扩展精度元数据：prompt 模板 / 判分器绑定 / 分学科字段），Settings → Datasets 同步展示
- 新增自定义路径支持：模型（Serving 自定义模型名 / Native 本地权重路径）、数据集（本地 JSONL 路径直接引用，免上传）
- 新增 LoRA 微调支持：任务可配置增量模型路径 `lora_path`（可选 `lora_name`）——Native 经 peft 加载（base + adapter），Serving 请求服务端已注册 adapter（标注服务端启用 LoRA 前置条件）；task.json 记录 LoRA 名称与增量路径，支持 base vs base+LoRA 微调效果溯源
- 实施路径 P4 / P14 说明、架构蓝图（落库字段 + 模型与数据集来源要点）、TODO 清单（P3 / P4 / P5 / P12 / P14）、`docs/Roadmap.md` 1.0.8 小节同步修订

**TODO 状态**：
- [x] 规划 — 开发计划修订（模型 / 数据集沿用设置界面 + 自定义路径 + LoRA 微调支持）

### 迭代 5（2026-08-30 11:25:55）：开发计划勘误——LoRA 微调训练的增量模型作为被测对象（精度 + 性能推理测试）

**背景**：用户勘误澄清：并非「LoRA 微调支持」功能，而是 **LoRA 微调训练产出的增量模型（adapter）作为被测模型**，既可进行精度测试，也可进行性能推理测试。

**变更内容**：
- 范围决策第 4 项表述修正：「被测对象包含 LoRA 微调训练的增量模型（精度 + 性能推理测试）」
- 架构蓝图修正：增量模型以 `lora_path`（可选 `lora_name`）配置——精度测试（Native peft 加载 / Serving 请求服务端已注册 adapter）+ **性能测试（Performance 压测请求 adapter 注册名，沿用现有 model 字符串能力）**；微调前后的精度与性能变化均可量化对比
- TODO 清单：P5 表述修正；P12 新增「被测模型选择统一（精度 + 性能）」条目（Performance 创建页同步支持选择 / 输入 LoRA 增量模型）
- `docs/Roadmap.md` 1.0.8 小节同步修正

**TODO 状态**：
- [x] 规划 — 开发计划勘误（LoRA 增量模型作为被测对象，精度 + 性能）

### 迭代 6（2026-08-30 14:08:40）：P1–P16 独立精度测试模块落地（Accuracy 全链路）

> **完成时间**：2026-08-30 14:08:40

**功能概述**：
- **架构方案（P1）**：新增 `docs/rules/AccuracyEngine.md`（引擎抽象 / 判分流水线 / 落库三件套字段表 / API 清单 / 解耦边界）
- **独立任务管理（P2）**：`benchscope/accuracy/task_manager.py` `EvalTaskManager`（daemon 线程执行 / `stop_event` 终止 / 服务重启 running→stopped 恢复 / WS `eval_task_*` 推送）；落库三件套 `evals/<task_id>/task.json + result.json + samples.jsonl`（另写 `run.json` 接入 Datas 记录体系）；`server/api_accuracy.py`（`/api/accuracy/tasks*` CRUD / stop / samples 分页筛选 / export-samples 错题集导出 / benchmark）挂载 `app.py`，WS 连接回放 eval 快照，lifespan 退出停止任务
- **评测引擎抽象（P3）**：`configs/benchs.yaml` 引擎体系并入精度内容——`benchscope` 引擎增加 `eval: serving` 能力与介绍、新增 `native-hf`（kind=native，requires torch+transformers）与 `mock`（kind=mock）引擎、对比表新增「Eval Support / 精度评测」维度；`benchs.py` kind 白名单扩展 native/mock、`engine_summary` 透出 eval 字段、`validate_benchs_yaml` 适配；`accuracy/engines.py` 精度引擎适配层（eval 引擎过滤 + native CUDA 校验）；**内置命令 `benchscope eval`**（`cli.py`，对齐 `benchscope perf`：`--engine/--model/--lora-path/--dataset/--limit/--seed/--temperature/--top-p/--max-tokens/--concurrency/--judge-model`，终端打印精度指标，产物落盘 `evals/` 可导入 Datas/evals）；mock 引擎可控正确率伪输出（mock 环境全链路联调）
- **评测数据集体系（P4）**：精度评测数据集并入 `configs/datasets.yaml`（9 个内置：MMLU/CMMLU/C-Eval/GSM8K/MATH/HumanEval/MBPP/MT-Bench/GAOKAO-Bench + eval 元数据：scorer 绑定 / prompt 模板 / 样本量声明；Settings → Datasets 新增精度类别分组）；`accuracy/datasets.py`（下载缓存沿用 `datasets_dir` / ModelScope 优先 / JSONL 标准化 question-choices-answer-subject / 各数据集字段适配 / 固定种子抽样 / 下载产物可解析校验 / 自定义本地路径直接引用 + 上传导入 / 预览 / 统计）
- **Serving 推理执行器（P5）**：`accuracy/executor.py`（即 `benchscope eval` 实现体）`run_eval` 编排核心：aiohttp 异步批量推理（SSE / 非流式双模式 / 完整回答收集 / usage 逐条采集（缺失 chars/4 近似）/ 失败重试→invalid / stop_event 中断 / 进度回调）；Provider 复用 + payload 级覆盖；LoRA 增量模型 Serving 请求服务端已注册 adapter（`lora_name`）
- **判分引擎（P6–P9）**：`scorers/` 注册表 + choice（多策略选项抽取：显式标记 / 独立字母行 / 括号 / 末行；分学科统计；错因 知识错误/输出格式错误）+ math（`\boxed` 与显式标记抽取 / 分数·根式·千分位规范化等价 / exact_match）+ code（代码块抽取 / HumanEval 补全与 MBPP 断言拼装 / **受限子进程沙箱**（`-I` 隔离 + 超时强杀 + 临时目录）/ pass@1 / 编译通过率）+ judge（MT-Bench 两轮对话 / 评审模型 JSON 评分 1–10 + 分项（有用性/真实性/无害性）/ 解析容错重评 / mt_bench_score）
- **Token 预估与强提醒（P10）**：`configs/token_estimates.yaml`（固化附件 9 数据集常量表）；`accuracy/estimator.py`（优先级：实测统计 > 内置常量 > 字符估算；预估耗时）；`GET /api/accuracy/estimate`；任务结束 `result.estimate_vs_actual`（预估 vs 实际偏差百分比）；前端 Step3 Serving **强提醒弹窗**（固定文案：数据集 / 预估总 Token / 计入计费负载 / 确认启动）
- **开源基线对标（P11）**：`configs/baselines.yaml` 内置基线池（通用 Llama3-8B/70B、Qwen2-7B/14B/72B、InternLM2-7B、Mistral-7B + 中文专项 Qwen2-Chinese、Llama3-CN、Zephyr × 9 数据集公开分数，含来源标注）；`accuracy/baselines.py`（同数据集差值百分点 / S-A-B-C 档位 / 同尺寸段排名百分比 / 能力雷达聚合 / 自动结论-风险预警）；`GET/PUT /api/accuracy/baselines`（管理员更新）
- **前端（P12–P13）**：`AccuracyCreateView.vue` 三步向导（数据集（Settings 体系 + 自定义路径 + 预览）/ 模式与引擎（环境明细阻断、模型目录/自定义、LoRA、推理参数、judge）/ 预览 + `benchscope eval` 命令 + Token 强提醒）；`AccuracyView.vue` 改造（任务列表 + 实时详情：指标卡六项 / 数据集专属指标 / 结论与错因分布 / Token 明细与预估偏差 / 基线对标 + **ECharts 能力雷达图** / 分学科表 / 实时日志终端 / 样本溯源筛选与错题集导出）；`store/accuracy.js`（eval_task_* 消息族，快照合并保留本地 result）；`DatasEvalsView.vue` 落地（记录列表 / 摘要 accuracy / 勾选 2 条对比 / 详情日志）；`DashboardView.vue` Eval Records 接通 + Overview Total/Max Acc Records 实数；i18n zh/en 全量键
- **Native 引擎（P14）**：`accuracy/native_runner.py`（transformers 本地加载（路径 / HF id）/ dtype·device_map 自动 / chat 模板 / generate 参数映射 / 固定种子可复现 / 进程内模型缓存 / **LoRA 增量模型 peft 合并加载**）；env-check 追加 CUDA 检测；依赖策略 extras `benchscope[accuracy-native]`（不进必装）
- **对比（P15）**：`accuracy/compare.py`（多任务横向对比 + Native vs Serving 一致性差值：|diff|≤2pp 训推一致 / ≤5pp 存在偏差 / >5pp 显著偏差）；`POST /api/accuracy/compare`；Datas/evals 对比面板
- **收口（P16）**：docs 同步（`prds/Accuracy.md` 全面改写为真实功能 PRD / `prds/Dashboard.md` / `prds/Datas.md` / `rules/Architecture.md` / `rules/Software.md`（extras 依赖）/ `pyproject.toml`（accuracy 包打包 + accuracy-native extras））；`test_settings_benches_*` WebUI 用例适配 5 引擎
- **Dashboard 后端**：`api_dashboard.py` `total_acc_runs` 实数 + `best_acc`/`best_acc_run_id`（精度任务不参与性能指标聚合）；`api_logs.py` run meta 增 kind/summary

**实现策略**：`accuracy/` 不 import 任何性能模块代码（task_manager / benches），仅共享 ConfigManager / WebSocketHub / benchs.py 引擎注册表 / datasets.yaml 公共设施；引擎注册表定位为公共基础设施（精度能力以 `eval` 字段声明）；mock 引擎（mock_correct_rate 可控正确率）保证无 GPU 全链路可测；判分口径对齐行业标准（accuracy / exact_match / pass@1 / mt_bench_score 0–10）。

**验证**：`check:i18n` 通过（zh/en 键集一致）；`npm run build` 通过；`./tests/run_tests.sh` 全量通过——**API 171/171**（新增 `tests/api/test_accuracy_scorers.py`（判分器单测）/ `test_accuracy_engines.py` / `test_accuracy_datasets.py` / `test_accuracy_tasks.py`（mock 全链路）/ `test_accuracy_estimate_baselines.py`，`test_benchs.py` 适配 5 引擎）、**WebUI 46/46**（新增 Accuracy 介绍页 / 创建向导（数据集下拉 + 引擎环境明细）/ mock 全链路列表详情 / Datas/evals 页；benches 面板适配 5 引擎）；CLI 冒烟：`benchscope eval --engine mock --dataset <path>` 全对 100% + 产物落盘验证、下载产物不可解析报错路径验证。

**修复记录**：
- mock 正确率 `mock_correct_rate=0.0` 被 `or 0.7` 兜底吞掉 → 改显式 None 判断（falsy 参数不能用 or 兜底）
- 自定义路径数据集判分器未探测（恒 math）→ 按样本字段自动探测（choices→choice / test→code / turns→judge）
- mock 数学错误答案 `num + choice or num + 1` 运算优先级导致错答可能等于正答 → 括号修正
- ModelScope 下载选取 `dataset_infos.json` 元数据文件当数据集 → 排除并优先 .jsonl、下载产物可解析校验
- 前端模板引用未定义的 `taskList` 绑定（store getter 不自动暴露）→ 补 computed；WS 快照回放覆盖已拉取的完整详情 → 快照合并保留本地 result；列表快照不含 result → 选中/自动选中时补拉完整详情
- 既有测试适配：`test_benchs`（引擎集合 3→5）/ `test_settings_benches_*`（卡片数与对比表列数）/ 技能 `validate.sh`（kind 白名单 + native requires）同步更新

**TODO 状态**：见 §4 TODO 清单（P1–P16 全部完成）

---

## 版本功能清单（Release Notes）

### Feature Highlights

- **Independent Accuracy Testing Module**: fully decoupled from the performance module — independent task manager, storage (task / result / per-sample traceability under `evals/`), scheduling and reports
- **Dual-mode evaluation**: Serving-link accuracy (any OpenAI-compatible API, aiohttp) and Native accuracy (transformers local weights, optional extras `benchscope[accuracy-native]`, CUDA environment check); fully independent and runnable separately
- **Built-in CLI command `benchscope eval`**: same evaluation core as Web tasks; prints accuracy metrics and persists artifacts importable into Datas/evals
- **Accuracy engines in the bench engines system**: `benchscope` (serving), `native-hf` (local weights), `mock` (controllable accuracy) with env-check and an "Eval Support" comparison dimension
- **9 built-in eval datasets**: MMLU / CMMLU / C-Eval / GSM8K / MATH / HumanEval / MBPP / MT-Bench / GAOKAO-Bench (registered in `configs/datasets.yaml`, reused by Settings → Datasets) + custom local-path / uploaded JSONL datasets
- **Scoring engines**: choice (per-subject accuracy) / math (exact_match with normalization) / code (sandboxed pass@1) / MT-Bench LLM-as-judge (turn & sub-dimension scores)
- **Token estimation & strong reminder (Serving)**: pre-run estimate dialog (built-in constants + measured stats), estimate-vs-actual deviation after the task
- **Open-source baseline benchmarking**: built-in baseline pool (Llama3 / Qwen2 / InternLM2 / Mistral / Chinese-special), diff pp, S/A/B/C grade, same-size ranking, ability radar chart and automatic conclusions
- **Model & dataset sources from Settings**: model catalog reuse + custom model name / local weight path; **LoRA fine-tuned incremental models (`lora_path`)** supported for both accuracy and performance testing (peft on Native, server-registered adapter on Serving)
- **Reports & linkage**: realtime task detail, per-sample traceability with wrong-set export, Native-vs-Serving consistency report, Datas/evals records page and Dashboard Eval Records

### 功能清单

- **独立精度测试模块**：与性能模块彻底解耦——独立任务管理器、独立落库（`evals/` 三件套：task.json / result.json / samples.jsonl）、独立调度与报表
- **双模式精度评测**：Serving 链路精度（任意 OpenAI 兼容服务）/ Native 原生精度（transformers 本地权重，可选依赖 + CUDA 环境校验），互不依赖可单独执行
- **内置命令 `benchscope eval`**：与 Web 任务共用评测核心，终端输出精度指标，产物可导入 Datas/evals
- **bench engines 并入精度内容**：benchscope（serving）/ native-hf（本地权重）/ mock（可控正确率）精度引擎，含环境校验与对比表「精度评测」维度
- **9 个内置评测数据集**：MMLU / CMMLU / C-Eval / GSM8K / MATH / HumanEval / MBPP / MT-Bench / GAOKAO-Bench（datasets.yaml 注册、Settings → Datasets 展示）+ 自定义路径 / 上传 JSONL
- **精度打分引擎**：客观题分学科判分 / 数学 exact_match（规范化等价）/ 代码沙箱 pass@1 / MT-Bench LLM-as-judge（单轮 / 多轮 / 分项）
- **Token 预估与强提醒**（Serving 专属）：创建前置预估弹窗（内置常量表 + 实测统计），任务结束预估 vs 实际偏差
- **开源基线对标**：内置基线库（含中文专项），差值百分点、S/A/B/C 档位、同尺寸排名、能力雷达图、自动结论（含风险预警）
- **模型与数据集沿用设置界面**：Settings → Models 厂商目录选模型 + 自定义模型名 / 本地权重路径；**LoRA 微调增量模型（lora_path）** 精度与性能均可测
- **报表与联动**：任务实时详情、单样本溯源与错题集导出、Native vs Serving 一致性对比、Datas/evals 记录页、Dashboard Eval Records 接通

---

### 迭代 7（2026-08-31）：性能测试启动前 Token 使用预警（前端估算）

**功能概述**：
- Performance/创建任务页 Step3 点 **Launch** 后，弹出 **Token 使用预估弹窗**（仅前端计算与提示，不改后端启动流程）
- 按并发 / 阈值两种模式分别估算每组输入/输出 token 与全部总输入/输出 token（百万单位）
- footer 显示 **确定 / 取消**：取消则弹窗消失不启动；确定才创建并启动任务

**变更内容**：

1. **并发模式 token 预估**：每组（condition）按 `requestRates` 每个请求数独立计算——`输入 token = inputLen × 请求数`、`输出 token = outputLen × 请求数`（`num-prompts`>0 时请求数取 num-prompts）；每组汇总 + 全部总计（百万单位）
2. **阈值模式 token 预估（阶梯累计）**：按 2 的次方阶梯（1, 2, 4, … ≤ maxRequests）逐级**累计**——`请求 N` 的行 = 前面所有 2 的次方之和（含自身）× inputLen/outputLen（如 请求 2 = (1+2)×1024、请求 4 = (1+2+4)×1024）
3. **预警弹窗 UI**：`PerfCreateView.vue` 加 `<a-modal>`（`.token-warning`）——`a-alert` 警告 + 每组 token 表（请求数/输入/输出）+ 组内合计 + 底部总输入/总输出（百万单位）；footer 自定义 **取消 / 确定（Confirm）**
4. `submit()` 改为先弹预警；新增 `doLaunch()`（确定后执行原创建+启动流程）；新增 `tokenEstimate` computed / `numPrompts` / `thresholdSteps` / `toMillions`
5. **i18n**：新增 `tokenWarningTitle/Alert/Requests/InputTotal/OutputTotal/GroupTotal/AllInput/AllOutput/Million` 中英双语
6. **测试**：`tests/webui/test_ui.py` 新增 `test_create_page_token_warning_concurrency`、`test_create_page_token_warning_threshold`（并发独立计算 + 阈值阶梯累计校验 + footer 取消）

**验证（增量）**：
- WebUI：`-k "create_page or perf_create or token_warning"` 9 项全部通过（含 2 个新增）
- Playwright 实测：并发模式 9 行阶梯 + 总 0.30M/0.30M；阈值模式 13 行阶梯累计（1→1024、2→3072、4→7168、8→15360）正确；footer Cancel/Confirm
- lint 无错误

**TODO 状态**：
- [x] UI — 创建页 Step3 Launch 后中间弹窗显示 Token 使用预估（每组输入/输出 + 总输入/输出百万单位）
- [x] 逻辑 — 并发模式按输入输出 × 全部请求数计算每组与总计
- [x] 逻辑 — 阈值模式按输入输出 × 2 的次方阶梯累计（请求 1/64/128 每组 3 条代表）预估
- [x] footer — 确定/取消：取消消失，确定启动任务
- [x] 测试与文档 — WebUI 断言新增 + VERSION / Performance-Create 同步

---

### 迭代 8（2026-08-31）：Accuracy 默认页整体 UI 优化

**功能概述**：
- 精度测试默认页（AccuracyView）整体 UI 现代化：无任务介绍页 hero 增强 + 有任务改为「左任务列表 + 右详情」两栏布局
- 指标卡、卡片、表格、控制台、响应式等样式统一细化

**变更内容**：

1. **无任务介绍页（hero 增强）**：`.intro-hero` 渐变背景 + 徽标（`hero-badge`）+ 大标题 + 副标题 + CTA + 统计条（2 模式 / 9 数据集 / S·A·B·C 评级）；3 张特性卡片带彩色渐变图标背景 + hover 上浮
2. **有任务两栏布局**：`.layout` 改 `flex-row`——左侧 `.list-card`（任务列表，固定宽 400px，内部表格纵向滚动）+ 右侧 `.detail`（详情卡片流，flex 滚动）；900px 以下回退纵向
3. **详情卡片美化**：`metric-box` 指标卡（悬浮上浮、边框圆角、背景区分）、`a-descriptions`/进度条、雷达图、控制台、样本表样式统一；卡片圆角 + header 紧凑
4. **新 i18n 键**：`accModeTag / accModes / accDatasets / accGrades`（中英）
5. **测试**：`test_accuracy_landing_intro` 选择器 `.intro-head` → `.intro-hero` + `.hero-cta`，并断言 hero 徽标/统计存在

**验证（增量）**：
- Playwright 实测：无任务 hero（徽标/标题/CTA/统计/3 卡片）+ 有任务两栏（列表卡片 + 任务行 + 详情区），无 JS 错误
- WebUI：`-k "accuracy"` 4 项全部通过
- lint 无错误

**TODO 状态**：
- [x] UI — 无任务介绍页 hero 增强（渐变/徽标/统计/特性卡片）
- [x] UI — 有任务两栏布局（左列表 + 右详情）+ 指标卡/卡片/表格/控制台美化
- [x] i18n — hero 统计与徽标中英文案
- [x] 测试与文档 — Accuracy WebUI 断言更新 + VERSION 同步

---

### 迭代 9（2026-08-31）：Accuracy 默认页对齐 Performance 默认页结构

**功能概述**：
- Accuracy 默认页（无任务介绍页）结构与字体样式改为**与 Performance 默认页一致**（`a-result` + 特性卡片）

**变更内容**：

1. **介绍页结构对齐 Performance**：`.intro-hero` 自定义 hero 改为 `.perf-intro` + `.planned-card` + `a-result`（标题/副标题/主色图标 `RobotOutlined` 72px / CTA 按钮）+ `.features` 特性卡片（居中 `a-row`，3 张）
2. **字体颜色与样式对齐**：`.feature-card` 特性卡 `text-align:center`、圆角 8px、meta-title 用 `--ant-color-text`、desc 用 `--ant-color-text-secondary`；`.result-icon` 用 `--ant-color-primary`（与 Performance 一致）
3. `.accuracy-page` 改 `flex-column`，`.perf-intro` flex 居中、`.layout` flex:1 填满
4. 移除上轮自定义 hero（`.hero-badge/.hero-title/.hero-stats` 等）及其 i18n 键使用；新增 `RobotOutlined / PlayCircleOutlined` 图标 import
5. **测试**：`test_accuracy_landing_intro` 选择器改为 `.perf-intro/.planned-card/.ant-result-extra button`，断言 a-result 结构与特性卡

**验证（增量）**：
- Playwright 实测：`a-result` 结构 + result-icon 主色 `rgb(22,119,255)` + 3 特性卡（text-align center）+ CTA，无 JS 错误
- WebUI：`-k "accuracy"` 4 项全部通过
- lint 无错误

**TODO 状态**：
- [x] UI — Accuracy 默认页改为与 Performance 一致的 `a-result` + 特性卡片结构
- [x] UI — 字体颜色与样式对齐 Performance（语义色/居中/圆角）
- [x] 测试与文档 — Accuracy WebUI 断言更新 + VERSION 同步

---

### 迭代 10（2026-08-31）：Accuracy 默认页大图标与主导航一致

**功能概述**：
- Accuracy 默认页介绍页的大图标（`result-icon`）改用与**主导航 Accuracy 项一致**的图标 `FundOutlined`

**变更内容**：

1. `AccuracyView.vue`：介绍页 `result-icon` 图标由 `RobotOutlined` 改为 **`FundOutlined`**（与 TopBar 主导航 Accuracy 项同一图标），保持主色 `--ant-color-primary`
2. import 相应更新（`FundOutlined` 替换 `RobotOutlined`）

**验证（增量）**：
- Playwright 实测：result-icon 为 `FundOutlined`（viewBox 64 64 896 896），主色 rgb(22,119,255)
- lint 无错误；前端已重建

**TODO 状态**：
- [x] UI — Accuracy 默认页大图标与主导航一致（FundOutlined）
- [x] 文档 — VERSION / Accuracy.md 同步

---

### 迭代 11（2026-08-31）：Performance 默认页阈值搜索介绍精简为 2 行

**功能概述**：
- Performance 默认页特性卡片「阈值搜索」介绍内容过多，精简为 2 行

**变更内容**：

1. **i18n 文案精简**：`featThresholdModeDesc` 中英精简为一句（`设置 TTFT / TPOT / 吞吐阈值，自动搜索满足阈值的最大并发。` / `Set TTFT/TPOT/throughput thresholds; auto-find the max concurrency still satisfying them.`）
2. **CSS 2 行截断**：`PerformanceView.vue` `.feature-card .ant-card-meta-description` 加 `-webkit-line-clamp: 2`（配合精简文案稳定 2 行）
3. **测试**：`test_perf_landing_intro_cards` 断言由"含逐步搜索机制"改为"含 max concurrency / 最大并发"

**验证（增量）**：
- Playwright 实测：阈值搜索描述 2 行（`设置 TTFT / TPOT / 吞吐阈值，自动搜索满足阈值的最大并发。`）
- WebUI：`-k "perf_landing_intro_cards"` 通过
- lint 无错误；前端已重建

**TODO 状态**：
- [x] UI — 阈值搜索介绍精简为 2 行（文案 + line-clamp）
- [x] 测试与文档 — WebUI 断言更新 + VERSION 同步

---

### 迭代 12（2026-08-31）：Accuracy 默认页标题简化 + 描述一句话

**功能概述**：
- Accuracy 默认页标题由「独立精度测试」简化为「精度测试」，描述信息改为一句话

**变更内容**：

1. **标题**：`accIntroTitle` 改为 `精度测试` / `Accuracy Testing`（去掉"独立"前缀）
2. **描述一句话**：`accIntroDesc` 精简为一句（`对模型进行标准精度评测，支持 Native 原生与 Serving 链路双模式、基线对标与 Token 预估。` / `Evaluate model accuracy: Native & Serving dual-mode, baseline benchmarking and token estimation.`）

**验证（增量）**：
- Playwright 实测：标题「精度测试」、描述一句话
- lint 无错误；前端已重建

**TODO 状态**：
- [x] UI — 标题简化为「精度测试」、描述一句话
- [x] 文档 — VERSION 同步

---

### 迭代 13（2026-08-31）：精度特性卡改名 + 会话发送/停止按钮

**功能概述**：
- 精度默认页三张特性卡改名（模型链路/离线模型/模型精度基准对比）+ 说明 ≤2 行
- 会话界面发送按钮：流式中显示「停止」，点击停止数据流并改回「发送」

**变更内容**：

1. **精度特性卡改名**（`accFeat1/2/3Title/Desc` 中英）：
   - 卡1 **模型链路精度测评**（Model Serving Accuracy Evaluation）— 对 OpenAI 兼容 Serving 链路端到端精度测评
   - 卡2 **离线模型精度测评**（Offline Model Accuracy Evaluation）— 直接评测本地 transformers 权重
   - 卡3 **模型精度基准对比**（Model Accuracy Benchmark Comparison）— 自动对标开源基线（差值/S·A·B·C/排名）
   - 每卡说明均 ≤2 行（沿用 `.feature-card` line-clamp:2）
2. **会话发送/停止按钮**（`SessionsView.vue`）：
   - 发送按钮文案随流式切换：`streaming ? 停止 : 发送`（`.send-stop` 红色样式）
   - 点击逻辑：流式中点按 → `stopStream()`（AbortController.abort 中止数据流，保存已生成部分，不报错）；否则 `sendMessage()`
   - 新增 `streamAbort` ref，`sendMessage` 用 `signal` 中止，catch 处理 `AbortError`，finally 清空

**验证（增量）**：
- Playwright 实测：精度三卡标题/说明 2 行；会话按钮 发送 → 停止 → 发送（数据流停止）
- WebUI：`-k "accuracy or sessions or perf_landing"` 8 项全部通过
- lint 无错误；前端已重建

**TODO 状态**：
- [x] UI — 精度默认页特性卡改名 + 说明 ≤2 行
- [x] UI — 会话发送/停止按钮（流式停止 + 文案切换）
- [x] 测试与文档 — WebUI 确认 + VERSION 同步

---

### 迭代 14（2026-09-01）：Design.md 规范增强（对齐 Ant Design 设计语言）

**功能概述**：
- 重新优化 `docs/rules/Design.md`，增加 **Ant Design 设计规范**（ant.design/design.md）基准

**变更内容**：

1. **新增 §0 Ant Design 设计规范基准**：
   - §0.1 设计价值观（四大）：自然 / 确定性 / 意义感 / 生长性 + 本项目落地
   - §0.2 设计令牌（Design Token）：统一 `var(--ant-color-*)`，禁止硬编码；主题自动跟随
   - §0.3 设计基础：色彩 / 字体 / 8px 间距 / 24 栅格 / 圆角 / 阴影 / 图标 / 动效 / 无障碍
2. **现有章节对齐 antd**：布局（8px 网格 + 24 栅格）、字体（antd 字体栈 + 数字等宽）、颜色（补 `--ant-color-info`、色阶派生）
3. **新增 §7 遵循检查清单**（对齐 antd：无硬编码令牌 / 8px 网格 / 24 栅格 / antd 语义组件 / 图标来源 / 中英双语）

**验证**：
- lint 无错误

**TODO 状态**：
- [x] 规范 — Design.md 增加 Ant Design 设计规范基准（价值观/令牌/设计基础）
- [x] 规范 — 现有章节对齐 antd + 遵循检查清单
- [x] 文档 — VERSION 同步

---

### 迭代 15（2026-09-01）：webui 代码对齐 Design.md（Ant Design 设计令牌）

**功能概述**：
- 根据 Design.md（对齐 Ant Design 设计语言）优化 webui 前端源码，将硬编码颜色改为 antd 设计令牌

**变更内容**：

1. **`MetricsTable.vue`**（硬编码最多）：`#999`/`#1677ff`/`#e6f4ff`/`#91caff`/`#bae0ff`/`#fafafa`/`#f5f5f5`/`#d9f7be`/`#c5e8ad`/`#fff1b8`/`#ffe58f` 等全部改为 `var(--ant-*)` 令牌（primary-bg / success-bg / warning-bg / text / fill-secondary 等，保留原 hex fallback）
2. **`StatusBadge.vue`**：`#52c41a`→`--ant-color-success`、`#ff4d4f`→`--ant-color-error`、`rgba(0,0,0,.65)`→`--ant-color-text-secondary`；label 字号 13px→12px
3. **`RunDataPanel.vue`**：`#f6ffed`→`--ant-color-success-bg`、`#b7eb8f`→`--ant-color-success-border`
4. **`RunDetailPanel.vue`**：`#fff`→`--ant-color-bg-container`、`#f0f0f0`→`--ant-color-border`、`#f6f8fa`→`--ant-color-fill-secondary`；内联 `color:#999`→`var(--ant-color-text-tertiary)`
5. **内联硬编码**：`AnalysisBlock`/`ConcurrencyEditor`/`FreeArgsEditor` 模板内联 `color:#999` → `var(--ant-color-text-tertiary)`

**验证（增量）**：
- 前端构建成功（12.78s，无错误）
- WebUI：`-k "dashboard or performance or datas"` 8 项全部通过（无回归）
- lint 无错误

**TODO 状态**：
- [x] 优化 — MetricsTable / StatusBadge / RunDataPanel / RunDetailPanel 硬编码颜色令牌化
- [x] 优化 — 组件模板内联硬编码颜色令牌化
- [x] 测试与文档 — 前端重建 + WebUI 确认 + VERSION 同步

---

## 4. TODO 清单

（1.0.8 待办，按 P1–P16 实施路径分解；每项落地后勾选并在 §3 记录迭代明细）

### 阶段一：地基（P1–P3）

**P1 架构方案与数据模型定型**
- [x] 新建 `docs/rules/AccuracyEngine.md`：精度引擎抽象（`serving` / `native-hf` / `mock`）、判分流水线（数据集加载 → 批量推理 → 答案抽取 → 判分 → 指标汇总 → 落库）、落库三件套字段表（`task.json` / `result.json` / `samples.jsonl`）、API 清单、与性能模块解耦边界
- [x] 定型 9 数据集元数据结构（prompt 模板 / few-shot / 分学科字段 / 答案字段 / token 均值兜底）与判分器接口（`score(sample) → {extracted, correct|invalid, error_tag}`）

**P2 独立任务管理器 + API 骨架**
- [x] `benchscope/accuracy/` 包骨架 + `task_manager.py` `EvalTaskManager`：`start / stop / list / get`、daemon 线程执行、`stop_event` 终止、RLock 并发保护、服务重启 running → stopped 恢复（对齐 TaskManager 范式但独立实现，不 import 性能模块）
- [x] 落库三件套读写：`evals/<task_id>/task.json`（任务主表全字段）、`result.json`（结果表）、`samples.jsonl`（单样本溯源，逐条追加）
- [x] `server/api_accuracy.py`（prefix `/api/accuracy`）挂载 `app.py`：`POST /tasks`（创建 + 启动）、`GET /tasks`、`GET /tasks/{id}`、`POST /tasks/{id}/stop`、`DELETE /tasks/{id}`、`GET /tasks/{id}/samples`（分页 / 错误与无效筛选）
- [x] WS 新增 `eval_task_*` 消息族（`eval_task_started / log / result / done / error` + 连接快照回放）
- [x] `tests/api/test_accuracy_tasks.py`（创建 / 启动 / 停止 / 恢复 / 落库字段 / samples 查询）

**P3 评测引擎抽象 + `benchscope eval` 内置命令 + mock 引擎**
- [x] bench engines 体系并入精度内容：`configs/benchs.yaml` 新增 `native-hf` 引擎条目（kind=native，requires `torch>=2.0` + `transformers>=4.40`，本地权重精度）、`mock` 引擎条目（kind=mock，测试演示）；`benchscope` 引擎 description / highlights 增加 `benchscope eval` serving 精度评测能力；`comparison` 对比表新增「Eval Support / 精度评测」维度（serving 精度 / 本地权重精度 / 不支持——vllm、sglang 原生引擎仅性能压测）
- [x] `benchs.py` 注册表增加 eval 能力字段解析（`eval: serving | native | mock`），`/api/benchs` 引擎清单透出；Settings → Bench 引擎栏展示精度评测内容（介绍 / 特性 / 对比维度）
- [x] 内置命令 `benchscope eval`（`cli.py` 新增子命令，对齐 `benchscope perf`）：参数 `--engine / --model / --lora-path / --base-url / --api-key / --dataset（内置 id 或自定义 JSONL 路径）/ --limit / --seed / --temperature / --top-p / --max-tokens / --concurrency / --judge-model`；执行评测核心，终端打印精度指标（accuracy / exact_match / pass@1 / mt_bench_score / Token 统计）；产物落盘 `evals/` 目录（run.json / task.json / result.json / samples.jsonl）供 Datas/evals 打包导入（对齐 `_save_perf_artifacts` 模式）
- [x] `accuracy/engines.py`：精度引擎适配层（从 bench 引擎注册表过滤 eval 引擎、`get_engine` / `check_env` native CUDA 校验）
- [x] mock 引擎：按样本返回可控伪输出（正确率可控），供全链路联调与测试
- [x] API：`GET /api/accuracy/engines`、`GET /api/accuracy/engines/{id}/env-check`
- [x] `tests/api/test_accuracy_engines.py`（注册表 / eval 能力字段 / 环境校验 / `benchscope eval` CLI 冒烟 / mock 输出）

### 阶段二：数据与推理（P4–P5）

**P4 评测数据集体系（沿用 Settings → Datasets + 自定义路径）**
- [x] 精度评测数据集并入设置界面数据集体系：`configs/datasets.yaml` 扩展 9 个评测数据集（MMLU 14079 / CMMLU 11960 / C-Eval 13480 / GSM8K 7473 / MATH 5000 / HumanEval 164 / MBPP 974 / MT-Bench 80 / GAOKAO-Bench 2000）及精度元数据（类别 知识 / 数学 / 代码 / 对话 / 综合、下载源、prompt 模板与 few-shot 数、答案字段、分学科字段、判分器类型绑定）；Settings → Datasets 面板同步展示（精度类别分组）；GAOKAO-Bench 取客观题子集（主观题标记不支持判分 → invalid 说明）
- [x] `accuracy/datasets.py`：沿用内置数据集下载缓存体系（`datasets_dir`，ModelScope 优先）、JSONL 标准化（统一 `question / choices / answer / subject`）、固定种子子集抽样（limit / 全量）、内容预览
- [x] 自定义数据集：① **本地路径直接引用**（输入 JSONL 路径，免上传，校验 + 预览 + 统计）；② 上传导入 + 格式校验（标准格式 `question` / `answer`，可选 `choices` / `subject`）
- [x] API：`GET /api/accuracy/datasets`（含自定义路径条目）、`POST /api/accuracy/datasets/import`、`GET /api/accuracy/datasets/{id}/preview`、`GET /api/accuracy/datasets/{id}/stats`（样本量 / 学科分布 / 实测 token 均值）
- [x] `tests/api/test_accuracy_datasets.py`（注册表 / 标准化 / 抽样 / 自定义路径校验 / 导入校验）

**P5 Serving 推理执行器**
- [x] `accuracy/executor.py`（即 `benchscope eval` 命令实现体，CLI 与 `EvalTaskManager` 共用同一评测核心入口）：aiohttp 异步批量推理（并发度可配 + 信号量、SSE / 非流式双模式、完整回答收集、`usage` 逐条 token 采集、think 标签分离、失败重试 N 次 → invalid 标记、`stop_event` 中断、进度回调）
- [x] Native 执行接口占位（`native-hf` 走同一 `executor` 契约，P14 落地）
- [x] 进度推送：WS `eval_task_result`（逐题）+ `eval_task_log`（流式日志 `eval_<run_id>.log`）
- [x] Provider 复用与模型定制：payload 级 api 覆盖（对齐性能任务语义，仅复用配置设施）；模型支持自定义模型名；**LoRA 微调训练的增量模型**任务请求服务端已注册 adapter（`lora_name`，服务端需启用 LoRA，如 vLLM `--enable-lora --lora-modules`，文档标注前置条件）
- [x] `tests/api/test_accuracy_executor.py`（对 mock OpenAI :8001：并发 / usage / 中断 / invalid）

### 阶段三：判分引擎（P6–P9）

**P6 判分框架 + 客观题（MMLU / CMMLU / C-Eval / GAOKAO-Bench）**
- [x] `accuracy/scorers/base.py` + 判分器注册表（按数据集绑定 scorer）
- [x] `choice.py`：答案抽取多策略（前缀 / 正则 / 末行选项）、无效输出判定（空 / 截断 / 无法解析）、错因标签（知识错误 / 输出格式错误）
- [x] 分学科统计：per-subject `accuracy`、学科最优 / 最差能力分布
- [x] GAOKAO-Bench 接入客观题子集（主观题标记不支持判分 → invalid 说明）
- [x] `tests/api/test_accuracy_scorer_choice.py`

**P7 数学判分（GSM8K / MATH）**
- [x] `math.py`：最终答案抽取（`\boxed{}` / `answer is` / 「答案是」/ `=` 等模式）、数值 / 分数 / 根式 / LaTeX 规范化等价
- [x] 指标：`exact_match`、`math_accuracy`、可选 `step_valid_rate`
- [x] `tests/api/test_accuracy_scorer_math.py`

**P8 代码判分（HumanEval / MBPP）**
- [x] `code.py`：代码块抽取（```python 围栏 / 裸函数）、HumanEval 函数补全拼装、MBPP 断言用例拼装
- [x] 受限子进程沙箱：临时目录执行、超时杀进程、输出隔离；安全边界文档标注
- [x] 指标：`pass@1`、编译通过率、用例通过率
- [x] `tests/api/test_accuracy_scorer_code.py`（含超时 / 异常用例）

**P9 MT-Bench judge 判分**
- [x] `judge.py`：两轮对话生成、judge 模型配置（复用 Provider 选模型）、评分 prompt（1–10 + 分项）、单轮 / 多轮 / 分项（有用性 / 真实性 / 无害性）、`mt_bench_score`
- [x] judge 输出解析容错（评分抽取失败 → 该轮重评 / invalid）
- [x] `tests/api/test_accuracy_scorer_judge.py`（mock judge）

### 阶段四：预估与对标（P10–P11）

**P10 Token 预估与强提醒**
- [x] `configs/token_estimates.yaml`：内置常量表（9 数据集单样本输入 / 输出 Token 均值、总样本量、全量预估总 Token，固化需求附件数值：MMLU 180/8、CMMLU 200/8、C-Eval 220/8、GSM8K 120/80、MATH 180/120、HumanEval 150/200、MBPP 130/180、MT-Bench 300/350、GAOKAO-Bench 400/150）
- [x] `accuracy/estimator.py`：预估优先级（数据集实测统计 > 内置常量 > 自定义数据集字符估算）、预估总输入 / 输出 / 总 Token + 预估耗时
- [x] API：`GET /api/accuracy/estimate?dataset_id=&mode=&limit=`
- [x] `result.json` 增：预估 vs 实际（总 / 输入 / 输出 + 偏差百分比）
- [x] 前端：创建向导 Step3 Serving 模式强提醒弹窗（固定文案：数据集 / 预估总 Token / 计入计费负载提醒 / 确认启动）；详情页 Token 消耗明细卡
- [x] `tests/api/test_accuracy_estimate.py`

**P11 开源基线对标**
- [x] `configs/baselines.yaml`：内置基线池 × 9 数据集公开分数（通用：Llama3-8B / 70B、Qwen2-7B / 14B / 72B、InternLM2、Mistral-7B；中文专项：Qwen2-Chinese、Llama3-CN、Zephyr；静态固化 + 来源标注）
- [x] `accuracy/baselines.py`：对标计算（per-数据集差值百分点、能力雷达聚合（知识 / 数学 / 代码 / 对话）、S / A / B / C 档位评级、同尺寸段排名百分比、自动结论：优于 / 持平 / 劣于 + 风险预警）
- [x] API：`GET /api/accuracy/baselines`、`PUT /api/accuracy/baselines`（管理员更新）、`GET /api/accuracy/tasks/{id}/benchmark`
- [x] 前端：基线对比面板（差值表 / 档位标签 / 雷达图 / 结论卡）
- [x] `tests/api/test_accuracy_baselines.py`

### 阶段五：前端（P12–P13）

**P12 Accuracy 前端主页面**
- [x] `web/src/views/AccuracyCreateView.vue` 三步向导：Step1 数据集（沿用 Settings → Datasets 数据源：评测数据集选择 / 类别筛选 / 样本量与抽样 / 预览，+ 自定义本地路径 JSONL），Step2 模式与引擎（native | serving、引擎选择 + 环境校验明细阻断、模型沿用 Settings → Models 厂商目录选择或自定义模型名 / 本地权重路径、LoRA 增量模型路径 `lora_path`（可选，附 `lora_name`）、推理参数：全局种子 / 温度 / top_p / max_tokens）、Step3 预览与启动（payload 摘要 + `benchscope eval` 预览命令展示（与 Performance 创建页预览命令一致模式）+ Token 预估强提醒弹窗确认）
- [x] `web/src/views/AccuracyView.vue` 改造：任务列表（状态 / 模式 / 数据集 / accuracy / Token）+ 详情实时（进度条 / 日志终端 / 实时逐题结果）+ 结果报表（核心指标卡 6 项、分学科表、能力雷达图、基线对比、Token 明细与预估偏差、样本溯源表（错误 / 无效筛选）、错误样本面板 + 错题集 JSONL 导出）
- [x] 被测模型选择统一（精度 + 性能）：模型数据源统一（Settings → Models 厂商目录 + 自定义模型名 / 本地权重路径 / LoRA 增量模型 adapter 注册名）；Performance 创建页（PerfCreateView）同步支持选择 / 输入 LoRA 微调训练的增量模型（服务端已注册 adapter 名）进行性能压测——LoRA 微调前后的精度与性能对比形成闭环
- [x] ECharts 组件：`AccuracyCharts.vue`（学科柱状 / 雷达 / Token 对比）；复用 MetricsTable / StatusBadge 组件模式
- [x] i18n zh / en 全量键 + `npm run check:i18n` 通过

**P13 Datas/Evals + Dashboard 联动**
- [x] `web/src/views/DatasEvalsView.vue`：精度记录列表（筛选 / 刷新 / 删除 / 导入 / 备份）+ 详情复用精度报表组件
- [x] `web/src/views/DashboardView.vue`：`total_acc_runs` 实数 + Eval Records 记录表 + More 跳转 Datas/Evals；Overview 六宫格 Max Acc Records 实数
- [x] `tests/webui` 用例：创建向导 / 强提醒弹窗 / 详情报表（Playwright）

### 阶段六：Native 模式（P14–P15）

**P14 Native 引擎（native-hf）**
- [x] `accuracy/native_runner.py`（`native-hf` 引擎执行实现，引擎条目已于 P3 注册入 `benchs.yaml`）：transformers 本地推理（模型路径 / HF id、dtype / device_map 自动、`generate` 参数映射 temperature / top_p / max_new_tokens、固定种子可复现、批量生成）；**LoRA 增量模型加载**（`peft` PeftModel：base 模型 + `lora_path` adapter 合并推理，微调效果验收）
- [x] 环境校验强化：torch / transformers 版本 + CUDA 可用性检测（配置 LoRA 时追加 `peft` 校验），不满足创建页阻断（同 bench 引擎交互）
- [x] mock native 引擎联调（无 GPU 全链路验证）
- [x] 依赖策略：torch / transformers / peft 不进必装依赖（extras `benchscope[accuracy-native]`），`rules/Software.md` 同步
- [x] `tests/api/test_accuracy_native.py`（mock 引擎）

**P15 一致性对比与多任务对比**
- [x] Native vs Serving 训推一致性报告：同模型同数据集双任务逐指标差值（accuracy / exact_match / pass@1）+ 结论（训推一致 / 存在偏差）
- [x] 多版本模型精度对比：多任务横向对比表与趋势图
- [x] API：`POST /api/accuracy/compare`（任务 id 集合）+ 前端对比面板（Accuracy / Datas-Evals 入口）

### 阶段七：收口（P16）

**P16 测试与文档收口**
- [x] `./tests/run_tests.sh` 全量（API + WebUI）+ `check:i18n` + `npm run build`
- [x] docs 同步：`prds/Accuracy.md` 全面改写（真实功能 PRD）、`prds/Dashboard.md`、`prds/Datas.md`、`rules/Architecture.md`、`rules/Software.md`、`Roadmap.md` 状态
- [x] `VERSION_1_0_8.md`「版本功能清单（Release Notes）」双语区块（发布前 AI 总结）

---

### 阶段六：性能测试启动前 Token 使用预警（前端估算）

- [x] `PerfCreateView.vue` 并发模式：按 requestRates × inputLen/outputLen 计算每组与全部总输入/输出 token（百万单位）
- [x] `PerfCreateView.vue` 阈值模式：按 2 的次方阶梯累计（请求 1/64/128 代表，前面全部 2 的次方之和）预估
- [x] Step3 Launch 后中间弹窗显示 Token 使用预估 + footer 确定/取消（取消消失、确定启动）
- [x] i18n 中英文案 + WebUI 测试（并发独立 / 阈值累计 + footer 取消）

---

## 5. 相关文档

- [docs/Roadmap.md](../Roadmap.md)（版本路线）
- [docs/rules/AccuracyEngine.md](../rules/AccuracyEngine.md)（精度引擎架构，P1 产出）
- 页面级行为细则见 `docs/prds/`（Accuracy 落地后更新 `prds/Accuracy.md`）

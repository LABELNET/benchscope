# Accuracy 引擎架构（1.0.8 精度测试模块）

> **版本**：1.0.8
> **最后更新**：2026-08-30
> **文档状态**：精度测试模块架构方案（引擎抽象 / 判分流水线 / 数据模型 / API 清单 / 解耦边界）
> **关联文档**：[BenchEngine.md](./BenchEngine.md)（bench 引擎抽象）· [Architecture.md](./Architecture.md) · [../prds/Accuracy.md](../prds/Accuracy.md)

---

## 1. 定位与硬性约束

精度测试模块（Accuracy）为**独立闭环系统**，与压测 / 性能模块彻底解耦：

1. **独立任务表 / 结果表 / 单样本溯源表**（文件持久化三件套，见 §4）、独立调度（`EvalTaskManager`）、独立报表；
2. **不承载任何性能指标**（无 QPS / 延迟 / 并发 / 吞吐）；
3. **不 import 任何性能模块代码**（`task_manager.py` / `benches/`），仅共享公共设施：`ConfigManager`（目录 / Provider）、`WebSocketHub`（实时推送）、`benchs.py` 引擎注册表（公共基础设施，精度内容并入，用户确认）；
4. **双模式独立运行**：Native 原生精度（本地权重）/ Serving 链路精度（OpenAI 兼容 API），互不依赖可单独执行；
5. **全量数据可落库、可溯源、可对比、可基线**。

核心代码包：`benchscope/accuracy/`。

```
benchscope/accuracy/
├── __init__.py
├── engines.py      # 精度引擎适配：从 bench 引擎注册表过滤 eval 引擎、native CUDA 校验
├── datasets.py     # 评测数据集：注册表（datasets.yaml 并入）+ 下载/标准化/抽样/预览/统计
├── executor.py     # 推理执行器（Serving/Native/Mock 统一接口；benchscope eval 命令实现体）
├── metrics.py      # 指标汇总（accuracy/pass_rate/分学科/Token 统计/结论）
├── estimator.py    # Token 预估（常量表 > 实测统计 > 字符估算）
├── baselines.py    # 开源基线库与对标计算（差值/档位/排名/雷达/结论）
├── task_manager.py # EvalTaskManager + EvalTask（独立调度、三件套落库、WS 推送）
├── compare.py      # 多任务对比 / Native vs Serving 一致性差值
└── scorers/
    ├── __init__.py # 判分器注册表（按数据集绑定）
    ├── base.py     # Scorer 接口 + 公共抽取工具
    ├── choice.py   # 客观题（MMLU/CMMLU/C-Eval/GAOKAO）：选项抽取、分学科
    ├── math.py     # 数学（GSM8K/MATH）：答案抽取、规范化等价、exact_match
    ├── code.py     # 代码（HumanEval/MBPP）：受限子进程沙箱、pass@1
    └── judge.py    # MT-Bench：LLM-as-judge 评分（单/多轮、分项）
```

## 2. 引擎抽象（并入 bench engines 体系）

精度引擎注册**并入 `configs/benchs.yaml`**（1.0.7 引擎抽象的公共基础设施），引擎条目新增 `eval` 能力字段：

| 引擎 id | kind | eval 能力 | 环境要求 | 说明 |
| --- | --- | --- | --- | --- |
| `benchscope` | builtin | `eval: serving` | 无（aiohttp） | Serving 链路精度：OpenAI 兼容 API，内置命令 `benchscope eval` |
| `native-hf` | native | `eval: native` | torch ≥ 2.0 + transformers ≥ 4.40（+ peft 配置 LoRA 时） | Native 原生精度：transformers 本地加载权重推理；CUDA 可用性校验 |
| `mock` | mock | `eval: mock` | 无 | mock 引擎：可控正确率伪输出，全链路联调与测试（mock 环境定位） |
| `vllm-0.23` / `sglang-0.5.10` | vllm / sglang | —（不支持精度评测） | torch + 框架 | 仅性能压测 |

- `benchs.py`：kind 白名单扩展 `native` / `mock`；`engine_summary()` 透出 `eval` 字段；`validate_benchs_yaml` 支持 native（requires 须含 torch + transformers）与 mock（无 requires）；对比表新增「Eval Support / 精度评测」维度。
- **内置命令 `benchscope eval`**（`cli.py` 新增子命令，对齐 `benchscope perf`）：CLI 与 Web 任务（`EvalTaskManager`）双入口共用同一评测核心（`accuracy.executor`）。

```bash
benchscope eval --engine benchscope|native-hf|mock \
  --model <model> [--lora-path <adapter_path>] [--lora-name <name>] \
  --dataset <dataset_id | /path/to/custom.jsonl> \
  [--base-url URL] [--api-key KEY] [--limit N] [--seed 1234] \
  [--temperature 0] [--top-p 1.0] [--max-tokens 512] [--concurrency 4] \
  [--judge-model <model>] [--name "<任务名>"]
```

产物落盘 `evals/eval-<MMDD-HHMMSS>/`（三件套），终端打印精度指标，可打包导入 Datas/evals。

## 3. 判分流水线

```
数据集加载（datasets.yaml 注册表 → 下载缓存 → JSONL 标准化 → 固定种子抽样）
    ↓
Prompt 构建（数据集元数据模板 + few-shot；聊天模板由 Serving 服务端应用）
    ↓
批量推理（executor：Serving=aiohttp 异步流式；Native=transformers generate；Mock=可控伪输出）
    ↓  逐条：完整回答 + usage Token 采集 + 失败重试(→invalid) + stop_event 中断 + WS 进度
判分（scorers 注册表按数据集绑定：choice / math / code / judge）
    ↓  逐条：答案抽取 → 判定 correct|wrong|invalid + 错因标签（知识错误/推理错误/输出格式错误）
指标汇总（metrics.py：accuracy/pass_rate/分学科/Token 统计/数据集专属指标/结论）
    ↓
基线对标（baselines.py：差值/S-A-B-C 档位/同尺寸排名/雷达聚合/自动结论）
    ↓
落库三件套（task.json / result.json / samples.jsonl）+ WS eval_task_* 推送
```

**判分器接口**（`scorers/base.py`）：

```python
class Scorer:
    def score(self, sample: dict, output: str) -> dict:
        """返回 {extracted, status: correct|wrong|invalid, error_tag, detail}"""
```

**错因标签**：`知识错误`（客观题解析成功但答案不符）、`推理错误`（数学答案不符）、`输出格式错误`（无法解析/空输出/截断）、`执行错误`（代码沙箱异常/超时）、`judge 异常`（评审模型评分失败）。

## 4. 数据模型（落库三件套，无数据库）

目录：`evals/<task_id>/`（task_id 形如 `eval-MMDD-HHMMSS`；配置项 `evals_dir`）。

### 4.1 任务主表 `task.json`（对齐 accuracy_task）

| 字段 | 说明 |
| --- | --- |
| `task_id` / `name` | 任务 ID / 任务名称 |
| `mode` | `serving`（链路）/ `native`（原生） |
| `engine_id` | 评测引擎（benchscope / native-hf / mock） |
| `model` / `model_version` | 被测模型名 / 版本（可选） |
| `lora_name` / `lora_path` | LoRA 微调增量模型：注册名与 adapter 路径（可选） |
| `dataset_id` / `dataset_name` / `dataset_path` | 数据集 id / 名称 / 自定义本地路径（三选二） |
| `base_model` | LoRA 任务记录的基模型（无 LoRA 时等于 model） |
| `status` | `pending / running / done / stopped / error` |
| `created_at` / `started_at` / `finished_at` | 时间 |
| `seed` / `temperature` / `top_p` / `max_tokens` / `concurrency` | 推理参数（固定种子可复现） |
| `limit` | 样本抽样上限（0 = 全量） |
| `judge_model` | MT-Bench 评审模型（可选） |
| `baseline_version` | 对标基线库版本 |
| `use_mock_env` | mock 环境开关（任务级，测试用） |
| `progress` | `{done, total}` 实时进度 |
| `estimate` | 预估 Token（见 §6） |
| `error` / `log_path` | 错误信息 / 终端日志路径（`logs/eval_<run_id>_<ts>.log`） |

### 4.2 结果表 `result.json`（对齐 accuracy_result）

| 字段 | 说明 |
| --- | --- |
| `total_samples` / `correct_samples` / `wrong_samples` / `invalid_samples` | 样本计数（溯源必备） |
| `accuracy` | 准确率 = correct / total（核心主指标，0–1 与百分比同存） |
| `pass_rate` | 有效可解析样本占比 = (total - invalid) / total |
| `subjects` | `[{subject, total, correct, accuracy}]` 分学科准确率（知识类） |
| `dataset_metrics` | 数据集专属：`exact_match` / `math_accuracy` / `pass@1` / `compile_rate` / `case_pass_rate` / `mt_bench_score`（首轮 / 二轮 / 分项）等 |
| `tokens` | Serving 专属：`prompt_tokens_total` / `completion_tokens_total` / `total_tokens` / `avg_prompt_tokens_per_sample` / `avg_completion_tokens_per_sample` |
| `estimate_vs_actual` | `{estimate_total, actual_total, deviation_pct, estimate_prompt, actual_prompt, estimate_completion, actual_completion}` |
| `invalid_sample_ids` / `error_sample_ids` | 异常样本 ID 列表 |
| `benchmark` | 基线对标结果（差值 / 档位 / 排名 / 雷达 / 结论，见 §7） |
| `conclusion` | 最终评测结论：`合格` / `精度下跌` / `异常` |
| `finished_at` | 结束时间 |

**结论规则**：`invalid / total > 0.2` 或 total = 0 → `异常`；有基线对标且主指标差值 < -5pp → `精度下跌`；其余 → `合格`。

### 4.3 单样本溯源 `samples.jsonl`（逐条追加，每行一个 JSON）

| 字段 | 说明 |
| --- | --- |
| `index` / `sample_id` | 行号 / 数据集样本 ID（缺失时用 index） |
| `subject` | 学科（知识类，可选） |
| `prompt` | 完整输入 Prompt（含 few-shot） |
| `output` | 模型原始输出 |
| `answer` | 标准答案 |
| `extracted` | 判分抽取结果 |
| `status` / `error_tag` | `correct / wrong / invalid` + 错因标签 |
| `tokens` | `{prompt_tokens, completion_tokens}`（Serving） |
| `latency_ms` | 单样本推理耗时 |
| `turns` / `judge` | MT-Bench：两轮对话与评审详情 |

## 5. 数据集体系（沿用 Settings → Datasets）

- 精度评测数据集**并入 `configs/datasets.yaml`** 注册表（Settings → Datasets 同步展示），新增精度元数据：`category: accuracy-*`（knowledge / math / code / chat / mix）、`eval` 段（`scorer` 绑定、`prompt_template`、`fewshot` 数、`answer_field`、`subject_field`、`choices_field`、`total_samples` 声明值、`metrics` 主指标名）。
- 9 个内置评测数据集：MMLU(14079) / CMMLU(11960) / C-Eval(13480) / GSM8K(7473) / MATH(5000) / HumanEval(164) / MBPP(974) / MT-Bench(80) / GAOKAO-Bench(2000，客观题子集，主观题标记不支持判分)。
- 下载缓存沿用 `datasets_dir`（ModelScope 优先，回退直链 URL）；JSONL 标准化为统一字段 `question / choices / answer / subject`（代码类 `prompt / test / entry_point`，对话类 `turns`）。
- 自定义数据集：① 本地 JSONL 路径直接引用（免上传）；② 上传导入。格式：`question` + `answer`（可选 `choices` / `subject`）。
- API：`GET /api/accuracy/datasets`、`POST /api/accuracy/datasets/import`、`GET .../{id}/preview`、`GET .../{id}/stats`（样本量 / 学科分布 / 实测 token 均值）。

## 6. Token 预估与强提醒（Serving 专属）

- `configs/token_estimates.yaml`：固化内置常量表（单样本输入 / 输出 Token 均值，工业界通用均值）：MMLU 180/8、CMMLU 200/8、C-Eval 220/8、GSM8K 120/80、MATH 180/120、HumanEval 150/200、MBPP 130/180、MT-Bench 300/350、GAOKAO-Bench 400/150。
- 预估优先级：**数据集实测统计**（`datasets_dir` 缓存实测 token 均值）> **内置常量** > 自定义数据集**字符估算**（chars/4）。
- `estimator.estimate(dataset_ref, limit, mode)` → `{prompt_tokens, completion_tokens, total_tokens, est_seconds, source}`。
- 前端：创建向导 Step3 Serving 模式**强提醒弹窗**（固定文案：数据集 / 预估总 Token / 计入计费负载提醒 / 确认启动），确认后才能执行；任务结束 `result.estimate_vs_actual` 记录预估 vs 实际偏差。

## 7. 开源基线对标

- `configs/baselines.yaml`：静态固化权威公开测评分数（通用：Llama3-8B/70B、Qwen2-7B/14B/72B、InternLM2、Mistral-7B；中文专项：Qwen2-Chinese、Llama3-CN、Zephyr），字段含 `params_b`（参数量，用于同尺寸排名）与 `source`（来源标注）；支持管理员手动更新（`PUT /api/accuracy/baselines`）。
- 对标计算（`baselines.py`）：
  1. **同数据集差值百分点**（当前模型 accuracy − 基线 accuracy）；
  2. **能力档位评级** S / A / B / C（按相对最优基线的差值：≥0 → S，≥-5pp → A，≥-15pp → B，否则 C）；
  3. **同尺寸段排名百分比**（参数量段内优于基线的比例）；
  4. **能力雷达图**（知识 / 数学 / 代码 / 对话四维，各维取该类数据集得分配比聚合）；
  5. **自动结论**：优于同尺寸开源基线 / 持平基线 / 明显劣于基线（风险预警）。
- API：`GET /api/accuracy/baselines`、`PUT /api/accuracy/baselines`、`GET /api/accuracy/tasks/{id}/benchmark`。

## 8. API 清单（`server/api_accuracy.py`，prefix `/api/accuracy`）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/tasks` | 精度任务列表（扫描 evals/*/task.json） |
| POST | `/tasks` | 创建并启动精度任务 |
| GET | `/tasks/{task_id}` | 任务详情（含 result / 进度） |
| POST | `/tasks/{task_id}/stop` | 终止任务 |
| DELETE | `/tasks/{task_id}` | 删除任务（目录一并删除） |
| GET | `/tasks/{task_id}/samples` | 单样本溯源（分页 / filter=all\|wrong\|invalid） |
| GET | `/tasks/{task_id}/export-samples` | 错题集 JSONL 导出（filter=wrong\|invalid） |
| GET | `/tasks/{task_id}/benchmark` | 基线对标详情 |
| GET | `/engines` | eval 引擎清单（含环境校验） |
| GET | `/engines/{id}/env-check` | 单引擎环境校验（native 含 CUDA） |
| GET | `/datasets` | 评测数据集清单（内置 + 自定义） |
| POST | `/datasets/import` | 自定义 JSONL 上传导入 |
| GET | `/datasets/{id}/preview` | 数据集预览（前 N 条） |
| GET | `/datasets/{id}/stats` | 样本统计（样本量 / 学科分布 / token 均值） |
| GET | `/estimate` | Token 预估（dataset_id 或 path + limit + mode） |
| GET | `/baselines` | 基线库清单 |
| PUT | `/baselines` | 管理员更新基线库 |
| POST | `/compare` | 多任务对比 / Native vs Serving 一致性差值 |

**WS 消息族**（复用 `WebSocketHub`，`/ws` 连接即回放 eval 任务快照）：`eval_task_snapshot / eval_task_started / eval_task_log / eval_task_progress / eval_task_result / eval_task_done / eval_task_error`。

## 9. 与性能模块的复用边界

| 设施 | 复用方式 |
| --- | --- |
| `ConfigManager` / 目录体系 / Providers | 直接使用（公共配置设施，含 payload 级 api 覆盖语义） |
| `WebSocketHub` / `/ws` | 直接使用（新增 eval_task_* 消息族） |
| `benchs.py` 引擎注册表 | 扩展（kind 白名单 + eval 能力字段 + 对比维度），精度引擎随注册表分发 |
| `datasets.yaml` / `datasets_dir` | 扩展（精度元数据）+ 沿用下载缓存 |
| `task_manager.py` / `benches/` / `parser.py` | **不复用**（EvalTaskManager / executor 独立实现） |
| `aiohttp` 调用底座 | 参考其 SSE 协议处理**独立重写**（accuracy/executor.py：完整答案收集 + usage，不共享代码） |
| 旧 `/api/test`（api_test.py） | 不动、不纳入精度体系（命名遗留，实为旧版性能压测） |

## 10. 依赖与测试

- **依赖策略**：`torch` / `transformers` / `peft` 不进必装依赖（extras `benchscope[accuracy-native]`）；Serving / Mock 引擎零新增依赖（aiohttp 已有）。
- **mock 环境**：`mock` 引擎（kind=mock）按样本返回可控伪输出（`mock_correct_rate` 控制正确率，默认 0.7），无 GPU 全链路可测；`mocks/openai_server.py` 支持 usage（Serving 引擎对 mock 服务联调）。
- **测试**：`tests/api/test_accuracy_*.py`（任务管理 / 引擎 / 数据集 / 执行器 / 判分器×4 / 预估 / 基线）；`tests/webui` 创建向导 / 强提醒 / 详情报表。

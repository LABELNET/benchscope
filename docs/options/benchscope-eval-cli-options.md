# benchscope eval — CLI 参数与说明

> **文档状态**：`benchscope eval` 子命令的完整参数与说明（对应 `benchscope/cli.py::_add_eval_args`）
> **用途**：直接执行一次精度评测并打印精度指标（与 Web 精度任务共用评测核心）
> **关联**：[docs/Readme.md](../Readme.md) · [docs/prds/Accuracy.md](../prds/Accuracy.md) · [docs/options/benchscope-perf-cli-options.md](./benchscope-perf-cli-options.md)

---

## 1. 概述

```bash
benchscope eval [选项]
```

- **作用**：执行一次精度评测（Serving / Native / Mock），输出精度指标（accuracy / pass_rate 等）。
- **数据集**：`--dataset` 传**内置数据集 id**（mmlu / gsm8k / ...）或**本地 JSONL 文件路径**。
- **引擎**：`--engine` 传精度引擎（`benchscope`=serving / `native-hf`=native / `mock`=联调）。
- **产物**：落盘 `evals/eval-<月日时分秒>/`（`task.json` / `result.json` / `samples.jsonl`），与 Web 精度任务一致，可在 **Datas/evals** 打包导入。

---

## 2. 常用示例

```bash
# Serving 链路评测（OpenAI 兼容服务，内置数据集 gsm8k）
benchscope eval --mode serving --model Qwen2.5-7B \
  --base-url http://127.0.0.1:8000 --dataset gsm8k --limit 200

# Native 原生评测（本地 transformers 权重 / HF id）
benchscope eval --mode native --model Qwen/Qwen2.5-7B --dataset mmlu --limit 100

# Mock 联调（无真实服务，验证链路）
benchscope eval --mode serving --engine mock --model mock-model --dataset gsm8k --use-mock-env
```

---

## 3. 参数表

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `--engine` | str | `benchscope` | 精度引擎 id（`benchscope`=serving / `native-hf`=native / `mock`=联调） |
| `--mode` | str | `serving` | 评测模式：`serving`（链路） / `native`（本地权重），取值 `serving` / `native` |
| `--model` | str | **必填** | 被测模型名（Native 可传本地权重路径或 HF id） |
| `--lora-path` | str | 空 | LoRA 微调增量模型（adapter）路径（可选） |
| `--lora-name` | str | 空 | LoRA 增量模型服务端注册名（Serving 请求侧 model，可选） |
| `--dataset` | str | **必填** | 内置数据集 id（mmlu / gsm8k / ...）或本地 JSONL 路径 |
| `--base-url` | str | 空 | 被测服务地址（Serving；缺省取全局 Provider 配置） |
| `--api-key` | str | 空 | 被测服务 API Key（可选） |
| `--limit` | int | `0` | 样本抽样上限（0 = 全量） |
| `--seed` | int | `1234` | 全局随机种子（抽样与生成，固定可复现） |
| `--temperature` | float | `0.0` | 采样温度 |
| `--top-p` | float | `1.0` | 核采样概率 |
| `--max-tokens` | int | `512` | 单样本最大输出 token |
| `--concurrency` | int | `4` | 并发推理数 |
| `--judge-model` | str | 空 | MT-Bench 评审模型（judge 数据集用） |
| `--mock-correct-rate` | float | `0.7` | mock 引擎正确率（0-1） |
| `--name` | str | 空 | 任务名称（可选） |
| `--use-mock-env` | flag | 关 | mock 环境标记（联调用） |

---

## 4. 输出指标

| 指标 | 含义 |
| --- | --- |
| `accuracy` (%) | 整体正确率 |
| `pass_rate` (%) | 通过率 |
| `total_samples` / `correct_samples` | 总样本数 / 正确数 |
| `wrong_samples` / `invalid_samples` | 错误数 / 无效数 |
| `dataset_metrics` | 数据集专项指标（`exact_match` / `math_accuracy` / `pass_at_1` / `compile_rate` / `mt_bench_score` 等） |
| `tokens.total_tokens` | 消耗总 token |
| `benchmark` | 基线对标（`baseline_used.name` / `diff_pp` / `grade` / `conclusion`） |
| `conclusion` | 结论（合格 / 精度下跌 / 持平 / 优于基线等） |

---

## 5. 产物与导入

- 落盘 `evals/eval-<月日时分秒>/`：
  - `task.json`（任务主表，对齐 Web 精度任务结构）
  - `result.json`（精度结果，含指标 / benchmark / conclusion）
  - `samples.jsonl`（单样本溯源）
- 另写终端日志 `logs/eval_<task_id>_<时间>.log`。
- 可在网页 **Datas → Evals** 查看 / 打包导入。

---

## 6. 相关

- 参数定义源码：`benchscope/cli.py::_add_eval_args`
- 评测核心：`benchscope/accuracy/`（executor / metrics / baselines / estimator）
- Web 精度任务：`docs/prds/Accuracy.md`、`web/src/views/AccuracyCreateView.vue`

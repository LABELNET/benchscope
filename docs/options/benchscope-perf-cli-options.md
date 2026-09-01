# benchscope perf — CLI 参数与说明

> **文档状态**：`benchscope perf` 子命令的完整参数与说明（对应 `benchscope/cli.py::_add_perf_args`）
> **用途**：执行一次 Bench CLI（自研引擎）压测并打印指标；与创建任务页 Step3 预览命令一致
> **关联**：[docs/Readme.md](../Readme.md) · [docs/prds/Performance.md](../prds/Performance.md) · [docs/options/benchscope-eval-cli-options.md](./benchscope-eval-cli-options.md)

---

## 1. 概述

```bash
benchscope perf [选项]
```

- **作用**：对 OpenAI 兼容推理服务执行一次自研引擎压测，输出吞吐与延迟指标。
- **模式**（`--mode`）：
  - `concurrency`（默认）：单并发压测一次；
  - `threshold`：从 1 并发起以 2 的次方递增 + 二分，找到满足阈值（TTFT/TPOT/吞吐）的**最大并发**（`best_concurrency`）。
- **产物**：自动落盘 `run.json` + 终端日志（`perf_<run_id>_*.log`），可打包导入 **Datas/perfs**。

---

## 2. 常用示例

```bash
# 并发模式：固定并发 8，每个并发 100 个请求，输入/输出各 1024 token
benchscope perf --model Qwen2.5-7B --base-url http://127.0.0.1:8000 \
  --concurrency 8 --num-prompts 100 --input-len 1024 --output-len 1024

# 阈值模式：TTFT ≤ 200ms 且 TPOT ≤ 100ms，搜索最大并发（上限 1024）
benchscope perf --model Qwen2.5-7B --mode threshold \
  --ttft-threshold-ms 200 --tpot-threshold-ms 100 \
  --max-concurrency-search 1024
```

---

## 3. 参数表

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `--engine` | str | `benchscope` | 引擎 id（默认自研引擎 benchscope） |
| `--model` | str | **必填** | 被测模型名 |
| `--base-url` | str | `http://127.0.0.1:8000` | 被测推理服务地址 |
| `--api-key` | str | 空 | 被测服务 API Key（可选） |
| `--backend` | str | `openai-chat` | 接口协议：`openai-chat` / `openai` |
| `--endpoint` | str | `/v1/chat/completions` | 请求的接口路径 |
| `--mode` | str | `concurrency` | 压测模式：`concurrency`（单并发） / `threshold`（阈值搜索找最佳并发） |
| `--concurrency` | int | `1` | 并发数（`concurrency` 模式） |
| `--num-prompts` | int | `0` | 请求总数（0 = 跟随并发数，每个 worker 一个请求） |
| `--input-len` | int | `1024` | 每个请求的输入 token 数 |
| `--output-len` | int | `1024` | 每个请求的输出 token 数 |
| `--request-rate` | str | `inf` | 请求速率（req/s，`inf` 表示不限速） |
| `--num-warmups` | int | `0` | 预热请求数（不计入指标） |
| `--chars-per-token` | float | `4.0` | 字符 / token 近似比（构造输入长度用） |
| `--timeout` | float | `600.0` | 单请求超时（秒），超时计为失败 |
| `--temperature` | float | `0.0` | 采样温度（压测建议固定为 0） |
| `--seed` | int | `0` | 随机种子（0 = 不固定） |

### 3.1 阈值模式专属参数

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `--ttft-threshold-ms` | float | `0.0` | TTFT 阈值（ms），`0` = 不判定 |
| `--tpot-threshold-ms` | float | `100.0` | TPOT 阈值（ms），`0` = 不判定 |
| `--output-threshold` | float | `0.0` | 输出吞吐阈值（tok/s），**低于**该值判为不满足，`0` = 不判定 |
| `--max-concurrency-search` | int | `4096` | 阈值搜索上限：达到仍满足阈值则取上限为最佳并发 |
| `--max-requests` | int | `4096` | 阈值探测中并发数超过该上限则强制结束（Finish） |

---

## 4. 阈值模式探测策略

1. 从 **1 并发**开始，以 **2 的次方递增**（1, 2, 4, 8, …）逐步压测；
2. 若 1 并发已不满足阈值 → 最佳并发为 1，结束；
3. 若执行到 `hi = 2^k` 不满足（`lo = 2^(k-1)` 满足）→ 在 `(lo, hi]` 内**二分**，直到相邻两个值，`lo` 即满足阈值的最大并发；
4. 达到搜索上限仍满足 → 上限并发为最佳（正常结束）。

输出每个已测并发的指标（吞吐 / TTFT / TPOT / ITL）与 `best_concurrency`。

---

## 5. 输出指标

| 指标 | 含义 |
| --- | --- |
| `successful_requests` | 成功请求数 |
| `failed_requests` | 失败请求数 |
| `benchmark_duration` | 压测墙钟时长 |
| `output_mean` (tok/s) | 输出吞吐（均值） |
| `total_mean` (tok/s) | 总吞吐（均值） |
| `ttft_mean` (ms) | 首 token 延迟（均值） |
| `tpot_mean` (ms) | 每输出 token 延迟（均值） |
| `itl_mean` (ms) | 令牌间隔延迟（均值） |

---

## 6. 产物与导入

- 落盘 `run.json`（含 `task_id` / `kind: perf` / `summary`）+ 日志 `perf_<run_id>_*.log`（写入 `perfs_dir` / `logs_dir`）。
- 打包为**扁平 zip**（含 `run.json` + 日志 + 可选 `metrics.json`），可在网页 **Datas → Perfs → 导入备份** 导入。

---

## 7. 相关

- 参数定义源码：`benchscope/cli.py::_add_perf_args`
- 自研引擎实现：`benchscope/benches/builtin_bench.py`
- 技能：`skills/bs-perfs-concurrency/`（并发）· `skills/bs-perfs-threshold/`（阈值）

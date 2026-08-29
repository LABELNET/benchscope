---
name: bs-perfs-threshold
description: >-
  Install benchscope and run a threshold-mode performance test with the
  benchscope perf command (search the max concurrency that still meets latency /
  throughput thresholds). Shows a built-in simple form for parameter
  configuration so the user can start benchmarking quickly. Saves the task and
  log data, then produces a zip archive importable in the Datas/perfs page.
  Use when the user wants to find the largest concurrency below a latency /
  throughput threshold with benchscope perf (e.g. "threshold 搜索", "找最佳并发",
  "max concurrency under TTFT < X").
version: 1.0.0
---

# bs-perfs-threshold — benchscope perf 阈值（threshold）搜索压测 (skill)

通过 **benchscope** 自研引擎的 `benchscope perf --mode threshold` 命令，对一个 OpenAI 兼容
推理服务执行**阈值搜索**：从 1 并发起，逐步升高并发，找到**仍满足阈值（TTFT / TPOT / 吞吐）
的最大并发数**（即推荐并发），并把任务数据与日志**打包成 zip**，可在网页 **Datas/perfs**
一键导入回 benchscope。

## When to use

- 用户想用 `benchscope perf` 做一次**阈值搜索压测**（找出满足延迟/吞吐阈值的最大并发）。
- 用户问「怎么用 benchscope 快速找最佳并发」「跑一次 threshold 测试」。
- 用户需要产出**可导入 Datas/perfs 的压缩包**，便于归档 / 分享 / 网页查看。

## 1. Prerequisites

- `pip install benchscope`（≥ 1.0.7；自研引擎基于 aiohttp + SSE）。
- 一个**可访问的 OpenAI 兼容推理服务**（`/v1/chat/completions` 或 `/v1/completions`），
  自研引擎**无需本地 vLLM / SGLang 框架环境**。
- （可选）`BENCHSCOPE_FAKE_BENCH=1` 走 mock 仿真，无真实服务也能演示。

## 2. 内置简单表单参数配置页面

加载本技能后，给用户展示一个**简单表单**（字段见 `templates/bench-perfs-config.yaml`），
让用户按需填写即可快速测试。字段说明：

| 表单字段 | CLI 参数 | 默认 | 说明 |
| --- | --- | --- | --- |
| 被测模型 | `--model` | （必填） | 服务中的模型名，如 `Qwen2.5-7B` |
| 服务地址 | `--base-url` | `http://127.0.0.1:8000` | 推理服务 Base URL |
| API Key | `--api-key` | 空 | 需要鉴权时填写 |
| 输入长度 | `--input-len` | `1024` | 每个请求的输入 token 数 |
| 输出长度 | `--output-len` | `1024` | 每个请求的输出 token 数 |
| 请求速率 | `--request-rate` | `inf` | `req/s`；`inf` 不限速 |
| 预热请求 | `--num-warmups` | `0` | 正式计时前的预热请求数 |
| 单请求超时 | `--timeout` | `600` | 单个请求最大等待秒数 |
| 采样温度 | `--temperature` | `0.0` | 压测建议固定为 0 |
| 随机种子 | `--seed` | `0` | `0` 表示不固定 |
| TTFT 阈值 | `--ttft-threshold-ms` | `0`（不判定） | 首 token 延迟上限（ms） |
| TPOT 阈值 | `--tpot-threshold-ms` | `100` | 每 token 延迟上限（ms） |
| 吞吐阈值 | `--output-threshold` | `0`（不判定） | 输出吞吐下限（tok/s），**低于**该值判为不满足 |
| 搜索上限 | `--max-concurrency-search` | `4096` | 达到上限仍满足阈值则取上限为最佳 |
| 最大请求数 | `--max-requests` | `4096` | 探测中并发数超过该上限则强制结束（Finish） |

**给用户的交互**：根据表单填写结果，AI 生成并执行对应的 `benchscope perf --mode threshold`
命令（见 §3），完成后按 §4 打包。

## 3. 执行 benchscope perf（threshold 模式）

```bash
benchscope perf \
  --engine benchscope \
  --model "<MODEL>" \
  --base-url "<BASE_URL>" \
  --api-key "<API_KEY>" \
  --backend openai-chat \
  --endpoint /v1/chat/completions \
  --input-len <INPUT_LEN> \
  --output-len <OUTPUT_LEN> \
  --request-rate <RATE> \
  --num-warmups <WARMUPS> \
  --timeout <TIMEOUT> \
  --temperature <TEMPERATURE> \
  --seed <SEED> \
  --mode threshold \
  --ttft-threshold-ms <TTFT_MS> \
  --tpot-threshold-ms <TPOT_MS> \
  --output-threshold <OUT_TOK_PER_S> \
  --max-concurrency-search <SEARCH_CAP> \
  --max-requests <MAX_REQS>
```

**探测策略**（与网页 Performance 阈值模式一致）：

1. 从 **1 并发**开始，以 **2 的次方递增**（1, 2, 4, 8, …）逐步压测；
2. 若 1 并发已不满足阈值 → 最佳并发为 1，结束（情景 1）；
3. 若执行到 `hi = 2^k` 不满足阈值（`lo = 2^(k-1)` 满足）→ 在 `(lo, hi]` 内**二分**，
   每次测 `(lo+hi)/2`，直到相邻两个值，`lo` 即满足阈值的**最大并发**；
4. 若达到搜索上限仍满足 → 上限并发为最佳（正常结束）。

命令行最终输出每个已测并发的指标（吞吐 / TTFT / TPOT / ITL），并给出
**best_concurrency**（满足阈值的最大并发）与建议。

## 4. 保存任务与日志，生成可导入压缩包（zip）

打包格式与 bs-perfs-concurrency 一致——**扁平 zip**（不含目录，`run.json` 必须项）：

```
<run_id>.zip
├── run.json                       # {"task_id":"<run_id>","kind":"perf","mode":"threshold","model":"...",
│                                  #  "status":"done","best_concurrency":N,"summary":{...}}
├── perf_<run_id>_<时间戳>.log     # 终端输出日志（前缀必须是 perf_）
├── metrics.json                   # 可选：各并发指标（concurrency → output/ttft/tpot/itl）
└── 其他文件                        # 可选：命令、配置、分析等
```

打包步骤（与 concurrency 技能一致）：

1. 确定 `run_id`（如 `perf_<model>_<MMDDHHMMSS>`，与 zip 内 run.json 的 `task_id` 一致）。
2. 写 `run.json`，至少含 `task_id` / `kind: "perf"` / `mode: "threshold"` / `model` / `status` /
   `best_concurrency` / `summary`。
3. 将终端输出保存为 `perf_<run_id>_<时间戳>.log`。
4. 打包：

```bash
cd <打包目录> && zip <run_id>.zip run.json perf_<run_id>_*.log metrics.json
```

> 提示：threshold 模式下 `run.json` 建议带 `mode: "threshold"` 与 `best_concurrency`，
> 便于网页按阈值模式展示。

## 5. 在网页 Datas/perfs 导入

1. 启动 benchscope（`benchscope serve` 或 `python -m benchscope`），打开网页。
2. 进入 **Datas** → **Perfs** → **导入备份**，选择上一步的 `<run_id>.zip`。
3. 导入成功后在 Perfs 记录中可见该任务；可查看日志 / 指标 / 重新导出。

## 6. 验收清单

- [ ] 表单字段已展示并收集（模型 / 服务地址 / 阈值 / 搜索上限等）
- [ ] `benchscope perf --mode threshold` 可运行（`--model` 必填）
- [ ] 输出了 `best_concurrency`（满足阈值的最大并发）
- [ ] 生成了 `run.json`（含 `task_id`、`kind: perf`、`mode: threshold`）与终端日志 `perf_<run_id>_*.log`
- [ ] 产物为**扁平 zip**，可在 Datas/perfs 导入成功

## 7. Troubleshooting

- **`--model` 必填** — 表单中的模型名为空时提示用户补全。
- **阈值全 0** — 默认仅 TPOT 阈值生效；其余阈值设为 0 表示不判定，避免误伤。
- **最佳并发=1** — 1 并发即不满足阈值，需检查服务性能或阈值是否过严。
- **服务不可达 / 指标全 0** — 见 bs-perfs-concurrency 的 Troubleshooting。

## References

- 阈值模式逻辑：[docs/prds/Performance.md](../../../docs/prds/Performance.md)、
  [docs/prds/Performance-Create.md](../../../docs/prds/Performance-Create.md)
- 表单参数模板：[templates/bench-perfs-config.yaml](templates/bench-perfs-config.yaml)
- 技能规范：[skills/Readme.md](../Readme.md)

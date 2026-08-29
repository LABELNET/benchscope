---
name: bs-perfs-concurrency
description: >-
  Install benchscope and run a concurrency-mode performance test with the
  benchscope perf command. Shows a built-in simple form for parameter
  configuration so the user can start benchmarking quickly. Saves the task and
  log data, then produces a zip archive importable in the Datas/perfs page.
  Use when the user wants to run a concurrency benchmark with benchscope perf
  (e.g. "run a concurrency perf test", "并发压测", "measure throughput at concurrency N").
version: 1.0.0
---

# bs-perfs-concurrency — benchscope perf 并发（concurrency）压测 (skill)

通过 **benchscope** 自研引擎的 `benchscope perf` 命令，对一个 OpenAI 兼容推理服务执行
**并发（concurrency）模式**性能压测：配置模型 / 服务地址 / 并发数 / 请求总量 / 输入输出长度等
参数，快速跑出吞吐与延迟指标，并把任务数据与日志**打包成 zip**，可在网页
**Datas/perfs** 一键导入回 benchscope 查看历史记录。

## When to use

- 用户想用 `benchscope perf` 做一次**并发压测**（测某个固定并发/多并发的吞吐与延迟）。
- 用户问「怎么用 benchscope 快速测并发性能」「跑一次 concurrency 测试」。
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
| 并发数 | `--concurrency` | `1` | 同时发起的请求并发数 |
| 请求总数 | `--num-prompts` | `0` | 总请求数；`0` = 跟随并发数 |
| 输入长度 | `--input-len` | `1024` | 每个请求的输入 token 数 |
| 输出长度 | `--output-len` | `1024` | 每个请求的输出 token 数 |
| 请求速率 | `--request-rate` | `inf` | `req/s`；`inf` 不限速 |
| 预热请求 | `--num-warmups` | `0` | 正式计时前的预热请求数 |
| 单请求超时 | `--timeout` | `600` | 单个请求最大等待秒数 |
| 采样温度 | `--temperature` | `0.0` | 压测建议固定为 0 |
| 随机种子 | `--seed` | `0` | `0` 表示不固定 |

**给用户的交互**：根据表单填写结果，AI 生成并执行对应的 `benchscope perf` 命令
（见 §3），完成后按 §4 打包。

## 3. 执行 benchscope perf（concurrency 模式）

组装命令（所有参数均可选填，缺省用表单/默认值）：

```bash
benchscope perf \
  --engine benchscope \
  --model "<MODEL>" \
  --base-url "<BASE_URL>" \
  --api-key "<API_KEY>" \
  --backend openai-chat \
  --endpoint /v1/chat/completions \
  --concurrency <CONCURRENCY> \
  --num-prompts <NUM_PROMPTS> \
  --input-len <INPUT_LEN> \
  --output-len <OUTPUT_LEN> \
  --request-rate <RATE> \
  --num-warmups <WARMUPS> \
  --timeout <TIMEOUT> \
  --temperature <TEMPERATURE> \
  --seed <SEED>
```

- 输出会打印各指标（吞吐 tok/s、TTFT / TPOT / ITL 的 mean / P99 等）。
- 若要同时测**多个并发**以观察扩展性，可对每个并发各执行一次并分别记录；
  如需完整「多并发曲线 + 网页可视化」，推荐在网页 **Performance → 创建任务**
  （concurrency 模式）中配置并发列表后运行。

## 4. 保存任务与日志，生成可导入压缩包（zip）

为让结果能在网页 **Datas/perfs** 导入，须把本次运行打包为一个 **zip**，结构如下
（**扁平文件名，不含目录**，`run.json` 是必须项）：

```
<run_id>.zip
├── run.json              # 必须：{"task_id":"<run_id>","kind":"perf","model":"...","status":"done","summary":{...}}
├── perf_<run_id>_<时间戳>.log   # 终端输出日志（可选，前缀必须是 perf_）
├── metrics.json          # 可选：结构化指标（output/total/ttft/tpot/itl 的 mean/p99）
└── 其他文件               # 可选：命令、配置、分析等
```

打包步骤：

1. 确定 `run_id`（如 `perf_<model>_<MMDDHHMMSS>`，需与 zip 内 run.json 的 `task_id` 一致）。
2. 写 `run.json`，至少含 `task_id` / `kind: "perf"` / `model` / `status` / `summary`
   （summary 可含 `concurrency` / `output_mean` / `ttft_mean` / `tpot_mean` 等）。
3. 将终端输出保存为 `perf_<run_id>_<时间戳>.log`（`run.json` 的 `log_path` 同步指向该文件名）。
4. 用 `zip` 命令打包（**不要带外层目录**）：

```bash
cd <打包目录> && zip <run_id>.zip run.json perf_<run_id>_*.log metrics.json
```

> 提示：benchscope 网页导出 / 备份用的是**扁平 zip**（含 run.json、终端日志、summary 等），
> Datas/perfs 的「导入备份」会校验 run.json 并写入 `perfs_dir/<run_id>/`。这里生成的 zip 与其格式一致。

## 5. 在网页 Datas/perfs 导入

1. 启动 benchscope（`benchscope serve` 或 `python -m benchscope`），打开网页。
2. 进入 **Datas** → **Perfs** → **导入备份**（或「导入」按钮），选择上一步的 `<run_id>.zip`。
3. 导入成功后在 Perfs 记录中可见该任务；可查看日志 / 指标 / 重新导出。
   - 若提示「已存在」，说明 `run_id` 已导入过（可用不同 `run_id` 或先删除旧记录）。

## 6. 验收清单

- [ ] 表单字段已展示并收集（模型 / 服务地址 / 并发 / 长度等）
- [ ] `benchscope perf` 命令可运行（`--model` 必填）
- [ ] 生成了 `run.json`（含 `task_id`、`kind: perf`）与终端日志 `perf_<run_id>_*.log`
- [ ] 产物为**扁平 zip**，可在 Datas/perfs 导入成功

## 7. Troubleshooting

- **`--model` 必填** — 表单中的模型名为空时提示用户补全。
- **服务不可达** — 检查 `--base-url` / `/v1/models`；可先 `curl` 验证。
- **指标全 0** — 使用 mock 时输出需匹配 benchscope 的 `parser.py` 正则；
  真实服务则检查服务是否正常返回 completions。
- **zip 导入失败（缺 run.json）** — 确认 zip 内含扁平的 `run.json`，且 `task_id` 非空。

## References

- 并发 / 阈值模式与命令参数：[docs/prds/Performance.md](../../../docs/prds/Performance.md)、
  [docs/prds/Performance-Create.md](../../../docs/prds/Performance-Create.md)
- 表单参数模板：[templates/bench-perfs-config.yaml](templates/bench-perfs-config.yaml)
- 技能规范：[skills/Readme.md](../Readme.md)

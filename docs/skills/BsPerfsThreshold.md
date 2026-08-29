# benchscope perf 阈值搜索压测技能 — bs-perfs-threshold

> **版本**：1.0.0　**技能目录**：[`skills/bs-perfs-threshold/`](../../skills/bs-perfs-threshold/)
> **最后更新**：2026-08-31
> **文档命名**：一个技能一个说明文档（`BsPerfsThreshold.md` ↔ `bs-perfs-threshold`）
> **关联**：[Skills 体系总入口](./Readme.md) · [BsPerfsConcurrency.md](./BsPerfsConcurrency.md)（并发压测）

---

## 1. 用途与触发场景

用 **benchscope** 自研引擎的 **`benchscope perf --mode threshold`** 命令，对一个 OpenAI 兼容
推理服务执行**阈值搜索**：从 1 并发起逐步升高，找到**仍满足阈值（TTFT / TPOT / 吞吐）的最大并发数**
（推荐并发），并把任务数据与日志**打包成 zip**，可在网页 **Datas/perfs** 一键导入查看。

**触发场景**：想用 benchscope 快速找满足延迟/吞吐阈值的最大并发、需要产出**可导入 Datas/perfs
的压缩包**归档结果。

**前置条件**：

- `pip install benchscope`（≥ 1.0.7，自研引擎依赖 aiohttp）；
- 一个**可访问的 OpenAI 兼容服务**（`/v1/chat/completions` 或 `/v1/completions`），
  自研引擎**无需本地 vLLM / SGLang 框架环境**；
- （可选）`BENCHSCOPE_FAKE_BENCH=1` 走 mock 仿真，无真实服务也能演示。

---

## 2. 内置表单参数配置

使用技能时会展示一个**简单表单**（字段见 `templates/bench-perfs-config.yaml`），让用户按需填写即可快速测试：

| 表单字段 | CLI 参数 | 默认 | 说明 |
| --- | --- | --- | --- |
| 被测模型 | `--model` | 必填 | 服务中的模型名 |
| 服务地址 | `--base-url` | `http://127.0.0.1:8000` | 推理服务 Base URL |
| API Key | `--api-key` | 空 | 需要鉴权时填写 |
| 输入/输出长度 | `--input-len` / `--output-len` | `1024` / `1024` | 每请求 token 数 |
| 请求速率 | `--request-rate` | `inf` | `req/s`；`inf` 不限速 |
| 预热请求 | `--num-warmups` | `0` | 不计入指标 |
| 单请求超时 | `--timeout` | `600` | 秒 |
| 采样温度 / 种子 | `--temperature` / `--seed` | `0.0` / `0` | 压测建议固定 |
| TTFT 阈值 | `--ttft-threshold-ms` | `0`（不判定） | 首 token 延迟上限（ms） |
| TPOT 阈值 | `--tpot-threshold-ms` | `100` | 每 token 延迟上限（ms） |
| 吞吐阈值 | `--output-threshold` | `0`（不判定） | 输出吞吐下限（tok/s），低于判为不满足 |
| 搜索上限 | `--max-concurrency-search` | `4096` | 达到上限仍满足阈值则取上限为最佳 |
| 最大请求数 | `--max-requests` | `4096` | 探测中并发数超过该上限则强制结束（Finish） |

---

## 3. 执行 benchscope perf（threshold 模式）

```bash
benchscope perf --model "<MODEL>" --base-url "<BASE_URL>" \
  --mode threshold --input-len 1024 --output-len 1024 \
  --ttft-threshold-ms 0 --tpot-threshold-ms 100 --output-threshold 0 \
  --max-concurrency-search 4096 --max-requests 4096
```

**探测策略**（与网页 Performance 阈值模式一致）：

1. 从 **1 并发**开始，以 **2 的次方递增**（1, 2, 4, 8, …）逐步压测；
2. 若 1 并发已不满足阈值 → 最佳并发为 1，结束（情景 1）；
3. 若执行到 `hi = 2^k` 不满足阈值（`lo = 2^(k-1)` 满足）→ 在 `(lo, hi]` 内**二分**，
   每次测 `(lo+hi)/2`，直到相邻两个值，`lo` 即满足阈值的**最大并发**；
4. 若达到搜索上限仍满足 → 上限并发为最佳（正常结束）。

命令行最终输出每个已测并发的指标（吞吐 / TTFT / TPOT / ITL），并给出 **best_concurrency**。

---

## 4. 保存任务/日志，生成可导入 Datas/perfs 的压缩包

为让结果能在网页 **Datas/perfs** 导入，须把本次运行打包为一个**扁平 zip**（不含目录）：

```
<run_id>.zip
├── run.json                       # 必须：{"task_id":"<run_id>","kind":"perf","mode":"threshold",...,
│                                  #        "status":"done","best_concurrency":N,"summary":{...}}
├── perf_<run_id>_<时间戳>.log     # 终端输出日志（前缀必须是 perf_）
├── metrics.json                   # 可选：各并发指标
└── 其他文件                        # 可选
```

- `run.json` 必须含 `task_id`（= run_id）与 `kind: "perf"`；阈值模式建议带 `mode: "threshold"`
  与 `best_concurrency`，便于网页按阈值模式展示。
- `benchscope perf --mode threshold`（`_perf_threshold`）已自动落盘 `run.json` 与日志占位，
  技能在此基础上补齐终端日志后 `zip` 打包即可。

```bash
cd <打包目录> && zip <run_id>.zip run.json perf_<run_id>_*.log metrics.json
```

---

## 5. 在网页 Datas/perfs 导入

1. 启动 benchscope（`benchscope serve` 或 `python -m benchscope`），打开网页；
2. 进入 **Datas** → **Perfs** → **导入备份**，选择 `<run_id>.zip`；
3. 导入成功后在 Perfs 记录中可见该任务，可查看日志 / 指标 / 重新导出。
   - 若提示「已存在」，说明 `run_id` 已导入过（换 `run_id` 或先删除旧记录）。

---

## 6. 排错

| 现象 | 原因与处理 |
| --- | --- |
| `--model` 必填 | 表单模型名为空，提示用户补全 |
| 阈值全 0 | 默认仅 TPOT 阈值生效；其余阈值设为 0 表示不判定，避免误伤 |
| 最佳并发=1 | 1 并发即不满足阈值，检查服务性能或阈值是否过严 |
| 服务不可达 / 指标全 0 | 见 BsPerfsConcurrency.md §6 |

---

## 7. 维护记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| 1.0.0 | 2026-08-30 | 初版：benchscope perf 阈值搜索（内置表单 + 打包导入 Datas/perfs） |

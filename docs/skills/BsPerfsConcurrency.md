# benchscope perf 并发压测技能 — bs-perfs-concurrency

> **版本**：1.0.0　**技能目录**：[`skills/bs-perfs-concurrency/`](../../skills/bs-perfs-concurrency/)
> **最后更新**：2026-08-31
> **文档命名**：一个技能一个说明文档（`BsPerfsConcurrency.md` ↔ `bs-perfs-concurrency`）
> **关联**：[Skills 体系总入口](./Readme.md) · [BsPerfsThreshold.md](./BsPerfsThreshold.md)（阈值搜索）

---

## 1. 用途与触发场景

用 **benchscope** 自研引擎的 **`benchscope perf`** 命令，对一个 OpenAI 兼容推理服务执行
**并发（concurrency）模式**性能压测：配置模型 / 服务地址 / 并发数 / 请求总量 / 输入输出长度等，
快速跑出吞吐与延迟指标，并把任务数据与日志**打包成 zip**，可在网页 **Datas/perfs** 一键导入查看。

**触发场景**：想用 benchscope 快速压测并发性能、需要产出**可导入 Datas/perfs 的压缩包**归档结果。

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
| 并发数 | `--concurrency` | `1` | 同时发起的请求并发数 |
| 请求总数 | `--num-prompts` | `0` | 总请求数；0 = 跟随并发数 |
| 输入/输出长度 | `--input-len` / `--output-len` | `1024` / `1024` | 每请求 token 数 |
| 请求速率 | `--request-rate` | `inf` | `req/s`；`inf` 不限速 |
| 预热请求 | `--num-warmups` | `0` | 不计入指标 |
| 单请求超时 | `--timeout` | `600` | 秒 |
| 采样温度 / 种子 | `--temperature` / `--seed` | `0.0` / `0` | 压测建议固定 |

---

## 3. 执行 benchscope perf（concurrency 模式）

```bash
benchscope perf --model "<MODEL>" --base-url "<BASE_URL>" \
  --concurrency <CONC> --num-prompts <N> \
  --input-len 1024 --output-len 1024 --request-rate inf \
  --num-warmups 0 --timeout 600 --temperature 0.0 --seed 0
```

- 输出会打印各指标（吞吐 tok/s、TTFT / TPOT / ITL 的 mean / P99 等）。
- 若要同时测**多个并发**以观察扩展性，可对每个并发各执行一次并分别记录；如需完整「多并发曲线 +
  网页可视化」，推荐在网页 **Performance → 创建任务**（concurrency 模式）中配置并发列表后运行。

---

## 4. 保存任务/日志，生成可导入 Datas/perfs 的压缩包

为让结果能在网页 **Datas/perfs** 导入，须把本次运行打包为一个**扁平 zip**（不含目录）：

```
<run_id>.zip
├── run.json                       # 必须：{"task_id":"<run_id>","kind":"perf","model":...,
│                                  #        "status":"done","summary":{...}}
├── perf_<run_id>_<时间戳>.log     # 终端输出日志（前缀必须是 perf_）
├── metrics.json                   # 可选：结构化指标
└── 其他文件                        # 可选
```

- `run.json` 必须含 `task_id`（= run_id）与 `kind: "perf"`；日志文件名前缀必须是 `perf_`。
- `benchscope perf`（`_perf`）已自动落盘 `run.json` 与日志占位（写入 `perfs_dir` / `logs_dir`），
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
| 服务不可达 | 检查 `--base-url` / `/v1/models`，先 `curl` 验证 |
| 指标全为 0 | 输出文本不匹配 `parser.py` 正则（FAKE 模式检查 `mocks/` 输出格式） |
| zip 导入失败（缺 run.json） | zip 内缺扁平的 `run.json` 或 `task_id` 为空 |

---

## 7. 维护记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| 1.0.0 | 2026-08-30 | 初版：benchscope perf 并发压测（内置表单 + 打包导入 Datas/perfs） |

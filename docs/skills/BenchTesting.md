# 性能测试技能 — vllm-bench-testing / sglang-bench-testing

> **版本**：1.1.0（两者同步）
> **技能目录**：[`skills/vllm-bench-testing/`](../../skills/vllm-bench-testing/) ·
> [`skills/sglang-bench-testing/`](../../skills/sglang-bench-testing/)
> **最后更新**：2026-08-29
> **关联**：[Skills 体系总入口](./Readme.md) · [BenchEngineAuthoring.md](./BenchEngineAuthoring.md)（新增引擎版本走该技能）

---

## 1. 用途与触发场景

对 **vLLM / SGLang 推理服务**执行性能测试：产出吞吐与延迟数据（TTFT / TPOT / ITL / output & total tok/s），
并留存日志与表格用于对比与验收。

**触发场景**：需要压测数据、需要可复现的压测配置、需要留档（日志 + xlsx 汇总）用于对比或验收。

> **需要新增引擎版本时**（如「添加 vllm 0.24」）→ 改用
> [bench-engine-authoring](./BenchEngineAuthoring.md) 技能。

**前置条件**：

- `pip install benchscope`（≥ 1.0.7，自研引擎依赖 aiohttp）；
- 原生引擎需要本地框架 CLI（`vllm --version` / `python -m sglang.bench_serving`），
  **或使用内置 `benchscope` 引擎（无需任何本地框架）**；
- 可达的 OpenAI 兼容端点（`/v1/models`、`/v1/chat/completions`）。

---

## 2. 引擎选择与环境校验（benchscope ≥ 1.0.7）

引擎**按版本管理**，且在配置参数前先做环境校验：

| 引擎 | kind | 命令 | 环境要求 |
| --- | --- | --- | --- |
| `benchscope` | builtin（进程内 aiohttp + SSE） | 无 | **无** —— 可对任意本地/远端 OpenAI 兼容服务压测 |
| `vllm-0.23` | vllm（子进程 CLI） | `vllm bench serve` | `torch>=2.0` + `vllm>=0.23,<0.24` |
| `sglang-0.5.10` | sglang（子进程 CLI） | `python -m sglang.bench_serving` | `torch` + `sglang>=0.5.10,<0.6` |
| 自定义 `<framework>-<ver>` | 对应 kind | 对应 CLI | `torch` + 该版本框架包 |

**强制规则**：

- 原生引擎**必须**通过环境校验（torch + 框架版本 spec + CLI 可用性），否则**「下一步」被阻断**并展示安装提示；
- 内置 `benchscope` 引擎**无框架依赖**，始终可用；
- 引擎定义为 **yaml 驱动**（`configs/benchs.yaml`），可在 Settings → Bench 引擎新增版本。

**操作**：Performance → Create → Step 1 → 选择**测试引擎** → 等待环境标签（`Ready` / `Not Satisfied`）→ 进入参数配置。

---

## 3. 配置

### 3.1 服务（Settings → 服务设置）

| 字段 | 取值 |
| --- | --- |
| Base URL | `http://<host>:<port>`（如 `http://192.168.1.67:8000`） |
| Endpoint | `/v1/chat/completions` |
| API Key | 服务端要求鉴权时填写，否则留空 |
| GPU | 通过 `nvidia-smi` 自动探测，否则手工填名称/数量 |
| logs_dir / datasets_dir | `./logs`、`./datasets` |
| TPOT 阈值（ms） | 用于高亮 best/最接近的行，如 `100` |
| bench 命令模板 | vLLM：`vllm bench serve`；SGLang：`python -m sglang.bench_serving` |

### 3.2 框架参数（测试配置 → 框架参数）

表单字段映射到各自 CLI flag：

- **vLLM**：`--backend openai-chat` · `--endpoint /v1/chat/completions` · `--host` · `--port` ·
  `--tokenizer <model>` · `--trust-remote-code` · `--ignore-eos` · `--burstiness 1.0` · `--seed 0` ·
  `--num-warmups 0` · `--metric-percentiles 99`；采样 `--temperature 0.0` · `--top-p 1.0` ·
  `--top-k -1` · `--min-p 0.0`；高级 `--sharegpt-output-len 128` · `--no-stream` ·
  `--disable-tqdm` · `--save-result` · `--profile`
- **SGLang**：对应 `sglang.bench_serving` 的等价参数（在自由编辑区补充其余 flag）

任意额外 flag 均可通过自由编辑区追加（如 `--frequency-penalty 0.0`、`--repetition-penalty 1.0`）。

### 3.3 数据集

- **random** —— 选择输入/输出长度对（默认 `3K/1K`=`3072/1024`、`1K/1K`=`1024/1024`、`256/256`），可自定义长度对；
- **sharegpt** —— 从 ModelScope 自动下载 `gliang1001/ShareGPT_V3_unfiltered_cleaned_split`
  （JSON 数组流式转换为 jsonl，缓存于 `datasets/sharegpt/`）；
- **custom** —— 上传 jsonl 或指定服务本地 jsonl 路径（行为同 ShareGPT）。

### 3.4 并发与速率

- 并发列表可编辑，默认 `1,4,8,16,32,40,64,128`；
- `--max-concurrency` = `--num-prompts` = 每个并发值；
- 请求速率：`inf`（不限，推荐）或指定 `req/s`。

---

## 4. 测试流程

1. 启动：`benchscope` → 打开 `http://127.0.0.1:8080`；
2. 确认顶部导航**服务**与**环境**在线，模型列表从 `/v1/models` 加载；
3. **Settings** 配置 Base URL / GPU / 模板；用**测试连接**验证；
4. 测试环境面板：从 `/v1/models` 选择**模型**（离线时可手工输入）；
5. **测试配置**：选择数据集、并发列表、请求速率、GPU 数量、TPOT 阈值、框架参数；
6. **命令预览**检查完整命令 → **测试进度 → 开始测试**；
7. 观察**测试进度**（进度环、当前 case@并发、实时日志尾部），可**取消测试**；
8. **测试结果**按并发流式产出每行结果（双语表格）与六条曲线
   （Output 吞吐、Total 吞吐、TTFT mean、TPOT mean、TTFT P99、TPOT P99 vs 并发）；
9. 无框架 CLI 的离线/演示运行：`BENCHSCOPE_FAKE_BENCH=1 python -m benchscope`。

**参考命令形态（vLLM）**：

```bash
vllm bench serve \
  --max-concurrency 8 --num-prompts 8 \
  --random-input-len 1024 --random-output-len 1024 \
  --model <model> --tokenizer <model> \
  --host <host> --port 8000 --trust-remote-code \
  --backend openai-chat --dataset-name random \
  --endpoint /v1/chat/completions --ignore-eos \
  --request-rate inf
# sharegpt/custom:  --dataset-name sharegpt --dataset-path <jsonl> --sharegpt-output-len 128
```

---

## 5. 日志与产物

每次运行生成 `logs/<MMDD-HHMMSS>/`：

| 产物 | 说明 |
| --- | --- |
| `<model>_<case>_X<gpu>.log` | 原始 bench 日志（每个 case，各并发追加） |
| `<model>_X<gpu>.log` | 均值汇总 CSV：`并发数,Output Token,Peak Output Token,Total Token,TTFT,TPOT,ITL` |
| `<model>_X<gpu>_p99.log` | P99 汇总 CSV（同列，TTFT/TPOT/ITL 为 P99） |
| `benchmark-*.xlsx` | 两个 sheet：**均值 Mean** / **P99**；列：`GPU, 模型, 精度, 推理框架, 输入长度, 输出长度, 并发数, Output, Peak Output, Total, TTFT, ITL, TPOT, 单用户`（`单用户 = 1000 / TPOT`） |

**解析指标**（mean + P99）：`output` · `peakoutput` · `total` · `ttft` · `tpot` · `itl`，另含 `req_per_s`；
best 并发高亮 = TPOT 最接近且不超过阈值的行。

**日志管理**页（或 Logs 视图）列出各次运行，可预览/下载原始日志，**均值分析** / **P99 分析** 标签展示表格 + 六条曲线。

---

## 6. 排错

| 现象 | 原因与处理 |
| --- | --- |
| 「未找到命令执行环境：vllm」 | 框架 CLI 缺失；安装它或修正 bench 命令模板（绝对路径 / conda 环境） |
| 推理服务离线 | Base URL/端点不可达；用**测试连接**检查 `/v1/models` |
| 数据集下载失败 | ModelScope 不可达；预置 `datasets/sharegpt/` 或改用 custom 数据集 |
| 无模型可选 | 服务离线；勾选**离线强制开始**并手工填写模型名 |
| 指标全为 0 | 输出文本不匹配 `parser.py` 正则（FAKE 模式检查 `mocks/` 输出格式） |

---

## 7. 维护记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| 1.1.0 | 2026-08-29 | 补 `version` frontmatter；新增「引擎选择与环境校验」章节（环境要求表 + 阻断规则）；新增 README.md 与 package.sh；章节重编号 |
| 1.0.0 | — | 初版：vLLM / SGLang 性能测试流程与参数说明 |

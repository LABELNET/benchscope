---
name: vllm-bench-testing
description: >-
  Configure and run performance benchmarks against a vLLM inference service
  using benchscope. Covers OpenAI-compatible service configuration, vllm bench
  serve parameters, random/sharegpt/custom datasets, concurrency & request rate,
  realtime results, and log recording (mean + P99 summary and benchmark-*.xlsx).
---

# vLLM Benchmark Testing (skill)

Use this skill to performance-test a **vLLM** inference service. The workflow
runs through `benchscope` (pip-installable web tool) which drives
`vllm bench serve` as a subprocess on the machine where benchscope is installed;
the inference server only needs an **OpenAI-compatible API** — no server-side
plugin required.

## When to use
- You want throughput/latency numbers (TTFT / TPOT / ITL / output & total tok/s) for a vLLM deployment.
- You need a reproducible benchmark config (host/port/model/dataset/concurrency).
- You need recorded logs + a spreadsheet summary (mean & P99) for comparison/sign-off.

## 1. Prerequisites
- `pip install benchscope` (or run from source).
- vLLM CLI available on the machine that runs benchscope: `vllm --version`.
- A reachable vLLM OpenAI-compatible endpoint (`/v1/models`, `/v1/chat/completions`).
- Benchscope reads `~/.pypirc` / `TWINE_USERNAME` + `TWINE_PASSWORD` only for publishing (optional); not needed to run.

## 2. Configuration

### Service (benchscope → Settings → 服务设置)
| Field | Value |
| --- | --- |
| Base URL | `http://<host>:<port>` (e.g. `http://192.168.1.67:8000`) |
| Endpoint | `/v1/chat/completions` |
| API Key | blank unless the server requires auth |
| GPU | auto-detect via `nvidia-smi`, else manual name/count |
| logs_dir / datasets_dir | `./logs`, `./datasets` |
| TPOT threshold (ms) | used to highlight best/nearest rows, e.g. `100` |
| vLLM bench command template | `vllm bench serve` |

### Framework parameters (vLLM page → 测试配置 → 框架参数)
Common form fields map to `vllm bench serve` flags:
- `--backend openai-chat` · `--endpoint /v1/chat/completions`
- `--host <host>` · `--port <port>` · `--tokenizer <model>`
- `--trust-remote-code` · `--ignore-eos` · `--burstiness 1.0` · `--seed 0`
- `--num-warmups 0` · `--metric-percentiles 99`
- sampling: `--temperature 0.0` · `--top-p 1.0` · `--top-k -1` · `--min-p 0.0`
- advanced: `--sharegpt-output-len 128` · `--no-stream` · `--disable-tqdm` · `--save-result` · `--profile`
- any extra flag can be added via the free-form editor (e.g. `--frequency-penalty 0.0`, `--repetition-penalty 1.0`).

### Datasets (vLLM page → 测试配置 → 数据集)
- **random** — pick input/output length pairs (default `3K/1K`=`3072/1024`, `1K/1K`=`1024/1024`, `256/256`); add custom pairs.
- **sharegpt** — auto-downloads from ModelScope
  `gliang1001/ShareGPT_V3_unfiltered_cleaned_split` (JSON array is stream-converted to jsonl and cached under `datasets/sharegpt/`).
- **custom** — upload a jsonl file or point to a server-local jsonl path (same behaviour as ShareGPT).

### Concurrency & rate (测试配置)
- Concurrency list editable: default `1,4,8,16,32,40,64,128`.
- `--max-concurrency` = `--num-prompts` = each concurrency value.
- Request rate: `inf` (unlimited, recommended) or a finite `req/s`.

## 3. Test process (benchscope UI)
1. Start: `benchscope` → open `http://127.0.0.1:8080`.
2. Confirm top nav shows **服务** and **环境** online; the model list loads from `/v1/models`.
3. **Settings** → set Base URL / GPU / tempaltes; **测试连接** to verify.
4. vLLM page → **测试环境** panel: choose **模型** from `/v1/models` (fallback manual input when offline).
5. **测试配置**: pick dataset (random pairs / sharegpt download / custom path), concurrency list, request rate, GPU count, TPOT threshold, framework params.
6. **命令预览** to inspect the exact `vllm bench serve` command → **测试进度 → 开始测试**.
7. Watch **测试进度** (progress ring, current case @ concurrency, live log tail); **取消测试** to abort.
8. **测试结果** streams each concurrency row (bilingual table) and the six curves
   (Output 吞吐, Total 吞吐, TTFT mean, TPOT mean, TTFT P99, TPOT P99) vs concurrency.
9. For offline/demo runs without a vLLM CLI: `BENCHSCOPE_FAKE_BENCH=1 python -m benchscope`.

### Reference command shape
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

## 4. Log recording & analysis
Each run creates `logs/<MMDD-HHMMSS>/`:
- Raw bench logs: `<model>_<case>_X<gpu>.log` (per case, all concurrency appended).
- Mean summary CSV: `<model>_X<gpu>.log`, format:
  ```
  ================
  测试条件：1K1K | 输入=1024 | 输出=1024 | 部署GPU=8张
  ================
  并发数,Output Token,Peak Output Token,Total Token,TTFT,TPOT,ITL
  1,49.72,51.00,99.63,204.72,19.93,19.91
  ```
- P99 summary CSV: `<model>_X<gpu>_p99.log` (same columns, TTFT/TPOT/ITL = P99).
- `benchmark-*.xlsx` — two sheets **均值 Mean** & **P99**; columns:
  `GPU, 模型, 精度, 推理框架, 输入长度, 输出长度, 并发数, output, peakoutput, total, ttft, itl, tpot, 单用户` where `单用户 = 1000 / tpot`.
- **Metrics parsed** (mean + P99): `output`, `peakoutput` (peak output tok/s), `total`, `ttft`, `tpot`, `itl`, plus `req_per_s`; best-concurrency highlight = the row with TPOT closest to (and below) the configured threshold.
- **日志管理** page (or vLLM Logs view) lists runs; preview/download raw logs; **均值分析** / **P99 分析** tabs show tables + six curves.

## 5. Troubleshooting
- **"未找到命令执行环境：vllm"** — vLLM CLI missing; install it or fix the bench command template (full path/conda env).
- **推理服务离线** — Base URL/endpoint unreachable; use **测试连接**, check `/v1/models`.
- **数据集下载失败** — ModelScope unreachable; pre-populate `datasets/sharegpt/` or use custom dataset.
- **无模型可选** — service offline; tick **离线强制开始** and type the model explicitly.

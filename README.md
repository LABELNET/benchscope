# benchscope

**English** | [简体中文](README.zh-CN.md)

> A single-process, pip-installable web UI for benchmarking **vLLM / SGLang** and any **OpenAI-compatible** inference service.

## Introduction

benchscope is a performance-testing tool for LLM inference services. It connects to a vLLM / SGLang (or any OpenAI-compatible) API and runs throughput/latency benchmarks through a clean **admin-console style web UI**.

- **How it runs** — the bench tool (`vllm bench serve` / `sglang.bench_serving`) executes as a subprocess on the machine where benchscope is installed. The inference server only needs to expose an OpenAI-compatible API — **no server-side plugin required**.
- **Live feedback** — every concurrency result streams into the table and charts in real time.
- **Single process** — `pip install` + one command starts the web server and the built-in front end.

## Quick Start

```bash
# Install from PyPI
pip install benchscope

# Start (default http://127.0.0.1:8080, opens browser automatically)
benchscope

# Options
benchscope --port 8080 --no-browser
```

Open the page and:

1. Confirm the top nav shows **Service** (app) and **Environment** (inference) as online.
2. Go to **Settings** (top-right) and set the inference service **Base URL** (any OpenAI-compatible endpoint).
3. Open the **vLLM / SGLang** page, choose a model (from `/v1/models`), a dataset (Random / ShareGPT / Custom) and a concurrency list.
4. Use **Test Progress → Start Test**. The **Test Results** panel updates live with a bilingual table and six curves.
5. Logs are written under `logs/<MMDD-HHMMSS>/` with a `benchmark-*.xlsx` summary (mean + P99 sheets).

## Features

- **Dual framework** — vLLM (`vllm bench serve`) and SGLang (`sglang.bench_serving`).
- **Datasets**
  - `random` — multiple input/output length pairs (default `3K/1K`, `1K/1K`, `256/256`, customisable).
  - `sharegpt` — auto-downloaded from [ModelScope](https://www.modelscope.cn/datasets/gliang1001/ShareGPT_V3_unfiltered_cleaned_split).
  - `custom` — upload a jsonl file or point to a local path (same behaviour as ShareGPT).
- **Configurable benchmark** — editable concurrency list (default `1,4,8,16,32,40,64,128`), `--max-concurrency` = `--num-prompts`, `inf` request rate, framework parameter forms plus a free-form flag editor, and command preview.
- **GPU auto-detect** (`nvidia-smi`) with a manual fallback, plus an editable **TPOT threshold** used to highlight the best/nearest rows.
- **Live results** — bilingual table + six curves (Output & Total throughput, TTFT/TPOT mean & P99) against concurrency.
- **Logs** — per-run `MMDD-HHMMSS` directory with raw bench logs, mean/P99 summary CSV and `benchmark-*.xlsx` (mean + P99 sheets); preview & download in the UI.
- **Analysis** — mean / P99 blocks with output/peakoutput/total/ttft/itl/tpot curves and **best-concurrency highlight** (closest to, and below, a TPOT threshold).
- **Admin-console UI** — fixed top nav, fixed left nav (test workflow / test records), and a fixed sub-nav; the content area scrolls internally.
- **Status monitoring** — Service & Environment online/offline indicators with live updates.

## Roadmap

| Version | Status | Scope |
| --- | --- | --- |
| 1.0.0 | 🚀 Released | Text-model performance testing — dual framework, three datasets, realtime results, logs & xlsx summary, analysis, admin UI |
| 2.0 | 🔜 Planned | Multimodal model performance testing |
| 3.0 | Planned | Full-modal (audio/video/…) model performance testing |
| 4.0 | Planned | World-model performance testing |
| 5.0 | Planned | Accuracy testing on common datasets |
| 6.0 | Planned | ModelScope official-model comparison & conclusions |

## Project Structure

```
benchscope/
├── benchscope/
│   ├── cli.py            # `benchscope` command entry
│   ├── config.py         # config persistence (~/.benchscope/config.json)
│   ├── datasets.py       # ShareGPT download/convert, custom datasets
│   ├── gpu.py            # GPU auto-detect
│   ├── parser.py         # bench output parsing (mean + P99)
│   ├── summary.py        # CSV & xlsx summary generation
│   ├── benches/          # vllm/sglang command building & execution
│   └── server/           # FastAPI + WebSocket + test orchestration
├── web/                  # Vue 3 + Ant Design Vue front-end source
└── tests/                # mock OpenAI server & UI smoke tests
```

## Development

```bash
# Backend
python -m benchscope.cli --port 8080 --no-browser

# Frontend (hot-reload, proxies /api and /ws to :8080)
cd web && npm install && npm run dev    # http://127.0.0.1:5173
```

- Run the UI without a vLLM/SGLang install: `BENCHSCOPE_FAKE_BENCH=1 python -m benchscope`.
- Mock an inference service locally: `python tests/mock_openai_server.py` (port 8001), then point **Base URL** to `http://127.0.0.1:8001` in Settings.

## Open Source

- **License** — [Apache License 2.0](LICENSE)
- **Published on** — [PyPI: benchscope](https://pypi.org/project/benchscope/)
- **Source** — <https://github.com/LABELNET/benchscope>
- **Contributing** — feel free to open issues / pull requests on the source repository.

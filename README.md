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

Open the page and switch between the five-item top nav — **Dashboard / Performance / Accuracy / Sessions / Settings**:

1. **Settings** → **Inference API** section, set the **Base URL** (any OpenAI-compatible endpoint) and use **Test Connection** to confirm it pulls `/v1/models`.
2. **Performance** → click **New Task** to open the task form (select model + framework, dataset, concurrency, advanced params, command preview). After creating the task you land on the task detail page.
3. On the **task detail page** the left column shows live progress + bench terminal, the right column shows the realtime bilingual table and six curves (start/stop/retry controls in the top status bar).
4. **Dashboard** shows aggregate stats (total runs / running tasks / avg TPOT / best model) and the historical run records list (with detail panel reusing the mean/P99 analysis).
5. **Sessions** opens an SSE streaming chat with the inference service (model picker + system prompt + Markdown rendering).
6. Logs are written under `logs/<MMDD-HHMMSS>/` with a `benchmark-*.xlsx` summary (mean + P99 sheets).

> UI language (EN/中) and theme (light/dark/system) can be toggled in **Settings → General**.

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
- **Task-based Performance (v1.0.5)** — create benchmark tasks on the **Performance** page; each task runs in its own thread and is persisted under `~/.benchscope/tasks/` so refreshing the page does not lose in-flight state. The task detail page shows live progress + bench terminal (left) and the realtime bilingual table + six curves (right).
- **Dashboard (v1.0.5)** — aggregate stats cards (total runs / running tasks / avg TPOT / best model) plus the historical run-records list with an inline mean/P99 analysis panel.
- **Sessions (v1.0.5)** — SSE streaming chat against the OpenAI-compatible API; sessions are persisted under `~/.benchscope/sessions/`.
- **Accuracy (v1.0.5)** — placeholder page reserved for the v5.0 accuracy-testing release.
- **i18n & theme (v1.0.5)** — bilingual UI (English / 简体中文) and light / dark / system theme switching, both configurable in Settings.
- **Admin-console UI** — five-item fixed top nav (Dashboard / Performance / Accuracy / Sessions / Settings) plus per-page sub-navigation; content area scrolls internally. Legacy `/vllm`, `/sglang`, `/logs` routes redirect to the new pages.
- **Status monitoring** — Service & Environment online/offline indicators with live updates.

## Roadmap

| Version | Status | Scope |
| --- | --- | --- |
| 1.0.0 | 🚀 Released | Text-model performance testing — dual framework, three datasets, realtime results, logs & xlsx summary, analysis, admin UI |
| 1.0.5 | 🚀 Released | v2.0 UI overhaul: 5-column nav (Dashboard / Performance / Accuracy / Sessions / Settings), task-based Performance with persistence, Sessions SSE chat, i18n (EN/中), light/dark/system theme |
| 2.0 | 🔜 Planned | Multimodal model performance testing |
| 3.0 | Planned | Full-modal (audio/video/…) model performance testing |
| 4.0 | Planned | World-model performance testing |
| 5.0 | Planned | Accuracy testing on common datasets |
| 6.0 | Planned | ModelScope official-model comparison & conclusions |

> Full version plan: [ROADMAP.md](ROADMAP.md) · Product spec: [PROJECTS-README.md](PROJECTS-README.md)

## Project Structure

```
benchscope/
├── benchscope/
│   ├── cli.py            # `benchscope` command entry
│   ├── config.py         # config persistence (~/.benchscope/config.json)
│   ├── task_manager.py   # task-based performance runner + persistence
│   ├── session_manager.py # chat sessions store + SSE streaming
│   ├── datasets.py       # ShareGPT download/convert, custom datasets
│   ├── gpu.py            # GPU auto-detect
│   ├── parser.py         # bench output parsing (mean + P99)
│   ├── summary.py        # CSV & xlsx summary generation
│   ├── benches/          # vllm/sglang command building & execution
│   └── server/           # FastAPI + WebSocket + test orchestration
│       ├── api_config.py     # config / models / GPU / status API
│       ├── api_test.py       # legacy single-test start/stop API
│       ├── api_tasks.py      # task CRUD + start/stop/preview
│       ├── api_sessions.py   # session CRUD + SSE chat
│       ├── api_dashboard.py  # dashboard stats (total runs / avg TPOT / best model)
│       ├── api_logs.py       # run-records & dataset management API
│       ├── test_manager.py   # legacy single-test manager (used by api_test)
│       └── ws.py             # WebSocket broadcast hub
├── web/                  # Vue 3 + Ant Design Vue front-end source
│   └── src/views/        # DashboardView / PerformanceView / TaskDetailView /
│                          CreateTaskView / AccuracyView / SessionsView / SettingsView
└── tests/                # mock OpenAI server & UI smoke tests
```

## Development

```bash
# Backend
python -m benchscope.cli --port 8080 --no-browser

# Frontend (hot-reload, proxies /api and /ws to :8080)
cd web && npm install && npm run dev    # http://127.0.0.1:5173
```

- **One-command full env** — `./scripts/dev.sh` starts mock OpenAI (8001) + FAKE-bench backend (8080) + frontend (5173) at once; `stop`/`status` subcommands manage them. Logs under `logs/dev/`.
- **No real vLLM/SGLang environment?** Use the bundled mock env — `./mocks/run_mock.sh` starts a mock OpenAI-compatible inference service plus a FAKE-bench backend (no GPU / real CLI needed). See [`mocks/README.md`](mocks/README.md) for mocking vLLM / SGLang bench output and SSE streaming chat.

- Run the UI without a vLLM/SGLang install: `BENCHSCOPE_FAKE_BENCH=1 python -m benchscope`.
- Mock an inference service locally: `python tests/mock_openai_server.py` (port 8001), then point **Base URL** to `http://127.0.0.1:8001` in Settings.

## Open Source

- **License** — [Apache License 2.0](LICENSE)
- **Published on** — [PyPI: benchscope](https://pypi.org/project/benchscope/)
- **Source** — <https://github.com/LABELNET/benchscope>
- **Contributing** — feel free to open issues / pull requests on the source repository.

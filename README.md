# benchscope

**English** | [简体中文](README.zh-CN.md)

> A single-process, pip-installable web UI for benchmarking **vLLM / SGLang** and any **OpenAI-compatible** inference service.

## Quick Start

```bash
pip install benchscope
benchscope                      # http://127.0.0.1:8080, opens browser automatically
benchscope --port 8080 --no-browser
```

1. **Settings → Inference API** — set the **Base URL** (any OpenAI-compatible endpoint) and run **Test Connection**.
2. **Performance → New Task** — pick model + framework, dataset, concurrency (or thresholds), params, and preview the command; you land on the task detail page.
3. **Task detail** — live progress + bench terminal on the left; realtime table and six curves on the right.

> UI language (EN/中) and theme (light/dark/system) are toggled in **Settings → General**.

## Features

**Benchmarking**
- Dual framework — vLLM (`vllm bench serve`) and SGLang (`sglang.bench_serving`); works with any OpenAI-compatible API, no server-side plugin.
- Datasets — `random` (multiple input/output length pairs), `sharegpt` (auto-download from ModelScope), `custom` (jsonl upload or local path).
- Configurable — editable concurrency list, `inf` request rate, framework param forms + free-form flags, command preview.
- Two execution modes — **concurrency** (multi-level load test) and **threshold** (TPOT / output-throughput threshold probing).

**Realtime Results**
- Realtime table grouped by case, sorted by requests within each group, with unique **Best / BestPerf** threshold highlighting (per-group, 0-threshold = ignored).
- Six curves — Output / Total throughput, TTFT / TPOT mean & P99.
- Local threshold trial: tune TPOT (default 100) / Output (default 0) and re-highlight instantly without touching the task.
- Successful rate shown as an integer percentage.

**Analysis, Logs & Export**
- Mean / P99 analysis panels with best-concurrency highlighting.
- Per-run `logs/<MMDD-HHMMSS>/` directory plus `benchmark-*.xlsx` summary (mean + P99 sheets, single-user `1000/tpot`).
- One-click **Excel export** of the realtime table (written into the task record cache).

**Tasks & Status**
- Task-based execution — each task runs in its own thread, persisted under `~/.benchscope/tasks/` (survives page refresh).
- Service / environment online-offline status monitoring.

**UI & UX**
- Admin-console UI — five-item top nav (Dashboard / Performance / Accuracy / Sessions / Settings).
- Dashboard — aggregate stats (total runs / running tasks / avg TPOT / best model) + run-records list.
- Sessions — SSE streaming chat, persisted under `~/.benchscope/sessions/`.
- i18n (English / 简体中文) and light / dark / system theme.

## Project Structure

```
benchscope/
├── benchscope/       # Python backend — CLI, task runner, bench orchestration, FastAPI + WebSocket
│   └── server/       #   api_config / api_tasks / api_sessions / api_dashboard / api_logs / ws
├── web/              # Vue 3 + Ant Design Vue front-end
├── mocks/            # mock inference service & FAKE bench outputs
└── tests/            # mock OpenAI server & UI smoke tests
```

## Development

- **Development mode (FAKE, no real inference needed)** — `./scripts/dev.sh` starts mock OpenAI (:8001) + FAKE-bench backend (:8080) + Vite frontend (:5173) at once; or `BENCHSCOPE_FAKE_BENCH=1 python -m benchscope.cli`.
- **Validation mode (real inference)** — start the backend **without** `BENCHSCOPE_FAKE_BENCH` (e.g. `--port 8081`), point Base URL to a real service (e.g. vLLM at :8000); used for concurrency / threshold regression validation.
- **Frontend hot-reload** — `cd web && npm install && npm run dev` (http://127.0.0.1:5173, proxies `/api` and `/ws` to :8080).

## Open Source

- **License** — [Apache License 2.0](LICENSE) · **PyPI** — [benchscope](https://pypi.org/project/benchscope/) · **Source** — <https://github.com/LABELNET/benchscope>

Version plan & iteration history: [VERSION_README.md](VERSION_README.md) · Product spec: [PROJECTS-README.md](PROJECTS-README.md)

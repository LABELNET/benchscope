# benchscope

**English** | [简体中文](README.zh-CN.md)

> A visualization testing platform for LLM model **performance & accuracy**, supporting models deployed with vLLM / SGLang and any OpenAI-compatible inference service.

<div align="center">
  <img src="asserts/main-performance.png" width="72%" alt="benchscope main performance screenshot" />
</div>

---

## Features

- **Easy to install** — `pip install` and one command starts the whole web platform.
- **Performance testing dual mode** — Concurrency Mode (multi-level concurrency load) and Threshold Mode (auto-search the max concurrency meeting the threshold).
- **Accuracy testing dual mode** — Online / offline testing (planned, v5.0).
- **Real-time data feedback** — every concurrency result streams into tables, charts and progress in real time.
- **Visualization curves** — multi-dimensional charts for throughput / TTFT / TPOT / ITL.
- **Log cache & download** — run logs, mean/P99 summaries and Excel export with online preview & download.

## Quick Start

```bash
# Install from PyPI
pip install benchscope

# Start
benchscope

# Options
benchscope --port 8080 --no-browser
```

## Development

See [docs/Readme.md](docs/Readme.md).

## Open Source

- **License** — [Apache License 2.0](LICENSE)
- **Published on** — [PyPI: benchscope](https://pypi.org/project/benchscope/)
- **Source** — <https://github.com/LABELNET/benchscope>
- **Contributing** — Feel free to open issues / pull requests on the source repository.

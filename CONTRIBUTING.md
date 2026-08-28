# Contributing to benchscope

Thanks for your interest in contributing! Here's how to get involved.

## Development setup

```bash
git clone https://github.com/LABELNET/benchscope.git
cd benchscope

# Backend
pip install -e .

# Frontend (optional; required before packaging to rebuild webui)
cd web && npm install && npm run dev   # http://127.0.0.1:5173
```

- Backend: `python -m benchscope.cli --port 8080 --no-browser`
- No vLLM/SGLang install for UI work: `BENCHSCOPE_FAKE_BENCH=1 python -m benchscope`
- Mock inference service: `python mocks/openai_server.py` (port 8001), then point **Base URL** to `http://127.0.0.1:8001` in Settings. (Mocks live only under `mocks/`.)

## Coding conventions

- **Backend** — Python, [FastAPI](https://fastapi.tiangolo.com/), type hints preferred; keep the public API backward compatible.
- **Frontend** — Vue 3 `<script setup>` + Ant Design Vue; reuse existing components in `web/src/components/`.
- **Commits** — write a clear, imperative commit subject; keep the change focused.
- **Formatting** — keep line endings as LF (see `.gitattributes`).

## Before submitting a PR

1. Run the full test suite — API + WebUI — with `./tests/run_tests.sh` (auto-starts the mock server and a fake-bench service with an isolated temp data dir; mocks live only under `mocks/`).
2. Make sure `python -m build` and `twine check` still pass if you touch packaging.
3. Update the docs (README / ROADMAP) if you change behavior or versions.

## Roadmap

See [docs/Roadmap.md](docs/Roadmap.md) for the version plan. Feature ideas or bug reports are welcome via [issues](https://github.com/LABELNET/benchscope/issues).

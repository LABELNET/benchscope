# Roadmap / 版本路线

benchscope 按版本迭代推进。下面标注每个版本的目标范围与状态。

| Version | Status | Scope |
| --- | --- | --- |
| **1.0.0** | 🚀 Released | Text-model performance testing — dual framework (vLLM/SGLang), three datasets (random / ShareGPT / custom), realtime results & six curves, logs & `benchmark-*.xlsx` summary (mean + P99), analysis & best-concurrency highlight, admin-console UI |
| **1.0.1 / 1.0.2 / 1.0.3** | ✅ Released | Patch releases — README (bilingual, EN default), packaging metadata, source-link updates |
| **1.0.4** | ✅ Released | Patch release — README refinements, packaging metadata updates |
| **1.0.5** | 🚀 Released | v2.0 UI overhaul: 5-column nav (Dashboard / Performance / Accuracy / Sessions / Settings), task-based Performance with multi-task persistence (`~/.benchscope/tasks/`), Sessions SSE chat (`~/.benchscope/sessions/`), Accuracy placeholder page, Settings split into General / Inference API / GPU sections, i18n (EN / 简体中文), light / dark / system theme |
| **2.0** | 🔜 Planned | Multimodal model performance testing (image / video inputs) |
| **3.0** | Planned | Full-modal model performance testing (audio / video / multi-modal) |
| **4.0** | Planned | World-model performance testing |
| **5.0** | Planned | Accuracy testing on common datasets (model quality evaluation) — the **Accuracy** page in 1.0.5 is a placeholder reserved for this release |
| **6.0** | Planned | ModelScope official-model comparison (links + analysis conclusions) |
| **7.0** | Planned | 内置GPU-适配模型下载，一键下载适配的模型，部署适配的模型 |

> **Notes**:
> - The **Accuracy** page (1.0.5) is a placeholder reserved for the **v5.0** accuracy-testing release; no functional logic is implemented yet.
> - The **Plugins** area inside Settings (1.0.5) is a placeholder reserved for a later release; no plugin manager is implemented yet.

## 发布流程 (Release checklist)

```bash
# 1. bump version in pyproject.toml, benchscope/__init__.py, web/package.json
# 2. rebuild front-end and package
cd web && npm run build
cd .. && python -m build
python -m twine check dist/*

# 3. publish (uses ~/.pypirc or TWINE_USERNAME/TWINE_PASSWORD env)
python -m twine upload dist/*
```

> The full product spec lives in [Projects.md](docs/Projects.md); this file tracks the version milestones.

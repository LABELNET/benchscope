# Roadmap / 版本路线

benchscope 按版本迭代推进。下面标注每个版本的目标范围与状态。

| Version | Status | Scope |
| --- | --- | --- |
| **1.0.0** | 🚀 Released | Text-model performance testing — dual framework (vLLM/SGLang), three datasets (random / ShareGPT / custom), realtime results & six curves, logs & `benchmark-*.xlsx` summary (mean + P99), analysis & best-concurrency highlight, admin-console UI |
| **1.0.1 / 1.0.2 / 1.0.3** | ✅ Released | Patch releases — README (bilingual, EN default), packaging metadata, source-link updates |
| **2.0** | 🔜 Planned | Multimodal model performance testing (image / video inputs) |
| **3.0** | Planned | Full-modal model performance testing (audio / video / multi-modal) |
| **4.0** | Planned | World-model performance testing |
| **5.0** | Planned | Accuracy testing on common datasets (model quality evaluation) |
| **6.0** | Planned | ModelScope official-model comparison (links + analysis conclusions) |

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

> The full product spec lives in `PROJECTS-README.md`; this file tracks the version milestones.

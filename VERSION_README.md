# VERSION_README — 版本规划与迭代记录

> benchscope 版本路线、各版本迭代记录与发布流程。整合自 `ROADMAP.md`,并持续随迭代更新。

## 版本路线（规划）

| Version | Status | Scope |
| --- | --- | --- |
| **1.0.0** | 🚀 Released | 纯文本性能测试 — 双框架（vLLM/SGLang）、三数据集（random / ShareGPT / custom）、实时结果与六条曲线、日志与 `benchmark-*.xlsx` 汇总（mean + P99）、分析与最佳并发高亮、管理台 UI |
| **1.0.1 / 1.0.2 / 1.0.3** | ✅ Released | 补丁 — README（双语，默认英文）、打包元数据、源码链接更新 |
| **1.0.4** | ✅ Released | 补丁 — README 完善、打包元数据更新 |
| **1.0.5** | 🚀 Released | v2.0 UI 大改 + 性能页双模式增强，详见下方迭代记录 |
| **2.0** | 🔜 Planned | 多模态模型性能测试（图像 / 视频输入） |
| **3.0** | Planned | 全模态模型性能测试（音频 / 视频 / 多模态） |
| **4.0** | Planned | 世界模型性能测试 |
| **5.0** | Planned | 常见数据集精度测试（Accuracy 页为 1.0.5 预留占位） |
| **6.0** | Planned | ModelScope 官方模型对比（链接 + 对比结论） |
| **7.0** | Planned | 内置 GPU 适配模型下载：一键下载 / 部署适配模型 |

> **Notes**：
> - **Accuracy 页**（1.0.5）为 v5.0 精度测试预留占位，暂无功能逻辑。
> - **Settings → Plugins**（1.0.5）为后续版本预留占位，暂无插件管理。

## 迭代记录

### v1.0.5（当前版本）

- 相关 PRD：
  - [docs/PRD_260826-1.md](docs/PRD_260826-1.md) — Performance 三行布局与表格 / 图表重构
  - [docs/PRD_260826-2.md](docs/PRD_260826-2.md) — 性能页双模式、分组高亮与 Excel 导出
- 行为文档：[docs/PERFORMANCES_260826.md](docs/PERFORMANCES_260826.md) — 性能页双模式行为说明

关键变更：

1. **v2.0 UI 大改** — 5 栏导航（Dashboard / Performance / Accuracy / Sessions / Settings）、任务化 Performance（持久化 `~/.benchscope/tasks/`）、Sessions SSE 对话（持久化 `~/.benchscope/sessions/`）、Accuracy 占位页、Settings 分区（通用 / 推理 API / GPU）、i18n（中英）+ 亮 / 暗 / 跟随系统主题。
2. **任务双模式** — `concurrency`（多档并发压测）/ `threshold`（阈值探测，`concurrency_list=[1]` 逐级增加）；阈值模式携带 `tpot_threshold_ms`、`output_throughput_threshold` 快照。
3. **创建任务三步表单** — 条件 / 参数 / 命令预览，独立创建页支持 `?mode=` 区分并发 / 阈值模式。
4. **Cases 面板（阈值模式）** — 只读展示阈值条件；按 case 独立展示请求状态（完整测试列表 / Pending），各 case 互不联动。
5. **Realtime 分组表格** — 按 case 分组、组内按并发数升序、每组独立阈值高亮；Best / BestPerf 组内唯一（取满足条件的最大并发行），两阈值全 0 不标记；本地阈值试算（TPOT 默认 100 / Output 默认 0）。
6. **Perf 面板** — 新增 Mode 行，移除 Requests 行；成功率整数展示。
7. **Excel 导出** — Realtime 表格 Download 按钮 → `POST /api/tasks/{task_id}/export` → 写入 `task.run_dir/realtime_{task_id}.xlsx`；footer 布局 Columns → Download 固定于右下角。

### v1.0.0（基线）

纯文本性能测试首个发布版：双框架、三数据集、实时结果与六条曲线、日志与 `benchmark-*.xlsx` 汇总（mean + P99 双 sheet，含单用户 `1000/tpot` 列）、均值 / P99 分析面板与最佳并发高亮、管理台风格 UI、服务 / 环境状态监控。

## 发布流程（Release checklist）

```bash
# 1. 更新版本号：pyproject.toml、benchscope/__init__.py、web/package.json
# 2. 重新构建前端并打包
cd web && npm run build
cd .. && python -m build
python -m twine check dist/*

# 3. 发布（使用 ~/.pypirc 或 TWINE_USERNAME/TWINE_PASSWORD 环境变量）
python -m twine upload dist/*
```

## 相关文档

- [ROADMAP.md](ROADMAP.md) — 版本里程碑（本文件为整合版）
- [PROJECTS-README.md](PROJECTS-README.md) — 完整产品需求与功能定义
- `docs/PRD_*.md` — 各期迭代 PRD（如 PRD_260826-1、PRD_260826-2）
- [docs/PERFORMANCES_260826.md](docs/PERFORMANCES_260826.md) — 性能页双模式行为说明

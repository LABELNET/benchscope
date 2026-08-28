# VERSION 1.0.7 — 版本修订记录

> **版本**：1.0.7  
> **状态**：开发中（In Development）  
> **发布时间**：待定  
> **文档状态**：当前开发版本——**未特别说明版本号时，项目内容所有变更均迭代在此版本**（显示 `v1.0.7-dev`），按时间顺序追加到本文档；仅当明确「迭代下一个版本」才切换  
> **目录**：页面级行为细则见 `docs/prds/`；版本路线见 `docs/Roadmap.md`

---

## 1. 版本概述

1.0.7 为 1.0.6 发布后的**迭代开发版本**，规划重点：**收口 1.0.6 遗留占位能力**（Dashboard 指标 / Datas-Evals / Datas-Analysis / Models 部署 / Plugins），并延续性能页与记录管理能力增强。规划功能见 [docs/Roadmap.md](../Roadmap.md) 1.0.7 小节，逐项落地后在此按时间顺序记录迭代明细。

## 2. 候选规划（待确认优先级）

> 基于 1.0.6 发布后现状梳理（占位页 / 待实现逻辑），按优先级候选，**最终范围与顺序由用户确认后写入下方迭代记录**。

| # | 规划项 | 现状 | 规划要点 |
| --- | --- | --- | --- |
| A | **Dashboard 指标补全** | Overview 六宫格 `Max Perf Records (RUN ID)` / `Max Acc Records (RUN ID)` 显示 `—`（逻辑待实现） | 接入实际最优记录（如 Output 吞吐最高）RUN ID 与跳转 Datas 详情 |
| B | **Datas/Analysis 记录对比分析页落地** | `DatasAnalysisView` 为占位页 | 独立对比页：多选 perf 记录 → 逐指标（mean/median/p99）对比表 + 对比图 |
| C | **Datas/Evals 精度记录页落地** | Evals 为占位（误差情况，v5.0 详情） | 精度记录列表 + 详情骨架（为 v5.0 精度测试铺路） |
| D | **Settings → Models 部署能力** | 部署按钮待实现（7.0 规划） | 内置模型一键下载到 `models_dir` + 下载进度（7.0 前置） |
| E | **Settings → Plugins 插件机制** | 仅占位 | 插件管理（列表 / 启用 / 禁用 / 上传） |
| F | **任务管理与导出增强** | 任务列表无搜索/筛选 | 任务搜索筛选、报告导出（HTML / PDF） |

## 3. 迭代记录（按时间顺序）

### 迭代 1（2026-08-28 17:38:03）：版本初始化（1.0.7 开发启动）

**功能概述**：
- 新建 `docs/versions/VERSION_1_0_7.md`（版本概述 + 候选规划 + TODO 清单框架）
- 版本号 `1.0.6` → `1.0.7.dev0`（`benchscope/__init__.py` `__version__` / `pyproject.toml` / `web/package.json` 同步），TopBar 动态显示 `v1.0.7-dev`
- `docs/Roadmap.md`：1.0.6 标记已发布（2026-08-28）+ 新增 1.0.7 小节
- `docs/Readme.md`：版本表新增 1.0.7 行，迭代规则当前版本改为 v1.0.7
- 开发环境：`./scripts/dev.sh start`（:8080 后端+前端，:8001 mock OpenAI）

**TODO 状态**：
- [x] 工程 — 1.0.7 版本初始化（版本文档 + 版本号 + Roadmap + Readme + 开发模式启动）

## 4. TODO 清单

- [x] **版本初始化**：VERSION_1_0_7.md + 版本号 `1.0.7.dev0` + Roadmap/Readme 同步 + 开发模式启动（2026-08-28 完成）

---

## 5. 相关文档

- 版本路线：[docs/Roadmap.md](../Roadmap.md)
- 上一版本：[VERSION_1_0_6.md](./VERSION_1_0_6.md)
- 页面行为文档：`docs/prds/`（Performance / Performance-Create / Dashboard / Datas / Accuracy / Sessions / Settings / TopBar）

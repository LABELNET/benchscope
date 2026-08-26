# VERSION 1.0.6 — 版本修订记录

> **版本**：1.0.6  
> **状态**：开发中（In Development）  
> **发布时间**：待定  
> **文档状态**：当前开发版本——**后续开发内容均迭代在此版本**，按时间顺序追加到本文档  
> **目录**：页面级行为细则见 `docs/prds/`；版本路线见 `docs/Roadmap.md`

---

## 1. 版本概述

1.0.6 为 1.0.5 发布后的**迭代开发版本**，规划重点：新增 **Datas 主导航**（性能/精度记录管理 + 详情页重规划 + 记录对比分析）、**内置数据集模块**、**缓存路径扩充**（模型/数据目录统一到 `.benchscope`）。规划功能见 [docs/Roadmap.md](../Roadmap.md) 1.0.6 小节，逐项落地后在此按时间顺序记录迭代明细。

## 2. 迭代记录（按时间顺序）

### 迭代 1（2026-08-27）：配置基础 + 内置数据集 + Datas 主导航

**功能概述**：
- **缓存路径扩充**：新增 `models_dir` 配置（默认 `~/.benchscope/models`，模型下载缓存目录），Settings → General → Cache Paths 面板新增「模型目录」行（修改即保存）
- **内置数据集模块**（Settings → Datasets 面板）：
  - 定义文件 `benchscope/configs/datasets.yaml`（id / name / description / url / download 命令 / source）
  - 后端 `benchscope/builtin_datasets.py`：读取定义、下载（modelscope 或 url 源）、缓存到 `data_dir/datasets/{id}/`
  - API：`GET /api/config/datasets`（列表 + 缓存状态）、`POST /api/config/datasets/download`（按 id 下载）
  - 前端面板：数据集卡片（名称/描述/访问链接/下载命令可复制 + 下载按钮 + 已缓存/未缓存状态）
  - 依赖：新增 `pyyaml>=6.0`
- **Datas 主导航**（Sessions 之后）：
  - `DatasView.vue`：Perfs / Evals 双 Tab
  - **Perfs**：分页记录表（10 条/页）+ **最佳测试记录**高亮（全量 rows 中 tpot_mean 最小，金色 Best 标记 + 行背景）+ **性能数据详情抽屉**（重规划：Output / TTFT / TPOT / ITL 的 mean / median / p99 三元组）+ **记录对比分析**（多选记录，逐指标对比 mean）
  - **Evals**：占位（误差情况，v5.0）

**实现策略**：数据集下载复用 `benchscope/datasets.py` 的 modelscope 下载能力；modelscope 源文件选择按大小降序（排除 `dataset_infos.json` 等元数据）；Datas 详情数据源为 `GET /api/logs/runs/{id}`（`run.rows`，含 mean/median/p99 全套指标）。

**TODO 状态**：
- [x] 设置/数据集 — 内置数据集模块（datasets.yaml + 下载缓存 + 面板）
- [x] 设置/通用/缓存路径 — 增加模型路径（models_dir，默认 ~/.benchscope/models）
- [x] 主导航 — 新增 Datas 主导航（Sessions 之后）
- [x] 主导航/Datas — Perfs 分页记录 + 最佳测试记录 + 性能数据详情页（mean/median/p99）
- [x] 主导航/Datas — Evals 分页记录（占位，误差情况待 v5.0）
- [x] 主导航/Datas — 记录对比分析界面
- [x] 主导航/Datas 联动 Dashboard 表格：Perf/Eval Records「更多」→ 跳转 /datas（2026-08-27 完成）

## 3. TODO 清单

- [x] **设置/数据集 — 内置数据集模块**：配置文件 `configs/datasets.yaml`，可点击下载，缓存到 `~/.benchscope/datasets`（2026-08-27 完成）
- [x] **设置/通用/缓存路径**：增加模型路径（`models_dir`，默认 `~/.benchscope/models`）（2026-08-27 完成）
- [x] **主导航**：新增 **Datas** 主导航，位于 Sessions 之后（2026-08-27 完成）
- [x] **主导航/Datas — Perfs 记录**：分页记录 + 最佳测试记录 + 性能数据详情页（mean / median / p99）（2026-08-27 完成）
- [x] **主导航/Datas — Evals 记录**：分页记录占位（误差情况，v5.0 实现详情）（2026-08-27 完成）
- [x] **主导航/Datas — 记录对比分析界面**：多记录逐指标对比（2026-08-27 完成）
- [x] **主导航/Datas 联动 Dashboard 表格**：Perf/Eval Records「更多」→ 跳转 /datas（2026-08-27 完成）

---

## 4. 相关文档

- 版本路线：[docs/Roadmap.md](../Roadmap.md)
- 上一版本：[VERSION_1_0_5.md](./VERSION_1_0_5.md)
- 页面行为文档：`docs/prds/`（Performance / Performance-Create / Dashboard / Accuracy / Sessions / Settings）
- **维护约定**：`docs/versions/` 下内容更新均以**时间顺序**进行——1.0.6 的迭代内容按时间先后追加到本文档。

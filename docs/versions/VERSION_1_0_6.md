# VERSION 1.0.6 — 版本修订记录

> **版本**：1.0.6  
> **状态**：开发中（In Development）  
> **发布时间**：待定  
> **文档状态**：当前开发版本——**未特别说明版本号时，项目内容所有变更均迭代在此版本**（显示 `v1.0.6-dev`），按时间顺序追加到本文档；仅当明确「迭代下一个版本」才切换  
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

### 迭代 2（2026-08-27）：目录配置体系（9 目录）+ settings.json 持久化 + Cache Paths 面板改造

**功能概述**：
- **9 目录配置体系**：`data_dir` 根（默认 `~/.benchscope`）+ 8 个功能子目录（`perfs` / `evals` / `analysis` / `logs` / `sessions` / `models` / `datasets` / `plugins`），子目录未自定义时跟随 `data_dir`（`resolve_dir` 联动）
- **settings.json 持久化**：配置落盘 `~/.benchscope/settings.json`；旧版 `config.json` 首启兼容迁移，旧默认值 `./logs` / `./datasets` 归一化为 `~/.benchscope/logs` / `datasets`
- **目录管理 API**：`GET/POST /api/config/dirs`（9 目录的 值/默认/存在性/锁定）、`POST /api/config/restart`（可选迁移）；`data_dir` 变更记录 `state.migration_source`，迁移进度经 WebSocket `migration` 事件广播
- **任务目录分流**：`Task` 新增 `kind`（perf/evals），run_dir 按类型落 `perfs_dir` / `evals_dir`；终端输出落盘 `logs_dir/perf|eval_runID_月日时分秒.log`（`task.log_path`）；cli 运行时日志 `logs_dir/runtime_年月日.log`
- **多根扫描**：`api_logs` / `api_dashboard` 按 perfs/evals（+ 旧 logs 目录兼容）多根扫描运行记录，排除 `tasks` 状态目录
- **Settings → Cache Paths 面板改造**：9 行行内编辑（点击值 → 输入 + 保存，Enter 保存 / 失焦取消）、Missing 标签、Perf/Eval 运行中锁定（409 兜底）、Data 修改 → 确认重启 → 确认迁移 → WS 进度 Modal
- **前端 API + i18n**：`api/index.js` 新增 `getDirs` / `updateDirs` / `restartService`；zh/en 新增 15 组文案

**实现策略**：`ConfigManager` 以 `RLock` + deepcopy 默认值实现线程安全读写；目录变更 `locked` 校验（存在运行中任务返回 409）。

**TODO 状态**：
- [x] 后端 — 9 目录配置 + settings.json 持久化 + 旧版 config.json 迁移
- [x] 后端 — 目录管理 API（dirs 列表/更新/重启迁移）
- [x] 后端 — 任务/日志/仪表盘接入新目录（perfs/evals/logs 多根扫描）
- [x] 前端 — Cache Paths 面板行内编辑 + 锁定 + 重启迁移进度
- [x] 前端 — 目录 API 封装 + i18n（zh/en）
- [x] 构建前端 + 重启服务验证通过（2026-08-27）

### 迭代 3（2026-08-27）：LOGO 体系（blue_logo / black_logo）

**功能概述**：
- **LOGO 资源**：`asserts/blue_logo.png`（蓝色海豚 LOGO，网站用）与 `asserts/black_logo.png`（黑色 LOGO，README 用）
- **WebUI**：TopBar 品牌 logo、Sessions AI 头像、浏览器 favicon 统一使用 `blue_logo.png`（静态资源经 `app.py` `/blue_logo.png` 路由提供，避免被 SPA fallback 吞掉）
- **README**：中英文 README 的 LOGO 使用 `asserts/black_logo.png`

**TODO 状态**：
- [x] 前端 — TopBar / Sessions 头像 / 浏览器 favicon 统一 blue_logo
- [x] 后端 — blue_logo 静态路由（app.py）
- [x] 文档 — README 使用 black_logo

### 迭代 4（2026-08-27）：版本号 v1.0.6-dev 标识

**功能概述**：
- **版本单一来源**：`benchscope/__init__.py` `__version__`（PEP 440，开发中 `1.0.6.dev0`，正式发布改为 `1.0.6`），`pyproject.toml` 同步
- **版本显示**：主导航 TopBar 版本标签由硬编码改为动态拉取 `GET /api/version`，开发中显示 `v1.0.6-dev`，正式发布只显示 `v1.0.6`（后端 `_version_display()` 生成）
- FastAPI `version` 参数同步使用 `__version__`

**TODO 状态**：
- [x] 后端 — `__version__` 升级 1.0.6.dev0 + `/api/version` 接口
- [x] 前端 — TopBar 版本标签动态渲染 + `api.getVersion`

## 3. TODO 清单

- [x] **设置/数据集 — 内置数据集模块**：配置文件 `configs/datasets.yaml`，可点击下载，缓存到 `~/.benchscope/datasets`（2026-08-27 完成）
- [x] **设置/通用/缓存路径**：增加模型路径（`models_dir`，默认 `~/.benchscope/models`）（2026-08-27 完成）
- [x] **主导航**：新增 **Datas** 主导航，位于 Sessions 之后（2026-08-27 完成）
- [x] **主导航/Datas — Perfs 记录**：分页记录 + 最佳测试记录 + 性能数据详情页（mean / median / p99）（2026-08-27 完成）
- [x] **主导航/Datas — Evals 记录**：分页记录占位（误差情况，v5.0 实现详情）（2026-08-27 完成）
- [x] **主导航/Datas — 记录对比分析界面**：多记录逐指标对比（2026-08-27 完成）
- [x] **主导航/Datas 联动 Dashboard 表格**：Perf/Eval Records「更多」→ 跳转 /datas（2026-08-27 完成）
- [x] **设置/通用/缓存路径 — 9 目录体系**：`data_dir` + 8 子目录，行内编辑 / 锁定 / 重启迁移（2026-08-27 完成）
- [x] **配置持久化 — settings.json**：旧版 config.json 首启兼容迁移，旧默认值归一化（2026-08-27 完成）
- [x] **后端 — 目录管理 API**：`/api/config/dirs`（GET/POST）+ `/api/config/restart`（2026-08-27 完成）
- [x] **后端 — 任务/日志分流**：perfs/evals run_dir + logs_dir 终端日志 + 多根扫描（2026-08-27 完成）
- [x] **LOGO 体系**：网站 blue_logo / README black_logo 统一（2026-08-27 完成）

---

## 4. 相关文档

- 版本路线：[docs/Roadmap.md](../Roadmap.md)
- 上一版本：[VERSION_1_0_5.md](./VERSION_1_0_5.md)
- 页面行为文档：`docs/prds/`（Performance / Performance-Create / Dashboard / Accuracy / Sessions / Settings）
- **维护约定**：`docs/versions/` 下内容更新均以**时间顺序**进行——1.0.6 的迭代内容按时间先后追加到本文档。

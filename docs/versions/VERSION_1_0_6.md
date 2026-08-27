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

### 迭代 5（2026-08-27）：Settings 页面重构（布局 / Models 厂商目录 / Datasets 分类 / 双语）

**功能概述**：
- **布局**：General / Environment / Plugins 面板宽度收窄（`max-width: 720px`），`settings-content` 移除 max-width，滚动条统一在页面最右侧
- **菜单顺序**：Models 移至 Datasets 上方（General → Environment → Models → Datasets → Plugins）
- **Models 厂商目录**：新增 `benchscope/configs/models.yaml`（41 厂商，国内 18 / 国外 23，数据源自 vLLM Recipes 左侧菜单）；`GET /api/config/model-catalog`；前端左侧副侧边栏按组折叠（▸ 箭头），点击厂商右侧显示其模型列表，匹配内置 modelCatalog 的模型可点开详情抽屉
- **Datasets 分类**：`datasets.yaml` 新增 `categories`（chat / instruction / math）并给 4 个数据集标注分类；前端左侧副侧边栏分类筛选，右侧改为「每行一个数据集」行式布局
- **缓存路径双语**：`/api/config/dirs` 的 label/desc 改为 `label_zh/label_en/desc_zh/desc_en` 双语文案，前端按界面语言渲染

**实现策略**：目录类展示配置统一放 `benchscope/configs/` yaml（datasets.yaml / models.yaml），后端解析透传；前端复用 catalog-layout 组件化布局（副侧边栏 + 内容区）。

**TODO 状态**：
- [x] 后端 — models.yaml（41 厂商 2 组）+ model-catalog API
- [x] 后端 — datasets.yaml categories + dirs 双语字段
- [x] 前端 — 布局收窄 + 滚动条贴右 + 菜单顺序调整
- [x] 前端 — Models 副侧边栏（分组折叠 + 厂商模型列表）
- [x] 前端 — Datasets 副侧边栏分类 + 行式数据集
- [x] 前端 — 缓存路径双语渲染 + i18n 文案

### 迭代 6（2026-08-27）：Datas 页面重构（副导航 + Perfs 详情 5 行布局）

**功能概述**：
- **副导航 + 子路由**：`DatasView.vue` 改为白底黑字副导航（Perfs / Evals / Analysis，`fit-content` 宽、最小 320px）；新增子路由 `/datas/perfs|evals|analysis`（`/datas` 重定向 `/datas/perfs`）；Evals / Analysis 为占位空页
- **Perfs 左右分栏**：左栏固定 280px 记录面板（Run ID + 状态 tag + model + 时间，倒序，加载 spinner + 刷新）；右栏可滚动详情区，默认提示「请选择任务」
- **详情 5 行布局**：
  - 行 1 元信息卡片：Run ID + 状态 tag + model/started_at/finished_at + 右下「删除 / 备份 / 分享」——删除确认 Modal（警告删日志）→ DELETE；备份确认 → zip 下载（可重新导入，spinner）；分享确认 → html2canvas 整页渲染 PNG 下载（spinner）
  - 行 2 三等分面板：Perf（model/framework/mode/dataset/concurrency/requests/created_at）、Cases（concurrency 模式 case 组列表 / threshold 模式阈值 + case 组列表）、Logs（run_dir 复制、summary 下载、日志文件表 name/size/预览/下载）
  - 行 3 数据面板：按 case 组 Tabs（分组键 `label#g{case_id}`）；表头 4 联动按钮 默认/Mean/Median/P99（后三者复用 `MetricsTable` preset 显示 Requests/Concurrency/Output/Peak/Total + TTFT/TPOT/ITL + Status）；阈值高亮同实时数据；底部列选择
  - 行 4 分析面板：4 行 × 3 图（Throughput/TTFT/TPOT/ITL，`echarts.connect` 联动）；表头 默认/TTFT/TPOT/ITL 显隐；固定条件行（默认 + case 组开关，关闭组数据不进图，ResizeObserver 自适应）
  - 行 5：底部 60px 空白
- **后端增强（api_logs.py）**：新增 `GET /runs/{id}/backup`（run 目录 + 终端日志打包 zip）；`DELETE /runs/{id}` 增强为同步删除终端日志；`get_run` files 修复为 `[{name,size}]` dict
- **前端依赖**：新增 `html2canvas@1.4.1`（分享截图）；i18n zh/en 新增约 35 组文案（含删除/备份/分享/数据面板/分析面板），清理旧重复 `deleteRunConfirm` 键

**实现策略**：表格列预设（默认/Mean/Median/P99）收敛进 `MetricsTable` 的 `preset` prop（watch 重置可见列），避免重复列定义；case 分组键与 PerformanceView `rowCaseKey` 一致；阈值高亮/Best/BestPerf 标注逻辑复刻 PerformanceView。

**TODO 状态**：
- [x] 前端 — Datas 副导航（Perfs/Evals/Analysis）+ 子路由 + 占位页
- [x] 前端 — Perfs 左右分栏（记录面板 + 详情区）
- [x] 前端 — 详情行 1：元信息 + 删除/备份/分享（确认 Modal + zip 下载 + html2canvas PNG）
- [x] 前端 — 详情行 2：Perf / Cases / Logs 三等分面板
- [x] 前端 — 详情行 3：case Tabs + 默认/Mean/Median/P99 预设表 + 列选择
- [x] 前端 — 详情行 4：分析面板（Throughput/TTFT/TPOT/ITL 联动图 + 条件行）
- [x] 后端 — backup 接口 + delete 清理终端日志 + get_run files 格式修复
- [x] 文档 — Datas.md 重写 + 本版本记录（2026-08-27 完成）
- [x] 验证 — 前端构建通过 + 后端接口冒烟测试（list/get/summary/preview/backup）通过
- [x] 修复 — RunChartsPanel 行隐藏/恢复时 echarts 实例随 DOM 重建（flush:'post'）+ RunDataPanel tabs 默认激活首组（2026-08-27）
- [x] 修复 — DatasPerfsView api 默认导入改为 `{ api }` 命名导入（修复 `listRuns is not a function`）+ 副导航改为与页面等宽（width:100%）（2026-08-27）
- [x] 修复 — DatasPerfsView 4 处响应 `.data` 误用（拦截器已返回数据本体）：listRuns/getRun/previewFile/backupRun（修复记录加载不出详情）（2026-08-27）

### 迭代 7（2026-08-27）：Datas/Perfs 界面优化 + 导入恢复功能

**功能概述**：
- **左栏 Records**：header 左侧标题 **Records**，右侧图标依次 **导入 / 刷新**；新增**导入面板**（右侧抽屉）——选择备份 zip 包上传（进度条）→ 后端解压并校验任务 ID 一致性 → 已存在显示「任务已存在，无需导入」/ 不存在显示「导入成功」并刷新列表，关闭图标取消导入；列表状态改为**无边框高亮文字**（done 绿/running 蓝/error 红/stopped 橙），hover 显示完整模型名，**底部预留 16px**
- **行 1 重构**：header 左侧只保留任务 ID，右侧放置**无边框**（type="text"）删除/备份/分享按钮；状态 tag 移入内容区（与 model/开始/结束同排）
- **行 2 等高**：三面板以 Perf Info 高度为准等高，超出滚动；**Cases 按行显示分组 + 请求信息**（label + g{id} + input/output + 组内并发档位右对齐）；**Logs**：Run Dir 与 summary 文件名**右对齐小字单行**，summary 下载仅保留**小图标**，日志表格**字号缩小紧凑**，操作列 Preview/Download 均用**小图标**
- **行 3 改名 Perf Datas** + **修复数据不显示**（`RunDataPanel` 未导入 `watch` 导致渲染中断）
- **行 4**：header 右侧 4 个**缩写按钮**（默认/TTFT/TPOT/ITL，去掉 Throughput）；**条件行移至内容第一行左侧**（左对齐）
- **后端新增导入接口** `POST /api/logs/runs/import`：上传 zip → 解压（zip-slip 防护，仅扁平文件名）→ 任务 ID 一致性校验（run.json run_id 优先，否则终端日志文件名提取）→ 已存在返回 `{ok:false,exists:true}`；否则写入 perfs/evals 目录，`perf_|eval_` 前缀日志归入 logs 根目录
- **前端**：新增 `importRun` API（含上传进度回调）；i18n 新增 records/import/importTip/uploadZip/importSuccess/importExists/importFailed/importZipHint/cancelImport/perfDatas 键

**验证**：`check:i18n` 通过（zh/en 键集一致）；`npm run build` 通过；后端导入冒烟测试通过（备份 zip 改新 run_id 导入成功且文件齐全、日志归 logs 根目录；重复导入返回 exists）。

**TODO 状态**：
- [x] 后端 — import 接口（解压/校验/归类）
- [x] 前端 — 左栏 Records（导入图标 + 导入抽屉 + 状态文字高亮 + 底部 16px）
- [x] 前端 — 行 1 header 布局重构
- [x] 前端 — 行 2 等高 + Cases 按行 + Logs 紧凑
- [x] 前端 — 行 3 Perf Datas 改名 + watch 修复
- [x] 前端 — 行 4 缩写按钮 + 条件行置顶
- [x] 验证 — 构建 + i18n + 后端导入冒烟测试
- [x] 文档 — Datas.md 更新 + 本版本记录（2026-08-27）

### 迭代 8（2026-08-27）：Datas/Perfs 详情优化（Cases 请求列表修复 / Logs Files 行式 / 面板 header 按钮上移）

**功能概述**：
- **行 2 — Cases 请求列表修复**：`caseGroupRows` 补算 `reqsText`（组内并发档位去重升序，如 `1 / 2 / 4`，右对齐显示）；兼容无 `cases` 元数据的历史任务——直接用 rows 生成分组（label 兜底），input/output 长度从 rows 补齐
- **行 2 — Logs Files 去表格**：日志文件列表由 `a-table` 改为**按行显示**（`log-file-item` 行式：文件名等宽 10px 小字省略号 / 大小 / Preview / Download 小图标），删除 `logColumns`
- **行 3 — Perf Datas**：默认/Mean/Median/P99 按钮上移**面板 header 右侧与标题同行**（`RunDataPanel` 的 `mode` 由内部 ref 改为 v-model prop，内部 header 移除）
- **行 4 — Statistics**：默认/TTFT/TPOT/ITL 按钮上移**面板 header 右侧与标题同行**（`RunChartsPanel` 的 `visible` 由内部 reactive 改为 v-model prop，内部 header 移除）；内容条件行标签 **Filter → Groups**（i18n `dataFilter` 键更名为 `groups`，zh `分组` / en `Groups`）
- **行 5**：底部占位高度 60px → **18px**
- **样式**：新增 `.row3-header/.row4-header`（flex space-between，`ant-card-head-title` 撑满整行）与 `.panel-head-btn`（选中态主色高亮）

**验证**：`check:i18n` 通过（zh/en 键集一致，`dataFilter`→`groups` 同步）；`npm run build` 通过。

**TODO 状态**：
- [x] 前端 — Cases 请求列表修复（reqsText + rows 兜底分组）
- [x] 前端 — Logs Files 表格改行式小字
- [x] 前端 — 行 3/行 4 header 右侧按钮（默认/Mean/Median/P99、默认/TTFT/TPOT/ITL）+ Filter→Groups
- [x] 前端 — 行 5 高度 60px→18px
- [x] 验证 — i18n + 构建
- [x] 文档 — Datas.md 更新 + 本版本记录（2026-08-27）

### 迭代 9（2026-08-27）：Datas/Perfs 详情修复（行 2 空白 / Log Files 显示 / Perf Datas 默认联动）

**功能概述**：
- **行 2 — 底部空白移除**：`.info-body` 去掉固定 `height: 252px; overflow-y: auto`，三面板高度随内容自适应（grid 自动拉伸等高），不再预留空白
- **行 2 — Log Files 完整显示**：日志文件行式列表随面板自适应完整展示，字体由 10px 减至 **9px**（文件名/大小）
- **行 3 — Perf Datas 默认联动修复**：`MetricsTable` 预设 watch 中 `if (!keys) return` 导致点击「默认」不重置列 → 改为 preset 为 default（或无匹配）时恢复**默认数据列**（`default: true` 列集：Requests/Concurrency/Output/Peak/Total + TTFT/TPOT 的 Mean/Median/P99 + Status），与实时数据一致

**验证**：`check:i18n` 通过；`npm run build` 通过；无 lint 错误。

**TODO 状态**：
- [x] 前端 — 行 2 移除固定高度、去底部空白
- [x] 前端 — Log Files 行式完整显示 + 字体 9px
- [x] 前端 — Perf Datas 默认按钮联动（恢复默认数据列）
- [x] 验证 — i18n + 构建 + lint
- [x] 文档 — Datas.md 更新 + 本版本记录（2026-08-27）

### 迭代 10（2026-08-27）：Datas/Perfs 详情优化（左栏导入提示 / Log Files 灰色面板）

**功能概述**：
- **左栏 Records — 导入提示文案**：导入按钮 tooltip 与导入抽屉标题由「导入任务 / Import Run」改为「**导入 record / Import Record**」（i18n `import` 键值更新，zh/en 同步）
- **行 2 — Log Files 灰色面板**：日志文件列表包裹为**灰色面板容器**（`#f5f5f5` 背景 + 1px 边框 + 圆角，最大高度 140px 超出滚动）；面板标题 12px→**10px**，文件名/大小 9px→**8px**，列表内 Preview/Download 图标按钮缩小（antd small 24px→**20px**，字号 10px）
- **验证**：Playwright 实测后端 `GET /api/logs/runs/{id}` 返回 files 正常、列表渲染 5 行；zh/en 两种语言下导入 tooltip 分别显示「导入 record / Import Record」；截图核验灰色面板与缩小文字/图标

**验证**：`check:i18n` 通过（zh/en 键集一致）；`npm run build` 通过；无 lint 错误；Playwright 截图核验灰色面板与 tooltip。

**TODO 状态**：
- [x] 前端 — 左栏导入提示文案（i18n `import` 键：导入 record / Import Record）
- [x] 前端 — Log Files 灰色面板 + 缩小文字（8px）与图标（20px）
- [x] 验证 — i18n + 构建 + Playwright 截图
- [x] 文档 — Datas.md 更新 + 本版本记录（2026-08-27）

### 迭代 11（2026-08-27）：Datas/Perfs 详情优化（删除确认 / 分享全页 / 各模式列集一致）

**功能概述**：
- **删除确认提示**：`deleteRunTitle/deleteRunConfirm` 文案统一为「**删除记录 / Delete Record**」语义（zh/en 同步），不再使用「任务 / run」；同时补齐 i18n 缺失的 `delete` 键（zh: 删除 / en: Delete）修复详情页删除按钮显示原始 key `delete` 的问题
- **分享 PNG 完整输出**：分享（`doShare`）渲染前临时放开右侧详情滚动容器的 `overflow:visible + flex:none + height:auto` 约束，并在 `html2canvas` 选项中显式传入 `height: scrollHeight / width: scrollWidth`；截图后 `finally` 恢复原样式。分享 PNG 现包含从任务元信息到行 4 全部统计图表（Output/Peak/Total 吞吐、TTFT/TPOT/ITL 3×3 曲线）的完整内容
- **Perf Datas 各模式列集对齐 Performance**：`MetricsTable` 的 `PRESET_KEYS.mean/median/p99` 预设统一补齐 `label`（用例/Case）、`requests`（请求/Requests）、`concurrency`（并发）、`successful`（成功）标识列，与默认预设和 Performance 实时页默认列集保持一致；切换 Default/Mean/Median/P99 不再丢失用例/请求/并发/成功列

**验证**：`check:i18n` 通过（zh/en 键集一致，新增 `delete` 键）；`npm run build` 通过；无 lint 错误；Playwright 实测删除确认 modal 标题/内容为「删除记录 / 将删除该记录及其日志数据，且不可恢复，确认删除？」；分享 PNG 1980×2994 完整呈现至图表底部；Mean/Median/P99 切换后表头均含 用例/Requests/Concurrency/Successful 列。

**TODO 状态**：
- [x] 前端 — 删除确认 prompt 改为 record 语义（deleteRunTitle/deleteRunConfirm + 新增 `delete` 键）
- [x] 前端 — 分享全页：临时放开滚动约束 + html2canvas scrollHeight/Width
- [x] 前端 — MetricsTable mean/median/p99 预设补齐 label/requests/concurrency/successful
- [x] 验证 — i18n + 构建 + Playwright（删除 modal / 分享 PNG / 列集）
- [x] 文档 — Datas.md 更新 + 本版本记录（2026-08-27）

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
- [x] **设置 — 布局重构**：窄面板 + 滚动条贴右 + 菜单顺序（2026-08-27 完成）
- [x] **设置 — Models 厂商目录**：41 厂商分组（国内/国外）副侧边栏 + 模型列表（2026-08-27 完成）
- [x] **设置 — Datasets 分类**：副侧边栏筛选 + 行式数据集（2026-08-27 完成）
- [x] **设置 — 缓存路径双语**：label/desc 中英双语文案（2026-08-27 完成）
- [x] **主导航/Datas — 副导航 + 子路由**：Perfs / Evals / Analysis 副导航，`/datas/*` 子路由 + 占位页（2026-08-27 完成）
- [x] **主导航/Datas — Perfs 左右分栏**：左栏记录面板（倒序 + 状态 tag）+ 右栏详情区（默认「请选择任务」）（2026-08-27 完成）
- [x] **主导航/Datas — 详情 5 行布局**：元信息 + 删除/备份/分享、Perf/Cases/Logs 面板、case Tabs 数据表（默认/Mean/Median/P99）、分析面板（Throughput/TTFT/TPOT/ITL 联动图 + 条件行）、底部 60px 空白（2026-08-27 完成）
- [x] **后端 — 备份/删除增强**：`/runs/{id}/backup` zip 打包 + delete 清理终端日志 + get_run files 格式修复（2026-08-27 完成）
- [x] **后端 — 导入恢复**：`POST /runs/import` 上传备份 zip 解压、任务 ID 一致性校验、已存在不重复导入（2026-08-27 完成）
- [x] **主导航/Datas — 左栏 Records**：导入/刷新图标 + 导入抽屉（进度/结果/关闭）+ 状态文字高亮 + 底部 16px（2026-08-27 完成）
- [x] **主导航/Datas — 详情界面优化**：行 1 header 无边框操作按钮、行 2 三面板等高 + Cases 按行请求信息 + Logs 紧凑、行 3 Perf Datas 修复、行 4 缩写按钮 + 条件行置顶（2026-08-27 完成）
- [x] **主导航/Datas — 详情二次优化**：Cases 请求列表修复（reqsText + rows 兜底）、Logs Files 表格改行式小字、行 3/行 4 按钮上移 header 右侧同行、Filter→Groups、行 5 高度 60px→18px（2026-08-27 完成）
- [x] **主导航/Datas — 详情三次修复**：行 2 移除固定高度去底部空白、Log Files 行式完整显示（字体 9px）、Perf Datas 默认按钮联动（恢复默认数据列）（2026-08-27 完成）
- [x] **主导航/Datas — 详情四次优化**：左栏导入提示（导入 record / Import Record）、Log Files 灰色面板 + 文字/图标缩小（8px/20px）（2026-08-27 完成）
- [x] **主导航/Datas — 详情五次优化**：删除确认 prompt 改为 record 语义（i18n `deleteRunTitle/deleteRunConfirm` + 新增 `delete` 键）、分享全页（`doShare` 临时放开滚动 + html2canvas scrollHeight/Width）、Perf Datas 各模式列集对齐 Performance（mean/median/p99 补齐 label/requests/concurrency/successful）（2026-08-27 完成）

---

## 4. 相关文档

- 版本路线：[docs/Roadmap.md](../Roadmap.md)
- 上一版本：[VERSION_1_0_5.md](./VERSION_1_0_5.md)
- 页面行为文档：`docs/prds/`（Performance / Performance-Create / Dashboard / Accuracy / Sessions / Settings）
- **维护约定**：`docs/versions/` 下内容更新均以**时间顺序**进行——1.0.6 的迭代内容按时间先后追加到本文档。

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

### 迭代 12（2026-08-27）：Statistics 图例与 Datas/Perfs UI 精修

**功能概述**：
- **Statistics 图例位于 Y 轴右侧、曲线图内竖排**（Performance 页 + Datas/Perfs 分析面板，`MetricsCharts.vue` / `RunChartsPanel.vue`）：
  - `orient: vertical` **竖排**，`left: 48, top: 12`（紧贴 Y 轴刻度右侧、曲线图内）；`type: scroll`、`align: left`
  - 颜色标记与文字缩小：`itemWidth/Height: 8`、`itemGap: 5`、`textStyle.fontSize: 9`
  - **透明度 60%**：`itemStyle.opacity: 0.6` + `textStyle.opacity: 0.6`
- **Datas/Perfs 页面 UI 精修**：
  - **Cases Info**：请求数过长时换行完整显示（`white-space: normal` + `word-break: break-all`，不再单行省略）
  - **Logs Info**：Run Dir 伪隐藏开头路径（`direction: rtl` 使省略号在左侧），最少保留末尾文件名
  - **Perf Datas 列默认**：`MetricsTable` 新增 `defaultHidden` prop，默认隐藏 **Case / Concurrency / Successful**（放入列控制可重新开启）；Case 列隐藏时 **Requests 自动固定左侧**（`visibleColumns` 无 fixed-left 列时自动固定首个可见任务列）；RunDataPanel 传 `:default-hidden="['label','concurrency','successful']"`
  - 预设（default/mean/median/p99）同样受 `defaultHidden` 过滤

**TODO 状态**：无新增待办（纯 UI 调整，已同步 prds 与 rules 文档）

### 迭代 13（2026-08-27）：Datas/Perfs 详情面板与分享优化

**补充（Performance 第一行对齐）**：Performance 页 Perf/Cases/Console 三面板——各占 1/3 固定宽度（flex `1 1 0` + min-width 0）、**最大高度 = Perf 面板高度**（JS 测量 + ResizeObserver → Cases/Console 卡片 `max-height`）、内容超出滚动（`.cases-body` / `.terminal-box` overflow-y auto）、宽度不够 `.info-value` 伪隐藏（省略号 + max-width 65%）；**Cases 内容改为分组信息/请求数两行**（`.case-head` + `.case-tags` 单独一行满宽换行，每行至少 8 个）

**功能概述**：
- **行 2 三面板**（Perf / Cases / Logs）：各占 1/3 固定宽度（grid `repeat(3, minmax(0,1fr))` + 卡片 `min-width:0`，防内容撑宽）；**高度以 Perf Info 为准**（JS 测量 Perf Info 卡片高度 → grid `gridAutoRows` 固定）；内容高度不够时**面板内部滚动**（`.ant-card-body` overflow-y auto）；行内容宽度不足时**伪隐藏**（`.info-value` 省略号 + `max-width: 65%`）
- **Log Files 高度填充**：`.log-files` 由 `max-height:140px` 改为 `flex:1; min-height:0; max-height:none`，随面板（以 Perf Info 为准）高度填充，内容超出滚动
- **行 1 Task Status**：由 `a-tag` 边框改为**高亮文字无边框**（复用 record-status + st-* 色类）
- **分享截图按当前界面状态**：截图前容器加 `sharing` 类（scoped 下 `:deep` 命中），CSS 强制 `.ant-table-body/.ant-table-content` 高度 auto + overflow visible，html2canvas 完整输出表格数据（含 Perf Datas）
- **Datas 阈值模式标记 BestPerf、不标记 Best**：`annotatedRows` 按 case 分组、组内并发升序；阈值模式用任务阈值每组唯一标记 `bestPerf`；`best` 不标记（Best 只在 Performance 界面）
- **Performance Cases 请求数多行显示**：改为**分组信息/请求数两行结构**（`.case-head` + `.case-tags` 单独一行 `width:100%` + flex-wrap），每行至少 8 个请求数（tag `min-width:26px`），一行不够自动换行多行
- **Performance Cases 滚动与字体**：Cases 面板高度不足时在 `.cases-body` 内滚动（卡片 body `overflow:hidden` + `overflow-y:auto`）；请求数字体缩小（10px、line-height 16px）
- **Performance 第一行 max-height 修复**：`ref` 在组件上需用 `$el` 取真实 DOM（此前 offsetHeight 恒为 0 导致 max-height 未生效）；ResizeObserver 观察 `$el`；Cases 面板高度不足时 Groups 列表在 `.cases-body` 内部滚动
- **Cases 阈值不参与滚动 + 高度修正**：阈值条件固定不滚动，仅分组列表 `.case-list` 独立滚动；测量改用 `scrollHeight`（自然内容高度，`offsetHeight` 在 stretch 下为拉伸高度导致超出 Perf 自然高）
- **Cases 高度直接设置 + 运行自动滚动**：Cases/Console 卡片 `height` 直接 = Perf 高度（非 max-height，无动画）；`.case-list` `scroll-behavior:auto`；任务 running 时 Groups 列表自动滚到底部（`scrollTop = scrollHeight`）

**TODO 状态**：无新增待办（已同步 prds/Datas.md）

### 迭代 14（2026-08-27）：Statistics 统计图联动开关

**功能概述**：
- **Performance Statistics + Datas/Perfs Statistics 面板 header 右侧新增「联动」开关**（默认开启）
  - 开启：鼠标光标进入任一统计图 → **同组所有统计图浮动信息（tooltip）联动显示**（`echarts.connect(GROUP)`）
  - 关闭：`echarts.disconnect(GROUP)`，不联动
- 实现：`MetricsCharts.vue`（`perf-charts` 组）/ `RunChartsPanel.vue`（`run-charts` 组）新增 `linked` prop + watch connect/disconnect；onMounted 按 `linked` 决定是否 connect（RunChartsPanel 此前设了组但从未 connect，本次补上）
- 面板：PerformanceView Statistics `#extra`、DatasPerfsView row-4 actions 各加 `a-switch`（`statLinkage` / `chartLinkage`）
- i18n：新增 `linkage` 键（联动 / Linkage）

**TODO 状态**：无新增待办
- **Performance 任务执行页底部 18px 空白**（`.row-5-spacer`，与 Datas/Perfs 行 5 一致）
- **Datas/Perfs 三处调整**：Cases Info 阈值固定 + 分组列表内部滚动（`.case-groups` flex:1 + overflow-y:auto）；Perf Datas 默认隐藏 Status 列（`defaultHidden` 含 status，右无固定列，阈值模式仅行颜色标记）；Statistics 联动开关**默认关闭**
- **Datas 行 2 高度测量修复**：`perfCardRef` 为组件 ref，需 `$el` 取真实 DOM + `scrollHeight` 取自然高度（此前 `offsetHeight` 为 undefined → `gridAutoRows` 未生效 → Cases 分组列表超出 Perf Info 高度）；`ResizeObserver` 观察 `$el` 重测
- **Datas 行 2 测量重构（可靠方案）**：行 2 每格外包普通 `div.row-2-col` 容器，测量容器 `scrollHeight`（普通 div ref 直接为 DOM，彻底摆脱组件 `$el` 不确定性）；Perf Datas 分组 Tab 过多时横向滚动（`.ant-tabs-nav-wrap` overflow-x:auto）
- **Datas 行 2 改为与 Performance 第一行同构**：flex 布局（`flex:1 1 0` + `align-items:stretch`）；测量 Perf 卡片 `$el.scrollHeight` → `sideCardStyle` 应用 Cases/Logs 卡片 `height`（不再用 grid + gridAutoRows）
- **Datas 行 2 测量防拉伸 + 灰面板**：测量前临时 `align-self:flex-start` 取 Perf 自然高度（否则被拉伸高度固化，切换任务高度不变）；`.case-groups` 改灰色面板（滚动条在面板内），`.case-req` 字体 10px；`ant-card-body` 补 `display:flex` 列（此前漏了导致滚动链断裂）

### 迭代 15（2026-08-28 00:16:53）：Dashboard 改版（Logo 放大 / Service 状态去文字 / 记录表格去删除 + 详情跳转 + footer 提示）

> **完成时间**：2026-08-28 00:16:53（commit `cd2cac3`，本轮全部改动随该提交落库）

**功能概述**：
- **主导航 TopBar**：
  - 品牌 Logo 放大：`blue_logo.png` 40×40 → **48×48**，圆角 12px
  - **Service 状态仅保留状态颜色图标，不再显示文字**：`StatusBadge` 新增 `noLabel` prop（`no-label` 用法），隐藏 `.status-label`，仅显示在线绿 / 离线红图标，hover tooltip 仍显示完整状态详情
- **Dashboard Perf Records / Eval Records 表格**：
  - **移除删除操作**（删除 popconfirm + `deleteRun` + `api.deleteRun` 调用全部删除，删除收敛到 Datas/Perfs 详情页）；操作列仅剩「详情」
  - **「详情」点击改为跳转 Datas/Perfs 并自动选中对应任务**：`router.push({path:'/datas/perfs', query:{run_id}})`；DatasPerfsView 读取 `route.query.run_id`，加载记录列表后匹配并 `selectRun` 自动选中（`onMounted` 与 `watch` 监听 query 变化）
  - **「更多」点击跳转 Datas/Perfs**：`router.push('/datas/perfs')`（原 `/datas` 重定向，改为显式子页）
  - **面板 footer**：Perf Records 与 Eval Records 表格下方新增 footer，**右侧灰色小字**显示 `*仅显示最新 8 条记录`（i18n 新增 `latest8Hint`：zh `*仅显示最新 8 条记录` / en `*Only the latest 8 records are shown`）
  - 清理：移除 DashboardView 中不再使用的 `RunDetailPanel` 导入、`detailOpen/detailRunId` 状态、详情 `<a-modal>`、`message` 导入；操作列宽 160→90

**验证**：`check:i18n` 通过（zh/en 键集一致，新增 `latest8Hint`）；`npm run build` 通过；`goRunDetail` / `.query.run_id` / `latest8Hint` 均在产物 bundle 中确认。

**TODO 状态**：
- [x] 前端 — TopBar Logo 48×48 + Service 状态无文字（StatusBadge noLabel）
- [x] 前端 — Dashboard 表格去删除、详情跳转 Datas/Perfs 自动选中、更多跳转 /datas/perfs
- [x] 前端 — Perf/Eval Records footer 右侧灰色小字（latest8Hint）
- [x] 前端 — DatasPerfsView 路由 query.run_id 自动选中任务（onMounted + watch）
- [x] 验证 — i18n + 构建 + bundle 内容确认
- [x] 文档 — Dashboard.md / Datas.md / Design.md 更新 + 本版本记录（2026-08-28 00:16:53 随 commit `cd2cac3` 落库）

### 迭代 16（2026-08-28 00:24:23）：新增主导航文档 TopBar.md（全局参数 + 精确时间变更记录）

**功能概述**：
- **新增 `docs/prds/TopBar.md`（主导航文档）**：docs/prds 此前缺少主导航（全局顶部导航栏）的页面级文档，本次补齐——
  - **全局参数**：品牌区（Logo `/blue_logo.png` 48×48 圆角 12 / 品牌名 BenchScope / 动态版本标签 `GET /api/version`）；导航菜单（6 栏 key/图标/i18n 文案/路由前缀映射表，`computed` 随 `i18nState` 响应语言切换）；右侧 Service 状态（`StatusBadge no-label` 仅图标无文字，`serviceReady` 当前占位恒 true）；`StatusBadge` 组件 prop 表（含 1.0.6 新增 `noLabel`）；`.topbar` 样式参数（56px / 白底 / 边框阴影 / 菜单样式）
  - **导航变更记录（精确到秒）**：自 v1.0.3 起共 10 条变更记录，**每条标注 commit + 精确时间（年-月-日 时:分:秒）**——`fc9fafb` 2026-08-24 11:13:52（v1.0.3 初始 3 栏导航）→ `895c905` 2026-08-24 16:19:29（v2.0 改 5 栏）→ `8f99cad` 2026-08-24 18:25:05（Logo 化）→ `c01fcaa` 2026-08-25 18:52:53（菜单 i18n 响应化）→ `890c7a2` 2026-08-26 00:54:05（右侧区精简去环境徽标）→ `00a09f8` 2026-08-26 23:56:12（v1.0.5 发布）→ `bbcf4cd` 2026-08-27 00:55:23（新增 Datas 导航 6 栏）→ `6f3a83d` 2026-08-27 13:20:02（Logo 换 blue_logo + 版本标签动态化）→ `02b2a8a` 2026-08-27 19:02:20（Datas 副导航子路由）→ `cd2cac3` 2026-08-28 00:16:53（Logo 放大 48px + Service 状态去文字）
  - **维护约定**：此后任何导航/全局参数修改必须在 TopBar.md **追加变更记录并标注精确到秒的时间**，同步 Design.md / 本版本记录
- **约定升级（重要）**：**全部迭代变更记录的时间须记录精确时间（年-月-日 时:分:秒）**——迭代标题与完成时间均标注 commit + 秒级时间，不再仅写日期（本条起执行，历史记录日期保留）

**TODO 状态**：
- [x] 文档 — 新增 docs/prds/TopBar.md（全局参数 + 变更记录精确到秒）
- [x] 文档 — VERSION_1_0_6.md 迭代 15 补精确完成时间 + 新增迭代 16 + 相关文档列表补 TopBar.md
- [x] 文档 — 维护约定升级：迭代记录时间精确到秒（年月日时分秒）

### 迭代 17（2026-08-28 11:02:26）：测试体系重构（mock 唯一归属 mocks/ + 功能测试全覆盖 + 测试约定）

**功能概述**：
- **mock 唯一归属**：删除 `tests/mock_openai_server.py`（与 `mocks/openai_server.py` 重复），mock 仿真代码只保留在 `mocks/`；同步删除旧版 `tests/ui_smoke.py`（被新测试体系取代）
- **tests 功能测试全覆盖**：
  - `tests/api/`：6 个模块覆盖全部后端 API——`test_config.py`（config/status/test-connection/datasets）、`test_dashboard.py`（stats/env）、`test_tasks.py`（preview/CRUD/start/stop/threshold/完整生命周期）、`test_logs.py`（runs/summary/backup/import/datasets）、`test_sessions.py`（CRUD + SSE 流式）、`test_test.py`（精度测试预览 + 运行）
  - `tests/webui/test_ui.py`：Playwright 页面功能测试（导航 / 各页面渲染 / Performance 模式入口 / Settings 表单 / Datas 详情跳转自动选中 / SPA 深度路由 fallback）
  - 支撑：`tests/helpers.py`（任务工具：wait_task_terminal / create_task 等）、`tests/conftest.py`（client/base_url/mock_url fixtures）
- **统一入口** `tests/run_tests.sh`：一键全量（支持 `--api-only` / `--ui-only`）；自动启动 mock(:8001，复用已运行实例) + 以「临时数据目录 + FAKE bench」启动被测服务(:18081)，退出自动清理
- **测试数据隔离**：`config.py` 新增 `BENCHSCOPE_DATA_DIR` 环境变量重定向数据根目录（默认 `~/.benchscope` → 临时目录），测试不污染真实数据
- **后端补全（暴露缺陷修复）**：`/api/test*`（精度测试 Accuracy）路由原实现未挂载（405）→ `app.py` `include_router(api_test.router)`；`state.tests`（TestManager）未接入 AppState 导致 500 → `AppState.__init__` 挂载 `TestManager`
- **约定（重要）**：**每次开发新功能必须生成并执行对应 tests**——后端 API/功能 → `tests/api/` 用例；页面/UI/交互 → `tests/webui/` 用例；提交前全量执行 `./tests/run_tests.sh`

**验证**：`./tests/run_tests.sh` 全量通过——API **45/45**、WebUI **14/14**；`pyproject.toml` 新增 `[tool.pytest.ini_options]`（testpaths/addopts）。

**TODO 状态**：
- [x] 工程 — mock 唯一归属 mocks/（删除 tests/mock_openai_server.py 与旧 ui_smoke.py）
- [x] 测试 — tests/api 全覆盖（config/dashboard/tasks/logs/sessions/test 6 模块）
- [x] 测试 — tests/webui 页面功能测试（test_ui.py）
- [x] 测试 — 统一入口 tests/run_tests.sh（mock + FAKE + 临时数据目录 + 退出清理）
- [x] 后端 — 修复 /api/test* 挂载（405）+ state.tests 接入 AppState（500）
- [x] 配置 — BENCHSCOPE_DATA_DIR 测试数据隔离
- [x] 约定 — 每次开发新功能生成并执行 tests（Development.md §3.1 测试约定）
- [x] 验证 — API 45/45 + WebUI 14/14 全量通过

### 迭代 18（2026-08-28 11:05:05）：文档约定升级（软件依赖/架构变更须同步 docs + README 以最新版为准）

**功能概述**：
- **README 以最新版为准**：`README.md` / `README.zh-CN.md` 由用户更新（herness coding 描述、`asserts/main-performance.png` 截图、Quick Start），后续文档引用与维护均以仓库内最新 README 为准
- **约定升级（重要）**：**软件依赖和架构更新均需同步更新 docs 文档**——Python 依赖（`pyproject.toml`）或前端依赖（`web/package.json`）的新增/升级/移除，必须同步 `docs/rules/Software.md`（§2 技术栈 + §3 依赖清单）与 `VERSION_x_y_z.md` 迭代记录；架构级变更同步 `Architecture.md`
- **依赖文档修正**：`Software.md` §3 依赖清单补齐 1.0.6 新增的 `pyyaml>=6.0`（内置数据集 / 厂商目录 yaml 解析）与可选依赖 `modelscope>=1.15`（数据集 modelscope 源下载）；新增 §6 维护约定

**TODO 状态**：
- [x] 约定 — 软件依赖与架构更新均需同步 docs（Development.md §4 + docs/Readme.md 维护约定）
- [x] 文档 — Software.md 依赖清单补齐 pyyaml + modelscope 可选依赖 + §6 维护约定
- [x] 文档 — README 以仓库最新版为准（不再按历史版本修改）

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
- [x] **测试体系重构**：mock 唯一归属 mocks/；tests 全覆盖（api 6 模块 + webui）；统一入口 run_tests.sh + 临时数据目录隔离；/api/test* 与 state.tests 修复；**约定：每次开发新功能生成并执行 tests**（2026-08-28 完成）
- [x] **文档约定升级**：软件依赖与架构更新均需同步 docs（rules/Software.md 依赖清单 / Architecture.md）；README 以仓库最新版为准（2026-08-28 完成）

---

## 4. 相关文档

- 版本路线：[docs/Roadmap.md](../Roadmap.md)
- 上一版本：[VERSION_1_0_5.md](./VERSION_1_0_5.md)
- 页面行为文档：`docs/prds/`（Performance / Performance-Create / Dashboard / Datas / Accuracy / Sessions / Settings / **TopBar 主导航**）
- **维护约定**：`docs/versions/` 下内容更新均以**时间顺序**进行——1.0.6 的迭代内容按时间先后追加到本文档；**所有迭代记录须标注精确时间（年-月-日 时:分:秒，含 commit）**，不再仅写日期；主导航变更另见 `docs/prds/TopBar.md` §5 变更记录。

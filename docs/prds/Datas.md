# Datas 页面 — 功能与约束说明

> **版本**：1.0.6（开发中）  
> **最后更新**：2026-08-28 15:00  
> **文档状态**：Datas（记录管理）页面的功能逻辑与约束条件说明  
> **关联文档**：[Performance.md](./Performance.md)（任务执行）· [Dashboard.md](./Dashboard.md)（记录入口联动）· [Performance-Create.md](./Performance-Create.md)（任务创建）

---

## 0. 总览

Datas 为 1.0.6 新增的主导航页（位于 Sessions 之后），采用**副导航 + 子页面**结构：

- **副导航**（白底黑字，位于主导航正下方、宽度较窄）：三个入口 **Perfs / Evals / Analysis**，当前项蓝色高亮
- **子路由**：`/datas` 默认重定向 `/datas/perfs`；`/datas/perfs|evals|analysis` 三个子页面
- **Perfs**：任务记录详情管理（记录列表 + 5 行详情布局 + 删除/备份/分享）
- **Evals / Analysis**：占位空页（提示「规划中」），v5.0 实现

---

## 1. 副导航与子页面

- 布局：白底黑字胶囊式副导航，置于主导航下方，宽度 `fit-content`（最小 320px），三项等分布局
- 路由：`DatasView.vue` 仅渲染副导航 + `<router-view>`；子页面 `DatasPerfsView.vue` / `DatasEvalsView.vue` / `DatasAnalysisView.vue`

## 2. Perfs 子页面（任务记录详情）

### 2.1 整体布局（左右分栏）

- **左栏（固定 280px 记录面板 Records）**：
  - header 左侧标题 **Records**，右侧图标依次为 **导入**、**刷新**；导入图标 tooltip 文案为 **「导入 record / Import Record」**
  - 导入：点击后右侧弹出导入面板（a-drawer）——点击上传按钮选择备份导出的 zip 包 → 上传（进度条）→ 后端解压并校验任务 ID 一致性：已存在 → 显示「任务已存在，无需导入」；不存在 → 显示「导入成功」并刷新列表；点击关闭图标取消导入
  - 列表按时间**倒序**；每项显示 Run ID + **framework 高亮标记**（1.0.7：`.record-framework`，位于任务 ID 右侧，蓝色小字 `font-size:9px` + 浅蓝底，数据来自 run.json 的 `framework_name`）+ **状态高亮文字**（无边框，done 绿 / running 蓝 / error 红 / stopped 橙）+ model + 时间；hover 显示完整模型名称；列表可滚动，**底部预留 16px 空间**
  - **路由联动选中**：进入页面或 `route.query.run_id` 变化时，在记录列表中匹配对应任务并自动选中（`selectRun`）——Dashboard Perf Records 的「详情」即通过 `?run_id=` 跳转至此
- **右栏（可滚动详情区）**：未选中时显示默认提示「请选择任务」；选中后展示 5 行布局

### 2.2 详情 5 行布局（自上而下）

#### 行 1 — 元信息卡片
- **header 左侧只保留任务 ID**；**右侧操作按钮**（删除/备份/分享，`type="text"` 无边框）
  - **删除**：确认 Modal（「删除记录 / Delete Record」语义，警告「将删除该记录及其日志数据，且不可恢复，确认删除？」）→ `DELETE /api/logs/runs/{id}`（同时清理终端日志）→ 成功提示 + 刷新列表；删除按钮文案由 i18n `delete` 键提供（zh: 删除 / en: Delete）
  - **备份**：确认 → 生成 zip 包下载（生成中按钮 spinner）→ `GET /api/logs/runs/{id}/backup`（zip 含 run 目录全部文件 + 终端日志，**可重新导入恢复任务**）
  - **分享**：确认 → `html2canvas` 将**整个详情页渲染为 PNG**（生成中 spinner）→ 自动下载；渲染前临时放开详情滚动容器约束（`overflow:visible + flex:none + height:auto`）并显式传入 `scrollHeight/scrollWidth`，**完整输出到页面底部（含行 3 数据表 + 行 4 全部统计图表）**，截图后恢复原样式
- **内容区**：任务状态**高亮文字（无边框）**（done 绿 / running 蓝 / error 红 / stopped 橙）+ model / started_at / finished_at

#### 行 2 — 三等分面板（Perf / Cases / Logs），**各占 1/3 固定宽度**（**flex** `flex:1 1 0` + `min-width:0` + `align-items:stretch`，与 Performance 第一行同构），**高度 = Perf Info 自然高度**（**`sideCardStyle`**：测量 Perf 卡片 `$el` 的 `offsetHeight`，**测量前临时 `align-self:flex-start` 防拉伸**——否则首次进入多组任务时 Perf 被 Cases 撑高、测到拉伸高度并固化，切换少组任务高度不变；`ResizeObserver` 重测 → 应用为 Cases / Logs 卡片 `height`）；内容高度不够时**面板内部滚动**（`.ant-card-body` `overflow:hidden`，内部容器各自滚动）；行内容宽度不足时**伪隐藏**（`.info-value` 省略号、`max-width: 65%`）
- **Perf**：model / framework / mode / dataset / concurrency / requests / created_at
- **Cases**：**分组 + 对应请求信息按行显示**——每行：case 组（label + g{case_id} + input_len/output_len）+ 组内并发档位（`reqsText`，来自 rows 的 concurrency 去重升序，如 `1 / 2 / 4`，右对齐；**请求数过长时自动换行完整显示**，`white-space: normal` + `word-break: break-all`，不再单行省略）；**每组阈值条件并入 case 组标记右侧**（`.case-threshold`，不单独显示；按每组 case 自带阈值生成（`caseThresholdText(cg)`，跟随 Groups 不跟随主任务），标识含统计量：TTFT-Mean/Median/P99、TPOT-Mean/Median/P99、Output；宽度不够伪隐藏：ellipsis + max-width，hover 显示完整；0 值项不显示），**仅分组列表（`.case-groups`）超出 Perf Info 高度时内部滚动**（`flex:1; min-height:0; overflow-y:auto`；卡片 body `overflow:hidden`）
  - 无 `cases` 元数据的历史任务：直接用 rows 生成分组（label 兜底），input/output 长度从 rows 补齐
  - concurrency 模式：case 组列表 + 并发档位
  - threshold 模式：case 组列表（每组阈值条件并入组标记右侧，含统计量标识，如 `TTFT-Mean ≤ 50ms · TPOT-Median ≤ 100ms · Output ≤ 200 tok/s`；**旧格式任务** cases 无 per-group 阈值、全 0 时**回退任务级阈值字段**展示，如 `TPOT-Mean ≤ 80ms`）+ 并发档位
- **Logs**：run_dir 文本（**右对齐小字单行，`direction: rtl` 伪隐藏开头路径、最少保留末尾文件名**，hover 显示完整路径）+ 复制图标；summary 文件名（**右对齐小字单行**）+ **仅下载小图标**（无文字）；日志文件列表**按行显示（非表格）**，整体包裹为**灰色面板容器**（`#f5f5f5` 背景 + 1px 边框 + 圆角，最大高度 140px 超出滚动）：文件名（等宽 **8px** 小字，省略号）/ 大小（8px）/ Preview / Download **小图标**（20px），字体与图标紧凑缩小，内容随面板自适应完整显示

#### 行 3 — 数据面板 **Perf Datas**（按 case 分组 Tabs）
- **header 右侧与标题同行 4 个联动按钮**：默认 / Mean / Median / P99（`RunDataPanel` 的 `mode` 由父级 v-model 控制）
  - 默认：恢复**默认数据列**——**默认隐藏 Case / Concurrency / Successful 列**（放入列控制，可重新开启）；**Requests 列固定左侧**（Case 列隐藏时自动固定首个可见任务列）
  - Mean/Median/P99：同样默认隐藏 Case / Concurrency / Successful，显示 Output / Peak / Total + 对应的 TTFT / TPOT / ITL + Status 列（复用 `MetricsTable` 的 `preset` + `defaultHidden` 属性；点击「默认」时重置为默认列集）
- 数据按 case 组切 Tabs，每个 Tab 一组 rows（分组键 `label#g{case_id}`，case_id 优先、label 兜底，与 Performance 实时数据一致）
- **每个分组 Tab 顶部展示该组阈值条**（`.group-threshold-bar`，**仅阈值模式**）：按每组 case 生成（`groupThresholdTexts`，由 `caseGroupRows` → 分组 key → `caseThresholdText(cg)`，与 Cases Info 面板同一口径，跟随 Groups 不跟随主任务），如 `TTFT-Mean ≤ 50ms · TPOT-Median ≤ 100ms · Output ≤ 200 tok/s`；绿色虚线信息条（`#f6ffed` 底 + `#b7eb8f` 虚线边框），宽度不够伪隐藏（ellipsis + title 完整文本）；0 值项不显示
- **分组 Tab 过多时横向可滚动**（`.ant-tabs-nav-wrap` `overflow-x:auto` + `nav-list` nowrap，不换行不溢出）
- **Status 列默认隐藏**（`defaultHidden` 含 `status`，阈值/并发/mean/median/p99 均不显示 Status 列）→ **右侧无固定列**（Status 原为右固定列）；阈值模式仅保留 **BestPerf 行颜色标记**（金色行背景，Status 列内 tag 不显示）
- **阈值模式标记 BestPerf、不标记 Best**：`annotatedRows` 按 case 分组、组内并发升序；阈值模式**按每组 case 自己的阈值全条件判断**（TTFT/TPOT 的 statistic + Output，跟随 Groups 数据不跟随主任务）每组唯一标记 `bestPerf`（满足所有配置阈值的最大并发行）；**case 阈值非有效正值（`0`/未配置）时旧格式任务回退任务级阈值字段**（含对应 statistic，与 Cases Info `caseThresholdText` 口径一致，旧格式任务同样恢复 BestPerf 金色高亮行）；`best` 不标记（Best 只在 Performance 界面）
- 底部「列选择」按钮（自定义显示列）

#### 行 4 — 分析面板（统计图）
- **header 右侧与标题同行 4 个缩写按钮**：默认 / TTFT / TPOT / ITL（TTFT/TPOT/ITL 为缩写，切换对应统计图行显隐；「默认」重新显示全部；`RunChartsPanel` 的 `visible` 由父级 v-model 控制）
- **header 右侧联动开关**（**默认关闭**）：开启时鼠标进入任一统计图，同组所有统计图浮动信息（tooltip）联动显示（`echarts.connect('run-charts')`）；关闭时 `echarts.disconnect` 不联动
- **内容第一行左侧为条件行**：**Groups** + 默认按钮 + 各 case 组按钮；组按钮可单独开关，关闭的组数据**不进入图表**（`filteredRows`）
- 每行 3 张图（ECharts），共 4 行：Throughput / TTFT / TPOT / ITL；同一指标 3 图 `echarts.connect` 联动 tooltip
- **图例（位于 Y 轴右侧、曲线图内，竖排对齐）**：`orient: vertical` 竖排、`left: 48, top: 12`（紧贴 Y 轴刻度右侧、图内）、颜色标记与文字缩小（`itemWidth/Height: 8`、`fontSize: 9`）、**透明度 60%**（`itemStyle/textStyle.opacity: 0.6`）
- 每张图独立 `ResizeObserver` 自适应宽度
- **分享截图**：**按当前界面状态生成图片**（不改动数据模式/图表显隐）；截图前加 `sharing` 类（scoped 下 `:deep` 命中）强制 `.ant-table-body/.ant-table-content` 高度 auto + overflow visible，保证 Perf Datas 表格数据完整进入 PNG

#### 行 5 — 底部 18px 空白占位

---

## 3. 后端接口（api_logs.py）

| 接口 | 说明 |
| --- | --- |
| `GET /api/logs/runs` | 记录列表（含 files 为 `[{name,size}]`） |
| `GET /api/logs/runs/{id}` | 详情：`{run, files}`（files 为 `[{name,size}]` dict，修复旧 tuple 格式） |
| `GET /api/logs/runs/{id}/summary` | 指标汇总（records / records_mean / best_* / threshold） |
| `GET /api/logs/runs/{id}/preview?name=` | 日志/文件尾部预览（文本） |
| `GET /api/logs/runs/{id}/download?name=` | 文件下载 |
| `GET /api/logs/runs/{id}/backup` | **新增**：run 目录全部文件 + 终端日志打包 zip（可重新导入） |
| `POST /api/logs/runs/import` | **新增**：上传备份 zip → 解压（zip-slip 防护，仅接受扁平文件名）→ 校验任务 ID（run.json 的 run_id 优先，否则从终端日志文件名提取）→ 已存在返回 `{ok:false, exists:true}`，否则写入 perfs/evals 目录（`perf_|eval_` 前缀日志归入 logs 根目录） |
| `DELETE /api/logs/runs/{id}` | 删除 run 目录 **+ 终端日志**（`logs_dir/perf|eval_{id}_*.log`，增强） |

---

## 4. 约束与边界

| 项 | 约束 |
| --- | --- |
| 分组键 | `label#g{case_id}`（case_id 优先，label 兜底），支持同条件重复组 |
| 分组阈值条 | 阈值模式 Perf Datas 每个分组 Tab 顶部展示该组阈值（`.group-threshold-bar`，跟随 Groups；0 值项不显示；宽度不够省略 + title） |
| 表格预设 | 默认隐藏 Case/Concurrency/Successful（列控制可开启）；Requests 固定左；Mean/Median/P99 仅切换列显示，不改数据；**阈值模式按每组 case 阈值全条件标记 BestPerf，不标记 Best（Best 只在 Performance 界面）** |
| 分享截图 | 依赖 `html2canvas@1.4.1`；**按当前界面状态生成**；`sharing` 类（`:deep`）展开表格滚动区，完整输出（含 Perf Datas 数据 + 行 4 图表） |
| 备份压缩包 | 含 run.json / 数据文件 / 终端日志，重名文件去重（保留 run 目录文件优先） |
| 导入压缩包 | 校验任务 ID 一致性：已存在不重复导入；`perf_|eval_` 前缀日志归入 logs 根目录；zip-slip 防护（仅扁平文件名） |
| 删除 | 不可恢复，前端二次确认；run 目录 + 终端日志一并清理 |
| 分析图表 | 关闭的 case 组数据不进入图表；「默认」重置全部显示；图例 Y 轴右侧图内竖排 + 60% 透明度 |
| Cases 请求信息 | 组内并发档位去重升序显示；无 cases 元数据时用 rows 兜底生成分组 |
| 行 2 等高 | 各占 1/3 固定宽度（minmax(0,1fr)）；高度以 Perf Info 为准（JS 测量 gridAutoRows），内容超出面板内部滚动；行内容宽度不足伪隐藏 |
| Log Files 面板 | 灰色面板容器（#f5f5f5 + 圆角边框），文件名/大小 8px，图标按钮 20px；**高度随面板填充（flex:1），内容超出滚动**（不再限 140px） |
| 导入提示 | 左栏导入图标 tooltip 与导入抽屉标题统一「导入 record / Import Record」（i18n `import` 键） |
| 副导航 | Evals / Analysis 为占位空页，路由已注册 |
| Dashboard 联动 | Perf/Eval Records「更多」→ 跳转 `/datas/perfs`；「详情」→ 跳转 `/datas/perfs?run_id={id}`，Perfs 页加载后按 query 自动选中对应任务 |

## 5. 相关文档约定

> **约定**：后续对 Datas 页面的设计/界面修改、逻辑与策略调整、UI 调整，均需同步更新本文档。

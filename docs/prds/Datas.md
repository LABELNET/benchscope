# Datas 页面 — 功能与约束说明

> **版本**：1.0.6（开发中）  
> **最后更新**：2026-08-27  
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
  - 列表按时间**倒序**；每项显示 Run ID + **状态高亮文字**（无边框，done 绿 / running 蓝 / error 红 / stopped 橙）+ model + 时间；hover 显示完整模型名称；列表可滚动，**底部预留 16px 空间**
- **右栏（可滚动详情区）**：未选中时显示默认提示「请选择任务」；选中后展示 5 行布局

### 2.2 详情 5 行布局（自上而下）

#### 行 1 — 元信息卡片
- **header 左侧只保留任务 ID**；**右侧操作按钮**（删除/备份/分享，`type="text"` 无边框）
  - **删除**：确认 Modal（「删除记录 / Delete Record」语义，警告「将删除该记录及其日志数据，且不可恢复，确认删除？」）→ `DELETE /api/logs/runs/{id}`（同时清理终端日志）→ 成功提示 + 刷新列表；删除按钮文案由 i18n `delete` 键提供（zh: 删除 / en: Delete）
  - **备份**：确认 → 生成 zip 包下载（生成中按钮 spinner）→ `GET /api/logs/runs/{id}/backup`（zip 含 run 目录全部文件 + 终端日志，**可重新导入恢复任务**）
  - **分享**：确认 → `html2canvas` 将**整个详情页渲染为 PNG**（生成中 spinner）→ 自动下载；渲染前临时放开详情滚动容器约束（`overflow:visible + flex:none + height:auto`）并显式传入 `scrollHeight/scrollWidth`，**完整输出到页面底部（含行 3 数据表 + 行 4 全部统计图表）**，截图后恢复原样式
- **内容区**：任务状态 tag（success/processing/error/warning）+ model / started_at / finished_at

#### 行 2 — 三等分面板（Perf / Cases / Logs），**等高（grid 自动拉伸；高度随内容自适应，不预留固定高度、无底部空白）**
- **Perf**：model / framework / mode / dataset / concurrency / requests / created_at
- **Cases**：**分组 + 对应请求信息按行显示**——每行：case 组（label + g{case_id} + input_len/output_len）+ 组内并发档位（`reqsText`，来自 rows 的 concurrency 去重升序，如 `1 / 2 / 4`，右对齐）
  - 无 `cases` 元数据的历史任务：直接用 rows 生成分组（label 兜底），input/output 长度从 rows 补齐
  - concurrency 模式：case 组列表 + 并发档位
  - threshold 模式：阈值信息（tpot_threshold_ms）+ case 组列表 + 并发档位
- **Logs**：run_dir 文本（**右对齐小字单行**）+ 复制图标；summary 文件名（**右对齐小字单行**）+ **仅下载小图标**（无文字）；日志文件列表**按行显示（非表格）**，整体包裹为**灰色面板容器**（`#f5f5f5` 背景 + 1px 边框 + 圆角，最大高度 140px 超出滚动）：文件名（等宽 **8px** 小字，省略号）/ 大小（8px）/ Preview / Download **小图标**（20px），字体与图标紧凑缩小，内容随面板自适应完整显示

#### 行 3 — 数据面板 **Perf Datas**（按 case 分组 Tabs）
- **header 右侧与标题同行 4 个联动按钮**：默认 / Mean / Median / P99（`RunDataPanel` 的 `mode` 由父级 v-model 控制）
  - 默认：恢复**默认数据列**（与实时数据一致的默认列集：Case / Requests / Concurrency / Successful / Output / Peak / Total + TTFT/TPOT 的 Mean/Median/P99 + Status）
  - Mean/Median/P99：显示 **Case / Requests / Concurrency / Successful** / Output / Peak / Total + 对应的 TTFT / TPOT / ITL + Status 列（复用 `MetricsTable` 的 `preset` 属性切换可见列；点击「默认」时重置为默认列集）。**各统计口径预设统一保留 用例/请求/并发/成功 标识列**，与 Performance 实时页默认列集一致，切换模式不丢失
- 数据按 case 组切 Tabs，每个 Tab 一组 rows（分组键 `label#g{case_id}`，case_id 优先、label 兜底，与 Performance 实时数据一致）
- 表格阈值高亮逻辑与实时数据一致（Best/BestPerf 标注）
- 底部「列选择」按钮（自定义显示列）

#### 行 4 — 分析面板（统计图）
- **header 右侧与标题同行 4 个缩写按钮**：默认 / TTFT / TPOT / ITL（TTFT/TPOT/ITL 为缩写，切换对应统计图行显隐；「默认」重新显示全部；`RunChartsPanel` 的 `visible` 由父级 v-model 控制）
- **内容第一行左侧为条件行**：**Groups** + 默认按钮 + 各 case 组按钮；组按钮可单独开关，关闭的组数据**不进入图表**（`filteredRows`）
- 每行 3 张图（ECharts），共 4 行：Throughput / TTFT / TPOT / ITL；同一指标 3 图 `echarts.connect` 联动 tooltip
- 每张图独立 `ResizeObserver` 自适应宽度

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
| 表格预设 | Mean/Median/P99 仅切换列显示，不改数据；各模式均保留 用例/请求/并发/成功 列 |
| 分享截图 | 依赖 `html2canvas@1.4.1`，临时放开滚动约束完整输出至底部（含行 4 图表） |
| 备份压缩包 | 含 run.json / 数据文件 / 终端日志，重名文件去重（保留 run 目录文件优先） |
| 导入压缩包 | 校验任务 ID 一致性：已存在不重复导入；`perf_|eval_` 前缀日志归入 logs 根目录；zip-slip 防护（仅扁平文件名） |
| 删除 | 不可恢复，前端二次确认；run 目录 + 终端日志一并清理 |
| 分析图表 | 关闭的 case 组数据不进入图表；「默认」重置全部显示；条件行标签 Groups |
| Cases 请求信息 | 组内并发档位去重升序显示；无 cases 元数据时用 rows 兜底生成分组 |
| 行 2 等高 | 三面板以 Perf Info 高度为准，超出滚动 |
| Log Files 面板 | 灰色面板容器（#f5f5f5 + 圆角边框），文件名/大小 8px，图标按钮 20px，最大高度 140px 超出滚动 |
| 导入提示 | 左栏导入图标 tooltip 与导入抽屉标题统一「导入 record / Import Record」（i18n `import` 键） |
| 副导航 | Evals / Analysis 为占位空页，路由已注册 |
| Dashboard 联动 | Perf/Eval Records「更多」→ 跳转 `/datas`（默认落到 Perfs） |

## 5. 相关文档约定

> **约定**：后续对 Datas 页面的设计/界面修改、逻辑与策略调整、UI 调整，均需同步更新本文档。

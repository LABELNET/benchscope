# benchscope Performance 任务执行页 — 双模式核心逻辑与联动说明

> **版本**：v1.0.6  
> **最后更新**：2026-08-28 15:00  
> **文档状态**：Performance 任务执行页双模式（并发 / 阈值）核心逻辑策略与联动关系说明  
> **前置文档**：[VERSION_1_0_5.md](../versions/VERSION_1_0_5.md)

---

## 0. 总览

Performance 任务执行页存在两种执行模式，由任务创建时的 `mode` 决定，并随任务快照下发到前端：

| 模式 | 判定字段 | Cases 阈值条件 | Realtime 任务级标记 | Realtime 本地标记 |
| --- | --- | --- | --- | --- |
| 并发模式 `concurrency` | `mode = concurrency` | 不显示 | 不处理 BestPerf | 处理 Best |
| 阈值模式 `threshold` | `mode = threshold` | 并入分组标记右侧（只读） | 处理 BestPerf | 处理 Best |

两种模式下，**表格排序、本地 Best 标记逻辑完全一致**；差异仅在于：阈值模式额外显示任务阈值条件，并基于任务阈值标记 BestPerf。

---

## 1. 模式定义与判定

- 模式字段 `mode` 来自任务快照（`task.payload.mode`，默认 `concurrency`），创建任务时写入。
- 阈值模式：阈值信息**跟随 Groups 数据（每组独立配置），不跟随主任务**——每组（case）自带：
  - `ttft_threshold_ms` + `ttft_statistic`（TTFT 阈值 ms + 统计量 mean|median|p99，默认 mean/0）
  - `tpot_threshold_ms` + `tpot_statistic`（TPOT 阈值 ms + 统计量 mean|median|p99，默认 mean/100）
  - `output_throughput_threshold`（Output token throughput 阈值，tok/s，可为 0 表示未配置）
- 数据链路：创建页 `length_pairs` 每项第 5 元素为该组阈值 dict → 后端 `build_cases` 解析写入每个 case（`ttft_threshold_ms/ttft_statistic/tpot_threshold_ms/tpot_statistic/output_throughput_threshold`）→ 任务快照 `cases` 透传（前端 `theTask.cases` / `run.cases` 读取，标识含统计量：TTFT-Mean/Median/P99、TPOT-Mean/Median/P99）；任务级同名字段保留（取第一组，兼容旧数据回退）。
- 后端阈值执行判定（`task_manager._execute_case_threshold`）：**按每组 case 的阈值与统计量**取值（`ttft_{stat}` / `tpot_{stat}` / `output_mean`，Output 兼容旧数据键 `output`）与阈值比较，任一非 0 阈值超标即违规。

---

## 1.5 第一行三面板布局（Perf / Cases / Console）

- **各占 1/3 固定宽度**（flex `1 1 0` + `min-width: 0`，宽度保持一致；宽度不够时行内容**伪隐藏**——`.info-value` 省略号 + `max-width: 65%`）
- **高度直接 = Perf 面板高度（无动画）**：JS 测量 Perf 卡片高度（`ref` 用 `$el` 取真实 DOM；用 **`scrollHeight`** 取自然内容高度——`offsetHeight` 在 `align-items:stretch` 下是拉伸后高度；`ResizeObserver` 观察 `$el` + 任务/状态/行数变化时重测）→ 直接应用为 **Cases / Console 卡片的 `height`**（`sideCardStyle`，非 max-height）；`align-items: stretch` 使三面板对齐；`.case-list` `scroll-behavior: auto` 无平滑动画
- **内容超出滚动**：Cases 面板（`.cases-body`）与 Console 终端（`.terminal-box`）均 `flex:1; min-height:0; overflow-y:auto`，超出部分滚动条

---

## 2. Cases 面板策略

| 项 | 规则 |
| --- | --- |
| header 右侧 mode | 纯文字绿色（`#52c41a`，12px，600），不做成 tag |
| 并发内容排列 | 按并发数量从小到大升序排列，与 Realtime Data 无关（脱钩，各自排序） |
| 阈值条件显示 | **仅阈值模式**：阈值条件文本**并入每个 case 分组标记右侧**（`.case-threshold`，紧跟在 label/g{id}/输入输出长度之后，不再单独显示区块），只读、不可编辑；**按每组 case 自己的阈值生成**（`caseThresholdText(case)`，跟随 Groups 不跟随主任务），标识含统计量（TTFT-Mean/Median/P99、TPOT-Mean/Median/P99、Output），完整显示三项非 0 阈值，如 `TTFT-Mean ≤ 50ms · TPOT-Median ≤ 100ms · Output ≤ 200 tok/s`；**旧格式任务**（cases 无 per-group 阈值、全 0）**回退任务级阈值字段**展示（任务级同名字段保留，取第一组口径，如 `TPOT-Mean ≤ 80ms`） |
| 阈值伪隐藏 | 宽度不够时**伪隐藏**（`overflow:hidden` + `text-overflow:ellipsis` + `white-space:nowrap` + `max-width` + `flex-shrink`，hover `title` 显示完整）；阈值为 0（未配置）的项不显示（TTFT 默认 0、TPOT 默认 100、Output 默认 0） |
| 分组列表滚动 | 仅**分组列表（`.case-list`）内部滚动**（`flex:1; min-height:0; overflow-y:auto`；`.cases-body` 本身不滚动） |
| 运行中自动滚动 | 任务 **running 时 Groups 列表自动向下滚动**（`caseListRef.scrollTop = scrollHeight`，随 rows/currentPos 变化触发） |
| 阈值模式请求显示 | 每个 case **独立**显示测试状态（请求数**不联动**）：已执行/执行中的 case 显示该 case 已测试过的**完整请求数列表**（已完成标绿、当前正在测试标蓝）；未执行的 case 显示灰色 `Pending`；并发模式仍显示全部请求数 tag（按并发升序） |
| 多组相同条件 | 每组独立（唯一 `case_id`），显示 `g{id}` 组 id 标签，状态/进度互不联动（见 2.1） |
| 请求数展示 | **分组信息/请求数两行结构**：第一行 `.case-head`（label + g{id} + 长度），第二行 `.case-tags` 请求数**单独一行**（`width:100%` + flex-wrap），一行不够**换行多行**，**每行至少 8 个**（tag `min-width:26px`、**字体缩小 10px**）；**面板高度不足时在 `.cases-body` 内滚动**（卡片 body `overflow:hidden` 约束 + `overflow-y:auto`） |

### 2.1 多组条件唯一组 id（case_id）

多组条件（如阈值模式下两个条件组同为 `1024x1024`）时，各组必须可区分，否则 Cases / Realtime / Statistics 均按 label 叠加合并。

- **数据链路**：创建页 `length_pairs` 每项第 4 个元素为条件组唯一 `id`、第 5 个元素为该组阈值 dict（如 `[1024, 1024, "1024x1024", 1, {ttft_statistic, ttft_threshold_ms, tpot_statistic, tpot_threshold_ms, output_throughput_threshold}]`）→ 后端 `build_cases` 生成 `case_id` 并将阈值写入每个 case → 每条结果行（row）携带 `case_id`；`task_log` 广播同样携带，用于前端定位当前执行位置。
- **Cases 面板**：每个 case 行显示 `g{case_id}` 组 id 标签（如 `1024x1024 g1` / `1024x1024 g2`）；已测试请求数、当前执行位置均按 case 身份（`case_id` 优先，缺省回退 label）匹配，互不联动。
- **Realtime Data**：分组键为 `caseKey = label#g{case_id}`（如 `1024x1024#g1`），相同 label 的多组独立成组，组内各自执行 Best/BestPerf 高亮。
- **Statistics**：12 张统计图序列键同样 case_id 感知（`label#g{case_id}`），相同条件多组独立成线；**图例位于 Y 轴右侧、曲线图内**（`orient: vertical` 竖排、`left:48/top:12`；标记/文字缩小 `itemWidth/Height:8` + `fontSize:9`、**透明度 60%**）。
- **Statistics 联动开关**：面板 header 右侧「联动」开关（默认开启）——开启时鼠标进入任一统计图，**同组所有统计图浮动信息（tooltip）联动显示**（`echarts.connect('perf-charts')`）；关闭时 `echarts.disconnect` 不联动。
- **后端聚合**：`_annotate_best` / `_find_best`（xlsx 与运行详情最佳标记）按 `case_id or label` 分组；详情页 merged/display rows 透传 `case_id`。
- **兼容性**：旧任务（无 `case_id`）自动回退按 label 匹配，行为不变。

---

## 3. Realtime Data 面板策略

### 3.1 表格排序

表格数据按 **case 身份分组**（分组键 `caseKey = label#g{case_id}`，相同 label 的多组独立分组；旧任务无 `case_id` 回退 label，如 `256x256`、`1K1K`），**组内**按请求数量（并发）**从小到大**排列；每组**单独执行** Best/BestPerf 高亮（每组有且仅有一个），组间互不影响。

### 3.2 Best 标记（本地面板阈值）

面板 header 右侧两个本地阈值控件，**仅对表格标记生效，不写回任务**：

| 控件 | 默认值 | 说明 |
| --- | --- | --- |
| TPOT Threshold | 100 | 本地阈值，可编辑 |
| Output Token Threshold | 0 | 本地阈值，可编辑 |

**唯一高亮行规则**：在满足阈值条件的行中，标记**并发最大的一行**为 `Best`（有且仅有一个）。

- 条件判定均为 `≤`：`tpot_mean ≤ TPOT Threshold` 且 `output_mean ≤ Output Token Threshold`
- 值为 0 的条件**不参与判定**（视为未配置）
- **两阈值全为 0（用户手动设置）→ 不处理逻辑，无 Best 标签**
- 任一非 0 → 该条件生效；两个非 0 → 两个条件同时满足才标记
- **默认 `(100, 0)` → 仅 tpot 条件生效（`tpot_mean ≤ 100`）**

处理流程（伪代码）：

```text
rows 按并发升序
bestRow = null
for r in rows:
    if 满足 tpot 条件(阈值>0 时 tpot_mean ≤ 阈值) and 满足 output 条件(阈值>0 时 output_mean ≤ 阈值):
        if r.concurrency > bestRow.concurrency: bestRow = r
bestRow.best = true
```

### 3.3 BestPerf 标记（每组 case 阈值，全条件判断）

**仅阈值模式**下，**按每组 case 自己的阈值全条件判断**（`markBestRow(groupRows, caseObj)`，阈值跟随 Groups 数据不跟随主任务）：

- 每组取该组 case 的阈值与统计量：`ttft_{stat}`（TTFT-Mean/Median/P99）、`tpot_{stat}`（TPOT-Mean/Median/P99）、`output_mean`（Output）——值 > 0 才参与判定（`≤`），任一配置条件不满足即排除
- 满足**所有配置条件**的行中，取**并发最大的一行**标记 `BestPerf`，每组有且仅有一个
- **旧格式任务回退**：case 阈值字段为有效正值（`> 0`）时以每组为准；否则（`0`/未配置，即 cases 无 per-group 阈值）**回退任务级阈值字段**（含对应 statistic），与 Cases 面板 `caseThresholdText` 口径一致——旧格式任务（如任务级 `tpot_threshold_ms=80`）在 Realtime Data 同样恢复 BestPerf 金色高亮行
- 全部阈值为 0 / 并发模式 → 不处理

### 3.4 两者定义区分（Best vs BestPerf）

| 项 | Best | BestPerf |
| --- | --- | --- |
| 阈值来源 | 面板本地 TPOT Threshold / Output Token Threshold | 每组 case 自带阈值（TTFT/TPOT 的 statistic + Output，跟随 Groups 不跟随主任务） |
| 生效模式 | 两种模式均生效 | 仅阈值模式 |
| 条件 | 同上本地阈值，0 不参与 | 按每组全条件判断：`ttft_{stat} ≤ 组TTFT`、`tpot_{stat} ≤ 组TPOT`、`output_mean ≤ 组Output`（0 不参与），所有配置条件均满足才候选 |
| 标记数 | 有且仅有一行 | 每组有且仅有一行 |
| 视觉 | 绿色行背景 + 金色 `Best` 标签 | 金色行背景 + 金色 `BestPerf` 标签 |

同一行可同时命中 Best 与 BestPerf；两者互不干扰。

### 3.5 output_mean 单元格展示

- Output 列数值始终黑色默认样式（不再按本地 Output Token Threshold 做金色达标高亮，`pass-val` 机制已移除；Best 标签与 BestPerf 行背景金色不受影响）。

### 3.6 约束

- TPOT Threshold / Output Token Threshold **必须为整数**（输入框 `:precision=0` + 保存时 `Math.round` 兜底校验）。
- 值变更后**即时重算**表格标记（响应式 computed，无需刷新）。

### 3.7 展示规则

- **Successful 百分比不显示小数点**（四舍五入为整数，如 `98%`）。
- Perf 面板不显示 Requests 行（仅保留 Concurrency 行，inf/follow/数值规则不变）。
- Perf 面板 Framework 行下新增 **Mode 行**：`Concurrency Mode`（并发模式）/ `Threshold Mode`（阈值模式），样式与 Framework 一致（不高亮）。
- **Realtime Data 分组标题行展示每组阈值条件**（`.group-threshold`，**仅阈值模式**）：分组标题行在 `label + 行数` 右侧追加**该组阈值条件文本**（按每组 case 生成（`groupThresholdTexts`，由 `theTask.cases` → `caseKeyOf(case)` → `caseThresholdText(case)`，与 Cases 面板同一口径，跟随 Groups 不跟随主任务），如 `TTFT-Mean ≤ 50ms · TPOT-Median ≤ 100ms · Output ≤ 200 tok/s`）；宽度不够伪隐藏（ellipsis + title 完整文本）；0 值项不显示
- **表格导出 Excel**：Realtime Data 表格底部 Columns 右侧有 **下载按钮**（图标+文字），点击后将**当前表格内容**（含分组标题行、当前可见列、Best/BestPerf 标记）导出为 xlsx：
  - 通过 `POST /api/tasks/{task_id}/export` 由后端 `openpyxl` 生成
  - 文件写入**任务记录缓存目录**（`task.run_dir/`，与 `run.json`/CSV/日志同目录），并同时返回给浏览器下载
  - 组标题行在 Excel 中加粗 + 浅蓝底色；表头加粗

### 3.8 Progress 计数策略（Perf 面板 header）

Perf 面板 header 右侧 `Progress done/total` 的计数与执行模式相关：

| 模式 | 计数规则 |
| --- | --- |
| 并发模式 | `total = case 数 × concurrency_list 档位数`（并发点预知、固定）；`done = 已有结果（成功或失败）的行数` |
| 阈值模式 | **按 Cases 计数**：`total = case 总数`（固定）；`done = 已有任意结果行的 case 数`（按 `case_id` 去重）；单个 case 任务显示 `1/1`，N 个 case 显示 `N/N` |

- **原因**：阈值模式并发点由策略**动态探测**（1→2→4→8…，`concurrency_list` 持续增长），若作为进度分母会产生不稳定、与 Cases 数量不对齐的数值（如 `32/36`）。
- 阈值模式进度与 Cases 面板数量严格一致：每完成一个 case，`done` 递增 1；与 Cases 面板的 `g{case_id}` 分组一一对应。

---

## 4. 双模式联动关系

| 联动点 | 规则 |
| --- | --- |
| 每组阈值 → Cases | 阈值模式按每组 case 显示只读条件（含统计量标识：TTFT-Mean/Median/P99、TPOT-Mean/Median/P99、Output） |
| 每组阈值 → Realtime 分组标题行 | 阈值模式下分组标题行展示该组只读阈值条件（`.group-threshold`，跟随 Groups，与 Cases 同一口径） |
| 每组阈值 → BestPerf | 阈值模式下按每组 case 全条件（TTFT/TPOT statistic + Output）唯一高亮行策略标记 |
| 任务阈值 → 本地阈值 | 互不影响：本地阈值默认 TPOT 100 / Output 0，不回退到任务值（区分两者定义） |
| 本地阈值 → Best | 唯一高亮行标记 + output_mean 单元格高亮 |
| 本地阈值 → 任务 | 不写回任务（不再调用更新阈值接口） |
| 切换任务 | 重置本地阈值覆盖值（回默认：TPOT 100 / Output 0） |
| 并发模式 | 无阈值条件、无 BestPerf；Best 正常处理 |

### 4.1 关联的页面规则（保持一致）

- 参数页 yaml 只读：表单修改仅存内存（`syncParams`），不写文件，仅用于前后命令生成。
- 命令生成规则：「只附加修改的参数」——未修改参数不进入命令。
- Realtime 行标记由前端 computed 计算，实时反映本地面板阈值变更。

---

## 5. 边界与约束汇总

| 场景 | 行为 |
| --- | --- |
| 本地两阈值全 0（手动设置） | 无 Best 标记 |
| 本地默认 (100, 0) | 仅判定 tpot 条件（tpot_mean ≤ 100） |
| 本地仅 TPOT 非 0 | 仅判定 tpot 条件 |
| 本地仅 Output 非 0 | 仅判定 output 条件 |
| 本地两阈值均非 0 | 两条件同时满足才标记 |
| 任务输出阈值 = 0 | 该条件不参与 BestPerf 判定 |
| 并发模式 | 无 BestPerf、无阈值条件显示 |
| 阈值模式 | BestPerf + Best 同时可用 |
| 阈值输入非整数 | 保存时取整（`Math.round`），小于 0 忽略 |
| 多组相同条件（阈值模式） | 每组独立运行与展示（唯一 `case_id`），不叠加合并 |
| 阈值模式 Progress | 按 case 数计数（`1/1`、`2/2`、`N/N`），不随动态并发点增长 |

---

## 6. 验证记录

- 用真实阈值模式任务数据（`task-0826-171219`，`mode=threshold`，`tpot_threshold_ms=100`，`output_throughput_threshold=0`）模拟验证：
  - `(0,0)` → 无高亮行
  - `(100,0)` → 并发 161（tpot 97.42 ≤ 100 中最大并发）
  - `(20,0)` → 并发 2
  - `(0,300)` → 并发 16（output 262 ≤ 300 中最大并发）
  - `(20,300)` → 并发 2（双条件同时满足中最大并发）
  - 任务阈值 BestPerf `(100,0)` → 并发 161（同策略）
- 多组相同条件验证（`mode=threshold`，两组 `1024x1024`，`case_id=1/2`）：
  - 任务快照 cases 各带唯一 `case_id`；执行后 rows 均携带 `case_id`，两组数据独立（Cases / Realtime / Statistics 不叠加）
  - Progress 按 case 数计数：2 个 case → `1/2` → `2/2`；单个 case → `1/1`
- 无 lint 错误，`dev.sh stop/start` 重启后接口与产物正常。

---

## 7. 相关文档约定

> **约定**：后续对 Performance 页面的设计/界面修改、逻辑与策略调整、UI 调整，均需同步更新本文档。

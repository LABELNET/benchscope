# benchscope Performance 任务执行页 — 双模式核心逻辑与联动说明

> **版本**：v1.0.5  
> **最后更新**：2026-08-26  
> **文档状态**：Performance 任务执行页双模式（并发 / 阈值）核心逻辑策略与联动关系说明  
> **前置文档**：[PRD_260826-1.md](./PRD_260826-1.md)

---

## 0. 总览

Performance 任务执行页存在两种执行模式，由任务创建时的 `mode` 决定，并随任务快照下发到前端：

| 模式 | 判定字段 | Cases 阈值条件 | Realtime 任务级标记 | Realtime 本地标记 |
| --- | --- | --- | --- | --- |
| 并发模式 `concurrency` | `mode = concurrency` | 不显示 | 不处理 BestPerf | 处理 Best |
| 阈值模式 `threshold` | `mode = threshold` | 显示（只读） | 处理 BestPerf | 处理 Best |

两种模式下，**表格排序、本地 Best 标记逻辑完全一致**；差异仅在于：阈值模式额外显示任务阈值条件，并基于任务阈值标记 BestPerf。

---

## 1. 模式定义与判定

- 模式字段 `mode` 来自任务快照（`task.payload.mode`，默认 `concurrency`），创建任务时写入。
- 阈值模式附带任务阈值参数：
  - `tpot_threshold_ms`（TPOT 均值阈值，ms）
  - `output_throughput_threshold`（Output token throughput 阈值，tok/s，可为 0 表示未配置）
- 任务快照中补充字段：`mode`、`output_throughput_threshold`，前端据此展示条件与标记。

---

## 2. Cases 面板策略

| 项 | 规则 |
| --- | --- |
| header 右侧 mode | 纯文字绿色（`#52c41a`，12px，600），不做成 tag |
| 并发内容排列 | 按并发数量从小到大升序排列，与 Realtime Data 无关（脱钩，各自排序） |
| 阈值条件显示 | **仅阈值模式**显示只读条件，格式与 Perf 内容一致（仅文字，不可编辑）：`TTOT mean(ms) ≤ Xms`、`Output token throughput (tok/s) ≤ Y tok/s`；并发模式不显示 |
| Output 条件显示 | 任务 `output_throughput_threshold > 0` 时才显示该条 |
| 阈值模式请求显示 | 每个 case **独立**显示测试状态（请求数**不联动**）：已执行/执行中的 case 显示该 case 已测试过的**完整请求数列表**（已完成标绿、当前正在测试标蓝）；未执行的 case 显示灰色 `Pending`；并发模式仍显示全部请求数 tag（按并发升序） |

---

## 3. Realtime Data 面板策略

### 3.1 表格排序

表格数据按 **case(label) 分组**（如 `256x256`、`1K1K`），**组内**按请求数量（并发）**从小到大**排列；每组**单独执行** Best/BestPerf 高亮（每组有且仅有一个），组间互不影响。

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

### 3.3 BestPerf 标记（任务阈值）

**仅阈值模式**下，用**任务阈值**（`tpot_threshold_ms`、`output_throughput_threshold`）按与 Best 完全相同的策略标记 `BestPerf`：

- 满足条件（值 > 0 才参与，`≤` 判定）的行中，取**并发最大的一行**，有且仅有一个
- 两个任务阈值全为 0 / 并发模式 → 不处理

### 3.4 两者定义区分（Best vs BestPerf）

| 项 | Best | BestPerf |
| --- | --- | --- |
| 阈值来源 | 面板本地 TPOT Threshold / Output Token Threshold | 任务快照任务阈值 |
| 生效模式 | 两种模式均生效 | 仅阈值模式 |
| 条件 | 同上本地阈值，0 不参与 | `tpot_mean ≤ 任务TPOT` 且 `output_mean ≤ 任务Output`（0 不参与） |
| 标记数 | 有且仅有一行 | 有且仅有一行 |
| 视觉 | 绿色行背景 + 金色 `Best` 标签 | 金色行背景 + 金色 `BestPerf` 标签 |

同一行可同时命中 Best 与 BestPerf；两者互不干扰。

### 3.5 output_mean 单元格达标高亮

- 本地 Output Token Threshold > 0 时，`output_mean ≤ 阈值` 的单元格金色加粗（`#faad14`）。

### 3.6 约束

- TPOT Threshold / Output Token Threshold **必须为整数**（输入框 `:precision=0` + 保存时 `Math.round` 兜底校验）。
- 值变更后**即时重算**表格标记（响应式 computed，无需刷新）。

### 3.7 展示规则

- **Successful 百分比不显示小数点**（四舍五入为整数，如 `98%`）。
- Perf 面板不显示 Requests 行（仅保留 Concurrency 行，inf/follow/数值规则不变）。
- Perf 面板 Framework 行下新增 **Mode 行**：`Concurrency Mode`（并发模式）/ `Threshold Mode`（阈值模式），样式与 Framework 一致（不高亮）。
- **表格导出 Excel**：Realtime Data 表格底部 Columns 右侧有 **下载按钮**（图标+文字），点击后将**当前表格内容**（含分组标题行、当前可见列、Best/BestPerf 标记）导出为 xlsx：
  - 通过 `POST /api/tasks/{task_id}/export` 由后端 `openpyxl` 生成
  - 文件写入**任务记录缓存目录**（`task.run_dir/`，与 `run.json`/CSV/日志同目录），并同时返回给浏览器下载
  - 组标题行在 Excel 中加粗 + 浅蓝底色；表头加粗

---

## 4. 双模式联动关系

| 联动点 | 规则 |
| --- | --- |
| 任务阈值 → Cases | 阈值模式显示只读条件（TTOT mean ≤ Xms、Output throughput ≤ Y tok/s） |
| 任务阈值 → BestPerf | 阈值模式下按唯一高亮行策略标记 |
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

---

## 6. 验证记录

- 用真实阈值模式任务数据（`task-0826-171219`，`mode=threshold`，`tpot_threshold_ms=100`，`output_throughput_threshold=0`）模拟验证：
  - `(0,0)` → 无高亮行
  - `(100,0)` → 并发 161（tpot 97.42 ≤ 100 中最大并发）
  - `(20,0)` → 并发 2
  - `(0,300)` → 并发 16（output 262 ≤ 300 中最大并发）
  - `(20,300)` → 并发 2（双条件同时满足中最大并发）
  - 任务阈值 BestPerf `(100,0)` → 并发 161（同策略）
- 无 lint 错误，`dev.sh stop/start` 重启后接口与产物正常。

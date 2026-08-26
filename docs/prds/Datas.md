# Datas 页面 — 功能与约束说明

> **版本**：1.0.6（开发中）  
> **最后更新**：2026-08-27  
> **文档状态**：Datas（记录管理）页面的功能逻辑与约束条件说明  
> **关联文档**：[Performance.md](./Performance.md)（任务执行）· [Dashboard.md](./Dashboard.md)（记录入口联动）

---

## 0. 总览

Datas 为 1.0.6 新增的主导航页（位于 Sessions 之后），提供性能/精度测试记录的集中管理：

- **Perfs Tab**：性能测试记录（分页、最佳记录高亮、性能数据详情、记录对比分析）
- **Evals Tab**：精度/评估测试记录（占位，误差情况待 v5.0）

---

## 1. Perfs Tab

### 1.1 记录列表

- 数据源：`GET /api/logs/runs`（与 Dashboard 同源）
- 表格：分页（每页 10 条，不分页开关）、纯文本样式（同 Dashboard：12px、状态/操作列着色）
- 列：Run ID / Model / Framework / Status / Time / Avg TPOT (ms) / 操作（详情）
- **Avg TPOT**：该记录全部 rows 的 `tpot_mean` 均值（无数据显示 `-`）

### 1.2 最佳测试记录（Best）

- 定义：全部记录的 rows 中 **`tpot_mean` 最小**的一条记录
- 展示：工具栏金色徽标 `🏆 最佳测试记录: {run_id}（TPOT {tpot_mean}ms）`；该记录行背景金色（`#fffbe6`）+ Run ID 旁 `Best` 金色 tag
- 计算为前端 computed（`bestRecord`），数据更新自动重算

### 1.3 性能数据详情页（详情抽屉）

- 数据源：`GET /api/logs/runs/{run_id}`（返回 `{run: {rows}}`，兼容直接返回 rows）
- 展示：**重规划后的 mean / median / p99 三元组**表格——Output mean、TTFT mean/median/p99、TPOT mean/median/p99、ITL mean/median/p99（每行一个 case×concurrency）
- 缺失指标显示 `-`

### 1.4 记录对比分析

- 入口：工具栏「记录对比分析」（≥2 条记录时可点）
- Modal：多选记录（最多 4 条）→ 对比表（行=指标 output/total/ttft/tpot/itl 的 mean 均值，列=所选记录）

---

## 2. Evals Tab

- 占位：说明「精度/评估测试记录（v5.0），展示误差情况」+ 空状态（`accuracyPlanned`）
- 分页记录与误差展示待 v5.0 实现

---

## 3. 约束与边界

| 项 | 约束 |
| --- | --- |
| 数据源 | 复用 `/api/logs/runs` 与 `/api/logs/runs/{id}`，不新增后端接口 |
| Best 记录 | 仅统计含 `tpot_mean` 的 rows；无任何记录时不显示徽标 |
| 详情抽屉 | 仅展示含 `metrics` 的 rows；mean/median/p99 缺失显示 `-` |
| 对比分析 | 至少 2 条、最多 4 条记录；指标取 mean 均值 |
| Dashboard 联动 | 「更多/详情」入口联动待接通（TODO） |

## 4. 相关文档约定

> **约定**：后续对 Datas 页面的设计/界面修改、逻辑与策略调整、UI 调整，均需同步更新本文档。

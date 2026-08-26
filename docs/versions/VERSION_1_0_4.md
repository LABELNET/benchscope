# VERSION 1.0.4 — 版本修订记录

> **版本**：1.0.4  
> **文档状态**：1.0.4 发布前的规划与 1.0.5 范围定义期文档归档（原 `.trae/` 目录内容，按时间顺序整理）  
> **说明**：`.trae/` 规划文档已归档删除；后续版本文档统一在 `docs/versions/VERSION_x_y_z.md` 按时间顺序维护

---

## 1. 版本概述

1.0.4 为补丁发布（README 完善、打包元数据更新），期间完成了 **1.0.5 范围定义与发布前收口规划**。本文件按时间顺序归档该阶段的 5 份规划文档：

| 序号 | 原文档 | 主题 |
| --- | --- | --- |
| 1 | `.trae/specs/define-1.0.5-scope/spec.md` | 1.0.5 功能范围与待办清单 Spec |
| 2 | `.trae/specs/define-1.0.5-scope/tasks.md` | 1.0.5 发布前收口清单（P0/P1/P2） |
| 3 | `.trae/specs/define-1.0.5-scope/checklist.md` | 1.0.5 验收检查清单 |
| 4 | `.trae/documents/performance-page-single-task-redesign.md` | Performance 页面单任务重设计 |
| 5 | `.trae/documents/ui-refinement-batch.md` | UI 精修与功能补全 Plan v2 |

---

## 2. 阶段 1 — 1.0.5 功能范围与待办清单 Spec（define-1.0.5-scope/spec.md）

**Why**：1.0.5 将「v2.0 UI 大改」（Dashboard / 任务化 Performance / Sessions / Accuracy / Settings 分区 + i18n + 主题）合并进当前版本，版本号已三处 bump（`pyproject.toml` / `benchscope/__init__.py` / `web/package.json`），但多处功能未完成或存在数据断链。本 Spec 梳理已落地与待开发项，形成 1.0.5 发布前收口依据。

**现状梳理（已落地）**：
- 后端：`TaskManager` 多任务并发 + JSON 持久化 + 重启恢复（running→stopped）+ best 标注 + xlsx/CSV 汇总；`SessionManager` 会话 CRUD + SSE 转发；WebSocket 消息带 `task_id` 路由
- 前端：5 标签导航（旧路由重定向兼容）；Dashboard 统计卡片 + 记录表 + 详情 Modal；Performance 任务列表 + 三步建任务 + 任务详情；Sessions 会话 + 流式 + 思考块 + Markdown；Settings 通用/模型/插件；i18n + 主题

**已确认的断点与缺陷（8 项）**：
1. TaskManager 不写 `run.json` → Dashboard 记录 meta 全空、统计漏算
2. i18n 重复键（zh/en 各 18 个键定义两次）
3. TaskDetailView 运行态高亮缺失（`caseConcRunning` 硬编码 false）
4. SessionsView 装饰控件（上传/搜索/质量）未接线
5. SessionsView 清空全部无 UI 入口
6. 模型管理库未实现（`model_manager.py` 等，实际用 `config.providers` 代替）
7. Settings 硬编码英文（Provider 表格标题等未 i18n）
8. 遗留文件（TestView/LogView 等未被路由引用）

## 3. 阶段 2 — 1.0.5 发布前收口清单（define-1.0.5-scope/tasks.md）

按优先级排序（P0 阻断性缺陷 / P1 未完成功能 / P2 清理与文档），8 项任务全部完成：

- **P0**
  - Task 1：打通 TaskManager 与 Dashboard/Logs 数据链（run.json 落盘，字段对齐 + 复用 `Task.snapshot()`，fake 任务验证）
  - Task 2：i18n 重复键去重（18 个键合并 + 加键唯一性校验脚本）
- **P1**
  - Task 3：TaskDetailView 运行态高亮（`caseConcRunning` 依据 task_log/task_result 判定）
  - Task 4：SessionsView 装饰控件决策（**默认移除**）+ 清空全部按钮（popconfirm）
  - Task 5：模型管理库决策（**推荐接受现状**，推迟到后续版本）
  - Task 6：Settings 硬编码英文 i18n 化
- **P2**
  - Task 7：遗留视图与组件清理（TestView/LogView 删除或归档，grep 确认无残留）
  - Task 8：文档对齐 1.0.5 发布（README 五栏导航 / ROADMAP 补 1.0.4/1.0.5 行 / docs/PRD.md 版本号）

**依赖关系**：Task 1 独立可并行；Task 2 先于 Task 6（避免键冲突）；Task 4/5/7/8 独立可并行；Task 3 独立。

## 4. 阶段 3 — 1.0.5 验收检查清单（define-1.0.5-scope/checklist.md）

- P0：run.json 存在且字段完整；Dashboard 记录 meta 非空；`avg_tpot`/`best_model` 计入；详情 Modal 正常加载；i18n 重复键各仅一次；zh/en 切换无回退 key 名
- P1：运行态 case/并发标签三色（green/processing/default）；Sessions 装饰控件已移除；清空全部可用；Settings 无硬编码英文；模型管理库方案已确认
- P2：遗留视图无引用残留；README/ROADMAP/PRD 文档同步；`npm run build` + `python -m build` + `twine check` 通过

## 5. 阶段 4 — Performance 页面单任务重设计（documents/performance-page-single-task-redesign.md）

**目标**：将 `/performance`、`/performance/create`、`/performance/:taskId` 三路由合并为**单一页面、单任务**体验——页面有且仅保留一个任务，默认显示功能介绍 +「开启测试」入口，创建后同页内联展示四块式详情，形成"创建→查看→删除→再创建"闭环。

**关键决策**：终端面板固定 420px；单任务策略**先删后建**（开启测试仅在无任务时显示）；旧路由重定向到 `/performance`。

**实现要点**：路由收敛（redirect）；store 增加 `theTask` getter（最新一个任务）；重写 PerformanceView（介绍页 + 四块式详情 + 创建 Modal 复用 TaskCreateForm）；删除 TaskDetailView / CreateTaskView；终端自动滚动；i18n 内联中文即可。

## 6. 阶段 5 — UI 精修与功能补全 Plan v2（documents/ui-refinement-batch.md）

1.0.5 收口后实测发现四类待补，按模块推进（已落地）：

- **模块 1 Settings**：移除 Execution Environment；暗色主题修复（`a-config-provider :key` 强制重渲染 / `config.save` 时序）；通用 tab 补充默认框架/TPOT 阈值/日志目录/数据集目录/请求速率
- **模块 2 Dashboard**：测试记录拆「性能/精度」双面板（上下并列）；性能面板加「删除」按钮（后端新增 `DELETE /api/logs/runs/{run_id}`）
- **模块 3 Performance**：任务列表卡片改表格（ID/模型/框架/数据集/并发/进展圆环/控制/操作列）；终端日志与实时数据点击右侧 **Drawer** 弹出
- **模块 4 TaskDetailView**：视觉统一（圆角/阴影/间距、硬编码色改 antd 变量适配暗色）、总览紧凑、命令预览默认折叠、运行态高亮沿用
- **模块 5 Sessions**：模型名改下拉框、发送改文字按钮、输入文字有内容蓝色/空 placeholder 灰色
- **i18n 新增键**：`perfTestRecords` / `accTestRecords` / `accuracyPlanned` / `deleteRun` / `deleteRunConfirm` / `terminalLog` / `realtimeData` / `viewDetail` / `requestRateInf` / `requestRateCustom`

---

## 7. 相关文档约定

> **约定**：后续 `docs/versions/` 下内容更新均以**时间顺序**维护：新版本创建 `VERSION_x_y_z.md`，同版本的迭代文档按时间先后追加到对应版本文档中。

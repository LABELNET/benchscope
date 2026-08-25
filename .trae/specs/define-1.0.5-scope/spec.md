# 1.0.5 功能范围与待办清单 Spec

## Why
1.0.5 将「v2.0 UI 大改」(Dashboard / 任务化 Performance / Sessions / Accuracy / Settings 分区 + i18n + 主题) 合并进当前版本,版本号已在 `pyproject.toml`、`benchscope/__init__.py`、`web/package.json` 三处 bump,但多处功能未完成或存在数据断链。本 spec 用于梳理 1.0.5 已落地与待开发项,形成可执行的 TODO 清单,作为 1.0.5 发布前的收口依据。

## 现状梳理(已落地)

### 后端
- `task_manager.py`:`TaskManager` 多任务并发、JSON 持久化(`~/.benchscope/tasks/<id>.json`)、服务重启恢复(running→stopped)、best-concurrency 标注、xlsx/CSV 汇总。
- `session_manager.py`:会话 CRUD + SSE 流式对话转发 OpenAI 兼容 API。
- `server/api_dashboard.py` / `api_tasks.py` / `api_sessions.py`:对应 REST 接口。
- WebSocket 消息带 `task_id` 路由(`task_started`/`task_result`/`task_log`/`task_done`/`task_error`)。

### 前端
- 5 标签导航:Dashboard / Performance / Accuracy / Sessions / Settings,旧路由 `/vllm` `/sglang` `/logs` 重定向兼容。
- Dashboard:统计卡片 + 测试记录表 + 详情 Modal(复用 `RunDetailPanel`)。
- Performance:任务卡片列表 + `/performance/create` 三步建任务 + `/performance/:taskId` 任务详情(左:进度+终端,右:总览+`RealtimeResultPanel` 含表格+6 曲线)。
- Sessions:会话列表 + 流式对话 + 思考块 + Markdown 渲染 + 性能提示栏。
- Settings:通用(主题/语言) / 模型(providers 表 + bench 命令) / 插件(占位)。
- i18n(zh/en 轻量自建)+ 主题(亮/暗/跟随系统)。

### 已确认的断点与缺陷
1. **TaskManager 不写 `run.json`**:`task_manager._execute` 仅写 detail 日志、mean/p99 CSV、xlsx,持久化在 `~/.benchscope/tasks/`;而 `api_dashboard._load_run_json` 与 `api_logs.list_runs` 都读 `logs_dir/<run>/run.json`。结果:任务化运行在 Dashboard 表格里 meta 全空、`avg_tpot`/`best_model` 统计漏算任务行。
2. **i18n 重复键**:zh.js 与 en.js 各有 18 个键定义两次(`selectModel`/`concurrency`/`framework`/`precision`/`datasetType`/`requestRate`/`advancedParams`/`modelStatus`/`models`/`newSession`/`clearSessions`/`clearConfirm`/`selectModelForChat`/`inputPlaceholder`/`send`/`cancel`/`noSession`/`tpotThreshold`),后者静默覆盖前者。
3. **TaskDetailView 运行态高亮缺失**:`caseConcRunning` 硬编码 `return false`,当前执行的 case/并发无法高亮。
4. **SessionsView 装饰性控件未接线**:上传文件(回形针)、联网搜索(地球)、质量(high/medium/low)绑定但未发往后端。
5. **SessionsView 清空全部**:`clearSessions` API 已存在,UI 无入口。
6. **模型管理库未实现**:`UI-REFACTOR-PLAN.md` 要求 `model_manager.py` + `api_models.py` + `~/.benchscope/models.json`,实际未建;Settings 用 `config.providers` 代替,TaskCreateForm 仅从 `/v1/models` 取模型。
7. **Settings 硬编码英文**:Provider 表格列标题、"Please enter provider name"、"Execution Environment" fallback 未 i18n。
8. **遗留文件**:TestView.vue / LogView.vue 及 legacy 组件未被路由引用。
9. **文档陈旧**:README/ROADMAP/PRD 仍描述 v1.0.0 三栏布局,未提 1.0.4/1.0.5 与新五栏 UI;PRD 标注 v1.0.4。
10. **SessionsView `cacheHit` 占位**:硬编码 `'—'`。

## What Changes
- **修复** TaskManager 在 run_dir 写 `run.json`,打通 Dashboard/Logs 与任务化运行的数据链。
- **去重** i18n zh.js / en.js 的重复键,合并为单一权威定义。
- **接线** TaskDetailView 的 case/并发运行态高亮。
- **决策** SessionsView 装饰控件(上传/搜索/质量):接线或移除,并补「清空全部会话」入口。
- **决策** 模型管理库:实现独立 `models.json` CRUD,或确认 `config.providers` 方案并更新计划文档。
- **i18n 化** Settings 中的硬编码英文。
- **清理** 未引用的 legacy 视图与组件(归档或删除)。
- **更新** README / ROADMAP / PRD 对齐 1.0.5 发布。
- **标注** Accuracy(v5.0 占位)与 Plugins(占位)在 ROADMAP 中注明。
- **标记 BREAKING 的项**(若有)在对应任务中注明。

## Impact
- Affected specs: 无前置 spec(本目录为首份)。
- Affected code:
  - 后端:[benchscope/task_manager.py](file:///root/benchscope/benchscope/task_manager.py)、[benchscope/server/api_dashboard.py](file:///root/benchscope/benchscope/server/api_dashboard.py)、[benchscope/server/api_logs.py](file:///root/benchscope/benchscope/server/api_logs.py),可能新增 `benchscope/server/api_models.py` + `benchscope/model_manager.py`。
  - 前端:[web/src/views/TaskDetailView.vue](file:///root/benchscope/web/src/views/TaskDetailView.vue)、[web/src/views/SessionsView.vue](file:///root/benchscope/web/src/views/SessionsView.vue)、[web/src/views/SettingsView.vue](file:///root/benchscope/web/src/views/SettingsView.vue)、[web/src/i18n/zh.js](file:///root/benchscope/web/src/i18n/zh.js)、[web/src/i18n/en.js](file:///root/benchscope/web/src/i18n/en.js),删除 [web/src/views/TestView.vue](file:///root/benchscope/web/src/views/TestView.vue) / [LogView.vue](file:///root/benchscope/web/src/views/LogView.vue)。
  - 文档:[README.md](file:///root/benchscope/README.md)、[README.zh-CN.md](file:///root/benchscope/README.zh-CN.md)、[ROADMAP.md](file:///root/benchscope/ROADMAP.md)、[docs/PRD.md](file:///root/benchscope/docs/PRD.md)。

## ADDED Requirements

### Requirement: TaskManager 运行元数据落盘
TaskManager 在每次任务执行时,SHALL 在 `run_dir` 内写 `run.json`(含 model/framework/status/started_at/finished_at/rows 等字段,字段集与现有 `_load_run_json` 读取一致),以保证 Dashboard 与 Logs 视图能正确展示任务化运行。

#### Scenario: 任务完成后 Dashboard 可见
- **WHEN** 一个任务执行完成
- **THEN** `logs/<run_id>/run.json` 存在
- **AND** Dashboard 表格该行 meta(model/framework/status/started_at)非空
- **AND** Dashboard 统计(avg_tpot/best_model)计入该任务的 rows

### Requirement: i18n 单一权威定义
zh.js 与 en.js 中每个翻译键 SHALL 仅出现一次;构建期不允许重复键静默覆盖。

#### Scenario: 重复键被消除
- **WHEN** 检查 zh.js / en.js
- **THEN** 上述 18 个键各只出现一次
- **AND** 对应中英文文案一致且正确

### Requirement: 任务运行态高亮
TaskDetailView 的用例/并发标签 SHALL 区分「已完成 / 正在执行 / 未开始」三种状态并以颜色标识。

#### Scenario: 正在执行的并发高亮
- **WHEN** 任务 running 且某 case@concurrency 正在执行
- **THEN** 该标签显示为 processing 状态色
- **AND** 已完成项为 green,未开始项为 default

## MODIFIED Requirements

### Requirement: Sessions 对话区
SessionsView 对话区 SHALL 仅保留可用的交互控件;装饰性图标(上传/搜索/质量)要么接线到后端能力,要么移除;并补「清空全部会话」入口(复用已存在的 `DELETE /api/sessions`)。

## REMOVED Requirements
(无)

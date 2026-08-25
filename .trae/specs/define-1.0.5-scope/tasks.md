# Tasks

> 1.0.5 发布前收口清单。按优先级排序,P0 为阻断性缺陷,P1 为未完成功能,P2 为清理与文档。

## P0 — 阻断性缺陷

- [x] Task 1: 打通 TaskManager 与 Dashboard/Logs 数据链(run.json 落盘)
  - [x] SubTask 1.1: 在 `benchscope/task_manager.py` 的 `_execute` 中,任务开始/每完成一个并发/完成/出错/停止时,向 `task.run_dir/run.json` 写入(或增量更新)运行元数据;字段集对齐 `api_logs._load_run_json` 与 `api_dashboard._load_run_json` 读取的 `framework_name`/`model`/`status`/`started_at`/`finished_at`/`rows`/`metrics`。
  - [x] SubTask 1.2: 复用 `Task.snapshot()` 生成 run.json 内容,避免双重结构维护;注意 `framework_name` 字段需保留(Dashboard 读取该键)。
  - [x] SubTask 1.3: 验证:跑一次 fake bench 任务,Dashboard 表格该行 meta 非空、`avg_tpot`/`best_model` 计入。

- [x] Task 2: i18n 重复键去重
  - [x] SubTask 2.1: 在 [web/src/i18n/zh.js](file:///root/benchscope/web/src/i18n/zh.js) 与 [en.js](file:///root/benchscope/web/src/i18n/en.js) 中合并 18 个重复键(`selectModel`/`concurrency`/`framework`/`precision`/`datasetType`/`requestRate`/`advancedParams`/`modelStatus`/`models`/`newSession`/`clearSessions`/`clearConfirm`/`selectModelForChat`/`inputPlaceholder`/`send`/`cancel`/`noSession`/`tpotThreshold`),保留语义正确的文案,删除重复定义。
  - [x] SubTask 2.2: 加一个构建期或 lint 校验,防止再次引入重复键(如 `npm run` 脚本对 i18n 文件做键唯一性检查)。

## P1 — 未完成功能

- [x] Task 3: TaskDetailView 运行态高亮
  - [x] SubTask 3.1: 在 [TaskDetailView.vue](file:///root/benchscope/web/src/views/TaskDetailView.vue) 实现 `caseConcRunning(label, conc)`:依据后端推送的 `task_log`/`task_result` 或 task 当前执行的 case/concurrency 判定,返回 true 时标签显示 processing 色。
  - [x] SubTask 3.2: 验证三种状态色:已完成 green、正在执行 processing、未开始 default。

- [x] Task 4: SessionsView 装饰控件决策与清空入口
  - [x] SubTask 4.1: 决策上传文件(回形针)/联网搜索(地球)/质量(high/medium/low)三控件去向:1.0.5 内接线到后端,或移除控件(默认移除,避免误导)。**推荐:移除,后续版本再实现。**
  - [x] SubTask 4.2: 在会话列表头部补「清空全部」按钮,调用已存在的 `api.clearSessions()`,带 popconfirm 确认。
  - [x] SubTask 4.3: 移除或实现 `perfStats.cacheHit` 占位(推荐移除该项显示)。

- [x] Task 5: 模型管理库决策
  - [x] SubTask 5.1: 评估是否实现 `UI-REFACTOR-PLAN.md` 中的独立模型库(`model_manager.py` + `api_models.py` + `~/.benchscope/models.json` CRUD,TaskCreateForm 可从模型库快速选择)。
  - [x] SubTask 5.2: **推荐方案**:1.0.5 接受现状(Settings `config.providers` + TaskCreateForm 从 `/v1/models` 取模型),不新建独立模型库;同步更新 `docs/UI-REFACTOR-PLAN.md` 与 `docs/PRD.md` 说明此项推迟到后续版本。若用户要求实现,再按计划建文件。

- [x] Task 6: Settings 硬编码英文 i18n 化
  - [x] SubTask 6.1: 在 [SettingsView.vue](file:///root/benchscope/web/src/views/SettingsView.vue) 将 Provider 表格列标题、"Please enter provider name"、"Execution Environment" fallback 等硬编码串替换为 `t('...')`,并在 zh.js/en.js 补键。

## P2 — 清理与文档

- [x] Task 7: 遗留视图与组件清理
  - [x] SubTask 7.1: 确认 [web/src/views/TestView.vue](file:///root/benchscope/web/src/views/TestView.vue) 与 [LogView.vue](file:///root/benchscope/web/src/views/LogView.vue) 未被路由引用(已确认 router 不引用)。
  - [x] SubTask 7.2: 检查 legacy 组件(EnvPanel/TestConfigPanel/TestProgressPanel/SubTabBar/RunRecordList/RunSummaryBlock)是否仍被引用;未被引用的删除或移入 `components/legacy/`。
  - [x] SubTask 7.3: 删除前 grep 确认无 import 残留。

- [x] Task 8: 文档对齐 1.0.5 发布
  - [x] SubTask 8.1: 更新 [README.md](file:///root/benchscope/README.md) / [README.zh-CN.md](file:///root/benchscope/README.zh-CN.md) 的功能特性、快速开始、目录结构,反映新五栏导航与任务化流程。
  - [x] SubTask 8.2: 更新 [ROADMAP.md](file:///root/benchscope/ROADMAP.md):补 1.0.4 / 1.0.5 行(1.0.5 = v2.0 UI 大改:Dashboard/任务化 Performance/Sessions/Accuracy 占位/Settings 分区/i18n/主题);注明 Accuracy 为 v5.0 占位、Plugins 为后续。
  - [x] SubTask 8.3: 更新 [docs/PRD.md](file:///root/benchscope/docs/PRD.md) 版本号至 v1.0.5,同步导航结构与 API 清单(tasks/sessions/dashboard)。
  - [x] SubTask 8.4: 更新 README 顶部的 Roadmap 表(当前只列 1.0.0 released / 2.0 planned)。

# Task Dependencies
- Task 1(run.json)独立,可并行。
- Task 2(i18n 去重)与 Task 6(Settings i18n)有耦合:先做 Task 2 去重,再做 Task 6 补键,避免再次冲突。
- Task 4 / Task 5 / Task 7 / Task 8 相互独立,可并行。
- Task 3 独立。

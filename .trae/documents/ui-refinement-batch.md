# UI 精修与功能补全 Plan (v2)

## Context
1.0.5 收口后实测发现四类待补:(1) Settings 暗色主题不生效、需移除 Execution Environment、通用设置项缺失;(2) Dashboard 测试记录需拆「性能/精度」双面板并加删除;(3) Performance 任务列表卡片改表格,终端日志/实时数据点击右侧 drawer 弹出;(4) Sessions 输入栏模型下拉与发送按钮调整。本 plan 严格贴合原始描述,不做超出需求的发挥。

---

## 模块 1:Settings

### 1.1 移除 Execution Environment(明确)
[SettingsView.vue:77-89](file:///root/benchscope/web/src/views/SettingsView.vue#L77-L89) Models tab 内的「执行环境配置」整块删除;同步删除 `benchCommands` ref、`saveBenchCommands` 函数、onMounted 中加载 bench_commands 的代码。bench 命令走代码默认值(`vllm bench serve` / `python -m sglang.bench_serving`)。后端 `ConfigPatch.bench_commands` 字段保留,仅前端不暴露。

### 1.2 暗色主题修复(排查路径)
**后端已确认通**:[api_config.py:33](file:///root/benchscope/benchscope/server/api_config.py#L33) ConfigPatch 有 theme 字段,update 返回完整 snapshot 含 theme。

**实施第一步:浏览器 DevTools 实测定位**
- Settings 选「暗色」后,控制台执行 `useConfigStore().config.theme` 看是否为 `'dark'`。
- 分支 A(值已是 dark 但 UI 没变):问题在 Ant Design 主题响应式。修 [App.vue:2](file:///root/benchscope/web/src/App.vue#L2) 给 `<a-config-provider :key="resolvedTheme" :theme="themeConfig">` 强制重渲染;或检查 `cssVar:true` 与动态 `algorithm` 切换的已知问题,必要时移除 cssVar 改纯 token。
- 分支 B(值未变 dark):问题在 [SettingsView.vue selectTheme](file:///root/benchscope/web/src/views/SettingsView.vue#L217-L225) 的 `config.$patch`/`config.save` 时序。改为先 `await config.save({theme})`(后端返回含 theme 的完整 config),不再用 `$patch` 预更新,避免被 save 返回值覆盖时序问题。

### 1.3 通用设置 checklist(盘点需补充项)
当前通用 tab 仅 `theme` + `locale`。对照 [PRD 3.2.3](file:///root/benchscope/docs/PRD.md) 补充到通用 tab:
- [ ] 默认框架(select vLLM/SGLang)
- [ ] TPOT 阈值(input number ms,默认 100)
- [ ] 日志目录(input,默认 ./logs)
- [ ] 数据集目录(input,默认 ./datasets)
- [ ] 请求速率(select inf / 自定义数值)
- (bench 命令模板:用户选完全删除,不加)

i18n 键已有(defaultFramework/tpotThreshold/logsDir/datasetsDir/requestRate),复用。

---

## 模块 2:Dashboard

### 2.1 拆双面板(上下并列同页)
[DashboardView.vue](file:///root/benchscope/web/src/views/DashboardView.vue) 测试记录区改为上下两张 `a-card` 并列(非 tabs):
- **性能测试记录**(上):现有测试记录表,数据源 `api.listRuns()`,actions 列加「删除」按钮。
- **精度测试记录**(下):空状态 `<a-empty description="精度测试功能规划中,待 v5.0">`,表格列定义预埋(同性能面板列),数据源空数组,为 v5.0 预留。

统计卡片保留在两个面板之上(全局统计)。

### 2.2 删除记录功能
- 后端新增 [api_logs.py](file:///root/benchscope/benchscope/server/api_logs.py):`DELETE /api/logs/runs/{run_id}`,复用 `_resolve_run_dir` 做路径穿越校验,`shutil.rmtree` 删除目录。
- 前端 [api/index.js](file:///root/benchscope/web/src/api/index.js) 加 `deleteRun(runId)`。
- 性能测试记录表 actions 列加「删除」按钮 + `a-popconfirm`,确认后调 `api.deleteRun`,成功后从 `runs` 移除并 `loadStats()`。

---

## 模块 3:Performance 任务表格 + Drawer

### 3.1 卡片网格 → 表格
[PerformanceView.vue](file:///root/benchscope/web/src/views/PerformanceView.vue) 改用 `a-table`,列:
- 任务 ID / 模型 / 框架(`<a-tag>`)/ 数据集(label)/ 并发(摘要)
- 进展列:`<a-progress type="circle" :percent="..." :width="36" />` 圆圈进度图标 + 状态 badge
- 控制列:开始/停止/删除按钮(按 status 显隐,`@click.stop` 防冒泡)
- 操作列:[终端日志] [实时数据] [详情] 按钮

整行点击跳详情(`customRow: { onClick }`);操作按钮 `@click.stop` 防冒泡。

### 3.2 Drawer 弹出
- **终端日志 drawer**:`<a-drawer placement="right" width="70%">` 放 terminal-box,数据源 `test.logLines[task_id]`。点「终端日志」按钮打开并记录当前 task_id。
- **实时数据 drawer**:`<a-drawer placement="right" width="60%">` 放 `<RealtimeResultPanel :rows="task.rows" :threshold="task.tpot_threshold_ms" :running="task.status==='running'" />`。点「实时数据」按钮打开。

两个 drawer 各自独立,可同时打开不同任务的(简化:同一时刻只一个 drawer,记录 currentDrawerTaskId)。

---

## 模块 4:TaskDetailView UI 优化(仅视觉+布局微调)
[TaskDetailView.vue](file:///root/benchscope/web/src/views/TaskDetailView.vue) 保持左右分栏结构,**不加圆圈进度图标**(那是 Performance 表格的),只做:
- 视觉:卡片圆角/阴影/间距统一;硬编码色(`#52c41a`/`#f52228` 等)改 `var(--ant-color-*)` 适配暗色主题。
- 布局微调:总览栏 4 个 statistic 改紧凑小号;命令预览默认折叠(`cmdCollapseKeys=[]`);case/并发标签间距优化;状态色条更醒目。
- 运行态高亮沿用上一轮 `caseConcRunning`。

---

## 模块 5:Sessions 输入栏
[SessionsView.vue:90-131](file:///root/benchscope/web/src/views/SessionsView.vue#L90-L131) 改造:
- 模型名 `<span class="model-name">` → 下拉框 `<a-select v-model="selectedModel" :options="modelOptions" size="small">`,仍放 `.input-right`。
- 发送按钮:圆形箭头(`<a-button shape="circle"><arrow-up-outlined /></a-button>`)→ 文字「发送」`<a-button type="primary" @click="sendMessage" :disabled="!inputText.trim()">{{ t('send') }}</a-button>`。
- 输入框**文字色**:有内容时蓝色,空时 placeholder 灰色。用 `:class="{ 'has-content': inputText.trim() }"` + CSS `.chat-textarea.has-content { color: #1677ff }`。
- 删除不再使用的 `ArrowUpOutlined` import 与 `.send-btn` 圆形样式。

---

## 后端 API 变更
- 新增 `DELETE /api/logs/runs/{run_id}` ([api_logs.py](file:///root/benchscope/benchscope/server/api_logs.py))
- 主题修复、Execution Environment 移除均不涉及后端

## i18n 新增键(zh.js / en.js)
`perfTestRecords` / `accTestRecords` / `accuracyPlanned` / `deleteRun` / `deleteRunConfirm` / `terminalLog` / `realtimeData` / `viewDetail` / `requestRateInf` / `requestRateCustom`。改完跑 `node scripts/check-i18n.js`。

## 验证
1. 语法:`python -c "import ast; ast.parse(open('benchscope/server/api_logs.py').read())"`;前端 esbuild 校验改动 .vue/.js。
2. i18n:`cd web && node scripts/check-i18n.js` exit 0。
3. e2e:启动 `python -m benchscope.cli --port 8080 --no-browser` 浏览器验证:
   - Settings 选暗色 → 页面变暗;通用 tab 补充项;Execution Environment 已无。
   - Dashboard 上下双面板;性能面板删除按钮可用;精度面板空状态。
   - Performance 任务表;点终端日志/实时数据弹 drawer;整行点进详情。
   - TaskDetail 视觉/布局微调生效。
   - Sessions 模型下拉、文字发送、输入蓝灰切换。
4. 构建:有 Node≥18 环境 `npm run build`(沙箱 Node v12 用 esbuild 替代校验)。

## 文件清单
- 后端:[benchscope/server/api_logs.py](file:///root/benchscope/benchscope/server/api_logs.py)
- 前端视图:[SettingsView.vue](file:///root/benchscope/web/src/views/SettingsView.vue) / [DashboardView.vue](file:///root/benchscope/web/src/views/DashboardView.vue) / [PerformanceView.vue](file:///root/benchscope/web/src/views/PerformanceView.vue) / [TaskDetailView.vue](file:///root/benchscope/web/src/views/TaskDetailView.vue) / [SessionsView.vue](file:///root/benchscope/web/src/views/SessionsView.vue)
- 前端其他:[App.vue](file:///root/benchscope/web/src/App.vue)(主题)/ [api/index.js](file:///root/benchscope/web/src/api/index.js)(deleteRun)/ [i18n/zh.js](file:///root/benchscope/web/src/i18n/zh.js) + [en.js](file:///root/benchscope/web/src/i18n/en.js)

# Performance 页面单任务重设计

## Context

当前 Performance 模块拆成三个独立路由：`/performance`(任务列表)、`/performance/create`(创建表单页)、`/performance/:taskId`(详情页)。用户希望合并为**单一页面、单任务**体验：Performance 页面有且仅保留一个任务，默认显示功能介绍 + "开启测试"入口，创建后直接在同一页面内联展示四块式测试详情。这样消除了页面跳转，让"创建→查看→删除→再创建"形成一个闭环。

## 目标布局

```
┌──────────────────────────────────────────────┐
│ TopBar (56px, 现有)                          │
├──────────────────────────────────────────────┤
│ 任务详情面板 (固定上方)                       │
│  状态/进度/耗时 + 进度网格 + 取消/删除按钮    │
├───────────┬──────────────────────────────────┤
│ 终端面板   │ 实时数据面板 (右侧可滑动)        │
│ (左侧固定 │ ┌────────────────────────────┐  │
│  420px)   │ │ MetricsTable (task.rows)   │  │
│           │ └────────────────────────────┘  │
│           │ ┌────────────────────────────┐  │
│           │ │ 测试曲线面板               │  │
│           │ │ MetricsCharts (6 条曲线)   │  │
│           │ └────────────────────────────┘  │
└───────────┴──────────────────────────────────┘
```

无任务时：页面正中显示功能介绍卡片 + "开启测试"按钮（居中、留白）。

## 关键决策（已与用户确认）

1. 终端面板宽度 **420px**（沿用现有详情页右侧终端宽度）
2. 单任务策略 **先删后建**："开启测试"按钮仅在无任务时显示；要新建必须先在详情顶部删除当前任务回到默认介绍页
3. 旧路由 `/performance/create`、`/performance/:taskId` **重定向到 `/performance`**

## 复用的现有组件/逻辑

- [TaskCreateForm.vue](file:///root/benchscope/web/src/components/performance/TaskCreateForm.vue) — 3 步表单，`emit('created', taskId)` + `emit('cancel')`，直接放入 `<a-modal>`，无需改动
- [MetricsTable.vue](file:///root/benchscope/web/src/components/MetricsTable.vue) — 实时数据表，props: `rows`/`threshold`/`pagination`
- [MetricsCharts.vue](file:///root/benchscope/web/src/components/MetricsCharts.vue) — ECharts 6 曲线，props: `rows`/`metricDefs`
- 终端历史日志加载 + 自动滚动逻辑：从 [TaskDetailView.vue](file:///root/benchscope/web/src/views/TaskDetailView.vue) 的 `loadTaskLogs` + `onTermScroll` + `scrollTermToBottom` 迁移到新 PerformanceView
- [test.js store](file:///root/benchscope/web/src/store/test.js) — `loadTaskLogs`/`startTask`/`stopTask`/`deleteTask` actions 已就绪

## 实现步骤

### 1. 路由收敛 — `web/src/router/index.js`

把 `/performance/create` 和 `/performance/:taskId` 改为 `redirect: '/performance'`，移除其 `component` 动态 import。

### 2. store 增加 `theTask` getter — `web/src/store/test.js`

```js
theTask: (s) => {
  const list = Object.values(s.tasks).sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
  return list[0] || null
}
```

返回最新一个任务（单任务语义下即"当前任务"）。`taskList` getter 保留不动供他处用。

### 3. 重写 PerformanceView.vue — `web/src/views/PerformanceView.vue`

**结构：**

```vue
<template>
  <div class="perf-page">
    <!-- 无任务：默认介绍页 -->
    <div v-if="!theTask && !loading" class="perf-intro">
      <div class="intro-card">
        <h2>性能测试</h2>
        <ul class="intro-features">…关键功能说明…</ul>
        <a-button type="primary" size="large" @click="createModalOpen = true">
          {{ t('startTest') }}  <!-- "开启测试" -->
        </a-button>
      </div>
    </div>

    <!-- 有任务：四块式详情 -->
    <div v-if="theTask" class="perf-detail">
      <!-- 块1: 任务详情面板 (固定上方) -->
      <div class="task-top-panel">…状态/进度/耗时 + 命令预览 + start/stop/delete 按钮 + 进度网格…</div>

      <!-- 块2-4: 终端(左固定) + 右侧可滑动 -->
      <div class="perf-body">
        <div class="terminal-left">
          <div class="terminal-box" ref="termBox" @scroll="onTermScroll">
            <div v-for="(line, i) in activeLogs" :key="i" class="term-line">{{ line }}</div>
          </div>
        </div>
        <div class="right-scroll">
          <a-card size="small" :title="t('realtimeData')">
            <MetricsTable :rows="theTask.rows || []" :threshold="theTask.tpot_threshold_ms" :pagination="{ pageSize: 20 }" />
          </a-card>
          <a-card size="small" title="测试曲线">
            <MetricsCharts :rows="theTask.rows || []" :metric-defs="metricDefs" />
          </a-card>
        </div>
      </div>
    </div>

    <!-- 创建任务 Modal -->
    <a-modal v-model:open="createModalOpen" :title="t('newTask')" width="760"
             :footer="null" :mask-closable="false" destroy-on-close>
      <TaskCreateForm @created="onCreated" @cancel="createModalOpen = false" />
    </a-modal>
  </div>
</template>
```

**script 要点：**

- `theTask = computed(() => test.theTask)` — 单任务引用
- `activeLogs = computed(() => theTask.value ? test.logLines[theTask.value.task_id] || [] : [])`
- 终端历史加载 + 自动滚动：从 TaskDetailView 搬过来，`onMounted` 调 `loadTasks()` → 若 `theTask` 存在则 `loadTaskLogs(theTask.task_id)` → `scrollTermToBottom()`；`watch(activeLogs.length)` 自动滚到底（用户向上阅读时不打扰）
- `metricDefs` 6 条（从 RealtimeResultPanel 复制过来，或抽到共享常量）
- `onCreated(taskId)`：关闭 modal，无需路由跳转（页面本就在 `/performance`，store 更新后 `theTask` 自动出现，视图切到详情）
- 顶部面板控件：`startTask`/`stopTask`/`deleteTask`（delete 后 `theTask` 变 null，回到介绍页）
- `canStart` / `canStop` / 状态文案辅助函数：从 TaskDetailView 搬过来

**CSS 要点（四块式布局）：**

```css
.perf-page { height: 100%; display: flex; flex-direction: column; overflow: hidden; padding: 16px 20px; }
.perf-intro { flex: 1; display: flex; align-items: center; justify-content: center; }
.intro-card { max-width: 520px; text-align: center; }  /* 介绍卡片居中 */
.perf-detail { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.task-top-panel { flex-shrink: 0; }  /* 固定上方 */
.perf-body { flex: 1; min-height: 0; display: flex; gap: 12px; overflow: hidden; }
.terminal-left { width: 420px; flex-shrink: 0; min-height: 0; display: flex; flex-direction: column; }
.terminal-box { flex: 1; min-height: 0; overflow-y: auto; …终端样式… }
.right-scroll { flex: 1; min-width: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
```

进度网格、命令预览、状态徽章等小组件的样式从 TaskDetailView 对应 class 迁移。

### 4. 删除不再使用的视图

- 删除 [TaskDetailView.vue](file:///root/benchscope/web/src/views/TaskDetailView.vue)
- 删除 [CreateTaskView.vue](file:///root/benchscope/web/src/views/CreateTaskView.vue)

已确认除 router 外无其他引用（grep 验证过），路由改为 redirect 后二者完全无用。`TaskCreateForm.vue` 保留（被 modal 复用）。

### 5. i18n 微调（可选）

介绍页文案可新增 key（如 `perfIntroTitle`、`perfIntroFeature1`…），或直接在模板内联中文文案（项目其他处也常见内联）。为减少改动，介绍页文案直接内联中文即可，按钮复用现有 `t('startTest') = '开始测试'`、`t('newTask') = '新建测试任务'`。

## 验证

1. `cd web && PATH=/tmp/node-v20.18.0-linux-x64/bin:$PATH npm run build` 构建通过
2. 停旧服务 → 后台重启 `python -m benchscope.cli --port 8080`
3. 浏览器访问 `/performance`：
   - 无任务时显示居中介绍 + "开启测试"按钮
   - 点"开启测试"弹出 modal，走完 3 步表单 → modal 关闭，页面切到四块详情
   - 详情顶部"删除任务"→ 回到介绍页
   - 终端进入即定位到底部，新日志到达自动滚到底，手动向上滚动不被打断
   - 右侧实时数据表 + 6 条曲线随测试推进更新，右侧整体可纵向滑动
4. 旧链接 `/performance/create`、`/performance/<taskId>` 自动跳回 `/performance`

<template>
  <div class="perf-page">
    <!-- 无任务：默认介绍页 (与 Accuracy 格式一致) -->
    <div v-if="!theTask && !loading" class="perf-intro">
      <div class="planned-card">
        <a-result
          :title="t('performance')"
          :sub-title="t('perfSubtitle')"
        >
          <template #icon>
            <span class="result-icon">
              <thunderbolt-outlined />
            </span>
          </template>
          <template #extra>
            <a-button type="primary" size="large" @click="createModalOpen = true">
              <template #icon><play-circle-outlined /></template>
              {{ t('startTest') }}
            </a-button>
          </template>
        </a-result>
        <div class="features">
          <a-row :gutter="24" justify="center">
            <a-col :xs="24" :sm="8" v-for="feat in features" :key="feat.title">
              <a-card size="small" class="feature-card" hoverable>
                <template #cover>
                  <div class="feature-icon">{{ feat.icon }}</div>
                </template>
                <a-card-meta :title="feat.title" :description="feat.desc" />
              </a-card>
            </a-col>
          </a-row>
        </div>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading && !theTask" class="perf-loading">
      <a-spin />
    </div>

    <!-- 有任务：四块式详情 -->
    <div v-if="theTask" class="perf-detail">
      <!-- 块1: 任务详情面板 (固定上方) — 模型为标题,右侧 Progress/Elapsed/Service/按钮 -->
      <a-card size="small" class="task-top-panel" :body-style="{ padding: '10px 14px' }">
        <template #title>
          <div class="panel-title-left">
            <span class="panel-title-model" :title="theTask.model">{{ theTask.model }}</span>
            <span class="title-sep">|</span>
            <span class="meta-text">
              <loading-outlined v-if="theTask.status === 'running'" class="title-spin" />
              {{ t('progress') }} {{ doneCount }}/{{ totalCount }}
            </span>
            <span class="meta-text">{{ t('elapsed') }} {{ elapsedText }}</span>
            <span class="meta-text">
              {{ t('perfStatus') }}:
              <span class="status-value" :class="statusClass(theTask.status)">{{ statusText(theTask.status) }}</span>
            </span>
          </div>
        </template>
        <template #extra>
          <div class="top-actions">
            <a-button v-if="canStart" type="primary" size="small" @click="startTask">{{ t('startTest') }}</a-button>
            <a-button v-if="theTask.status === 'running'" size="small" danger @click="stopTask">{{ t('stopTest') }}</a-button>
            <a-button v-if="canClose" size="small" danger ghost @click="closeTask">{{ t('close') }}</a-button>
          </div>
        </template>
        <!-- 面板内容:框架/精度/数据集 + Service Status + Service URL + 测试 case -->
        <div class="panel-body">
          <div class="info-row">
            <span class="info-item"><span class="info-label">{{ t('framework') }}</span><a-tag :color="theTask.framework === 'vllm' ? 'blue' : 'purple'" size="small">{{ theTask.framework_name || theTask.framework }}</a-tag></span>
            <span class="info-item" v-if="theTask.precision"><span class="info-label">{{ t('precision') }}</span>{{ theTask.precision }}</span>
            <span class="info-item"><span class="info-label">{{ t('dataset') }}</span>{{ datasetText }}</span>
            <span class="info-item" v-if="theTask.concurrency_list?.length"><span class="info-label">{{ t('concurrency') }}</span>{{ theTask.concurrency_list.join(', ') }}</span>
            <span class="info-item" v-if="theTask.request_rate && theTask.request_rate !== 'inf'"><span class="info-label">{{ t('requestRateLabel') }}</span>{{ theTask.request_rate }}</span>
            <span class="info-item">
              <span class="info-label">{{ t('serviceStatus') }}</span>
              <span :style="{ color: serviceReady ? 'var(--ant-color-success, #52c41a)' : 'var(--ant-color-error, #f5222d)' }">
                {{ serviceReady ? t('online') : t('offline') }}
              </span>
            </span>
            <span class="info-item"><span class="info-label">{{ t('serviceUrl') }}</span>{{ serviceUrl || '-' }}</span>
          </div>
          <div class="case-grid">
            <div v-for="(c, i) in theTask.cases || []" :key="i" class="case-item">
              <span class="case-label">{{ c.label }}</span>
              <span class="case-meta" v-if="c.input_len">{{ c.input_len }}/{{ c.output_len }}</span>
              <a-tag
                v-for="conc in theTask.concurrency_list || []"
                :key="conc"
                :color="caseConcDone(c.label, conc) ? 'green' : caseConcRunning(c.label, conc) ? 'processing' : 'default'"
                size="small"
              >{{ conc }}</a-tag>
            </div>
          </div>
        </div>
      </a-card>

      <!-- 块2-4: 控制台(左固定) + 右侧可滑动 -->
      <div class="perf-body">
        <!-- 块2: 控制台面板 (左固定 420px) -->
        <a-card size="small" class="terminal-left" :body-style="{ flex: '1', minHeight: '0', padding: '0', display: 'flex', flexDirection: 'column' }">
          <template #title>{{ t('terminal') }}</template>
          <template #extra>
            <a-button size="small" type="link" @click="downloadLog">
              <template #icon><download-outlined /></template>
              {{ t('download') }}
            </a-button>
          </template>
          <div class="terminal-box" ref="termBox" @scroll="onTermScroll">
            <div v-for="(line, i) in activeLogs" :key="i" class="term-line">{{ line }}</div>
          </div>
        </a-card>

        <!-- 块3+4: 右侧实时数据 + 数据分析 (可滑动) -->
        <div class="right-scroll">
          <!-- 块3: 实时数据面板 — 标题右侧放阈值等信息,内容仅表格 -->
          <a-card size="small" class="right-card">
            <template #title>{{ t('realtimeData') }}</template>
            <template #extra>
              <div class="rt-extra">
                <span class="rt-threshold">
                  <span class="info-label">{{ t('tpotThresholdLabel') }}</span>
                  <a-input-number
                    v-if="thresholdEditing"
                    v-model:value="thresholdInput"
                    size="small"
                    :step="10"
                    :min="1"
                    style="width: 90px"
                    @blur="saveThreshold"
                    @press-enter="saveThreshold"
                  />
                  <span v-else class="threshold-value" @click="editThreshold">
                    {{ theTask.tpot_threshold_ms || '-' }}ms
                  </span>
                </span>
              </div>
            </template>
            <MetricsTable
              :rows="annotatedRows"
              :threshold="theTask.tpot_threshold_ms"
              :pagination="false"
            />
          </a-card>
          <!-- 块4: 数据分析面板 -->
          <a-card size="small" class="right-card">
            <template #title>{{ t('dataAnalysis') }}</template>
            <MetricsCharts :rows="theTask.rows || []" :metric-defs="metricDefs" />
          </a-card>
        </div>
      </div>
    </div>

    <!-- 创建任务 Modal -->
    <a-modal
      v-model:open="createModalOpen"
      :title="t('newTask')"
      width="300"
      :footer="null"
      :mask-closable="false"
      destroy-on-close
    >
      <TaskCreateForm @created="onCreated" @cancel="createModalOpen = false" />
    </a-modal>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  DownloadOutlined,
  LoadingOutlined,
  PlayCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons-vue'
import { useTestStore } from '@/store/test'
import { useConfigStore } from '@/store/config'
import { t } from '@/i18n'
import MetricsTable from '@/components/MetricsTable.vue'
import MetricsCharts from '@/components/MetricsCharts.vue'
import TaskCreateForm from '@/components/performance/TaskCreateForm.vue'

const test = useTestStore()
const config = useConfigStore()
const loading = ref(false)
const features = computed(() => [
  { icon: '⚡', title: t('featMultiFramework'), desc: t('featMultiFrameworkDesc') },
  { icon: '🎯', title: t('featMultiCombination'), desc: t('featMultiCombinationDesc') },
  { icon: '📈', title: t('featRealtimeData'), desc: t('featRealtimeDataDesc') },
])
const createModalOpen = ref(false)
const termBox = ref(null)
const userNearBottom = ref(true)

// 阈值就地编辑
const thresholdEditing = ref(false)
const thresholdInput = ref(null)

const theTask = computed(() => test.theTask)
const taskId = computed(() => theTask.value?.task_id || null)
const activeLogs = computed(() => (taskId.value ? test.logLines[taskId.value] || [] : []))
const serviceReady = computed(() => config.status?.inference === 'ready')
const serviceUrl = computed(() => config.apiBase || '')

const totalCount = computed(() => {
  if (!theTask.value) return 0
  return (theTask.value.cases?.length || 0) * (theTask.value.concurrency_list?.length || 0)
})
const doneCount = computed(() => {
  if (!theTask.value) return 0
  return (theTask.value.rows || []).filter((r) => r.metrics || r.error).length
})
const canStart = computed(() => {
  if (!theTask.value) return false
  const s = theTask.value.status
  return s === 'pending' || s === 'error'
})
const canClose = computed(() => {
  if (!theTask.value) return false
  // 进行中不能关闭,只能停止
  return theTask.value.status !== 'running'
})

// 数据集文案
const datasetText = computed(() => {
  const ds = theTask.value?.dataset || {}
  const typeMap = { random: t('randomDataset'), sharegpt: 'ShareGPT', custom: t('custom'), file: t('fileDataset') }
  const type = typeMap[ds.type] || ds.type || '-'
  const pairs = theTask.value?.cases?.map((c) => (c.input_len ? `${c.input_len}/${c.output_len}` : c.label)).join(', ')
  return pairs ? `${type}(${pairs})` : type
})

// 每次新记录就对比阈值标注最佳(前端计算,与后端 _annotate_best 一致)
const annotatedRows = computed(() => {
  const rows = (theTask.value?.rows || []).map((r) => ({ ...r }))
  const threshold = theTask.value?.tpot_threshold_ms
  if (!rows.length || !threshold) return rows
  const byCase = {}
  for (const r of rows) {
    const tpot = r.metrics?.tpot_mean
    if (tpot === undefined || tpot === null) continue
    ;(byCase[r.label] ||= []).push(r)
  }
  for (const label of Object.keys(byCase)) {
    const valid = byCase[label]
      .map((r) => [parseFloat(r.metrics.tpot_mean), r])
      .filter(([v]) => !isNaN(v))
    if (!valid.length) continue
    const below = valid.filter(([v]) => v < threshold)
    const best = below.length
      ? below.reduce((a, b) => (a[0] >= b[0] ? a : b))      // 低于阈值中最接近阈值
      : valid.reduce((a, b) => (a[0] <= b[0] ? a : b))        // 无低于阈值则取最小
    best[1].best = true
    best[1].best_tpot = best[0]
  }
  return rows
})

// 6 条实时曲线定义 — 3 列布局:第一列吞吐 / 第二列 TTFT / 第三列 TPOT
const metricDefs = computed(() => [
  { key: 'output_mean', label: t('metricOutputMean'), color: '#1677ff' },
  { key: 'ttft_mean', label: t('metricTtftMean'), color: '#faad14' },
  { key: 'tpot_mean', label: t('metricTpotMean'), color: '#52c41a' },
  { key: 'total_mean', label: t('metricTotalMean'), color: '#1677ff' },
  { key: 'ttft_p99', label: t('metricTtftP99'), color: '#faad14' },
  { key: 'tpot_p99', label: t('metricTpotP99'), color: '#52c41a' },
])

// 运行时长
const now = ref(Date.now())
let timer = null
watch(() => theTask.value?.status, (v) => {
  if (timer) clearInterval(timer)
  if (v === 'running') {
    now.value = Date.now()
    timer = setInterval(() => (now.value = Date.now()), 1000)
  }
}, { immediate: true })
onBeforeUnmount(() => { if (timer) clearInterval(timer) })

const elapsedText = computed(() => {
  if (!theTask.value?.started_at) return '-'
  const start = new Date(theTask.value.started_at).getTime()
  if (isNaN(start)) return '-'
  const end = theTask.value.finished_at ? new Date(theTask.value.finished_at).getTime() : now.value
  const sec = Math.max(0, Math.floor((end - start) / 1000))
  return `${Math.floor(sec / 60)}${t('elapsedMin')}${sec % 60}${t('elapsedSec')}`
})

function statusBadge(s) {
  return s === 'running' ? 'processing' : s === 'done' ? 'success' : s === 'error' ? 'error' : s === 'stopped' ? 'warning' : 'default'
}
function statusText(s) {
  const map = { pending: t('pending'), running: t('running'), done: t('done'), stopped: t('stopped'), error: t('error') }
  return map[s] || s
}
function statusClass(s) {
  if (s === 'error') return 'st-error'
  if (s === 'running') return 'st-running'
  if (s === 'done') return 'st-done'
  return ''
}
function caseConcDone(label, conc) {
  return (theTask.value?.rows || []).some((r) => r.label === label && r.concurrency === conc && (r.metrics || r.error))
}
function caseConcRunning(label, conc) {
  if (theTask.value?.status !== 'running') return false
  const pos = test.currentPos[taskId.value]
  return !!pos && pos.case === label && pos.concurrency === conc
}

async function loadTasks() {
  loading.value = true
  try { await test.loadTasks() } finally { loading.value = false }
}

async function startTask() {
  try {
    await test.startTask(taskId.value)
    message.success(t('startTest'))
  } catch (e) { message.error(e.message) }
}
async function stopTask() {
  // 进行中只能停止;停止后后端广播 stopped,store 自动清理任务 → 恢复默认
  try {
    await test.stopTask(taskId.value)
    message.info(t('stopTest'))
  } catch (e) { message.error(e.message) }
}
async function closeTask() {
  // close:中间弹框确认,确认后从后端删除任务 → 恢复默认界面,任务不留在后台,需要重新创建
  Modal.confirm({
    title: t('close'),
    content: t('closeConfirm'),
    okText: t('confirm'),
    cancelText: t('cancel'),
    okButtonProps: { danger: true },
    onOk: async () => {
      try {
        await test.deleteTask(taskId.value)
      } catch (e) { message.error(e.message) }
    },
  })
}

// 阈值就地编辑:点击变输入框,失焦保存
function editThreshold() {
  thresholdInput.value = theTask.value?.tpot_threshold_ms || 100
  thresholdEditing.value = true
}
async function saveThreshold() {
  if (!thresholdEditing.value) return
  thresholdEditing.value = false
  const val = Number(thresholdInput.value)
  if (!val || val <= 0 || val === theTask.value?.tpot_threshold_ms) return
  try {
    await test.updateThreshold(taskId.value, val)
    message.success(t('saved'))
  } catch (e) { message.error(e.message) }
}

// 控制台日志下载:文件名 任务ID_时分秒.txt
function downloadLog() {
  const lines = activeLogs.value
  if (!lines.length) { message.info(t('noData')); return }
  const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
  const d = new Date()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  const fname = `${taskId.value}_${hh}${mm}${ss}.txt`
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fname
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// 控制台滚动处理:用户在底部附近时自动滚动,向上阅读时不打扰
function onTermScroll() {
  if (!termBox.value) return
  const el = termBox.value
  userNearBottom.value = (el.scrollHeight - el.scrollTop - el.clientHeight) < 50
}
function scrollTermToBottom() {
  if (termBox.value) termBox.value.scrollTop = termBox.value.scrollHeight
}

// 自动滚动控制台(仅当用户在底部附近时)
watch(() => activeLogs.value.length, async () => {
  await nextTick()
  if (termBox.value && userNearBottom.value) scrollTermToBottom()
})

// 任务切换:加载完整快照(含 rows)+ 历史日志并滚到底(数据状态来自后台,刷新即恢复)
watch(taskId, async (id, oldId) => {
  if (!id || id === oldId) return
  userNearBottom.value = true
  await test.loadTask(id)
  await test.loadTaskLogs(id)
  await nextTick()
  scrollTermToBottom()
})

function onCreated(_taskId) {
  createModalOpen.value = false
  message.success(t('startTest'))
}

onMounted(async () => {
  await loadTasks()
  if (taskId.value) {
    userNearBottom.value = true
    await test.loadTask(taskId.value)
    await test.loadTaskLogs(taskId.value)
    await nextTick()
    scrollTermToBottom()
  }
  config.refreshStatus()
})
</script>

<style scoped>
.perf-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 20px;
}

/* 默认介绍页 (与 Accuracy 格式一致) */
.perf-intro {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  min-height: 0;
  overflow: auto;
  padding: 40px 20px;
}
.planned-card {
  max-width: 900px;
  width: 100%;
}
.features {
  margin-top: 24px;
}
.feature-card {
  text-align: center;
  border-radius: 8px;
}
.feature-icon {
  font-size: 48px;
  padding-top: 24px;
}
.result-icon {
  font-size: 72px;
  color: var(--ant-color-primary, #1677ff);
}
.perf-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 四块式详情 */
.perf-detail {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  gap: 12px;
}
.task-top-panel {
  flex-shrink: 0;
}
.panel-title-model {
  font-weight: 600;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 360px;
  display: inline-block;
  vertical-align: middle;
}
.panel-title-left {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: normal;
  min-width: 0;
}
.title-sep {
  color: var(--ant-color-border, #d9d9d9);
}
.title-spin {
  margin-right: 2px;
  color: var(--ant-color-primary, #1677ff);
}
.status-value { font-weight: 600; }
.st-running { color: var(--ant-color-primary, #1677ff); }
.st-done { color: var(--ant-color-success, #52c41a); }
.st-error { color: var(--ant-color-error, #f5222d); }
.top-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.meta-text {
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
}
.panel-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.info-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 12px;
}
.info-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.info-label {
  color: var(--ant-color-text-tertiary, #999);
}
.case-grid {
  max-height: 120px;
  overflow: auto;
}
.case-item {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  padding: 3px 0;
  border-bottom: 1px solid var(--ant-color-border, #f0f0f0);
  font-size: 12px;
}
.case-label {
  font-weight: 600;
  min-width: 60px;
}
.case-meta {
  color: var(--ant-color-text-tertiary, #999);
  font-size: 11px;
}

/* 控制台 + 右侧 */
.perf-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 12px;
  overflow: hidden;
}
.terminal-left {
  width: 420px;
  flex-shrink: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.terminal-box {
  flex: 1;
  min-height: 0;
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.5;
  overflow-y: auto;
  overflow-x: hidden;
  white-space: pre-wrap;
  word-break: break-all;
  scroll-behavior: smooth;
}
.term-line {
  min-height: 14px;
}
.right-scroll {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-right: 4px;
}
.right-card {
  flex-shrink: 0;
}
.rt-extra {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
}
.rt-threshold {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.threshold-value {
  cursor: pointer;
  padding: 0 4px;
  border-radius: 4px;
  color: var(--ant-color-primary, #1677ff);
  font-weight: 600;
}
.threshold-value:hover {
  background: var(--ant-color-fill-secondary, #f5f5f5);
}
</style>

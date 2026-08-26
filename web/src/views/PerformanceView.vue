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
              <experiment-outlined />
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
          <a-row :gutter="[24, 24]" justify="center">
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

    <!-- 有任务：三行布局 -->
    <div v-if="theTask" class="perf-detail">
      <!-- 第一行：Perf + Cases + Console (各占 1/3，等高) -->
      <div class="row-1">
        <!-- Perf 面板 -->
        <a-card size="small" class="perf-panel" :body-style="{ padding: '10px 14px', display: 'flex', flexDirection: 'column', flex: '1', minHeight: '0' }">
          <template #title>
            <div class="panel-title-left">
              <span class="title-text">Perf</span>
              <span class="title-sep">|</span>
              <span class="panel-title-model" :title="theTask.model">{{ theTask.model }}</span>
            </div>
          </template>
          <template #extra>
            <div class="panel-title-right">
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
          <!-- 内容：每项一行，两端对齐，详情值字体样式一致 -->
          <div class="panel-body">
            <div class="info-row">
              <span class="info-label">{{ t('model') }}</span>
              <span class="info-value">{{ theTask.model }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('framework') }}</span>
              <span class="info-value">{{ theTask.framework_name || theTask.framework }}</span>
            </div>
            <div class="info-row" v-if="theTask.precision">
              <span class="info-label">{{ t('precision') }}</span>
              <span class="info-value">{{ theTask.precision }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('dataset') }}</span>
              <span class="info-value">{{ datasetText }}</span>
            </div>
            <div class="info-row" v-if="theTask.concurrency_list?.length">
              <span class="info-label">{{ t('concurrency') }}</span>
              <span class="info-value">{{ theTask.concurrency_list.join(', ') }}</span>
            </div>
            <div class="info-row" v-if="theTask.request_rate && theTask.request_rate !== 'inf'">
              <span class="info-label">{{ t('requestRateLabel') }}</span>
              <span class="info-value">{{ theTask.request_rate }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('serviceStatus') }}</span>
              <span class="info-value" :style="{ color: serviceReady ? 'var(--ant-color-success, #52c41a)' : 'var(--ant-color-error, #f5222d)' }">
                {{ serviceReady ? t('online') : t('offline') }}
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('serviceUrl') }}</span>
              <span class="info-value">{{ serviceUrl || '-' }}</span>
            </div>
          </div>
          <!-- footer：右侧操作按钮 -->
          <div class="panel-footer">
            <div class="footer-actions">
              <a-button v-if="canStart" type="primary" size="small" @click="startTask">{{ t('startTest') }}</a-button>
              <a-button v-if="theTask.status === 'running'" size="small" danger @click="stopTask">{{ t('stopTest') }}</a-button>
              <a-button v-if="canClose" size="small" danger ghost @click="closeTask">{{ t('close') }}</a-button>
            </div>
          </div>
        </a-card>

        <!-- Cases 面板：显示并发 case 列表 (1K1K 等) -->
        <a-card size="small" class="cases-panel" :body-style="{ padding: '10px 14px', display: 'flex', flexDirection: 'column', flex: '1', minHeight: '0' }">
          <template #title>{{ t('casesPanelTitle') }}</template>
          <div class="cases-body">
            <div v-for="(c, i) in theTask.cases || []" :key="i" class="case-row">
              <span class="case-label">{{ c.label }}</span>
              <span class="case-meta" v-if="c.input_len">{{ c.input_len }}/{{ c.output_len }}</span>
              <span class="case-tags">
                <a-tag
                  v-for="conc in theTask.concurrency_list || []"
                  :key="conc"
                  :color="caseConcDone(c.label, conc) ? 'green' : caseConcRunning(c.label, conc) ? 'processing' : 'default'"
                  size="small"
                >{{ conc }}</a-tag>
              </span>
            </div>
            <div v-if="!theTask.cases?.length" class="empty-hint">{{ t('noData') }}</div>
          </div>
          <!-- footer：空（保持三面板等高） -->
          <div class="panel-footer empty-footer"></div>
        </a-card>

        <!-- Console 面板 (白底黑字) -->
        <a-card size="small" class="console-panel" :body-style="{ flex: '1', minHeight: '0', padding: '0', display: 'flex', flexDirection: 'column' }">
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
          <!-- footer：空（保持三面板等高） -->
          <div class="panel-footer empty-footer"></div>
        </a-card>
      </div>

      <!-- 第二行：实时数据面板 -->
      <a-card size="small" class="full-row-card">
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
          :request-rate="theTask.request_rate || 'inf'"
        />
      </a-card>

      <!-- 第三行：统计图面板 -->
      <a-card size="small" class="full-row-card">
        <template #title>{{ t('statistics') }}</template>
        <MetricsCharts :rows="theTask.rows || []" />
      </a-card>
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
  ExperimentOutlined,
  LoadingOutlined,
  PlayCircleOutlined,
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
      ? below.reduce((a, b) => (a[0] >= b[0] ? a : b))
      : valid.reduce((a, b) => (a[0] <= b[0] ? a : b))
    best[1].best = true
    best[1].best_tpot = best[0]
  }
  return rows
})

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
  try {
    await test.stopTask(taskId.value)
    message.info(t('stopTest'))
  } catch (e) { message.error(e.message) }
}
async function closeTask() {
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

function onTermScroll() {
  if (!termBox.value) return
  const el = termBox.value
  userNearBottom.value = (el.scrollHeight - el.scrollTop - el.clientHeight) < 50
}
function scrollTermToBottom() {
  if (termBox.value) termBox.value.scrollTop = termBox.value.scrollHeight
}

// 内容更新时始终滚到底,确保看到最新数据
watch(() => activeLogs.value.length, async () => {
  await nextTick()
  if (termBox.value) scrollTermToBottom()
})

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
  overflow: auto;
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
  height: 100%;
  display: flex;
  flex-direction: column;
}
.feature-card :deep(.ant-card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.feature-card :deep(.ant-card-meta-title) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.feature-card :deep(.ant-card-meta-description) {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 40px;
  line-height: 20px;
  margin-top: 4px;
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

/* 三行布局 */
.perf-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

/* 第一行：Perf + Cases + Console，各占 1/3 等高
   Perf 面板内容决定高度，Cases/Console 内容超出时滑动 */
.row-1 {
  display: flex;
  gap: 12px;
  align-items: stretch;
}
.row-1 > :deep(.ant-card) {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Perf 面板：标题左侧 "Perf | 模型名称" 采用标题字号颜色 */
.panel-title-left {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.title-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
}
.panel-title-model {
  font-size: 14px;
  font-weight: 600;
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
  display: inline-block;
  vertical-align: middle;
}
.panel-title-right {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: normal;
  min-width: 0;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.title-sep {
  color: var(--ant-color-text-secondary, #666);
  font-weight: 600;
}
.title-spin {
  margin-right: 2px;
  color: var(--ant-color-primary, #1677ff);
}
.status-value { font-weight: 600; }
.st-running { color: var(--ant-color-primary, #1677ff); }
.st-done { color: var(--ant-color-success, #52c41a); }
.st-error { color: var(--ant-color-error, #f5222d); }
.meta-text {
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
}
/* Perf 面板 body：不滚动，内容决定面板高度 */
.panel-body {
  flex: 0 1 auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  padding: 2px 0;
}
.info-label {
  color: var(--ant-color-text-tertiary, #999);
  flex-shrink: 0;
}
.info-value {
  color: var(--ant-color-text, #000);
  text-align: right;
  word-break: break-all;
  font-size: 12px;
  font-weight: 400;
}
.mono-url {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}

/* Cases 面板 */
.cases-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.case-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 3px 0;
  border-bottom: 1px solid var(--ant-color-border, #f0f0f0);
}
.case-label {
  font-weight: 600;
  min-width: 60px;
  color: var(--ant-color-text, #000);
}
.case-meta {
  color: var(--ant-color-text-tertiary, #999);
  font-size: 12px;
}
.case-tags {
  margin-left: auto;
  display: inline-flex;
  gap: 2px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.empty-hint {
  text-align: center;
  color: var(--ant-color-text-tertiary, #999);
  font-size: 12px;
  padding: 24px 0;
}

/* Footer：所有面板等高，空 footer 占位 */
.panel-footer {
  flex-shrink: 0;
  padding-top: 8px;
  border-top: 1px solid var(--ant-color-border, #f0f0f0);
  margin-top: 6px;
  min-height: 36px;
}
.empty-footer {
  border-top: 1px solid transparent;
  padding-top: 0;
  min-height: 8px;
}
.footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* Console 面板：白底黑字 */
.console-panel :deep(.ant-card-body) {
  background: #fff;
}
.terminal-box {
  flex: 1 1 0;
  min-height: 0;
  background: #ffffff;
  color: #000000;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.5;
  overflow-y: auto;
  overflow-x: hidden;
  white-space: pre-wrap;
  word-break: break-all;
  scroll-behavior: smooth;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  border: 1px solid var(--ant-color-border, #e8e8e8);
}
.term-line {
  min-height: 14px;
}

/* 第二行 / 第三行：整行卡片 */
.full-row-card {
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

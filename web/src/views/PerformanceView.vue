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
            <a-space size="middle">
              <a-button type="primary" size="large" @click="goCreate('concurrency')">
                <template #icon><play-circle-outlined /></template>
                {{ t('concurrencyMode') }}
              </a-button>
              <a-button type="primary" size="large" ghost @click="goCreate('threshold')">
                <template #icon><dashboard-outlined /></template>
                {{ t('thresholdMode') }}
              </a-button>
            </a-space>
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
            <div class="info-row">
              <span class="info-label">{{ t('modeLabel') }}</span>
              <span class="info-value">{{ theTask.mode === 'threshold' ? t('thresholdMode') : t('concurrencyMode') }}</span>
            </div>
            <div class="info-row" v-if="theTask.precision">
              <span class="info-label">{{ t('precision') }}</span>
              <span class="info-value">{{ theTask.precision }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('dataset') }}</span>
              <span class="info-value">{{ datasetText }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ t('concurrencyCol') }}</span>
              <span class="info-value">{{ concurrencyDisplay }}</span>
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
          <template #extra>
            <span class="cases-mode">{{ theTask.mode === 'threshold' ? t('thresholdMode') : t('concurrencyMode') }}</span>
          </template>
          <div class="cases-body">
            <!-- 阈值模式：显示任务阈值条件（TTOT mean(ms) ≤ x ms；Output token throughput ≤ y tok/s；仅文字，不可编辑，并发模式不显示） -->
            <div v-if="theTask.mode === 'threshold'" class="threshold-conds">
              <div class="info-row">
                <span class="info-label">{{ t('tpotCondLabel') }} ≤</span>
                <span class="info-value">{{ theTask.tpot_threshold_ms || '-' }}ms</span>
              </div>
              <div class="info-row" v-if="theTask.output_throughput_threshold">
                <span class="info-label">{{ t('outputCondLabel') }} ≤</span>
                <span class="info-value">{{ theTask.output_throughput_threshold }} tok/s</span>
              </div>
            </div>
            <div v-for="(c, i) in theTask.cases || []" :key="c.case_id || c.label || i" class="case-row">
              <span class="case-label">{{ c.label }}</span>
              <a-tag v-if="c.case_id" size="small" class="case-gid">g{{ c.case_id }}</a-tag>
              <span class="case-meta" v-if="c.input_len">{{ c.input_len }}/{{ c.output_len }}</span>
              <span class="case-tags">
                <!-- 阈值模式：已执行/执行中的 case 显示完整请求数列表（当前测试的标蓝、已完成标绿），未执行显示 Pending -->
                <template v-if="theTask.mode === 'threshold'">
                  <template v-if="caseTestedTags(c).length">
                    <a-tag
                      v-for="tt in caseTestedTags(c)"
                      :key="tt.conc"
                      :color="tt.running ? 'processing' : 'green'"
                      size="small"
                    >{{ tt.conc }}</a-tag>
                  </template>
                  <a-tag v-else color="default" size="small">{{ t('pending') }}</a-tag>
                </template>
                <!-- 并发模式：显示全部请求数 -->
                <template v-else>
                  <a-tag
                    v-for="conc in sortedConcurrency"
                    :key="conc"
                    :color="caseConcColor(c, conc)"
                    size="small"
                  >{{ conc }}</a-tag>
                </template>
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
                v-if="tpotThresholdEditing"
                v-model:value="tpotThresholdInput"
                size="small"
                :step="10"
                :min="0"
                :precision="0"
                style="width: 90px"
                @blur="saveTpotThreshold"
                @press-enter="saveTpotThreshold"
              />
              <span v-else class="threshold-value" @click="editTpotThreshold">
                {{ effectiveTpotThreshold }}ms
              </span>
            </span>
            <span class="rt-threshold">
              <span class="info-label">{{ t('outputTokenThresholdLabel') }}</span>
              <a-input-number
                v-if="outputThresholdEditing"
                v-model:value="outputThresholdInput"
                size="small"
                :step="50"
                :min="0"
                :precision="0"
                style="width: 90px"
                @blur="saveOutputThreshold"
                @press-enter="saveOutputThreshold"
              />
              <span v-else class="threshold-value" @click="editOutputThreshold">
                {{ effectiveOutputThreshold }} tok/s
              </span>
            </span>
          </div>
        </template>
        <MetricsTable
          :rows="annotatedRows"
          :threshold="theTask.tpot_threshold_ms"
          :request-rate="theTask.request_rate || 'inf'"
          :output-threshold="effectiveOutputThreshold"
          group-by="caseKey"
          :task-id="taskId"
          exportable
        />
      </a-card>

      <!-- 第三行：统计图面板 -->
      <a-card size="small" class="full-row-card">
        <template #title>{{ t('statistics') }}</template>
        <MetricsCharts :rows="theTask.rows || []" />
      </a-card>
    </div>

  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  DashboardOutlined,
  DownloadOutlined,
  ExperimentOutlined,
  LoadingOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons-vue'
import { useRouter } from 'vue-router'
import { useTestStore } from '@/store/test'
import { useConfigStore } from '@/store/config'
import { t } from '@/i18n'
import MetricsTable from '@/components/MetricsTable.vue'
import MetricsCharts from '@/components/MetricsCharts.vue'

const test = useTestStore()
const config = useConfigStore()
const router = useRouter()
const loading = ref(false)
const features = computed(() => [
  { icon: '⚡', title: t('featMultiFramework'), desc: t('featMultiFrameworkDesc') },
  { icon: '🎯', title: t('featMultiCombination'), desc: t('featMultiCombinationDesc') },
  { icon: '📈', title: t('featRealtimeData'), desc: t('featRealtimeDataDesc') },
])
const termBox = ref(null)
const userNearBottom = ref(true)

// 本地面板阈值（仅对表格标记生效，不写回任务，与任务阈值区分）
// TPOT Threshold 默认 100 / Output Token Threshold 默认 0：全为 0 时不处理标记（无 Best）；任一非 0 即处理，非 0 的条件均需满足；值必须为整数
const tpotThresholdEditing = ref(false)
const tpotThresholdInput = ref(null)
const tpotThreshold = ref(null) // 本地覆盖值；null 表示使用默认 100
const effectiveTpotThreshold = computed(() => {
  if (tpotThreshold.value != null) return tpotThreshold.value
  return 100
})

const outputThresholdEditing = ref(false)
const outputThresholdInput = ref(null)
const outputThreshold = ref(null) // 本地覆盖值；null 表示使用默认 0
const effectiveOutputThreshold = computed(() => {
  if (outputThreshold.value != null) return outputThreshold.value
  return 0
})

const theTask = computed(() => test.theTask)
const taskId = computed(() => theTask.value?.task_id || null)
const activeLogs = computed(() => (taskId.value ? test.logLines[taskId.value] || [] : []))
const serviceReady = computed(() => config.status?.inference === 'ready')
const serviceUrl = computed(() => config.apiBase || '')

// 进度计数：
//   并发模式：case 数 × 并发档位数（并发点是预知的）
//   阈值模式：按 Cases 计数——每个 case 算 1 个进度单位，总共几个 case 就显示几个
//   （并发点由阈值策略动态探测，不再作为进度分母，避免出现 32/36 这类不稳定/不对齐的数值）
const totalCount = computed(() => {
  if (!theTask.value) return 0
  if (theTask.value.mode === 'threshold') {
    return theTask.value.cases?.length || 0
  }
  return (theTask.value.cases?.length || 0) * (theTask.value.concurrency_list?.length || 0)
})
const doneCount = computed(() => {
  if (!theTask.value) return 0
  const rows = theTask.value.rows || []
  if (theTask.value.mode === 'threshold') {
    // 一个 case 出现任意一条结果（成功或失败）即视为该 case 已完成
    const done = new Set()
    for (const r of rows) {
      if (!(r.metrics || r.error)) continue
      done.add(r.case_id !== undefined && r.case_id !== null ? `g${r.case_id}` : (r.label || r.case || '-'))
    }
    return done.size
  }
  return rows.filter((r) => r.metrics || r.error).length
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

// 并发数量从小到大排列（展示用，非执行顺序）
const sortedConcurrency = computed(() => {
  return [...(theTask.value?.concurrency_list || [])].sort((a, b) => Number(a) - Number(b))
})

// 面板 Concurrency 行：inf → Inf；follow → 同 Requests(升序)；其他 → 请求率值
const concurrencyDisplay = computed(() => {
  const rr = theTask.value?.request_rate
  if (!rr || rr === 'inf') return 'Inf'
  if (rr === 'follow') return sortedConcurrency.value.join(', ') || '-'
  return String(rr)
})

// 数据集文案
const datasetText = computed(() => {
  const ds = theTask.value?.dataset || {}
  const typeMap = { random: t('randomDataset'), sharegpt: 'ShareGPT', custom: t('custom'), file: t('fileDataset') }
  const type = typeMap[ds.type] || ds.type || '-'
  const pairs = theTask.value?.cases?.map((c) => (c.input_len ? `${c.input_len}/${c.output_len}` : c.label)).join(', ')
  return pairs ? `${type}(${pairs})` : type
})

// 表格数据：按 case(label) 分组，组内按请求数量（并发）从小到大排列
// Best/BestPerf 高亮策略一致：每组内在满足阈值条件（阈值 ≤ 0 视为未配置、不参与该条件）的行中，标记并发最大的一行（有且仅有一个）；全部阈值为 0 时不处理、无标签
const annotatedRows = computed(() => {
  const rows = (theTask.value?.rows || []).map((r) => ({ ...r }))
  if (!rows.length) return rows
  // 清除后端/旧逻辑残留的标记
  for (const r of rows) {
    r.best = false
    r.bestPerf = false
  }

  const condPass = (v, thr) => {
    if (!(thr > 0)) return true
    if (v === undefined || v === null) return false
    const n = Number(v)
    return !isNaN(n) && n <= thr
  }

  // 在 groupRows 中，满足 tpotThr/outThr 条件的行里取并发最大的一行标记；两阈值全为 0 时不处理
  const markBestRow = (groupRows, tpotThr, outThr, flag) => {
    if (!(tpotThr > 0) && !(outThr > 0)) return
    let bestRow = null
    let bestConc = -Infinity
    for (const r of groupRows) {
      if (!condPass(r.metrics?.tpot_mean, tpotThr)) continue
      if (!condPass(r.metrics?.output_mean, outThr)) continue
      const c = Number(r.concurrency)
      if (c > bestConc) {
        bestConc = c
        bestRow = r
      }
    }
    if (bestRow) bestRow[flag] = true
  }

  // 按 case 分组（case_id 优先，相同 label 的多组独立分组）；每组内按并发升序，并单独执行阈值高亮
  const groupMap = new Map()
  for (const r of rows) {
    r.caseKey = rowCaseKey(r)
    const key = r.caseKey
    if (!groupMap.has(key)) groupMap.set(key, [])
    groupMap.get(key).push(r)
  }
  const grouped = []
  for (const groupRows of groupMap.values()) {
    groupRows.sort((a, b) => Number(a.concurrency) - Number(b.concurrency))
    // 任务阈值 → BestPerf（仅阈值模式，同样策略）
    if (theTask.value?.mode === 'threshold') {
      markBestRow(
        groupRows,
        Number(theTask.value?.tpot_threshold_ms) || 0,
        Number(theTask.value?.output_throughput_threshold) || 0,
        'bestPerf'
      )
    }
    // 本地面板阈值 → Best
    markBestRow(groupRows, effectiveTpotThreshold.value, effectiveOutputThreshold.value, 'best')
    grouped.push(...groupRows)
  }
  return grouped
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
// 唯一组标识：有 case_id 用 case_id，旧数据回退 label（相同条件多组也能区分）
function caseKeyOf(caseObj) {
  return caseObj && caseObj.case_id !== undefined && caseObj.case_id !== null
    ? `${caseObj.label}#g${caseObj.case_id}`
    : (caseObj?.label || '-')
}
function rowCaseKey(r) {
  return r.case_id !== undefined && r.case_id !== null ? `${r.label}#g${r.case_id}` : (r.label || r.case || '-')
}
function caseConcDone(caseObj, conc) {
  const key = caseKeyOf(caseObj)
  return (theTask.value?.rows || []).some((r) => rowCaseKey(r) === key && r.concurrency === conc && (r.metrics || r.error))
}
function caseConcRunning(caseObj, conc) {
  if (theTask.value?.status !== 'running') return false
  const pos = test.currentPos[taskId.value]
  return !!pos && rowCaseKey({ label: pos.case, case_id: pos.case_id }) === caseKeyOf(caseObj) && pos.concurrency === conc
}
function caseConcColor(caseObj, conc) {
  if (caseConcDone(caseObj, conc)) return 'green'
  if (caseConcRunning(caseObj, conc)) return 'processing'
  return 'default'
}

// 阈值模式：case 已测试过的请求数列表（含当前正在测试的，当前测试标 running），按请求数升序；未开始执行返回空数组
function caseTestedTags(caseObj) {
  const key = caseKeyOf(caseObj)
  const set = new Set()
  for (const r of theTask.value?.rows || []) {
    if (rowCaseKey(r) === key && (r.metrics || r.error)) set.add(Number(r.concurrency))
  }
  let runningConc = null
  if (theTask.value?.status === 'running') {
    const pos = test.currentPos[taskId.value]
    if (pos && rowCaseKey({ label: pos.case, case_id: pos.case_id }) === key) {
      runningConc = Number(pos.concurrency)
      set.add(runningConc)
    }
  }
  const list = [...set].map((conc) => ({ conc, running: conc === runningConc }))
  list.sort((a, b) => a.conc - b.conc)
  return list
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

function editTpotThreshold() {
  tpotThresholdInput.value = effectiveTpotThreshold.value
  tpotThresholdEditing.value = true
}
function saveTpotThreshold() {
  if (!tpotThresholdEditing.value) return
  tpotThresholdEditing.value = false
  const val = Math.round(Number(tpotThresholdInput.value))
  if (isNaN(val) || val < 0) return
  tpotThreshold.value = val
}

function editOutputThreshold() {
  outputThresholdInput.value = effectiveOutputThreshold.value
  outputThresholdEditing.value = true
}
function saveOutputThreshold() {
  if (!outputThresholdEditing.value) return
  outputThresholdEditing.value = false
  const val = Math.round(Number(outputThresholdInput.value))
  if (isNaN(val) || val < 0) return
  outputThreshold.value = val
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
  tpotThreshold.value = null
  outputThreshold.value = null
  await test.loadTask(id)
  await test.loadTaskLogs(id)
  await nextTick()
  scrollTermToBottom()
})

function goCreate(mode) {
  router.push({ path: '/performance/create', query: { mode } })
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

/* Perf 面板：标题左侧 "Perf" 采用标题字号颜色 */
.panel-title-left {
  display: inline-flex;
  align-items: center;
  min-width: 0;
}
.title-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
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
.cases-mode {
  color: var(--ant-color-success, #52c41a);
  font-size: 12px;
  font-weight: 600;
}
.threshold-conds {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 0 8px;
  margin-bottom: 4px;
  border-bottom: 1px dashed var(--ant-color-border, #f0f0f0);
}
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
.case-gid {
  font-size: 11px;
  line-height: 16px;
  color: #8c8c8c;
  border-color: #d9d9d9;
  margin: 0;
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

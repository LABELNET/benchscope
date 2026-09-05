<template>
  <!-- 第二行：Profile Progress(1/3) + Real-Time Metrics(2/3)，antd 对齐，等高 -->
  <div class="row-2">
    <!-- Profile Progress 面板 -->
    <a-card ref="profilePanelRef" size="small" class="profile-panel">
      <template #title>{{ t('profileProgress') }}</template>
      <template #extra><span class="rt-case-text">{{ rtCaseText }}</span></template>
      <!-- 状态卡片 -->
      <div class="pp-status" :class="`pp-${statusKey}`">
        <span class="pp-status-label">{{ t('profCurrentStatus') }}</span>
        <span class="pp-status-value">{{ statusText }}</span>
        <warning-outlined v-if="statusKey === 'error'" class="pp-err-icon" />
      </div>
      <!-- 双进度条 -->
      <div class="pp-bars">
        <div class="pp-bar-row">
          <span class="pp-bar-label">{{ t('profProfiling') }}</span>
          <a-progress :percent="profPct" :show-info="false" :size="['100%', 8]" :stroke-color="'#1677ff'" class="pp-progress" />
          <span class="pp-bar-num">{{ profPct }}%</span>
        </div>
        <div class="pp-bar-row">
          <span class="pp-bar-label">{{ t('profRecords') }}</span>
          <a-progress :percent="recPct" :show-info="false" :size="['100%', 8]" :stroke-color="'#52c41a'" class="pp-progress" />
          <span class="pp-bar-num">{{ recPct }}%</span>
        </div>
      </div>
      <!-- 每个指标一行 -->
      <div class="pp-metrics">
        <div class="pp-metric"><span class="pp-mk">{{ t('profProgress') }}</span><span class="pp-mv">{{ progressText }}</span></div>
        <div class="pp-metric"><span class="pp-mk">{{ t('profErrors') }}</span><span class="pp-mv" :class="{ 'pp-err-val': errorsHaveErr }">{{ errorsText }}</span></div>
        <div class="pp-metric"><span class="pp-mk">{{ t('profReqRate') }}</span><span class="pp-mv">{{ reqRateText }}</span></div>
        <div class="pp-metric"><span class="pp-mk">{{ t('profProcRate') }}</span><span class="pp-mv">{{ procRateText }}</span></div>
        <div class="pp-metric"><span class="pp-mk">{{ t('profElapsed') }}</span><span class="pp-mv">{{ elapsedClock }}</span></div>
        <div class="pp-metric"><span class="pp-mk">{{ t('profEta') }}</span><span class="pp-mv">{{ etaText }}</span></div>
      </div>
    </a-card>

    <!-- Real-Time Metrics 面板（高度与 Profile Progress 保持一致） -->
    <a-card size="small" class="rtm-panel" :style="rtmCardStyle">
      <template #title>{{ t('realTimeMetrics') }}</template>
      <template #extra><span class="rt-case-text">{{ rtCaseText }}</span></template>
      <!-- 单表 + 单表头（Metric 列右对齐；表头与 Metric 列默认保留，无数据为空，放大填满面板） -->
      <div class="rtm-grid rtm-head">
        <span class="ta-r">{{ t('liveMetric') }}</span><span class="ta-r">avg</span><span class="ta-r">min</span><span class="ta-r">max</span><span class="ta-r">p99</span><span class="ta-r">p90</span><span class="ta-r">p50</span><span class="ta-r">std</span>
      </div>
      <div
        v-for="r in liveMetrics"
        :key="r.key"
        class="rtm-grid"
        :title="r.n ? r.n + ' ' + t('liveSamples') : ''"
      >
        <span class="ta-r rtm-name">{{ r.label }}</span>
        <span v-for="(c, i) in r.cols" :key="i" class="ta-r rtm-cell" :class="c.c">{{ c.t }}</span>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { WarningOutlined } from '@ant-design/icons-vue'
import { t } from '@/i18n'

// 一个“请求”的实时快照：{ case, case_id, concurrency, label, stats }
const props = defineProps({
  snapshot: { type: Object, default: null },
  // 当前是否正在执行该请求（状态显示 Profiling）
  live: { type: Boolean, default: false },
})

const stats = computed(() => props.snapshot?.stats || null)

// header 右侧 case-请求数
const rtCaseText = computed(() => {
  const s = props.snapshot
  if (!s) return '-'
  const cid = s.case_id !== undefined && s.case_id !== null ? `#g${s.case_id}` : ''
  return `${s.case || s.label || '-'}${cid} · ${s.concurrency ?? '-'}${t('reqCountSuffix')}`
})

// 状态：live(执行中)=Profiling；否则 Completed
const statusKey = computed(() => (props.live ? 'profiling' : 'completed'))
const statusText = computed(() => (statusKey.value === 'profiling' ? t('profProfiling') : t('profCompleted')))

// 双进度条（单个请求口径：completed/total）
const pct = computed(() => {
  const s = stats.value
  if (!s || !s.total) return 0
  return Math.round((s.completed / s.total) * 100)
})
const profPct = computed(() => pct.value)
const recPct = computed(() => pct.value)

// 文本指标
const fmtInt = (n) => (isFinite(Number(n)) ? Math.round(Number(n)).toLocaleString('en-US') : '0')
const fmtDec = (n, d = 1) => (isFinite(Number(n)) ? Number(n).toFixed(d) : '-')

const progressText = computed(() => {
  const s = stats.value
  if (s && s.total) return `${fmtInt(s.completed)} / ${fmtInt(s.total)} requests (${(s.completed / s.total) * 100}%)`
  return '-'
})
const errorsText = computed(() => {
  const s = stats.value
  if (s) {
    const p = s.completed && s.errors != null ? (s.errors / s.completed) * 100 : 0
    return `${fmtInt(s.errors)} / ${fmtInt(s.completed)} (${p.toFixed(1)}%)`
  }
  return '-'
})
const errorsHaveErr = computed(() => !!stats.value?.errors)
const reqRateText = computed(() => {
  const s = stats.value
  return s ? `${fmtDec(s.req_per_s)} requests/s` : '-'
})
const procRateText = computed(() => {
  const s = stats.value
  if (s && s.t > 0) return `${fmtDec(s.completed / s.t)} records/s`
  return '-'
})
function fmtClock(sec) {
  if (!isFinite(sec) || sec < 0) return '0s'
  const s = Math.round(sec)
  const m = Math.floor(s / 60)
  const r = s % 60
  if (m >= 60) return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m`
  return `${m}m ${String(r).padStart(2, '0')}s`
}
const elapsedClock = computed(() => fmtClock(stats.value?.t || 0))
const etaText = computed(() => {
  const s = stats.value
  if (!s || s.total <= 0 || s.completed <= 0) return '-'
  if (s.completed >= s.total) return '0s'
  const remain = (s.t / s.completed) * (s.total - s.completed)
  if (remain < 120) return `${remain.toFixed(1)}s`
  return fmtClock(remain)
})

// ===== Real-Time Metrics 单表（11 行，单元格带类型） =====
const ORDER = ['avg', 'min', 'max', 'p99', 'p90', 'p50', 'std']
const dashCell = () => ({ t: '-', c: 'rtm-dash' })
const naCell = () => ({ t: 'N/A', c: 'rtm-na' })
const numCell = (v, convert) => (v === undefined || v === null || isNaN(Number(v))
  ? dashCell()
  : { t: fmtMrk(v, convert), c: 'rtm-fill' })
const naCellsN = (n) => Array.from({ length: n }, () => naCell())
const fmtMrk = (v) => {
  const x = Number(v)
  return (Number.isInteger(x) ? x : +x.toFixed(2)).toLocaleString('en-US')
}
const LIVE_METRIC_DEFS = [
  { key: 'TTFT', label: 'TTFT (ms)', src: 'TTFT', convert: true },
  { key: 'TTST', label: 'TTST (ms)', src: 'TTST', convert: true },
  { key: 'TPOT', label: 'TPOT (ms)', src: 'TPOT', convert: true },
  { key: 'ReqLatency', label: 'Req Latency (ms)', src: 'ReqLatency', convert: true },
  { key: 'ITL', label: 'ITL (ms)', src: 'ITL', convert: true },
  { key: 'OutputTPSUser', label: 'Output TPS/User', src: 'OutputTPSPerUser', convert: false },
  { key: 'OSL', label: 'OSL (tokens)', src: 'OSL', convert: true },
  { key: 'ISL', label: 'ISL (tokens)', src: 'ISL', convert: true },
  { key: 'OutputTPS', label: 'Output TPS', src: 'OutputTPS', convert: false },
  { key: 'ReqSec', label: 'Req/sec', src: 'ReqSec', convert: false },
  { key: 'Requests', label: 'Requests', src: '__completed__', convert: false },
]
const liveMetrics = computed(() => {
  const s = stats.value
  const m = (s && s.metrics) || {}
  return LIVE_METRIC_DEFS.map((def) => {
    if (def.src === '__completed__') {
      return { key: def.key, label: def.label, n: 0, cols: [numCell(s ? s.completed : null, false), ...naCellsN(6)] }
    }
    const ms = m[def.src] || {}
    return { key: def.key, label: def.label, n: ms.n || 0, cols: ORDER.map((k) => numCell(ms[k], def.convert)) }
  })
})

// 等高：测量 Profile 高度赋给 Real-Time Metrics
const profilePanelRef = ref(null)
const profileRowHeight = ref(0)
const rtmCardStyle = computed(() => (profileRowHeight.value ? { height: `${profileRowHeight.value}px` } : {}))
function measureProfileRow() {
  const el = profilePanelRef.value?.$el || profilePanelRef.value
  if (el && el.scrollHeight) profileRowHeight.value = el.scrollHeight
}
let rowObserver = null
onMounted(() => {
  measureProfileRow()
  const el = profilePanelRef.value?.$el || profilePanelRef.value
  if (el && typeof ResizeObserver !== 'undefined') {
    rowObserver = new ResizeObserver(() => measureProfileRow())
    rowObserver.observe(el)
  }
})
watch(() => props.snapshot, async () => {
  await nextTick()
  measureProfileRow()
})
onBeforeUnmount(() => {
  if (rowObserver) rowObserver.disconnect()
})
</script>

<style scoped>
.row-2 {
  display: flex;
  gap: 12px;
  align-items: stretch;
  min-width: 0;
}
.row-2 .profile-panel,
.row-2 .rtm-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.row-2 .profile-panel {
  flex: 0 0 36%;
  width: 36%;
}
.row-2 .rtm-panel {
  flex: 1 1 0;
}
.row-2 :deep(.ant-card-head) { padding: 0 12px; }
.row-2 :deep(.ant-card-body) {
  padding: 10px 12px;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.row-2 .profile-panel :deep(.ant-card-body) { overflow: hidden; }
.row-2 .rtm-panel :deep(.ant-card-body) { overflow: hidden; }
/* 表格行纵向拉伸，放大填满面板 */
.row-2 .rtm-panel .rtm-grid { flex: 1; }

.rt-case-text { font-size: 11px; color: var(--ant-color-text-tertiary, #999); }

/* Profile Progress */
.pp-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid var(--ant-color-border, #e8e8e8);
  margin-bottom: 10px;
  font-size: 12px;
}
.pp-status.pp-profiling { border-color: var(--ant-color-primary, #1677ff); background: var(--ant-color-primary-bg, #e6f4ff); }
.pp-status.pp-completed { border-color: var(--ant-color-success, #52c41a); background: #f6ffed; }
.pp-status.pp-error { border-color: var(--ant-color-error, #f5222d); background: #fff2f0; }
.pp-status-label { color: var(--ant-color-text-secondary, #666); }
.pp-status-value { font-weight: 600; color: var(--ant-color-text, #000); }
.pp-err-icon { margin-left: auto; color: var(--ant-color-error, #f5222d); font-size: 14px; }
.pp-bars { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
.pp-bar-row { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.pp-bar-label { width: 82px; flex-shrink: 0; color: var(--ant-color-text-secondary, #666); }
.pp-bar-row :deep(.ant-progress) { flex: 1; }
.pp-bar-num { width: 34px; flex-shrink: 0; text-align: right; color: var(--ant-color-text, #000); }
.pp-metrics { display: flex; flex-direction: column; }
.pp-metric {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  padding: 5px 2px;
  border-bottom: 1px solid var(--ant-color-border-secondary, #f0f0f0);
  font-size: 12px;
}
.pp-metrics .pp-metric:last-child { border-bottom: none; }
.pp-mk { color: var(--ant-color-text-secondary, #666); flex-shrink: 0; }
.pp-mv { color: var(--ant-color-text, #000); text-align: right; word-break: break-all; }
.pp-mv.pp-err-val { color: var(--ant-color-error, #f5222d); font-weight: 600; }

/* Real-Time Metrics 表 */
.rtm-grid {
  display: grid;
  grid-template-columns: 1.6fr repeat(7, 1fr);
  padding: 1px 6px;
  font-size: 10px;
  line-height: 1.25;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  align-items: center;
  border-bottom: 1px solid var(--ant-color-border-secondary, #f0f0f0);
}
.rtm-grid.rtm-head { background: var(--ant-color-fill-secondary, #fafafa); font-weight: 600; border-bottom: 1px solid var(--ant-color-border, #e8e8e8); }
.ta-r { text-align: right; }
.rtm-name { font-weight: 500; }
.rtm-cell { font-weight: 600; }
.rtm-cell.rtm-fill { color: #1677ff; }
.rtm-cell.rtm-dash { color: #bfbfbf; font-weight: 400; }
.rtm-cell.rtm-na { color: #595959; font-weight: 400; }
</style>

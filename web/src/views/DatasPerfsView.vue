<template>
  <div class="perfs-page">
    <!-- 左侧固定面板：任务记录（任务ID和状态，时间倒序） -->
    <div class="record-panel">
      <div class="record-panel-title">
        <span>{{ t('records') }}</span>
        <div class="title-actions">
          <a-tooltip :title="t('import')">
            <a-button size="small" type="text" class="icon-btn" @click="openImport">
              <template #icon><upload-outlined /></template>
            </a-button>
          </a-tooltip>
          <a-tooltip :title="t('refresh')">
            <a-button size="small" type="text" class="icon-btn" @click="loadRuns">
              <template #icon><reload-outlined /></template>
            </a-button>
          </a-tooltip>
        </div>
      </div>
      <div class="record-list">
        <a-spin :spinning="loadingList" :tip="t('loading')">
          <div
            v-for="r in runs"
            :key="r.run_id"
            class="record-item"
            :class="{ active: current && current.run_id === r.run_id }"
            @click="selectRun(r)"
          >
            <div class="record-head">
              <span class="record-id" :title="r.run_id">{{ shortId(r.run_id) }}</span>
              <span v-if="r.meta?.framework" class="record-framework" :title="r.meta.framework">{{ r.meta.framework }}</span>
              <span class="record-status" :class="statusClass(r.meta?.status)">{{ statusText(r.meta?.status) }}</span>
            </div>
            <div class="record-meta">
              <span class="record-model" :title="r.meta?.model">{{ r.meta?.model || '-' }}</span>
              <span class="record-time">{{ fmtTime(r.meta?.started_at) }}</span>
            </div>
          </div>
          <a-empty v-if="!loadingList && !runs.length" :description="t('noData')" class="record-empty" />
        </a-spin>
      </div>
    </div>

    <!-- 右侧滑动页面：任务详情 -->
    <div class="detail-panel">
      <!-- 默认提示请选择任务 -->
      <div v-if="!current" class="select-hint">
        <a-empty :description="t('selectRun')" />
      </div>

      <div v-else ref="detailRef" class="detail-scroll">
        <!-- 第1行：header 左侧任务ID + 右侧操作按钮（无边框）；内容区 状态/模型/开始/结束 -->
        <a-card size="small" class="row-1" :body-style="{ padding: '12px 16px' }">
          <template #title>
            <div class="row1-header">
              <span class="run-title" :title="current.run_id">{{ current.run_id }}</span>
              <div class="row1-actions">
                <a-button size="small" type="text" danger :disabled="!!busy" @click="onDelete">
                  <template #icon><delete-outlined /></template>
                  {{ t('delete') }}
                </a-button>
                <a-button size="small" type="text" :loading="busy === 'backup'" :disabled="busy === 'share'" @click="onBackup">
                  <template #icon><download-outlined /></template>
                  {{ t('backup') }}
                </a-button>
                <a-button size="small" type="text" :loading="busy === 'share'" :disabled="busy === 'backup'" @click="onShare">
                  <template #icon><share-alt-outlined /></template>
                  {{ t('share') }}
                </a-button>
              </div>
            </div>
          </template>
          <div class="row1-desc">
            <span class="desc-item">
              <span class="desc-label">{{ t('taskStatus') }}</span>
              <span class="record-status" :class="statusClass(current.run?.status)">{{ statusText(current.run?.status) }}</span>
            </span>
            <span class="desc-item">
              <span class="desc-label">{{ t('model') }}</span>
              <span class="desc-value">{{ current.run?.model || '-' }}</span>
            </span>
            <span class="desc-item">
              <span class="desc-label">{{ t('startedAt') }}</span>
              <span class="desc-value">{{ fmtTime(current.run?.started_at) }}</span>
            </span>
            <span class="desc-item">
              <span class="desc-label">{{ t('finishedAt') }}</span>
              <span class="desc-value">{{ fmtTime(current.run?.finished_at) }}</span>
            </span>
          </div>
        </a-card>

        <!-- 第2行：3 个面板各 1/3，高度 = Perf Info 高度（参考 Performance 第一行实现），内容超出滚动 -->
        <div class="row-2">
          <!-- Perf 信息 -->
          <a-card size="small" class="half-card" ref="perfPanelRef">
            <template #title>{{ t('perfInfo') }}</template>
            <div class="info-body">
              <div class="info-row">
                <span class="info-label">{{ t('model') }}</span>
                <span class="info-value">{{ current.run?.model || '-' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">{{ t('framework') }}</span>
                <span class="info-value">{{ current.run?.framework_name || current.run?.framework || '-' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">{{ t('modeLabel') }}</span>
                <span class="info-value">{{ current.run?.mode === 'threshold' ? t('thresholdMode') : t('concurrencyMode') }}</span>
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
                <span class="info-label">{{ t('requests') }}</span>
                <span class="info-value">{{ requestDisplay }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">{{ t('createdAt') }}</span>
                <span class="info-value">{{ fmtTime(current.run?.created_at) }}</span>
              </div>
            </div>
            <div class="panel-footer"></div>
          </a-card>

          <!-- Cases 信息：并发模式显示 case groups 列表；阈值模式显示阈值信息 + case groups 列表 -->
          <a-card size="small" class="half-card" :style="sideCardStyle">
            <template #title>{{ t('casesInfo') }}</template>
            <div class="info-body">
              <div class="case-groups">
                <div v-for="cg in caseGroupRows" :key="cg.key" class="case-group-item">
                  <span class="case-label" :title="cg.label">{{ cg.label }}</span>
                  <span class="case-gid" v-if="cg.case_id !== undefined && cg.case_id !== null">g{{ cg.case_id }}</span>
                  <span class="case-meta" v-if="cg.inputLen">{{ cg.inputLen }}/{{ cg.outputLen }}</span>
                  <span v-if="caseThresholdText(cg)" class="case-threshold" :title="caseThresholdText(cg)">{{ caseThresholdText(cg) }}</span>
                  <span class="case-req" :title="cg.reqsText">{{ cg.reqsText }}</span>
                </div>
                <div v-if="!caseGroupRows.length" class="empty-hint">{{ t('noData') }}</div>
              </div>
            </div>
            <div class="panel-footer"></div>
          </a-card>

          <!-- Logs 信息：run_dir 文本+复制；summary 点击下载；日志文件表格 -->
          <a-card size="small" class="half-card" :style="sideCardStyle">
            <template #title>{{ t('logsInfo') }}</template>
            <div class="info-body logs-body">
              <div class="run-dir-row">
                <span class="info-label">{{ t('runDir') }}</span>
                <span class="run-dir-text" :title="current.dir">{{ current.dir }}</span>
                <a-tooltip :title="t('copyRunDir')">
                  <copy-outlined class="copy-icon" @click="copyRunDir" />
                </a-tooltip>
              </div>
              <div class="summary-row">
                <span class="info-label">{{ t('summary') }}</span>
                <span class="summary-name" :title="summaryName">{{ summaryName }}</span>
                <a-tooltip :title="t('download')">
                  <a-button size="small" type="text" class="icon-btn" @click="downloadSummary">
                    <template #icon><download-outlined /></template>
                  </a-button>
                </a-tooltip>
              </div>
              <div class="log-files">
                <div class="log-file-head">
                  <span>{{ t('logFiles') }}</span>
                </div>
                <div v-for="f in current.files || []" :key="f.name" class="log-file-item">
                  <span class="log-file-name" :title="f.name">{{ f.name }}</span>
                  <span class="log-file-size">{{ fmtSize(f.size) }}</span>
                  <a-tooltip :title="t('preview')">
                    <a-button size="small" type="text" class="icon-btn" @click="previewLog(f.name)">
                      <template #icon><eye-outlined /></template>
                    </a-button>
                  </a-tooltip>
                  <a-tooltip :title="t('download')">
                    <a-button size="small" type="text" class="icon-btn" @click="downloadFile(f.name)">
                      <template #icon><download-outlined /></template>
                    </a-button>
                  </a-tooltip>
                </div>
                <div v-if="!(current.files || []).length" class="empty-hint">{{ t('noData') }}</div>
              </div>
            </div>
            <div class="panel-footer"></div>
          </a-card>
        </div>

        <!-- 第3行：数据面板，按 cases 分组分 tab；header 右侧 默认/Mean/Median/P99 -->
        <a-card size="small" class="row-3">
          <template #title>
            <div class="row3-header">
              <span class="row3-title">{{ t('perfDatas') }}</span>
              <div class="row3-actions">
                <a-button
                  v-for="m in dataModes"
                  :key="m.key"
                  size="small"
                  type="text"
                  class="panel-head-btn"
                  :class="{ 'is-on': dataMode === m.key }"
                  @click="dataMode = m.key"
                >
                  {{ m.label }}
                </a-button>
              </div>
            </div>
          </template>
          <RunDataPanel
            v-model:mode="dataMode"
            :rows="annotatedRows"
            :threshold="current.run?.tpot_threshold_ms || null"
            :request-rate="current.run?.request_rate || 'inf'"
            :group-thresholds="groupThresholdTexts"
          />
        </a-card>

        <!-- 第4行：分析面板；header 右侧 默认/TTFT/TPOT/ITL -->
        <a-card size="small" class="row-4">
          <template #title>
            <div class="row4-header">
              <span class="row4-title">{{ t('statistics') }}</span>
              <div class="row4-actions">
                <span class="linkage-toggle">
                  <span class="linkage-label">{{ t('linkage') }}</span>
                  <a-switch v-model:checked="chartLinkage" size="small" />
                </span>
                <a-button
                  size="small"
                  type="text"
                  class="panel-head-btn"
                  :class="{ 'is-on': chartAllOn }"
                  @click="setChartsAll"
                >
                  {{ t('defaultBtn') }}
                </a-button>
                <a-button
                  size="small"
                  type="text"
                  class="panel-head-btn"
                  :class="{ 'is-on': chartVisible.ttft }"
                  @click="toggleChart('ttft')"
                >
                  TTFT
                </a-button>
                <a-button
                  size="small"
                  type="text"
                  class="panel-head-btn"
                  :class="{ 'is-on': chartVisible.tpot }"
                  @click="toggleChart('tpot')"
                >
                  TPOT
                </a-button>
                <a-button
                  size="small"
                  type="text"
                  class="panel-head-btn"
                  :class="{ 'is-on': chartVisible.itl }"
                  @click="toggleChart('itl')"
                >
                  ITL
                </a-button>
              </div>
            </div>
          </template>
          <RunChartsPanel v-model:visible="chartVisible" :rows="current.run?.rows || []" :linked="chartLinkage" />
        </a-card>

        <!-- 第5行：距底部 18px 留白 -->
        <div class="row-5-spacer"></div>
      </div>
    </div>

    <!-- 删除/备份/分享 确认框 -->
    <a-modal
      :open="confirmVisible"
      :title="confirmTitle"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
      :confirm-loading="confirmLoading"
      @ok="doConfirm"
      @cancel="confirmVisible = false"
    >
      <p>{{ confirmContent }}</p>
    </a-modal>

    <!-- 预览日志 Modal -->
    <a-modal
      :open="previewVisible"
      :title="previewName"
      :footer="null"
      width="720px"
      @cancel="previewVisible = false"
    >
      <pre class="preview-box">{{ previewContent }}</pre>
    </a-modal>

    <!-- 导入面板：右侧抽屉，上传备份 zip 恢复任务 -->
    <a-drawer
      :open="importVisible"
      :title="t('import')"
      placement="right"
      width="360"
      @close="closeImport"
    >
      <div class="import-body">
        <p class="import-tip">{{ t('importTip') }}</p>
        <a-upload :before-upload="onPickZip" :show-upload-list="false" accept=".zip">
          <a-button type="primary" :loading="importing" :disabled="!!importResult">
            <template #icon><upload-outlined /></template>
            {{ t('uploadZip') }}
          </a-button>
        </a-upload>
        <a-progress v-if="importing" :percent="importPercent" size="small" class="import-progress" />
        <div v-if="importResult === 'ok'" class="import-msg success">
          <check-circle-outlined /> {{ t('importSuccess') }}
        </div>
        <div v-else-if="importResult === 'exists'" class="import-msg warn">
          <info-circle-outlined /> {{ t('importExists') }}
        </div>
        <div v-else-if="importResult === 'fail'" class="import-msg error">
          <close-circle-outlined /> {{ importError }}
        </div>
        <a-button v-if="importResult" size="small" type="link" class="import-reset" @click="resetImport">
          {{ t('cancelImport') }}
        </a-button>
      </div>
    </a-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import html2canvas from 'html2canvas'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  CopyOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EyeOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  ShareAltOutlined,
  UploadOutlined,
} from '@ant-design/icons-vue'
import { t } from '@/i18n'
import { api } from '@/api'
import RunDataPanel from '@/components/RunDataPanel.vue'
import RunChartsPanel from '@/components/RunChartsPanel.vue'

const route = useRoute()

// ---------- 任务记录列表 ----------
const runs = ref([])
const loadingList = ref(false)
const current = ref(null) // getRun 返回 {run_id, dir, files, run}

async function loadRuns() {
  loadingList.value = true
  try {
    const resp = await api.listRuns()
    runs.value = (resp?.runs || []).slice().sort((a, b) => (b.run_id || '').localeCompare(a.run_id || ''))
  } catch (e) {
    message.error(e.message || String(e))
  } finally {
    loadingList.value = false
  }
}

async function selectRun(r) {
  if (current.value && current.value.run_id === r.run_id) return
  current.value = null
  try {
    const resp = await api.getRun(r.run_id)
    current.value = resp
  } catch (e) {
    message.error(e.message || String(e))
    current.value = null
  }
}

function shortId(id) {
  if (!id) return '-'
  return id.length > 40 ? `${id.slice(0, 40)}…` : id
}

function fmtTime(v) {
  if (!v) return '-'
  const d = new Date(v)
  if (isNaN(d.getTime())) return String(v)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function fmtSize(n) {
  if (n === undefined || n === null) return '-'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

function statusText(s) {
  const map = { pending: t('pending'), running: t('running'), done: t('done'), stopped: t('stopped'), error: t('error') }
  return map[s] || s || '-'
}
function statusColor(s) {
  if (s === 'done') return 'success'
  if (s === 'running') return 'processing'
  if (s === 'error') return 'error'
  if (s === 'stopped') return 'warning'
  return 'default'
}
function statusClass(s) {
  return 'st-' + (s || 'unknown')
}

// ---------- Perf 面板 ----------
const datasetText = computed(() => {
  const ds = current.value?.run?.dataset || {}
  const typeMap = { random: t('randomDataset'), sharegpt: 'ShareGPT', custom: t('custom'), file: t('fileDataset') }
  const type = typeMap[ds.type] || ds.type || '-'
  const pairs = current.value?.run?.cases?.map((c) => (c.input_len ? `${c.input_len}/${c.output_len}` : c.label)).join(', ')
  return pairs ? `${type}(${pairs})` : type
})
const concurrencyDisplay = computed(() => {
  const list = current.value?.run?.concurrency_list || []
  return list.length ? list.join(', ') : '-'
})
const requestDisplay = computed(() => {
  const v = current.value?.run?.request_rate
  if (v === undefined || v === null || v === '') return '-'
  return String(v) === 'inf' ? 'inf' : String(v)
})

// ---------- 行3：数据表格 默认/Mean/Median/P99 ----------
const dataModes = [
  { key: 'default', label: t('defaultBtn') },
  { key: 'mean', label: t('mean') },
  { key: 'median', label: t('median') },
  { key: 'p99', label: t('p99') },
]
const dataMode = ref('default')

// Statistics 统计图联动开关（默认关闭：不联动浮动信息）
const chartLinkage = ref(false)

// ---------- 行4：图表行显示状态（默认全部开启） ----------
const chartVisible = ref({ throughput: true, ttft: true, tpot: true, itl: true })
const chartAllOn = computed(() => chartVisible.value.throughput && chartVisible.value.ttft && chartVisible.value.tpot && chartVisible.value.itl)
function toggleChart(key) {
  chartVisible.value = { ...chartVisible.value, [key]: !chartVisible.value[key] }
}
function setChartsAll() {
  chartVisible.value = { throughput: true, ttft: true, tpot: true, itl: true }
}

// ---------- Cases 面板：分组 + 对应请求（并发）信息，按行显示 ----------
const caseGroupRows = computed(() => {
  const rows = current.value?.run?.rows || []
  const cases = current.value?.run?.cases || []
  const map = new Map()
  const seed = (label, caseId, inputLen, outputLen, c) => {
    const key = caseId !== undefined && caseId !== null ? `${label}#g${caseId}` : label || 'unknown'
    if (!map.has(key)) {
      map.set(key, { key, label: label || 'unknown', case_id: caseId, inputLen, outputLen, concs: [], reqsText: '',
        // 阈值信息跟随 Groups 数据（每组独立配置），供 caseThresholdText 展示
        ttft_threshold_ms: c?.ttft_threshold_ms, ttft_statistic: c?.ttft_statistic,
        tpot_threshold_ms: c?.tpot_threshold_ms, tpot_statistic: c?.tpot_statistic,
        output_throughput_threshold: c?.output_throughput_threshold })
    }
  }
  for (const c of cases) seed(c.label, c.case_id, c.input_len, c.output_len, c)
  // 兼容无 cases 元数据的历史任务：直接用 rows 生成分组
  if (!cases.length) {
    for (const r of rows) seed(r.label || r.case, r.case_id, r.input_len, r.output_len)
  }
  for (const r of rows) {
    const g = map.get(rowCaseKey(r))
    if (!g) continue
    if (r.concurrency !== undefined && r.concurrency !== null) {
      const c = Number(r.concurrency)
      if (!g.concs.includes(c)) g.concs.push(c)
    }
    if (!g.inputLen && r.input_len) g.inputLen = r.input_len
    if (!g.outputLen && r.output_len) g.outputLen = r.output_len
  }
  const list = Array.from(map.values())
  for (const g of list) {
    g.concs.sort((a, b) => a - b)
    g.reqsText = g.concs.length ? g.concs.join(' / ') : ''
  }
  return list
})

// ---------- 行2：三面板高度 = Perf Info 高度（参考 Performance 第一行实现） ----------
const perfPanelRef = ref(null)
const perfRowHeight = ref(0)
const sideCardStyle = computed(() => (perfRowHeight.value ? { height: `${perfRowHeight.value}px` } : {}))
function measurePerfInfo() {
  // 关键：测量前临时 align-self:flex-start，避免 Perf 卡片被 flex 行拉伸，
  // 导致测到"拉伸后高度"（首次进入多组任务时会被 Cases 撑高并固化）
  const el = perfPanelRef.value?.$el || perfPanelRef.value
  if (!el) return
  const prev = el.style.alignSelf
  el.style.alignSelf = 'flex-start'
  const h = el.offsetHeight
  el.style.alignSelf = prev
  if (h) {
    perfRowHeight.value = h
  }
}
watch(
  () => current.value?.run_id,
  async () => {
    await nextTick()
    measurePerfInfo()
  },
  { immediate: true },
)
let perfInfoObserver = null
onMounted(() => {
  const el = perfPanelRef.value?.$el || perfPanelRef.value
  if (el && typeof ResizeObserver !== 'undefined') {
    perfInfoObserver = new ResizeObserver(() => measurePerfInfo())
    perfInfoObserver.observe(el)
  }
})
onBeforeUnmount(() => {
  if (perfInfoObserver) perfInfoObserver.disconnect()
})

// 阈值模式：单 case 的阈值条件文本（并入每个 case 分组标记右侧；0 表示未配置不显示）。
// 阈值信息跟随 Groups 数据（每组独立配置），不跟随主任务；
// 标识使用 TTFT-Mean/Median/P99、TPOT-Mean/Median/P99（statistic 由每组决定）
const statSuffix = (stat) => (stat === 'median' ? 'Median' : stat === 'p99' ? 'P99' : 'Mean')
function caseThresholdText(cg) {
  const run = current.value?.run
  if (!run || run.mode !== 'threshold') return ''
  // 兼容旧格式任务：cases 无 per-group 阈值（全 0）时回退任务级阈值字段（任务级同名字段保留，取第一组口径）
  const legacy = (run.cases || []).every(
    (x) => !Number(x?.ttft_threshold_ms) && !Number(x?.tpot_threshold_ms) && !Number(x?.output_throughput_threshold),
  )
  const parts = []
  const tt = Number(cg?.ttft_threshold_ms) || (legacy ? Number(run.ttft_threshold_ms) || 0 : 0)
  if (tt > 0) parts.push(`${t('ttftThresholdLabel')}-${statSuffix(cg?.ttft_statistic || (legacy ? run.ttft_statistic : '') || 'mean')} ≤ ${tt}ms`)
  const tp = Number(cg?.tpot_threshold_ms) || (legacy ? Number(run.tpot_threshold_ms) || 0 : 0)
  if (tp > 0) parts.push(`${t('condTpotLabel')}-${statSuffix(cg?.tpot_statistic || (legacy ? run.tpot_statistic : '') || 'mean')} ≤ ${tp}ms`)
  const ot = Number(cg?.output_throughput_threshold) || (legacy ? Number(run.output_throughput_threshold) || 0 : 0)
  if (ot > 0) parts.push(`${t('condOutputLabel')} ≤ ${ot} tok/s`)
  return parts.join(' · ')
}
// Perf Datas 分组（tab）：分组 key → 该组阈值条件文本（跟随 Groups，与 Cases Info 面板同一口径）
const groupThresholdTexts = computed(() => {
  const map = {}
  for (const cg of caseGroupRows.value) {
    map[cg.key] = caseThresholdText(cg)
  }
  return map
})

// ---------- 行3：annotatedRows（Datas 不标记 Best——Best 仅在 Performance 界面；阈值模式标记 BestPerf） ----------
function rowCaseKey(r) {
  return r.case_id !== undefined && r.case_id !== null ? `${r.label}#g${r.case_id}` : (r.label || r.case || '-')
}
const annotatedRows = computed(() => {
  const rows = (current.value?.run?.rows || []).map((r) => ({ ...r }))
  if (!rows.length) return rows
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
  // 阈值模式：按每组 case 的阈值全条件判断（TTFT/TPOT 的 statistic + Output），
  // 满足所有配置条件的行里取并发最大的一行标记 BestPerf（阈值跟随 Groups 数据，不跟随主任务）；
  // 旧格式任务（cases 无每组阈值）回退任务级阈值，与分组阈值文本（caseThresholdText）一致
  const markBestPerf = (groupRows, caseObj) => {
    const run = current.value?.run || {}
    const legacy = (run.cases || []).every(
      (x) => !Number(x?.ttft_threshold_ms) && !Number(x?.tpot_threshold_ms) && !Number(x?.output_throughput_threshold),
    )
    const cTtft = Number(caseObj?.ttft_threshold_ms) || 0
    const cTpot = Number(caseObj?.tpot_threshold_ms) || 0
    const cOut = Number(caseObj?.output_throughput_threshold) || 0
    // caseObj 阈值为有效正值时以每组为准；否则（0/未配置）旧格式任务回退任务级阈值
    const ttftThr = cTtft > 0 ? cTtft : (legacy ? Number(run.ttft_threshold_ms) || 0 : 0)
    const tpotThr = cTpot > 0 ? cTpot : (legacy ? Number(run.tpot_threshold_ms) || 0 : 0)
    const outThr = cOut > 0 ? cOut : (legacy ? Number(run.output_throughput_threshold) || 0 : 0)
    const ttftStat = cTtft > 0 ? caseObj?.ttft_statistic || 'mean' : (legacy ? run.ttft_statistic || 'mean' : 'mean')
    const tpotStat = cTpot > 0 ? caseObj?.tpot_statistic || 'mean' : (legacy ? run.tpot_statistic || 'mean' : 'mean')
    if (!(ttftThr > 0) && !(tpotThr > 0) && !(outThr > 0)) return
    let bestRow = null
    let bestConc = -Infinity
    for (const r of groupRows) {
      if (!condPass(r.metrics?.[`ttft_${ttftStat}`], ttftThr)) continue
      if (!condPass(r.metrics?.[`tpot_${tpotStat}`], tpotThr)) continue
      if (!condPass(r.metrics?.output_mean ?? r.metrics?.output, outThr)) continue
      const c = Number(r.concurrency)
      if (c > bestConc) {
        bestConc = c
        bestRow = r
      }
    }
    if (bestRow) bestRow.bestPerf = true
  }
  // 按 case 分组，组内按并发升序
  const groupMap = new Map()
  for (const r of rows) {
    r.caseKey = rowCaseKey(r)
    const key = r.caseKey
    if (!groupMap.has(key)) groupMap.set(key, [])
    groupMap.get(key).push(r)
  }
  // 由 run.cases 构建 caseKey → case（含每组阈值）
  const caseByKey = new Map()
  for (const c of current.value?.run?.cases || []) {
    const key = c.case_id !== undefined && c.case_id !== null ? `${c.label}#g${c.case_id}` : c.label || '-'
    caseByKey.set(key, c)
  }
  const grouped = []
  for (const [key, groupRows] of groupMap) {
    groupRows.sort((a, b) => Number(a.concurrency) - Number(b.concurrency))
    if (current.value?.run?.mode === 'threshold') {
      markBestPerf(groupRows, caseByKey.get(key) || {})
    }
    grouped.push(...groupRows)
  }
  return grouped
})

// ---------- Logs 面板 ----------
const summaryName = computed(() => {
  const xlsx = current.value?.run?.summary?.xlsx
  if (xlsx) return String(xlsx).split(/[\\/]/).pop()
  return 'run.json'
})
const previewVisible = ref(false)
const previewName = ref('')
const previewContent = ref('')

async function previewLog(name) {
  try {
    const resp = await api.previewFile(current.value.run_id, name)
    previewContent.value = resp?.content || ''
    previewName.value = name
    previewVisible.value = true
  } catch (e) {
    message.error(e.message || String(e))
  }
}
function downloadFile(name) {
  window.open(api.downloadUrl(current.value.run_id, name), '_blank')
}
function downloadSummary() {
  const run = current.value?.run || {}
  const xlsx = run.summary?.xlsx
  if (xlsx) {
    const name = xlsx.split(/[\\/]/).pop()
    window.open(api.downloadUrl(current.value.run_id, name), '_blank')
    return
  }
  downloadFile('run.json')
}
async function copyRunDir() {
  try {
    await navigator.clipboard.writeText(current.value?.dir || '')
    message.success(t('copied'))
  } catch (e) {
    message.error(e.message || String(e))
  }
}

// ---------- 删除 / 备份 / 分享 ----------
const confirmVisible = ref(false)
const confirmTitle = ref('')
const confirmContent = ref('')
const confirmLoading = ref(false)
const busy = ref('') // '' | 'delete' | 'backup' | 'share'：生成中 spinner 状态
let confirmAction = null

function onDelete() {
  confirmTitle.value = t('deleteRunTitle')
  confirmContent.value = t('deleteRunConfirm')
  confirmAction = 'delete'
  confirmVisible.value = true
}
function onBackup() {
  confirmTitle.value = t('backup')
  confirmContent.value = t('backupConfirm')
  confirmAction = 'backup'
  confirmVisible.value = true
}
function onShare() {
  confirmTitle.value = t('share')
  confirmContent.value = t('shareConfirm')
  confirmAction = 'share'
  confirmVisible.value = true
}

async function doConfirm() {
  confirmLoading.value = true
  busy.value = confirmAction
  try {
    if (confirmAction === 'delete') {
      await api.deleteRun(current.value.run_id)
      message.success(t('deleted'))
      current.value = null
      await loadRuns()
    } else if (confirmAction === 'backup') {
      await doBackup()
    } else if (confirmAction === 'share') {
      await doShare()
    }
    confirmVisible.value = false
  } catch (e) {
    message.error(e.message || String(e))
  } finally {
    confirmLoading.value = false
    busy.value = ''
  }
}

// 备份：打包下载任务全部日志 zip（可重新导入恢复）
async function doBackup() {
  const resp = await api.backupRun(current.value.run_id)
  const blob = new Blob([resp], { type: 'application/zip' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${current.value.run_id}.zip`
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
  message.success(t('backupDone'))
}

// 分享：将当前界面状态的任务详情页面渲染为 PNG 图片并下载
async function doShare() {
  await nextTick()
  const el = detailRef.value
  if (!el) throw new Error('no element')
  // 按当前界面状态截图（不改动数据模式/图表显隐）；临时放开滚动容器的高度/裁剪约束，
  // 保证长详情页（含数据表与图表分析区）全部内容输出到图片
  const saved = {
    overflow: el.style.overflow,
    height: el.style.height,
    flex: el.style.flex,
  }
  el.style.overflow = 'visible'
  el.style.height = 'auto'
  el.style.flex = 'none'
  // 展开嵌套滚动区（MetricsTable 的 ant-table-body 固定高度会被 html2canvas 裁剪），
  // 保证 Perf Datas 表格数据完整进入分享图片
  el.classList.add('sharing')
  await nextTick()
  // 等图表完成重绘再截图
  await new Promise((r) => setTimeout(r, 200))
  try {
    const canvas = await html2canvas(el, {
      useCORS: true,
      backgroundColor: '#ffffff',
      scale: 1.5,
      windowWidth: document.documentElement.offsetWidth,
      height: el.scrollHeight,
      width: el.scrollWidth,
    })
    const url = canvas.toDataURL('image/png')
    const a = document.createElement('a')
    a.href = url
    a.download = `${current.value.run_id}.png`
    a.click()
  } finally {
    el.classList.remove('sharing')
    el.style.overflow = saved.overflow
    el.style.height = saved.height
    el.style.flex = saved.flex
  }
  message.success(t('shareDone'))
}

// ---------- 导入：从备份 zip 恢复任务 ----------
const importVisible = ref(false)
const importing = ref(false)
const importPercent = ref(0)
const importResult = ref('') // '' | 'ok' | 'exists' | 'fail'
const importError = ref('')

function openImport() {
  importVisible.value = true
  resetImport()
}
function closeImport() {
  importVisible.value = false
  resetImport()
}
function resetImport() {
  importResult.value = ''
  importError.value = ''
  importPercent.value = 0
  importing.value = false
}

async function onPickZip(file) {
  if (!/\.zip$/i.test(file.name || '')) {
    message.error(t('importZipHint'))
    return false
  }
  importing.value = true
  importPercent.value = 0
  importResult.value = ''
  importError.value = ''
  const form = new FormData()
  form.append('file', file)
  try {
    const resp = await api.importRun(form, (e) => {
      if (e && e.total) importPercent.value = Math.round((e.loaded / e.total) * 100)
    })
    importPercent.value = 100
    if (resp?.ok) {
      importResult.value = 'ok'
      message.success(t('importSuccess'))
      await loadRuns()
    } else if (resp?.exists) {
      importResult.value = 'exists'
      message.warning(t('importExists'))
    } else {
      importResult.value = 'fail'
      importError.value = String(resp?.detail || t('importFailed'))
    }
  } catch (e) {
    importResult.value = 'fail'
    importError.value = e?.message || e?.detail || String(e)
    message.error(importError.value)
  } finally {
    importing.value = false
  }
  return false
}

const detailRef = ref(null)

// 根据路由 query.run_id 自动选中对应任务（Dashboard Detail 跳转入口）
async function selectRunFromQuery(rid) {
  if (!rid) return
  const target = runs.value.find((r) => r.run_id === rid)
  if (target) {
    await selectRun(target)
  }
}

onMounted(async () => {
  await loadRuns()
  await selectRunFromQuery(route.query.run_id)
})

watch(
  () => route.query.run_id,
  async (rid) => {
    await selectRunFromQuery(rid)
  },
)
</script>

<style scoped>
.perfs-page {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* 左侧固定面板 */
.record-panel {
  width: 280px;
  flex-shrink: 0;
  border-right: 1px solid var(--ant-color-border, #f0f0f0);
  background: var(--ant-color-bg-container, #fff);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.record-panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  font-weight: 600;
  font-size: 13px;
  border-bottom: 1px solid var(--ant-color-border, #f0f0f0);
  flex-shrink: 0;
}
.record-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px 6px 16px;
}
.record-item {
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
  border: 1px solid transparent;
}
.record-item:hover {
  background: var(--ant-color-fill-secondary, #fafafa);
}
.record-item.active {
  background: rgba(22, 119, 255, 0.06);
  border-color: rgba(22, 119, 255, 0.35);
}
.record-head {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 6px;
}
.record-id {
  font-family: monospace;
  font-size: 12px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 记录 framework 高亮标记：任务 ID 右边，字体再小些 */
.record-framework {
  font-size: 9px;
  line-height: 1;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: 3px;
  color: #1677ff;
  background: rgba(22, 119, 255, 0.1);
  flex-shrink: 0;
  white-space: nowrap;
  max-width: 96px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.record-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-top: 4px;
}
.record-model {
  font-size: 11px;
  color: var(--ant-color-text-secondary, #666);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.record-time {
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
  flex-shrink: 0;
}
.record-status {
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
  white-space: nowrap;
  margin-left: auto;  /* 状态推到最右 */
}
.st-done {
  color: #52c41a;
}
.st-running {
  color: #1677ff;
}
.st-error {
  color: #ff4d4f;
}
.st-stopped {
  color: #fa8c16;
}
.st-pending,
.st-unknown {
  color: var(--ant-color-text-tertiary, #999);
}
.title-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}
.icon-btn {
  color: var(--ant-color-text-secondary, #666);
}
.record-empty {
  margin-top: 40px;
}

/* 右侧滑动详情 */
.detail-panel {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.select-hint {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.detail-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 分享截图：展开嵌套滚动区（scoped 下需 :deep 命中 antd 类），保证 Perf Datas 表格数据完整输出 */
.detail-scroll.sharing :deep(.ant-table-body),
.detail-scroll.sharing :deep(.ant-table-content) {
  height: auto !important;
  max-height: none !important;
  overflow: visible !important;
}

/* 行1 */
.row1-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}
.run-title {
  font-size: 16px;
  font-weight: 700;
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.row1-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}
.row1-desc {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
}
.desc-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.desc-label {
  color: var(--ant-color-text-secondary, #666);
}
.desc-value {
  font-weight: 500;
}

/* 行2：三面板各 1/3 固定宽度（minmax(0,1fr) 防止内容撑宽），等高（gridAutoRows 由 JS 固定为 Perf Info 高度），内容超出内部滚动 */
.row-2 {
  display: flex;
  gap: 12px;
  align-items: stretch;
}
.row-2 > .half-card {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.row-2 .half-card :deep(.ant-card-body) {
  flex: 1;
  min-height: 0;
  overflow: hidden;   /* body 不滚动：内部容器（case-groups / log-files）各自滚动 */
  display: flex;      /* 关键：body 需为 flex 列容器，info-body 的 flex:1 才生效 */
  flex-direction: column;
}
.info-body {
  padding: 4px 0;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 0;
  border-bottom: 1px dashed var(--ant-color-border-secondary, #f0f0f0);
  gap: 12px;
}
.info-row:last-child {
  border-bottom: none;
}
.info-label {
  color: var(--ant-color-text-secondary, #666);
  font-size: 12px;
  flex-shrink: 0;
}
.info-value {
  font-size: 12px;
  font-weight: 500;
  text-align: right;
  /* 宽度不够时伪隐藏（省略号） */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  max-width: 65%;
}
.case-groups {
  display: flex;
  flex-direction: column;
  gap: 2px;
  /* 灰色面板容器：滚动条在面板内部 */
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--ant-color-fill-tertiary, #f5f5f5);
  border: 1px solid var(--ant-color-border-secondary, #eee);
  border-radius: 4px;
  padding: 4px 6px;
}
.case-group-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 0;
  border-bottom: 1px dashed var(--ant-color-border-secondary, #f0f0f0);
  flex-wrap: wrap;
}
.case-group-item:last-child {
  border-bottom: none;
}
.case-label {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 55%;
}
.case-gid {
  color: var(--ant-color-primary, #1677ff);
  font-size: 11px;
  flex-shrink: 0;
}
.case-meta {
  color: var(--ant-color-text-secondary, #666);
  font-size: 11px;
  flex-shrink: 0;
}
/* 阈值条件文本：并入分组标记右侧，宽度不够伪隐藏（省略号） */
.case-threshold {
  color: var(--ant-color-text-tertiary, #999);
  font-size: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex-shrink: 1;
  max-width: 45%;
}
.case-req {
  margin-left: auto;
  font-size: 10px;   /* 请求数字体缩小 */
  color: var(--ant-color-text-secondary, #666);
  /* 请求数过长时换行显示（不省略） */
  white-space: normal;
  word-break: break-all;
  max-width: 100%;
  text-align: right;
}
.empty-hint {
  color: var(--ant-color-text-tertiary, #999);
  font-size: 12px;
  padding: 8px 0;
}

/* Logs 面板 */
.logs-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-height: 0;
}
.run-dir-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.run-dir-text {
  flex: 1;
  min-width: 0;
  font-family: monospace;
  font-size: 10px;
  color: var(--ant-color-text-secondary, #666);
  overflow: hidden;
  white-space: nowrap;
  text-align: right;
  /* 伪隐藏开头：方向反转使省略号在左侧，最少保留末尾文件名 */
  direction: rtl;
  text-overflow: ellipsis;
}
.copy-icon {
  color: var(--ant-color-primary, #1677ff);
  cursor: pointer;
  flex-shrink: 0;
}
.summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.summary-name {
  flex: 1;
  min-width: 0;
  font-size: 10px;
  font-family: monospace;
  color: var(--ant-color-text-secondary, #666);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: right;
}
/* Log Files 列表：灰色面板 + 缩小文字与图标 */
.log-files {
  background: var(--ant-color-fill-tertiary, #f5f5f5);
  border: 1px solid var(--ant-color-border-secondary, #eee);
  border-radius: 4px;
  padding: 6px 8px;
  /* 高度随面板（以 Perf Info 为准）填充，内容超出滚动 */
  flex: 1;
  min-height: 0;
  max-height: none;
  overflow-y: auto;
}
.log-file-head {
  font-size: 10px;
  font-weight: 600;
  color: var(--ant-color-text-secondary, #666);
  margin-bottom: 2px;
}
.log-file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
  border-bottom: 1px dashed var(--ant-color-border-secondary, #f0f0f0);
}
.log-file-item:last-child {
  border-bottom: none;
}
.log-file-name {
  flex: 1;
  min-width: 0;
  font-family: monospace;
  font-size: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ant-color-text, #333);
}
.log-file-size {
  flex-shrink: 0;
  font-size: 8px;
  color: var(--ant-color-text-tertiary, #999);
}
.log-file-item .icon-btn {
  width: 20px;
  height: 20px;
  min-width: 20px;
  padding: 0;
  font-size: 10px;
  line-height: 20px;
}

/* 行3/行4：header 右侧操作按钮（默认/Mean/Median/P99、默认/TTFT/TPOT/ITL） */
.row-3 :deep(.ant-card-head-title),
.row-4 :deep(.ant-card-head-title) {
  width: 100%;
}
.row3-header,
.row4-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}
.row3-title,
.row4-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ant-color-text, #333);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.row3-actions,
.row4-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.linkage-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-right: 8px;
}
.linkage-label {
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
}
.panel-head-btn {
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
  border-radius: 4px;
}
.panel-head-btn.is-on {
  color: var(--ant-color-primary, #1677ff);
  font-weight: 600;
  background: rgba(22, 119, 255, 0.08);
}

/* 行5：距底部 18px 留白 */
.row-5-spacer {
  height: 18px;
  flex-shrink: 0;
}

.preview-box {
  max-height: 60vh;
  overflow: auto;
  background: #111;
  color: #e6e6e6;
  font-size: 12px;
  padding: 12px;
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-all;
}

/* 导入抽屉 */
.import-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-start;
}
.import-tip {
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
  margin: 0;
}
.import-progress {
  width: 100%;
}
.import-msg {
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.import-msg.success {
  color: #52c41a;
}
.import-msg.warn {
  color: #fa8c16;
}
.import-msg.error {
  color: #ff4d4f;
}
.import-reset {
  padding-left: 0;
}
</style>

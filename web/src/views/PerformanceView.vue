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
            <a-col :xs="24" :sm="8" v-for="(feat, idx) in features" :key="feat.title">
              <a-card size="small" class="feature-card" hoverable>
                <template #cover>
                  <div class="feature-icon" :class="`fi-${idx % 4}`">{{ feat.icon }}</div>
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
      <!-- 第一行：Perf + Cases + Console (各占 1/3，最大高度 = Perf 高度，超出滚动) -->
      <div class="row-1">
        <!-- Perf 面板 -->
        <a-card size="small" class="perf-panel" ref="perfPanelRef" :body-style="{ padding: '10px 14px', display: 'flex', flexDirection: 'column', flex: '1', minHeight: '0' }">
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
              <span class="info-value">
                {{ theTask.framework_name || theTask.framework }}
                <a-tag v-if="theTask.use_mock_env" color="orange" size="small" class="mock-env-tag" :title="t('mockEnvTagHint')">
                  {{ t('mockEnvTag') }}
                </a-tag>
              </span>
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
        <a-card size="small" class="cases-panel" :style="sideCardStyle" :body-style="{ padding: '10px 14px', display: 'flex', flexDirection: 'column', flex: '1', minHeight: '0' }">
          <template #title>{{ t('casesPanelTitle') }}</template>
          <template #extra>
            <span class="cases-mode">{{ theTask.mode === 'threshold' ? t('thresholdMode') : t('concurrencyMode') }}</span>
          </template>
          <div class="cases-body">
            <!-- 分组列表：独立滚动区域 -->
            <div class="case-list" ref="caseListRef">
            <div v-for="(c, i) in theTask.cases || []" :key="c.case_id || c.label || i" class="case-row">
              <!-- 第一行：分组信息（阈值模式：阈值条件并入分组标记右侧，宽度不够伪隐藏） -->
              <div class="case-head">
                <span class="case-label">{{ c.label }}</span>
                <a-tag v-if="c.case_id" size="small" class="case-gid">g{{ c.case_id }}</a-tag>
                <span class="case-meta" v-if="c.input_len">{{ c.input_len }}/{{ c.output_len }}</span>
                <span v-if="caseThresholdText(c)" class="case-threshold" :title="caseThresholdText(c)">{{ caseThresholdText(c) }}</span>
              </div>
              <!-- 第二行：请求数（单独一行，一行不够自动换行多行） -->
              <span class="case-tags">
                <!-- 阈值模式：已执行/执行中的 case 显示完整请求数列表（当前测试的标蓝、已完成标绿），未执行显示 Pending -->
                <template v-if="theTask.mode === 'threshold'">
                  <template v-if="caseTestedTags(c).length">
                    <a-tag
                      v-for="tt in caseTestedTags(c)"
                      :key="tt.conc"
                      :color="tt.running ? 'processing' : 'green'"
                      size="small"
                      class="req-tag"
                      :class="{ 'req-selected': isReqSelected(c, tt.conc) }"
                      :title="t('reqViewHint')"
                      @click="selectReq(c, tt.conc)"
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
                    class="req-tag"
                    :class="{ 'req-selected': isReqSelected(c, conc) }"
                    :title="t('reqViewHint')"
                    @click="selectReq(c, conc)"
                  >{{ conc }}</a-tag>
                </template>
              </span>
            </div>
            <div v-if="!theTask.cases?.length" class="empty-hint">{{ t('noData') }}</div>
            </div>
          </div>
          <!-- footer：空（保持三面板等高） -->
          <div class="panel-footer empty-footer"></div>
        </a-card>

        <!-- Logs 面板（原 Console：白底、日志高亮、小号字体） -->
        <a-card size="small" class="console-panel" :style="sideCardStyle" :body-style="{ flex: '1', minHeight: '0', padding: '0', display: 'flex', flexDirection: 'column' }">
          <template #title>{{ t('logs') }}</template>
          <template #extra>
            <a-button size="small" type="link" @click="downloadLog">
              <template #icon><download-outlined /></template>
              {{ t('download') }}
            </a-button>
          </template>
          <div class="terminal-box" ref="termBox" @scroll="onTermScroll">
            <div v-for="(line, i) in activeLogs" :key="i" class="term-line" :class="logLineClass(line)">{{ line }}</div>
          </div>
          <!-- footer：空（保持三面板等高） -->
          <div class="panel-footer empty-footer"></div>
        </a-card>
      </div>

      <!-- 第二行：Profile Progress(1/3) + Real-Time Metrics(2/3)，按请求快照渲染 -->
      <LivePanels :snapshot="activeLiveSnapshot" :live="isLiveRunning" />

      <!-- Realtime Data 面板：所有请求行表格（保持不变，承载 Best/BestPerf + 本地面板阈值 + 列设置 + 导出） -->
      <a-card size="small" class="full-row-card realtime-data-card">
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
          :group-thresholds="groupThresholdTexts"
          group-by="caseKey"
          :task-id="taskId"
          exportable
        />
      </a-card>

      <!-- 第四行：统计图面板 -->
      <a-card size="small" class="full-row-card">
        <template #title>{{ t('statistics') }}</template>
        <template #extra>
          <a-space size="small" class="linkage-toggle">
            <span class="linkage-label">{{ t('linkage') }}</span>
            <a-switch v-model:checked="statLinkage" size="small" />
          </a-space>
        </template>
        <MetricsCharts :rows="theTask.rows || []" :linked="statLinkage" />
      </a-card>

      <!-- 底部 18px 空白 -->
      <div class="row-5-spacer"></div>
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
  WarningOutlined,
} from '@ant-design/icons-vue'
import { useRouter } from 'vue-router'
import { reqKeyOf, useTestStore } from '@/store/test'
import { useConfigStore } from '@/store/config'
import { api } from '@/api'
import { t } from '@/i18n'
import MetricsTable from '@/components/MetricsTable.vue'
import MetricsCharts from '@/components/MetricsCharts.vue'
import LivePanels from '@/components/LivePanels.vue'

const test = useTestStore()
const config = useConfigStore()
const router = useRouter()
const loading = ref(false)
const features = computed(() => [
  { icon: '⚡', title: t('featConcurrencyMode'), desc: t('featConcurrencyModeDesc') },
  { icon: '🎯', title: t('featThresholdMode'), desc: t('featThresholdModeDesc') },
  { icon: '📈', title: t('featRealtimePerf'), desc: t('featRealtimePerfDesc') },
])
const termBox = ref(null)
const userNearBottom = ref(true)
// Statistics 统计图联动开关（默认开启：hover 联动浮动信息）
const statLinkage = ref(true)

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

// ===== 单个请求回看：点击 Cases 请求数可查看该请求的 Profile Progress / Real-Time Metrics =====
const selectedReqKey = ref(null)
function selectReq(caseObj, conc) {
  selectedReqKey.value = reqKeyOf(caseObj.label || caseObj.case, caseObj.case_id, conc)
}
function isReqSelected(caseObj, conc) {
  return selectedReqKey.value === reqKeyOf(caseObj.label || caseObj.case, caseObj.case_id, conc)
}
// 当前展示的快照：优先选中请求 → 执行中 realtime → 默认最后一个已完成请求
const activeLiveSnapshot = computed(() => {
  const tid = taskId.value
  if (!tid) return null
  const cache = test.liveReq[tid] || {}
  if (selectedReqKey.value && cache[selectedReqKey.value]) return cache[selectedReqKey.value]
  const pos = test.currentPos[tid]
  if (pos && pos.case != null) {
    const k = reqKeyOf(pos.case, pos.case_id, pos.concurrency)
    if (cache[k]) return cache[k]
    const live = test.liveMetrics[tid]
    if (live && live.stats) {
      return { case: pos.case, case_id: pos.case_id, concurrency: pos.concurrency, label: pos.case, stats: live.stats }
    }
  }
  // 默认显示最后一个已完成请求
  const rows = theTask.value?.rows || []
  if (rows.length) {
    const last = rows[rows.length - 1]
    const k = reqKeyOf(last.label || last.case, last.case_id, last.concurrency)
    if (cache[k]) return cache[k]
  }
  return null
})
// 是否以“执行中”呈现（状态 Profiling）；选中某个已缓存请求时视为已完成的回看
const isLiveRunning = computed(() => theTask.value?.status === 'running' && !selectedReqKey.value)
// 切换任务时重置选中的请求
watch(taskId, () => { selectedReqKey.value = null })
// 任务结束时加载持久化按请求快照（原生引擎靠结束解析结果落盘，内置引擎已有实时缓存）
watch(() => theTask.value?.status, (st) => {
  if (['done', 'stopped', 'error'].includes(st) && taskId.value) loadPersistedLive(taskId.value)
})

// 加载该任务持久化的按请求实时快照（原生引擎无实时流，靠结束解析结果落盘）
async function loadPersistedLive(id) {
  try {
    const runId = String(id).replace(/^task-/, '')
    const resp = await api.getRunLive(runId)
    if (!test.liveReq[id]) test.liveReq[id] = {}
    for (const s of resp?.snapshots || []) {
      const k = reqKeyOf(s.label ?? s.case, s.case_id, s.concurrency)
      // 已存在（如内置引擎实时缓存）则保留更完整的
      if (!test.liveReq[id][k]) test.liveReq[id][k] = s
    }
  } catch { /* 无快照或运行不存在时忽略 */ }
}
const activeLogs = computed(() => (taskId.value ? test.logLines[taskId.value] || [] : []))
const serviceReady = computed(() => config.status?.inference === 'ready')
const serviceUrl = computed(() => config.apiBase || '')

// 日志行高亮分类：按内容给每条日志行附加 CSS 类（Logs 面板）
function logLineClass(line) {
  if (!line) return ''
  const s = String(line)
  if (s.trim().startsWith('$')) return 'log-cmd'           // 命令行
  // 真实错误才标红：不再用宽泛的 "fail"（会误伤正常的 "Failed requests:" 汇总行）
  if (/error|exception|traceback|失败|FAILED/i.test(s)) return 'log-error'  // 错误
  if (/warn|warning|deprecat/i.test(s)) return 'log-warn'  // 警告
  if (/success|done|complete|成功|完成/i.test(s)) return 'log-ok'        // 成功
  if (/====|----|Result|指标|Serving Benchmark/i.test(s)) return 'log-head' // 区块/汇总标题
  return ''
}

// 第一行三面板（Perf/Cases/Console）：最大高度 = Perf 面板高度，超出滚动；三面板对齐
const perfPanelRef = ref(null)
const perfRowHeight = ref(0)
const sideCardStyle = computed(() => (perfRowHeight.value ? { height: `${perfRowHeight.value}px` } : {}))
function measurePerfRow() {
  // ref 在组件上拿到的是实例，需用 $el 取真实 DOM
  const el = perfPanelRef.value?.$el || perfPanelRef.value
  // 用 scrollHeight 取自然内容高度：offsetHeight 在 align-items:stretch 下是拉伸后的高度（超 Perf 自然高）
  if (el && el.scrollHeight) {
    perfRowHeight.value = el.scrollHeight
  }
}
watch(
  () => [theTask.value?.task_id, theTask.value?.status, theTask.value?.rows?.length],
  async () => {
    await nextTick()
    measurePerfRow()
  },
  { immediate: true },
)
let perfRowObserver = null
onMounted(() => {
  const el = perfPanelRef.value?.$el || perfPanelRef.value
  if (el && typeof ResizeObserver !== 'undefined') {
    perfRowObserver = new ResizeObserver(() => measurePerfRow())
    perfRowObserver.observe(el)
  }
})
onBeforeUnmount(() => {
  if (perfRowObserver) perfRowObserver.disconnect()
})

// 第二行：Real-Time Metrics 高度与 Profile Progress 保持一致（测量 Profile 自然高度作为参考）
const profilePanelRef = ref(null)
const profileRowHeight = ref(0)
const rtmCardStyle = computed(() => (profileRowHeight.value ? { height: `${profileRowHeight.value}px` } : {}))
function measureProfileRow() {
  // ref 在 a-card 上拿到的是实例，需用 $el 取真实 DOM；scrollHeight 取自然内容高度
  const el = profilePanelRef.value?.$el || profilePanelRef.value
  if (el && el.scrollHeight) {
    profileRowHeight.value = el.scrollHeight
  }
}
watch(
  () => [theTask.value?.task_id, theTask.value?.mode, theTask.value?.status],
  async () => {
    await nextTick()
    measureProfileRow()
  },
  { immediate: true },
)
let profileRowObserver = null
onMounted(() => {
  const el = profilePanelRef.value?.$el || profilePanelRef.value
  if (el && typeof ResizeObserver !== 'undefined') {
    profileRowObserver = new ResizeObserver(() => measureProfileRow())
    profileRowObserver.observe(el)
  }
})
onBeforeUnmount(() => {
  if (profileRowObserver) profileRowObserver.disconnect()
})

// 阈值模式：单 case 的阈值条件文本（并入每个 case 分组标记右侧；0 表示未配置不显示）。
// 阈值信息跟随 Groups 数据（每组独立配置），不跟随主任务；
// 标识使用 TTFT-Mean/Median/P99、TPOT-Mean/Median/P99（statistic 由每组决定）
const statSuffix = (stat) => (stat === 'median' ? 'Median' : stat === 'p99' ? 'P99' : 'Mean')
function caseThresholdText(c) {
  const tk = theTask.value
  if (!tk || tk.mode !== 'threshold') return ''
  // 兼容旧格式任务：cases 无 per-group 阈值（全 0）时回退任务级阈值字段（任务级同名字段保留，取第一组口径）
  const legacy = (tk.cases || []).every(
    (x) => !Number(x?.ttft_threshold_ms) && !Number(x?.tpot_threshold_ms) && !Number(x?.output_throughput_threshold),
  )
  const parts = []
  const tt = Number(c?.ttft_threshold_ms) || (legacy ? Number(tk.ttft_threshold_ms) || 0 : 0)
  if (tt > 0) parts.push(`${t('ttftThresholdLabel')}-${statSuffix(c?.ttft_statistic || (legacy ? tk.ttft_statistic : '') || 'mean')} ≤ ${tt}ms`)
  const tp = Number(c?.tpot_threshold_ms) || (legacy ? Number(tk.tpot_threshold_ms) || 0 : 0)
  if (tp > 0) parts.push(`${t('condTpotLabel')}-${statSuffix(c?.tpot_statistic || (legacy ? tk.tpot_statistic : '') || 'mean')} ≤ ${tp}ms`)
  const ot = Number(c?.output_throughput_threshold) || (legacy ? Number(tk.output_throughput_threshold) || 0 : 0)
  if (ot > 0) parts.push(`${t('condOutputLabel')} ≤ ${ot} tok/s`)
  return parts.join(' · ')
}

// Groups 列表：任务运行中自动向下滚动（跟随最新执行位置）
const caseListRef = ref(null)
watch(
  () => [theTask.value?.status, theTask.value?.rows?.length, test.currentPos[taskId.value]?.concurrency],
  async () => {
    if (theTask.value?.status !== 'running') return
    await nextTick()
    if (caseListRef.value) {
      caseListRef.value.scrollTop = caseListRef.value.scrollHeight
    }
  },
)

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

// ===== Profile Progress 面板（第二行左 1/3）：当前正在进行的请求指标、进度 =====
// 当前 case-请求数（两个面板 header 右侧灰色小字）——优先执行中的位置，其次已完成行
const rtCaseText = computed(() => {
  const pos = taskId.value ? test.currentPos[taskId.value] : null
  const tk = theTask.value
  const suffix = t('reqCountSuffix')
  if (pos && pos.case) {
    const cid = pos.case_id !== undefined && pos.case_id !== null ? `#g${pos.case_id}` : ''
    return `${pos.case}${cid} · ${pos.concurrency}${suffix}`
  }
  const rows = tk?.rows || []
  if (rows.length) {
    const last = rows[rows.length - 1]
    const key = last.case_id !== undefined && last.case_id !== null ? `#g${last.case_id}` : ''
    return `${last.label || last.case || '-'}${key} · ${last.concurrency}${suffix}`
  }
  return '-'
})

// 状态：执行中=Profiling；错误=Error；其余=Completed
const profileStatusKey = computed(() => {
  const s = theTask.value?.status
  if (s === 'running') return 'profiling'
  if (s === 'error') return 'error'
  return 'completed'
})
const profileStatusText = computed(() => {
  const k = profileStatusKey.value
  return k === 'profiling' ? t('profProfiling') : k === 'error' ? t('profError') : t('profCompleted')
})

// 请求完成度（Profile Progress 上条）
const reqPct = computed(() => {
  if (!totalCount.value) return 0
  return Math.round((doneCount.value / totalCount.value) * 100)
})
// 记录处理度（下条）：按 case 数
const recTotalCases = computed(() => (theTask.value?.cases?.length || 0))
const recDoneCases = computed(() => {
  const rows = theTask.value?.rows || []
  const seen = new Set()
  for (const r of rows) {
    if (!(r.metrics || r.error)) continue
    seen.add(r.case_id !== undefined && r.case_id !== null ? `g${r.case_id}` : (r.label || r.case || '-'))
  }
  return seen.size
})
const recPct = computed(() => (recTotalCases.value ? Math.round((recDoneCases.value / recTotalCases.value) * 100) : 0))

// 已完成请求数 / 错误数（Phase-1：来自已完成行的聚合；真实逐请求流在 Phase-2）
const requestsDone = computed(() => {
  let n = 0
  for (const r of theTask.value?.rows || []) {
    const m = r.metrics || {}
    n += (m.successful_requests || 0) + (m.failed_requests || 0)
  }
  return n
})
const errorsDone = computed(() => {
  let n = 0
  for (const r of theTask.value?.rows || []) {
    const m = r.metrics || {}
    n += m.failed_requests || 0
  }
  return n
})

// 已运行秒数
const elapsedSec = computed(() => {
  if (!theTask.value?.started_at) return 0
  const start = new Date(theTask.value.started_at).getTime()
  const sec = Math.max(0, (Date.now() - start) / 1000)
  return sec
})

// ===== Profile Progress 文本指标（终端风格：Status/Progress/Errors/Rate/Elapsed/ETA） =====
const fmtInt = (n) => {
  const x = Number(n)
  if (!isFinite(x)) return '0'
  return Math.round(x).toLocaleString('en-US')
}
const fmtDec = (n, d = 1) => {
  const x = Number(n)
  if (!isFinite(x)) return '-'
  return x.toFixed(d)
}
// 实时快照（task_live）优先；无流时回退已完成行聚合
const liveStats = computed(() => (liveBuf.value && liveBuf.value.stats) || null)

const progressText = computed(() => {
  const ls = liveStats.value
  if (ls && ls.total) {
    const pct = (ls.completed / ls.total) * 100
    return `${fmtInt(ls.completed)} / ${fmtInt(ls.total)} requests (${pct.toFixed(1)}%)`
  }
  return `${fmtInt(doneCount.value)} / ${fmtInt(totalCount.value)} (${reqPct.value}%)`
})
const errorsText = computed(() => {
  const ls = liveStats.value
  if (ls) {
    const pct = ls.completed ? (ls.errors / ls.completed) * 100 : 0
    return `${fmtInt(ls.errors)} / ${fmtInt(ls.completed)} (${pct.toFixed(1)}%)`
  }
  const total = requestsDone.value
  const pct = total ? (errorsDone.value / total) * 100 : 0
  return `${fmtInt(errorsDone.value)} / ${fmtInt(total)} (${pct.toFixed(1)}%)`
})
// 是否有错误（高亮 Errors 值）
const errorsHaveErr = computed(() => {
  const ls = liveStats.value
  if (ls) return (ls.errors || 0) > 0
  return errorsDone.value > 0
})
const reqRateText = computed(() => {
  const ls = liveStats.value
  if (ls) return `${fmtDec(ls.req_per_s)} requests/s`
  return elapsedSec.value > 0 ? `${fmtDec(requestsDone.value / elapsedSec.value)} requests/s` : '-'
})
const procRateText = computed(() => {
  const ls = liveStats.value
  if (ls && ls.t > 0) return `${fmtDec(ls.completed / ls.t)} records/s`
  return elapsedSec.value > 0 ? `${fmtDec(recDoneCases.value / elapsedSec.value, 3)} records/s` : '-'
})
const elapsedClock = computed(() => fmtClock(elapsedSec.value))
function fmtClock(sec) {
  if (!isFinite(sec) || sec < 0) return '0s'
  const s = Math.round(sec)
  const m = Math.floor(s / 60)
  const r = s % 60
  if (m >= 60) return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m`
  return `${m}m ${String(r).padStart(2, '0')}s`
}
const etaText = computed(() => {
  const ls = liveStats.value
  let pct = 0
  let elapsed = elapsedSec.value
  if (ls) {
    pct = ls.total ? (ls.completed / ls.total) * 100 : reqPct.value
    elapsed = ls.t || elapsed
  } else {
    pct = reqPct.value
  }
  if (pct <= 0 || elapsed <= 0) return '-'
  if (pct >= 100) return '0s'
  if (theTask.value?.status !== 'running') return '-'
  const remain = (elapsed / pct) * (100 - pct)
  if (remain < 120) return `${remain.toFixed(1)}s`
  return fmtClock(remain)
})

// ===== Real-Time Metrics 指标表（task_live 流，终端风格分组表） =====
const liveBuf = computed(() => (taskId.value ? test.liveMetrics[taskId.value] : null))
const hasLive = computed(() => !!(liveBuf.value && liveBuf.value.stats))
const liveUnitDiv = ref(1)
// 单位换算开关：ms/tok ↔ s/k，切换 liveUnitDiv（1 / 1000）
const liveUnit1000 = computed({
  get: () => liveUnitDiv.value === 1000,
  set: (v) => { liveUnitDiv.value = v ? 1000 : 1 },
})
// 当前并发：优先执行位置，其次末行
const currentConcurrency = computed(() => {
  const pos = taskId.value ? test.currentPos[taskId.value] : null
  if (pos && pos.concurrency != null) return Number(pos.concurrency)
  const rows = theTask.value?.rows || []
  if (rows.length) return Number(rows[rows.length - 1].concurrency)
  return 1
})
const na = () => 'N/A'
// 通用数值：convert=true 的 ms/tok 指标受单位换算开关影响（÷1000 → s/k）
const fmtMrk = (v, convert) => {
  if (v === undefined || v === null || isNaN(Number(v))) return na()
  const x = convert && liveUnitDiv.value > 1 ? Number(v) / liveUnitDiv.value : Number(v)
  return (Number.isInteger(x) ? x : +x.toFixed(2)).toLocaleString('en-US')
}
// 单表指标定义（顺序固定；special 表示派生计算指标）
const LIVE_METRIC_DEFS = [
  { key: 'TTFT', label: 'TTFT (ms)', src: 'TTFT', warn: 2000, convert: true },
  { key: 'TTST', label: 'TTST (ms)', src: 'TTST', warn: 3000, convert: true },
  { key: 'TPOT', label: 'TPOT (ms)', src: 'TPOT', convert: true },
  { key: 'ReqLatency', label: 'Req Latency (ms)', src: 'ReqLatency', warn: 10000, convert: true },
  { key: 'ITL', label: 'ITL (ms)', src: 'ITL', warn: 500, convert: true },
  { key: 'OutputTPSUser', label: 'Output TPS/User', src: 'OutputTPSPerUser', convert: false },
  { key: 'OSL', label: 'OSL (tokens)', src: 'OSL', convert: true },
  { key: 'ISL', label: 'ISL (tokens)', src: 'ISL', convert: true },
  { key: 'OutputTPS', label: 'Output TPS', src: 'OutputTPS', convert: false },
  { key: 'ReqSec', label: 'Req/sec', src: 'ReqSec', convert: false },
  { key: 'Requests', label: 'Requests', special: 'requests', convert: false },
]
const ORDER = ['avg', 'min', 'max', 'p99', 'p90', 'p50', 'std']
// 单元格类型：
//   - 可计算但未出值 → 灰色横线 '-'（rtm-dash）
//   - 不可计算 → 灰黑色 'N/A'（rtm-na）
//   - 已计算出值 → 蓝色（rtm-fill）
const dashCell = () => ({ t: '-', c: 'rtm-dash' })
const naCell = () => ({ t: 'N/A', c: 'rtm-na' })
const numCell = (v, convert) => (v === undefined || v === null || isNaN(Number(v))
  ? dashCell()
  : { t: fmtMrk(v, convert), c: 'rtm-fill' })
const naCellsN = (n) => Array.from({ length: n }, () => naCell())
// 单表扁平数据：始终返回全部 11 行；每格带类型（表头 + Metric 列默认保留）
const liveMetrics = computed(() => {
  const stats = (liveBuf.value && liveBuf.value.stats) || null
  const m = (stats && stats.metrics) || {}
  return LIVE_METRIC_DEFS.map((def) => {
    // Requests：仅 avg 可计算（已完成的请求总数），其余 6 列不可计算 → N/A
    if (def.special === 'requests') {
      return { key: def.key, label: def.label, n: 0, cols: [numCell(stats ? stats.completed : null, false), ...naCellsN(6)] }
    }
    // 分布统计行（含后端直算的 TPOT / Output TPS/User）：7 列均可计算
    const s = m[def.src] || {}
    return { key: def.key, label: def.label, n: s.n || 0, cols: ORDER.map((k) => numCell(s[k], def.convert)) }
  })
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

  // 在 groupRows 中，按 caseObj 的阈值条件（TTFT/TPOT 的 statistic + Output）全条件判断，
  // 满足所有配置条件的行里取并发最大的一行标记；全部阈值为 0 时不处理。
  // 阈值信息跟随 Groups 数据（每组独立配置），不跟随主任务；
  // 旧格式任务（cases 无每组阈值）回退任务级阈值，与分组阈值文本（caseThresholdText）一致
  const markBestRow = (groupRows, caseObj, flag) => {
    const tk = theTask.value || {}
    const legacy = (tk.cases || []).every(
      (x) => !Number(x?.ttft_threshold_ms) && !Number(x?.tpot_threshold_ms) && !Number(x?.output_throughput_threshold),
    )
    const cTtft = Number(caseObj?.ttft_threshold_ms) || 0
    const cTpot = Number(caseObj?.tpot_threshold_ms) || 0
    const cOut = Number(caseObj?.output_throughput_threshold) || 0
    // caseObj 阈值为有效正值时以每组为准；否则（0/未配置）旧格式任务回退任务级阈值
    const ttftThr = cTtft > 0 ? cTtft : (legacy ? Number(tk.ttft_threshold_ms) || 0 : 0)
    const tpotThr = cTpot > 0 ? cTpot : (legacy ? Number(tk.tpot_threshold_ms) || 0 : 0)
    const outThr = cOut > 0 ? cOut : (legacy ? Number(tk.output_throughput_threshold) || 0 : 0)
    const ttftStat = cTtft > 0 ? caseObj?.ttft_statistic || 'mean' : (legacy ? tk.ttft_statistic || 'mean' : 'mean')
    const tpotStat = cTpot > 0 ? caseObj?.tpot_statistic || 'mean' : (legacy ? tk.tpot_statistic || 'mean' : 'mean')
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
  // 由任务 cases 构建 caseKey → case（含每组阈值）
  const caseByKey = new Map()
  for (const c of theTask.value?.cases || []) {
    caseByKey.set(caseKeyOf(c), c)
  }
  const grouped = []
  for (const [key, groupRows] of groupMap) {
    groupRows.sort((a, b) => Number(a.concurrency) - Number(b.concurrency))
    const caseObj = caseByKey.get(key) || {}
    // 阈值模式：按每组自己的阈值全条件判断 → BestPerf
    if (theTask.value?.mode === 'threshold') {
      markBestRow(groupRows, caseObj, 'bestPerf')
    }
    // 本地面板阈值 → Best（沿用 tpot_mean + output，output 兼容后端原始键 output / 转换键 output_mean）
    markBestRow(
      groupRows,
      {
        ttft_statistic: 'mean',
        ttft_threshold_ms: 0,
        tpot_statistic: 'mean',
        tpot_threshold_ms: effectiveTpotThreshold.value,
        output_throughput_threshold: effectiveOutputThreshold.value,
      },
      'best'
    )
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
  // 阈值模式强制结束（下一次执行请求数超过 max_requests）：显示 Finish 而非 Done
  if (s === 'done' && theTask.value?.forced_finish) return t('statusFinish')
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
// Realtime Data 分组标题行：caseKey → 该组阈值条件文本（跟随 Groups 每组独立配置，与 Cases 面板同一口径）
const groupThresholdTexts = computed(() => {
  const map = {}
  for (const c of theTask.value?.cases || []) {
    map[caseKeyOf(c)] = caseThresholdText(c)
  }
  return map
})
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
  await loadPersistedLive(id)
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
    await loadPersistedLive(taskId.value)
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
  font-size: 14px;
  font-weight: 600;
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
}
.feature-card :deep(.ant-card-meta-description) {
  line-height: 20px;
  margin-top: 4px;
  color: var(--ant-color-text-secondary, #666);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.feature-icon {
  font-size: 48px;
  padding-top: 24px;
}
.fi-0 { background: linear-gradient(135deg, rgba(22,119,255,.08), transparent); }
.fi-1 { background: linear-gradient(135deg, rgba(82,196,26,.08), transparent); }
.fi-2 { background: linear-gradient(135deg, rgba(250,173,20,.08), transparent); }
.fi-3 { background: linear-gradient(135deg, rgba(114,46,209,.08), transparent); }
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
/* 底部 18px 空白 */
.row-5-spacer {
  height: 18px;
  flex-shrink: 0;
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
/* Mock 运行标识 */
.mock-env-tag {
  margin-left: 6px;
  vertical-align: middle;
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
  font-size: 12px;
  font-weight: 400;
  /* 宽度不够时伪隐藏（省略号） */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  max-width: 65%;
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
/* 阈值条件文本：并入分组标记右侧，宽度不够伪隐藏（省略号） */
.case-threshold {
  margin-left: auto;
  color: var(--ant-color-text-tertiary, #999);
  font-size: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex-shrink: 1;
  max-width: 55%;
}
/* Cases 面板：仅分组列表（case-list）内部滚动 */
.cases-panel :deep(.ant-card-body) {
  overflow: hidden;
}
.cases-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.case-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 0;
  /* 高度直接固定（无动画/平滑滚动） */
  scroll-behavior: auto;
}
.case-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  padding: 4px 0;
  border-bottom: 1px solid var(--ant-color-border, #f0f0f0);
}
.case-head {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
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
  /* 请求数单独一行：满宽（width:100%），受面板宽度约束换行多行，每行至少 8 个 */
  width: 100%;
  display: inline-flex;
  gap: 2px;
  flex-wrap: wrap;
  justify-content: flex-start;
}
.case-tags :deep(.ant-tag) {
  min-width: 26px;
  text-align: center;
  /* 请求数字体缩小 */
  font-size: 10px;
  line-height: 16px;
  padding: 0 5px;
}
/* 请求数可点击查看对应实时快照 */
.case-tags :deep(.req-tag) {
  cursor: pointer;
}
.case-tags :deep(.req-tag.req-selected) {
  outline: 2px solid #1677ff;
  outline-offset: 0;
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
  font-size: 10px; /* Logs：字体减小 */
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
  min-height: 13px;
}
/* 日志行高亮 */
.term-line.log-cmd {
  color: #8a8a8a;
}
.term-line.log-error {
  color: #f5222d;
  font-weight: 600;
}
.term-line.log-warn {
  color: #d48806;
}
.term-line.log-ok {
  color: #389e0d;
}
.term-line.log-head {
  color: #1677ff;
  font-weight: 600;
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

/* 第二行：Profile Progress(1/3) + Real-Time Metrics(2/3)，antd 对齐 */
.row-2 {
  display: flex;
  gap: 12px;
  align-items: stretch;
  margin-bottom: 12px;
}
.row-2 .profile-panel,
.row-2 .rtm-panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
/* 固定 1/3 : 2/3 分栏 */
.row-2 .profile-panel {
  flex: 0 0 33.333%;
  width: 33.333%;
}
.row-2 .rtm-panel {
  flex: 1 1 0;
  width: 66.666%;
  max-width: 66.666%;
}
.row-2 :deep(.ant-card-head) { padding: 0 12px; }
/* 面板 body 纵向填满卡片高度；Real-Time Metrics 高度 = Profile Progress 高度，超出的表格内部滚动 */
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
/* 表格行纵向拉伸，放大填满面板内容（表头 + 11 行指标均分高度） */
.row-2 .rtm-panel .rtm-grid { flex: 1; }
/* 面板 header 右侧灰色 case-请求数 */
.rt-case-text {
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
  /* 完整显示当前测试条件（case 名称-请求数），不截断 */
}

/* ===== Profile Progress 内部（antd 对齐） ===== */
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
.pp-status.pp-profiling {
  border-color: var(--ant-color-primary, #1677ff);
  background: var(--ant-color-primary-bg, #e6f4ff);
}
.pp-status.pp-completed {
  border-color: var(--ant-color-success, #52c41a);
  background: #f6ffed;
}
.pp-status.pp-error {
  border-color: var(--ant-color-error, #f5222d);
  background: #fff2f0;
}
.pp-status-label { color: var(--ant-color-text-secondary, #666); }
.pp-status-value { font-weight: 600; color: var(--ant-color-text, #000); }
.pp-err-icon { margin-left: auto; color: var(--ant-color-error, #f5222d); font-size: 14px; }

.pp-bars { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
.pp-bar-row { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.pp-bar-label { width: 82px; flex-shrink: 0; color: var(--ant-color-text-secondary, #666); }
.pp-bar-row :deep(.ant-progress) { flex: 1; }
.pp-bar-num { width: 34px; flex-shrink: 0; text-align: right; color: var(--ant-color-text, #000); }

/* 每个指标一行（label 左、值右） */
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

/* ===== Real-Time Metrics 分组指标表（小字体） ===== */
.rtm-tools { display: inline-flex; align-items: center; gap: 10px; font-size: 12px; }
.rtm-unit { font-size: 12px; }
.rtm-copy { color: var(--ant-color-primary, #1677ff); }
.rtm-group { margin-bottom: 2px; }
.rtm-group-head {
  font-size: 10px;
  font-weight: 600;
  color: var(--ant-color-primary, #1677ff);
  padding: 1px 2px;
}
/* 更紧凑的行，让表格正好填满面板高度 */
.rtm-grid {
  display: grid;
  grid-template-columns: 1.6fr repeat(7, 1fr);
  padding: 1px 6px;
  font-size: 10px; /* 表格小字体 */
  line-height: 1.25;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  align-items: center; /* 内容垂直居中，水平右对齐（ta-r） */
  border-bottom: 1px solid var(--ant-color-border-secondary, #f0f0f0);
}
.rtm-grid.rtm-head {
  background: var(--ant-color-fill-secondary, #fafafa);
  font-weight: 600;
  border-bottom: 1px solid var(--ant-color-border, #e8e8e8);
}
.rtm-group .rtm-grid:last-child { border-bottom: none; }
.rtm-grid.rtm-alert { background: #fff2f0; }
.ta-r { text-align: right; }
.rtm-name { font-weight: 500; }
/* 数据单元格类型：
   rtm-fill=已计算值(蓝) / rtm-dash=可计算未出值(灰横线) / rtm-na=不可计算(N/A 灰黑) */
.rtm-cell { font-weight: 600; }
.rtm-cell.rtm-fill { color: #1677ff; }
.rtm-cell.rtm-dash { color: #bfbfbf; font-weight: 400; }
.rtm-cell.rtm-na { color: #595959; font-weight: 400; }
.live-empty {
  padding: 18px 0;
  text-align: center;
  color: var(--ant-color-text-tertiary, #999);
  font-size: 12px;
}
.linkage-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.linkage-label {
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
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

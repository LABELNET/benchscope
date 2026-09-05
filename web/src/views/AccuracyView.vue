<template>
  <div class="accuracy-page">
    <!-- 无任务：介绍页（与 Performance 默认页结构/样式一致） -->
    <div v-if="!hasTasks" class="perf-intro">
      <div class="planned-card">
        <a-result :title="t('accIntroTitle')" :sub-title="t('accIntroDesc')">
          <template #icon>
            <span class="result-icon">
              <fund-outlined />
            </span>
          </template>
          <template #extra>
            <a-button type="primary" size="large" @click="goCreate">
              <template #icon><play-circle-outlined /></template>
              {{ t('accCreateTask') }}
            </a-button>
          </template>
        </a-result>
        <div class="features">
          <a-row :gutter="[24, 24]" justify="center">
            <a-col :xs="24" :sm="8" v-for="(feat, idx) in features" :key="feat.icon">
              <a-card size="small" class="feature-card" hoverable>
                <template #cover>
                  <div class="feature-icon" :class="`fi-${idx % 4}`">{{ feat.icon }}</div>
                </template>
                <a-card-meta :title="t(feat.title)" :description="t(feat.desc)" />
              </a-card>
            </a-col>
          </a-row>
        </div>
      </div>
    </div>

    <!-- 有任务：两栏布局（左侧任务列表 + 右侧详情） -->
    <template v-else>
      <div class="layout">
        <a-card size="small" class="list-card" :title="t('accTasks')">
          <template #extra>
            <a-space :size="4">
              <a-button size="small" @click="refresh">{{ t('refresh') }}</a-button>
              <a-button type="primary" size="small" @click="goCreate">{{ t('accCreateTask') }}</a-button>
            </a-space>
          </template>
          <a-table
            :columns="taskColumns"
            :data-source="taskList"
            :pagination="false"
            size="small"
            row-key="task_id"
            :scroll="{ y: 'calc(100vh - 260px)' }"
            :row-class-name="({ record }) => (record.task_id === activeTaskId ? 'row-active' : '')"
            :custom-row="(record) => ({ onClick: () => selectTask(record.task_id), style: { cursor: 'pointer' } })"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'model'">
                <span class="cell-main">{{ record.model }}</span>
                <a-tag v-if="record.lora_path" color="purple" style="margin-left:6px">LoRA</a-tag>
              </template>
              <template v-else-if="column.key === 'mode'">
                <a-tag :color="record.mode === 'native' ? 'green' : 'blue'">{{ record.mode === 'native' ? 'Native' : 'Serving' }}</a-tag>
              </template>
              <template v-else-if="column.key === 'status'">
                <a-badge :status="statusBadge(record.status)" :text="statusText(record.status)" />
              </template>
              <template v-else-if="column.key === 'accuracy'">
                <span v-if="record.result" class="acc-num">{{ record.result.accuracy }}%</span>
                <a-progress
                  v-else-if="record.status === 'running' && record.progress"
                  :percent="progressPct(record)" size="small" style="width:120px"
                />
                <span v-else>—</span>
              </template>
              <template v-else-if="column.key === 'actions'">
                <a-space :size="0">
                  <a-button v-if="record.status === 'running'" size="small" danger type="text" @click.stop="stopTask(record.task_id)">{{ t('stop') }}</a-button>
                  <a-button size="small" danger type="text" @click.stop="removeTask(record.task_id)">{{ t('delete') }}</a-button>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-card>

        <!-- 详情 -->
        <div v-if="active" class="detail">
          <a-card size="small" :title="active.name || active.task_id" class="detail-head block">
            <template #extra>
              <a-space :size="6">
                <a-tag :color="active.mode === 'native' ? 'green' : 'blue'">{{ active.mode === 'native' ? 'Native 原生' : 'Serving 链路' }}</a-tag>
                <a-badge :status="statusBadge(active.status)" :text="statusText(active.status)" />
                <a-button v-if="active.status === 'running'" size="small" danger @click="stopTask(active.task_id)">{{ t('stop') }}</a-button>
              </a-space>
            </template>
            <a-descriptions size="small" :column="4">
              <a-descriptions-item :label="t('accModel')">
                {{ active.model }}<a-tag v-if="active.lora_path" color="purple" style="margin-left:6px">LoRA</a-tag>
              </a-descriptions-item>
              <a-descriptions-item :label="t('accDataset')">{{ active.dataset_name || active.dataset_id }}</a-descriptions-item>
              <a-descriptions-item :label="t('accSeed')">{{ active.seed }}</a-descriptions-item>
              <a-descriptions-item :label="t('accTemp')">{{ active.temperature }} / {{ active.top_p }}</a-descriptions-item>
            </a-descriptions>
            <a-progress
              v-if="active.status === 'running' && active.progress"
              :percent="progressPct(active)"
              :format="() => `${active.progress.done}/${active.progress.total}`"
              class="run-progress"
            />
          </a-card>

          <!-- 核心指标 -->
          <a-card v-if="result" size="small" :title="t('accMetrics')" class="block">
            <a-row :gutter="12">
              <a-col :xs="12" :sm="8" :md="4" v-for="m in metricCards" :key="m.label">
                <div class="metric-box">
                  <div class="metric-value" :class="m.accent">{{ m.value }}</div>
                  <div class="metric-label">{{ m.label }}</div>
                </div>
              </a-col>
            </a-row>
            <div v-if="datasetMetrics(result)" class="dm-row">
              <a-tag v-for="(v, k) in datasetMetrics(result)" :key="k" color="geekblue">{{ k }}: {{ v === null ? '—' : v }}</a-tag>
            </div>
            <div class="concl-row">
              <span>{{ t('accConclusion') }}：</span>
              <a-tag :color="conclColor(result.conclusion)">{{ result.conclusion || '—' }}</a-tag>
              <template v-if="errorTagSummary(result)">
                <a-tag v-for="(n, tag) in errorTagSummary(result)" :key="tag" color="orange">{{ tag }} × {{ n }}</a-tag>
              </template>
            </div>
          </a-card>

          <!-- Token 统计（Serving 专属） -->
          <a-card v-if="result && result.tokens" size="small" :title="t('accTokenReport')" class="block">
            <a-descriptions size="small" :column="5">
              <a-descriptions-item :label="t('accTokPrompt')">{{ result.tokens.prompt_tokens_total }}</a-descriptions-item>
              <a-descriptions-item :label="t('accTokCompletion')">{{ result.tokens.completion_tokens_total }}</a-descriptions-item>
              <a-descriptions-item :label="t('accTokTotal')">{{ result.tokens.total_tokens }}</a-descriptions-item>
              <a-descriptions-item :label="t('accTokAvgIn')">{{ result.tokens.avg_prompt_tokens_per_sample }}</a-descriptions-item>
              <a-descriptions-item :label="t('accTokAvgOut')">{{ result.tokens.avg_completion_tokens_per_sample }}</a-descriptions-item>
            </a-descriptions>
            <div v-if="result.estimate_vs_actual" class="dm-row">
              <a-tag color="cyan">{{ t('accEstVsActual') }}：{{ result.estimate_vs_actual.estimate_total }} → {{ result.estimate_vs_actual.actual_total }}
                ({{ result.estimate_vs_actual.deviation_pct === null || result.estimate_vs_actual.deviation_pct === undefined ? '—' : (result.estimate_vs_actual.deviation_pct > 0 ? '+' : '') + result.estimate_vs_actual.deviation_pct + '%' }})</a-tag>
            </div>
          </a-card>

          <!-- 基线对标 -->
          <a-card v-if="result && result.benchmark" size="small" :title="t('accBenchmark')" class="block">
            <a-space wrap size="middle">
              <a-tag :color="gradeColor(result.benchmark.grade)" class="grade-tag">{{ t('accGrade') }} {{ result.benchmark.grade }}</a-tag>
              <span>{{ result.benchmark.baseline_used?.name }}：{{ result.benchmark.score }} vs {{ result.benchmark.baseline_used?.score }}
                <b :style="{ color: result.benchmark.diff_pp >= 0 ? 'var(--ant-color-success)' : 'var(--ant-color-error)' }">
                  ({{ result.benchmark.diff_pp >= 0 ? '+' : '' }}{{ result.benchmark.diff_pp }}pp)</b>
              </span>
              <span>{{ t('accRankPct') }}：{{ result.benchmark.rank_pct ?? '—' }}%</span>
              <a-tag :color="result.benchmark.conclusion.startsWith('优于') ? 'green' : (result.benchmark.conclusion.startsWith('持平') ? 'gold' : 'red')">
                {{ result.benchmark.conclusion }}
              </a-tag>
            </a-space>
            <div ref="radarRef" class="radar-chart"></div>
          </a-card>

          <!-- 分学科 -->
          <a-card v-if="result && result.subjects && result.subjects.length" size="small" :title="t('accSubjects')" class="block">
            <a-table :columns="subjectColumns" :data-source="result.subjects" :pagination="false" size="small" row-key="subject" />
          </a-card>

          <!-- 实时日志 -->
          <a-card size="small" :title="t('accConsole')" class="block">
            <pre ref="consoleRef" class="console">{{ logs.join('') || ' ' }}</pre>
          </a-card>

          <!-- 样本溯源 -->
          <a-card size="small" class="block" :title="t('accSamples')">
            <template #extra>
              <a-space :size="6">
                <a-radio-group v-model:value="sampleFilter" size="small" button-style="solid">
                  <a-radio-button value="all">{{ t('accSampleAll') }}</a-radio-button>
                  <a-radio-button value="wrong">{{ t('accSampleWrong') }}</a-radio-button>
                  <a-radio-button value="invalid">{{ t('accSampleInvalid') }}</a-radio-button>
                </a-radio-group>
                <a-button size="small" @click="downloadWrong">{{ t('accExportWrong') }}</a-button>
              </a-space>
            </template>
            <a-table
              :columns="sampleColumns" :data-source="samples" :loading="samplesLoading"
              :pagination="{ pageSize: 10, showSizeChanger: false }" size="small" row-key="index"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <a-tag :color="record.status === 'correct' ? 'green' : record.status === 'wrong' ? 'red' : 'orange'">
                    {{ statusLabel(record.status) }}<span v-if="record.error_tag"> · {{ record.error_tag }}</span>
                  </a-tag>
                </template>
                <template v-else-if="column.key === 'prompt'">
                  <span class="clamp2">{{ record.prompt }}</span>
                </template>
                <template v-else-if="column.key === 'output'">
                  <a-tooltip :title="record.output"><span class="clamp2">{{ record.output }}</span></a-tooltip>
                </template>
                <template v-else-if="column.key === 'tokens'">
                  <span class="tok-cell">{{ record.tokens?.prompt_tokens || 0 }} / {{ record.tokens?.completion_tokens || 0 }}</span>
                </template>
              </template>
            </a-table>
          </a-card>
        </div>

        <div v-else class="detail empty-detail">
          <a-empty :description="t('accSelectTask')" />
        </div>
      </div>
    </template>

    <!-- 创建精度任务：敬请期待 -->
    <a-modal v-model:open="createOpen" :title="t('comingSoon')" :footer="null" :width="360">
      <p class="coming-soon-tip">{{ t('comingSoon') }}</p>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { FundOutlined, PlayCircleOutlined } from '@ant-design/icons-vue'
import * as echarts from 'echarts'
import { api } from '@/api'
import { t } from '@/i18n'
import { useAccuracyStore } from '@/store/accuracy'

const store = useAccuracyStore()
const createOpen = ref(false)
const consoleRef = ref(null)
const radarRef = ref(null)
let radarChart = null
const sampleFilter = ref('all')
const samples = ref([])
const samplesLoading = ref(false)

const hasTasks = computed(() => store.taskList.length > 0)
const taskList = computed(() => store.taskList)
const active = computed(() => store.activeTask)
const activeTaskId = computed(() => store.activeTaskId)
const result = computed(() => active.value?.result || null)
const logs = computed(() => store.activeLogs)

const features = [
  { icon: '🎯', title: 'accFeat1Title', desc: 'accFeat1Desc' },
  { icon: '⚖️', title: 'accFeat2Title', desc: 'accFeat2Desc' },
  { icon: '🚨', title: 'accFeat3Title', desc: 'accFeat3Desc' },
]

const taskColumns = computed(() => [
  { title: t('accTaskId'), dataIndex: 'task_id', key: 'task_id', width: 132 },
  { title: t('accModel'), key: 'model' },
  { title: t('accMode'), key: 'mode', width: 82 },
  { title: t('accDataset'), key: 'dataset_name', width: 96, ellipsis: true },
  { title: t('accStatus'), key: 'status', width: 88 },
  { title: t('accAccuracy'), key: 'accuracy', width: 120 },
  { title: '', key: 'actions', width: 96 },
])

const subjectColumns = computed(() => [
  { title: t('accSubject'), dataIndex: 'subject', key: 'subject' },
  { title: t('accCorrect'), dataIndex: 'correct', key: 'correct', width: 100 },
  { title: t('accTotal'), dataIndex: 'total', key: 'total', width: 100 },
  { title: t('accAccuracy'), dataIndex: 'accuracy', key: 'accuracy', width: 120 },
])

const sampleColumns = computed(() => [
  { title: '#', dataIndex: 'index', key: 'index', width: 60 },
  { title: t('accSubject'), dataIndex: 'subject', key: 'subject', width: 80 },
  { title: t('accPromptCol'), key: 'prompt', ellipsis: true },
  { title: t('accOutputCol'), key: 'output', ellipsis: true },
  { title: t('accAnswerCol'), dataIndex: 'answer', key: 'answer', width: 90, ellipsis: true },
  { title: t('accTokCol'), key: 'tokens', width: 90 },
  { title: t('accStatusCol'), key: 'status', width: 160 },
])

const metricCards = computed(() => {
  const r = result.value || {}
  return [
    { label: t('accAccuracy'), value: r.accuracy != null ? `${r.accuracy}%` : '—', accent: 'accent-blue' },
    { label: t('accPassRate'), value: r.pass_rate != null ? `${r.pass_rate}%` : '—', accent: 'accent-cyan' },
    { label: t('accTotal'), value: r.total_samples ?? '—', accent: '' },
    { label: t('accCorrect'), value: r.correct_samples ?? '—', accent: 'accent-green' },
    { label: t('accWrong'), value: r.wrong_samples ?? '—', accent: 'accent-red' },
    { label: t('accInvalid'), value: r.invalid_samples ?? '—', accent: 'accent-orange' },
  ]
})

function statusBadge(status) {
  return { running: 'processing', done: 'success', error: 'error', stopped: 'warning', pending: 'default' }[status] || 'default'
}
function statusText(status) {
  return { running: t('statusRunning'), done: t('statusDone'), error: t('statusError'), stopped: t('statusStopped'), pending: t('statusPending') }[status] || status
}
function statusLabel(status) {
  return { correct: t('accSampleCorrect'), wrong: t('accSampleWrong'), invalid: t('accSampleInvalid') }[status] || status
}
function progressPct(task) {
  const p = task.progress || {}
  if (!p.total) return 0
  return Math.round(((p.done || 0) / p.total) * 100)
}
function datasetMetrics(r) {
  const dm = r.dataset_metrics || {}
  return Object.keys(dm).length ? dm : null
}
function conclColor(c) {
  return c === '合格' ? 'green' : c === '精度下跌' ? 'red' : 'orange'
}
function gradeColor(g) {
  return { S: 'purple', A: 'green', B: 'gold', C: 'red' }[g] || 'default'
}
function errorTagSummary(r) {
  const s = r.error_tag_summary || {}
  return Object.keys(s).length ? s : null
}

async function refresh() { await store.loadTasks() }
async function selectTask(taskId) {
  store.setActive(taskId)
  await store.loadTask(taskId) // 列表快照不含 result，拉取完整详情
  loadSamples()
}
function goCreate() { createOpen.value = true }
async function stopTask(taskId) {
  try { await api.stopAccTask(taskId); message.info(t('accStopSent')) } catch (e) { message.error(e.message) }
}
async function removeTask(taskId) {
  try {
    await store.deleteTask(taskId)
    message.success(t('deleted'))
    if (!store.activeTaskId) samples.value = []
  } catch (e) { message.error(e.message) }
}
async function loadSamples() {
  if (!active.value) return
  samplesLoading.value = true
  try {
    const resp = await api.listAccSamples(active.value.task_id, { filter: sampleFilter.value, limit: 200, offset: 0 })
    samples.value = resp.samples || []
  } catch { samples.value = [] } finally { samplesLoading.value = false }
}
function downloadWrong() {
  if (!active.value) return
  window.open(api.exportAccSamplesUrl(active.value.task_id, 'wrong'))
}

watch(sampleFilter, loadSamples)

// 能力雷达图（知识 / 数学 / 代码 / 对话）
function renderRadar() {
  if (!radarRef.value || !result.value?.benchmark) return
  const radar = result.value.benchmark.radar || {}
  const dims = ['知识', '数学', '代码', '对话']
  const scale = result.value.benchmark.metric === 'mt_bench' ? 10 : 1 // mt_bench 0-10 → 0-100 口径
  if (!radarChart) {
    radarChart = echarts.init(radarRef.value)
  }
  radarChart.setOption({
    radar: {
      indicator: dims.map((d) => ({ name: d, max: 100 })),
      radius: '65%',
      axisName: { color: 'var(--ant-color-text-secondary, #999)', fontSize: 11 },
    },
    series: [{
      type: 'radar',
      areaStyle: { opacity: 0.25 },
      data: [{
        value: dims.map((d) => (radar[d] == null ? 0 : +(radar[d] * scale).toFixed(1))),
        name: result.value.benchmark.baseline_used?.name || '',
      }],
    }],
  }, true)
}
watch(result, () => nextTick(renderRadar), { deep: false })
function onResize() { radarChart && radarChart.resize() }
window.addEventListener('resize', onResize)
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (radarChart) { radarChart.dispose(); radarChart = null }
})
watch(active, (task, old) => {
  // 自动选中首个任务时补拉完整详情（含 result）
  if (task && task.result == null && (!old || task.task_id !== old.task_id)) {
    store.loadTask(task.task_id).then(loadSamples)
    return
  }
  if (sampleFilter.value !== 'all') sampleFilter.value = 'all'
  else loadSamples()
})
watch(logs, () => {
  nextTick(() => {
    if (consoleRef.value) consoleRef.value.scrollTop = consoleRef.value.scrollHeight
  })
})

onMounted(async () => {
  await store.loadTasks()
  if (!store.activeTaskId && store.taskList.length) store.setActive(store.taskList[0].task_id)
  loadSamples()
})
</script>

<style scoped>
.accuracy-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: auto;
  padding: 16px 20px;
  background: transparent;
}

/* ===== 无任务介绍页（与 Performance 默认页一致） ===== */
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
.result-icon {
  font-size: 72px;
  color: var(--ant-color-primary, #1677ff);
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
}
.feature-icon {
  font-size: 48px;
  padding-top: 24px;
}
.fi-0 { background: linear-gradient(135deg, rgba(22,119,255,.08), transparent); }
.fi-1 { background: linear-gradient(135deg, rgba(82,196,26,.08), transparent); }
.fi-2 { background: linear-gradient(135deg, rgba(250,173,20,.08), transparent); }
.fi-3 { background: linear-gradient(135deg, rgba(114,46,209,.08), transparent); }

/* ===== 有任务：两栏布局 ===== */
.layout { display: flex; gap: 14px; align-items: flex-start; flex: 1; min-height: 0; }
.list-card { width: 400px; flex-shrink: 0; border-radius: 10px; }
.list-card :deep(.ant-card-body) { padding: 8px; }
.list-card :deep(.ant-table-thead > tr > th) { font-size: 12px; }
.cell-main { font-weight: 600; }
.acc-num { font-weight: 700; color: var(--ant-color-primary); }
.detail { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px; }
.empty-detail { padding: 60px 0; text-align: center; }
.block { border-radius: 10px; width: 100%; }
.block :deep(.ant-card-head) { min-height: 40px; }
.run-progress { margin-top: 10px; }

/* ===== 核心指标 ===== */
.metric-box {
  text-align: center; padding: 12px 6px; height: 100%;
  border: 1px solid var(--ant-color-border-secondary); border-radius: 10px;
  background: var(--ant-color-bg-layout, #fafafa);
  transition: transform .15s ease;
}
.metric-box:hover { transform: translateY(-2px); }
.metric-value { font-size: 24px; font-weight: 700; line-height: 1.2; }
.metric-label { font-size: 12px; color: var(--ant-color-text-secondary); margin-top: 4px; }
.accent-blue { color: var(--ant-color-primary); }
.accent-cyan { color: var(--ant-color-cyan); }
.accent-green { color: var(--ant-color-success); }
.accent-red { color: var(--ant-color-error); }
.accent-orange { color: var(--ant-color-warning); }
.dm-row { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 4px; }
.concl-row { margin-top: 14px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.grade-tag { font-size: 14px; font-weight: 700; padding: 2px 10px; }
.radar-chart { width: 100%; max-width: 360px; height: 220px; margin: 8px auto 0; }
.coming-soon-tip {
  text-align: center;
  margin: 16px 0;
  font-size: 15px;
  color: var(--ant-color-text-secondary, #666);
}

/* ===== 控制台 / 样本 ===== */
.console {
  background: var(--ant-color-bg-layout, #141414);
  color: #d6deeb; font-size: 12px; line-height: 1.5;
  max-height: 240px; overflow: auto; margin: 0; padding: 10px;
  border-radius: 6px; white-space: pre-wrap; word-break: break-all;
}
.clamp2 {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; font-size: 12px;
}
.tok-cell { font-size: 12px; color: var(--ant-color-text-secondary); }
:deep(.row-active) td { background: var(--ant-color-primary-bg); }

/* 响应式：窄屏回退纵向 */
@media (max-width: 900px) {
  .layout { flex-direction: column; }
  .list-card { width: 100%; }
}
</style>

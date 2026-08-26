<template>
  <div class="datas-page">
    <!-- 顶部：Perfs / Evals 双 Tab -->
    <a-tabs v-model:activeKey="activeTab" class="datas-tabs" size="small">
      <!-- Perfs 记录 -->
      <a-tab-pane :key="'perfs'" :tab="t('perfsTab')">
        <div class="tab-toolbar">
          <span class="best-badge" v-if="bestRecord">
            🏆 {{ t('bestRecord') }}: {{ bestRecord.run_id }}（TPOT {{ bestRecord.metrics.tpot_mean }}ms）
          </span>
          <a-space>
            <a-button type="link" size="small" @click="loadRuns">
              <template #icon><reload-outlined /></template>
              {{ t('refresh') }}
            </a-button>
            <a-button type="link" size="small" :disabled="runs.length < 2" @click="compareOpen = true">
              {{ t('compareAnalysis') }}
            </a-button>
          </a-space>
        </div>

        <a-table
          class="plain-table"
          :columns="perfColumns"
          :data-source="runs"
          :loading="loading"
          size="small"
          row-key="run_id"
          :pagination="{ pageSize: 10, showSizeChanger: false }"
          :row-class-name="rowClassName"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'run_id'">
              <span class="cell-run">{{ record.run_id }}</span>
              <a-tag v-if="isBestRecord(record)" color="gold" size="small">Best</a-tag>
            </template>
            <template v-if="column.key === 'model'">
              <span class="cell-text">{{ record.meta?.model || '-' }}</span>
            </template>
            <template v-if="column.key === 'framework'">
              <span class="cell-framework" :class="record.meta?.framework === 'vLLM' ? 'fw-vllm' : 'fw-sglang'">
                {{ record.meta?.framework || '-' }}
              </span>
            </template>
            <template v-if="column.key === 'status'">
              <span class="cell-status" :class="'st-' + (record.meta?.status || '')">{{ statusText(record.meta?.status) }}</span>
            </template>
            <template v-if="column.key === 'time'">
              <span class="cell-text">{{ record.meta?.started_at || '-' }}</span>
            </template>
            <template v-if="column.key === 'tpot'">
              <span class="cell-text">{{ avgTpot(record) }}</span>
            </template>
            <template v-if="column.key === 'actions'">
              <span class="cell-action" @click="openDetail(record.run_id)">{{ t('detail') }}</span>
            </template>
          </template>
        </a-table>
      </a-tab-pane>

      <!-- Evals 记录 -->
      <a-tab-pane :key="'evals'" :tab="t('evalsTab')">
        <p class="section-desc">{{ t('evalsHint') }}</p>
        <a-empty :description="t('accuracyPlanned')" />
      </a-tab-pane>
    </a-tabs>

    <!-- 性能数据详情抽屉：mean / median / p99 -->
    <a-drawer
      v-model:open="detailOpen"
      :width="760"
      placement="right"
      :title="`${t('detail')}: ${detailRunId}`"
    >
      <a-spin :spinning="detailLoading">
        <template v-if="detailRows.length">
          <div class="detail-summary">
            <span class="detail-sum-item">{{ t('rows') }}: {{ detailRows.length }}</span>
            <span class="detail-sum-item">{{ t('mean') }}/{{ t('median') }}/P99</span>
          </div>
          <a-table
            :columns="detailColumns"
            :data-source="detailRows"
            size="small"
            row-key="label-concurrency"
            :pagination="false"
            class="plain-table"
          />
        </template>
        <a-empty v-else-if="!detailLoading" :description="t('noData')" />
      </a-spin>
    </a-drawer>

    <!-- 记录对比分析 -->
    <a-modal
      v-model:open="compareOpen"
      :title="t('compareAnalysis')"
      width="900px"
      :footer="null"
      :destroy-on-close="true"
    >
      <div class="compare-toolbar">
        <a-select
          v-model:value="compareIds"
          mode="multiple"
          :max-tag-count="4"
          style="width: 420px"
          :placeholder="t('compareSelect')"
          :options="compareOptions"
        />
      </div>
      <a-table
        v-if="compareRows.length"
        :columns="compareColumns"
        :data-source="compareRows"
        size="small"
        row-key="metric"
        :pagination="false"
        class="plain-table compare-table"
      />
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { api } from '@/api'
import { t } from '@/i18n'

const activeTab = ref('perfs')
const loading = ref(false)
const runs = ref([])
const detailOpen = ref(false)
const detailRunId = ref('')
const detailLoading = ref(false)
const detailRows = ref([])
const compareOpen = ref(false)
const compareIds = ref([])

// 最佳测试记录：全量 rows 中 tpot_mean 最小的记录
const bestRecord = computed(() => {
  let best = null
  for (const r of runs.value) {
    for (const row of r.rows || []) {
      const tpot = row.metrics?.tpot_mean
      if (tpot === undefined || tpot === null) continue
      if (!best || Number(tpot) < Number(best.metrics.tpot_mean)) {
        best = { run_id: r.run_id, metrics: row.metrics }
      }
    }
  }
  return best
})

function isBestRecord(record) {
  return bestRecord.value && bestRecord.value.run_id === record.run_id
}

function rowClassName(record) {
  return isBestRecord(record) ? 'best-row' : ''
}

function avgTpot(record) {
  const values = (record.rows || []).map((r) => r.metrics?.tpot_mean).filter((v) => v !== undefined && v !== null)
  if (!values.length) return '-'
  return (values.reduce((a, b) => a + Number(b), 0) / values.length).toFixed(2)
}

function statusText(s) {
  return s === 'done' ? t('done') : s === 'error' ? t('error') : s === 'stopped' ? t('stopped') : t('running')
}

const perfColumns = [
  { title: 'Run ID', key: 'run_id', width: 150 },
  { title: 'Model', key: 'model', width: 180 },
  { title: 'Framework', key: 'framework', width: 100 },
  { title: 'Status', key: 'status', width: 90 },
  { title: 'Time', key: 'time', width: 170 },
  { title: 'Avg TPOT (ms)', key: 'tpot', width: 110 },
  { title: '', key: 'actions', width: 80 },
]

// 详情列：每行一个 case×concurrency，展示 mean/median/p99
const detailColumns = [
  { title: 'Case', key: 'label', width: 140 },
  { title: 'Concurrency', key: 'concurrency', width: 90 },
  { title: 'Output mean', key: 'output_mean', width: 110 },
  { title: 'TTFT mean/med/p99', key: 'ttft', width: 150 },
  { title: 'TPOT mean/med/p99', key: 'tpot', width: 150 },
  { title: 'ITL mean/med/p99', key: 'itl', width: 150 },
]

function fmtMetric(m, key) {
  const v = m ? m[key] : undefined
  return v === undefined || v === null ? '-' : Number(v).toFixed(2)
}

function fmtTriple(m, base) {
  const mean = fmtMetric(m, `${base}_mean`)
  const median = fmtMetric(m, `${base}_median`)
  const p99 = fmtMetric(m, `${base}_p99`)
  return `${mean} / ${median} / ${p99}`
}

function detailTableRows(records) {
  return records.map((r) => ({
    key: `${r.label}-${r.concurrency}`,
    label: r.label,
    concurrency: r.concurrency,
    output_mean: fmtMetric(r.metrics, 'output_mean'),
    ttft: fmtTriple(r.metrics, 'ttft'),
    tpot: fmtTriple(r.metrics, 'tpot'),
    itl: fmtTriple(r.metrics, 'itl'),
  }))
}

async function openDetail(runId) {
  detailRunId.value = runId
  detailOpen.value = true
  detailLoading.value = true
  detailRows.value = []
  try {
    const resp = await api.getRun(runId)
    // getRun 返回 { run: {...rows} }，兼容直接返回 rows 的形式
    const records = ((resp.run?.rows || resp.rows) || []).filter((r) => r.metrics)
    detailRows.value = detailTableRows(records)
  } catch (e) {
    detailRows.value = []
  } finally {
    detailLoading.value = false
  }
}

// 对比分析
const compareOptions = computed(() => runs.value.map((r) => ({ value: r.run_id, label: `${r.run_id} (${r.meta?.model || '-'})` })))
const compareRows = computed(() => {
  const selected = runs.value.filter((r) => compareIds.value.includes(r.run_id))
  if (!selected.length) return []
  const metrics = ['output', 'total', 'ttft', 'tpot', 'itl']
  const rows = []
  for (const m of metrics) {
    const row = { key: m, metric: m }
    for (const r of selected) {
      const vals = (r.rows || []).map((x) => x.metrics?.[`${m}_mean`]).filter((v) => v !== undefined && v !== null)
      row[r.run_id] = vals.length ? (vals.reduce((a, b) => a + Number(b), 0) / vals.length).toFixed(2) : '-'
    }
    rows.push(row)
  }
  return rows
})

const compareColumns = computed(() => {
  const cols = [{ title: 'Metric', key: 'metric', width: 140, fixed: 'left' }]
  for (const r of runs.value) {
    if (compareIds.value.includes(r.run_id)) {
      cols.push({ title: `${r.run_id} (${r.meta?.model || '-'})`, key: r.run_id, width: 180 })
    }
  }
  return cols
})

async function loadRuns() {
  loading.value = true
  try {
    const resp = await api.listRuns()
    runs.value = resp.runs || []
  } finally {
    loading.value = false
  }
}

onMounted(loadRuns)
</script>

<style scoped>
.datas-page {
  height: 100%;
  overflow: auto;
  padding: 16px 20px;
}
.datas-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 8px;
}
.tab-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.best-badge {
  font-size: 12px;
  color: #ad6800;
  background: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: 8px;
  padding: 2px 10px;
}
.section-desc {
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
  margin: 0 0 16px;
}

/* 表格纯文本样式（与 Dashboard 一致） */
.plain-table :deep(.ant-table) { font-size: 12px; }
.plain-table :deep(.ant-table-thead > tr > th) { font-size: 12px; }
.cell-run { color: var(--ant-color-text, rgba(0, 0, 0, 0.88)); }
.cell-text { color: var(--ant-color-text, rgba(0, 0, 0, 0.88)); }
.cell-framework.fw-vllm { color: #1677ff; }
.cell-framework.fw-sglang { color: #722ed1; }
.cell-status.st-done { color: #52c41a; }
.cell-status.st-error { color: #f5222d; }
.cell-status.st-stopped { color: #fa8c16; }
.cell-status.st-running { color: #1677ff; }
.cell-status.st-pending { color: var(--ant-color-text-secondary, #666); }
.cell-action {
  color: #1677ff;
  cursor: pointer;
  font-size: 12px;
}
.best-row > td {
  background: #fffbe6 !important;
}

.detail-summary {
  display: flex;
  gap: 16px;
  margin-bottom: 10px;
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
}
.compare-toolbar {
  margin-bottom: 12px;
}
.compare-table {
  max-height: 420px;
  overflow: auto;
}
</style>

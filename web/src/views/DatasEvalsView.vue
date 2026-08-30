<template>
  <div class="evals-page">
    <a-card size="small" :title="t('evalsRecords')" class="list-card">
      <template #extra>
        <a-space>
          <a-button size="small" :loading="loading" @click="refresh">{{ t('refresh') }}</a-button>
          <a-button size="small" :disabled="selectedIds.length !== 2" @click="doCompare">{{ t('evalsCompare') }}</a-button>
        </a-space>
      </template>

      <a-table
        :columns="columns" :data-source="runs" :loading="loading"
        :pagination="{ pageSize: 15, showSizeChanger: false }" size="small"
        row-key="run_id" :row-selection="{ selectedRowKeys: selectedIds, onChange: onSelectChange }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'model'">
            <span>{{ record.meta?.model || '—' }}</span>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-badge :status="badge(record.meta?.status)" :text="record.meta?.status || '—'" />
          </template>
          <template v-else-if="column.key === 'summary'">
            <a-tag v-if="summaryOf(record)" color="geekblue">{{ summaryOf(record) }}</a-tag>
            <span v-else>—</span>
          </template>
          <template v-else-if="column.key === 'actions'">
            <a-space>
              <a-button size="small" type="link" @click="openDetail(record)">{{ t('evalsDetail') }}</a-button>
              <a-button size="small" type="link" @click="downloadLog(record)">{{ t('evalsLog') }}</a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 对比面板（含 Native vs Serving 一致性差值） -->
    <a-card v-if="compareData" size="small" :title="t('evalsCompareTitle')" class="compare-card">
      <template #extra>
        <a-button size="small" type="text" @click="compareData = null">{{ t('close') }}</a-button>
      </template>
      <a-table :columns="cmpColumns" :data-source="compareData.items" :pagination="false" size="small" row-key="task_id">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'mode'">
            <a-tag :color="record.mode === 'native' ? 'green' : 'blue'">{{ record.mode }}</a-tag>
          </template>
          <template v-else-if="column.key === 'metric_value'">
            <b>{{ record.metric_value ?? '—' }}%</b>
          </template>
        </template>
      </a-table>
      <div v-for="g in compareData.groups" :key="g.key" class="consist-row">
        <template v-if="g.consistency">
          <a-tag color="geekblue">Native vs Serving · {{ g.dataset_id }}</a-tag>
          <span>
            {{ g.consistency.native_value }}% → {{ g.consistency.serving_value }}%
            <b :style="{ color: Math.abs(g.consistency.diff_pp) <= 2 ? 'var(--ant-color-success)' : 'var(--ant-color-error)' }">
              ({{ g.consistency.diff_pp >= 0 ? '+' : '' }}{{ g.consistency.diff_pp }}pp)
            </b>
          </span>
          <a-tag :color="g.consistency.conclusion === '训推一致' ? 'green' : 'orange'">{{ g.consistency.conclusion }}</a-tag>
        </template>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { api } from '@/api'
import { t } from '@/i18n'

const loading = ref(false)
const runs = ref([])
const selectedIds = ref([])
const compareData = ref(null)

const columns = computed(() => [
  { title: t('evalsRunId'), dataIndex: 'run_id', key: 'run_id', width: 180 },
  { title: t('accModel'), key: 'model' },
  { title: t('accStatus'), key: 'status', width: 110 },
  { title: t('evalsSummary'), key: 'summary', width: 220 },
  { title: t('evalsStarted'), dataIndex: ['meta', 'started_at'], key: 'started_at', width: 170 },
  { title: '', key: 'actions', width: 140 },
])

const cmpColumns = computed(() => [
  { title: t('accTaskId'), dataIndex: 'task_id', width: 170 },
  { title: t('accMode'), key: 'mode', width: 90 },
  { title: t('accModel'), dataIndex: 'model' },
  { title: t('accDataset'), dataIndex: 'dataset_name' },
  { title: t('accMetricMain'), key: 'metric_value', width: 110 },
  { title: t('accCorrect'), dataIndex: 'correct_samples', width: 90 },
  { title: t('accTotal'), dataIndex: 'total_samples', width: 90 },
  { title: t('accConclusion'), dataIndex: 'conclusion', width: 100 },
])

function summaryOf(record) {
  const s = record.summary
  if (s && s.accuracy != null) return `${s.accuracy}% · ${s.total_samples} 样本`
  return null
}
function badge(status) {
  return { running: 'processing', done: 'success', error: 'error', stopped: 'warning' }[status] || 'default'
}
function onSelectChange(keys) {
  selectedIds.value = keys.slice(-2) // 最多选两个（对比用）
}

async function refresh() {
  loading.value = true
  try {
    const resp = await api.listRuns()
    // evals 记录 = run 目录位于 evals 下（dir 含 /evals/），或 run.json kind=eval
    runs.value = (resp.runs || []).filter((r) => r.dir.includes('/evals') || r.meta?.kind === 'eval')
  } catch (e) { message.error(e.message) } finally { loading.value = false }
}

async function doCompare() {
  try {
    compareData.value = await api.compareAccTasks(selectedIds.value)
  } catch (e) { message.error(e.message) }
}

function openDetail(record) {
  window.open(`/#/accuracy?task=${record.run_id}`, '_blank')
}
function downloadLog(record) {
  const logFile = (record.files || []).find((f) => f.name.startsWith('eval_') && f.name.endsWith('.log'))
  if (logFile) window.open(api.downloadUrl(record.run_id, logFile.name))
  else message.info(t('evalsNoLog'))
}

onMounted(refresh)
</script>

<style scoped>
.evals-page { height: 100%; overflow: auto; padding: 12px; display: flex; flex-direction: column; gap: 12px; }
.compare-card { width: 100%; }
.consist-row { margin-top: 10px; display: flex; align-items: center; gap: 10px; font-size: 13px; }
</style>

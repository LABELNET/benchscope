<template>
  <div class="dashboard-page">
    <!-- 统计卡片 -->
    <a-row :gutter="16" class="stats-row">
      <a-col :xs="12" :sm="6" v-for="card in statCards" :key="card.key">
        <a-card size="small" class="stat-card">
          <a-statistic
            :title="card.title"
            :value="card.value"
            :prefix="card.prefix"
            :suffix="card.suffix"
            :value-style="card.style || {}"
          />
        </a-card>
      </a-col>
    </a-row>

    <!-- 性能测试记录 -->
    <a-card size="small" class="records-card">
      <template #title>{{ t('perfTestRecords') }}</template>
      <template #extra>
        <a-space>
          <a-select v-model:value="filterFramework" size="small" style="width: 120px" allow-clear :placeholder="t('allFrameworks')">
            <a-select-option value="vLLM">vLLM</a-select-option>
            <a-select-option value="SGLang">SGLang</a-select-option>
          </a-select>
          <a-select v-model:value="filterStatus" size="small" style="width: 110px" allow-clear :placeholder="t('allStatus')">
            <a-select-option value="done">{{ t('done') }}</a-select-option>
            <a-select-option value="running">{{ t('running') }}</a-select-option>
            <a-select-option value="error">{{ t('error') }}</a-select-option>
            <a-select-option value="stopped">{{ t('stopped') }}</a-select-option>
          </a-select>
          <a-button size="small" @click="loadRuns">
            <template #icon><reload-outlined /></template>
            {{ t('refresh') }}
          </a-button>
        </a-space>
      </template>

      <a-table
        :columns="columns"
        :data-source="filteredRuns"
        :loading="loading"
        size="small"
        row-key="run_id"
        :pagination="{ pageSize: 15, showSizeChanger: true, showTotal: (t) => `${t} ${t('perfTestRecords')}` }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'run_id'">
            <span style="font-weight: 600">{{ record.run_id }}</span>
          </template>
          <template v-if="column.key === 'model'">
            <a-tag>{{ record.meta?.model || '-' }}</a-tag>
          </template>
          <template v-if="column.key === 'framework'">
            <a-tag :color="record.meta?.framework === 'vLLM' ? 'blue' : 'purple'">{{ record.meta?.framework || '-' }}</a-tag>
          </template>
          <template v-if="column.key === 'status'">
            <a-tag :color="statusColor(record.meta?.status)">{{ statusText(record.meta?.status) }}</a-tag>
          </template>
          <template v-if="column.key === 'time'">
            {{ record.meta?.started_at || '-' }}
          </template>
          <template v-if="column.key === 'actions'">
            <a-button type="link" size="small" @click="openDetail(record.run_id)">{{ t('detail') }}</a-button>
            <a-popconfirm :title="t('deleteRunConfirm')" @confirm="deleteRun(record)">
              <a-button danger size="small">{{ t('deleteRun') }}</a-button>
            </a-popconfirm>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 精度测试记录（v5.0 预留） -->
    <a-card size="small" class="records-card">
      <template #title>{{ t('accTestRecords') }}</template>
      <a-table
        :columns="accColumns"
        :data-source="[]"
        size="small"
        row-key="run_id"
        :pagination="false"
      >
        <template #emptyText>
          <a-empty :description="t('accuracyPlanned')" />
        </template>
      </a-table>
    </a-card>

    <!-- 详情弹窗 -->
    <a-modal
      v-model:open="detailOpen"
      :title="`${t('detail')}: ${detailRunId}`"
      width="1100px"
      :footer="null"
      :destroy-on-close="true"
    >
      <RunDetailPanel v-if="detailRunId" :run-id="detailRunId" />
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { api } from '@/api'
import { t } from '@/i18n'
import RunDetailPanel from '@/components/RunDetailPanel.vue'

const loading = ref(false)
const runs = ref([])
const filterFramework = ref(null)
const filterStatus = ref(null)
const detailOpen = ref(false)
const detailRunId = ref('')

// 统计数据
const stats = ref({ total_runs: 0, running_tasks: 0, avg_tpot: null, best_model: '-' })

const statCards = computed(() => [
  { key: 'total', title: t('totalRuns'), value: stats.value.total_runs, prefix: undefined, style: { color: '#1677ff' } },
  { key: 'running', title: t('runningTasks'), value: stats.value.running_tasks, style: { color: stats.value.running_tasks > 0 ? '#52c41a' : '#999' } },
  { key: 'tpot', title: t('avgTpot'), value: stats.value.avg_tpot ?? '-', suffix: stats.value.avg_tpot ? 'ms' : '', style: { color: '#faad14' } },
  { key: 'best', title: t('bestModel'), value: stats.value.best_model || '-', style: { color: '#722ed1', fontSize: '16px' } },
])

const filteredRuns = computed(() => {
  let list = runs.value
  if (filterFramework.value) {
    list = list.filter((r) => r.meta?.framework === filterFramework.value)
  }
  if (filterStatus.value) {
    list = list.filter((r) => r.meta?.status === filterStatus.value)
  }
  return list
})

const columns = [
  { title: 'Run ID', key: 'run_id', width: 140 },
  { title: 'Model', key: 'model', width: 180 },
  { title: 'Framework', key: 'framework', width: 100 },
  { title: 'Status', key: 'status', width: 100 },
  { title: 'Time', key: 'time', width: 180 },
  { title: '', key: 'actions', width: 160 },
]

// 精度测试记录列定义预埋（v5.0）
const accColumns = [
  { title: 'Run ID', key: 'run_id', width: 140 },
  { title: 'Model', key: 'model', width: 180 },
  { title: 'Framework', key: 'framework', width: 100 },
  { title: 'Status', key: 'status', width: 100 },
  { title: 'Time', key: 'time', width: 180 },
  { title: '', key: 'actions', width: 160 },
]

function statusColor(s) {
  return s === 'done' ? 'green' : s === 'error' ? 'red' : s === 'stopped' ? 'orange' : 'blue'
}
function statusText(s) {
  return s === 'done' ? t('done') : s === 'error' ? t('error') : s === 'stopped' ? t('stopped') : t('running')
}

async function loadStats() {
  try {
    const resp = await api.getDashboardStats()
    stats.value = resp
  } catch {
    // fallback: 从 runs 计算
    stats.value.total_runs = runs.value.length
    stats.value.running_tasks = runs.value.filter((r) => r.meta?.status === 'running').length
  }
}

async function loadRuns() {
  loading.value = true
  try {
    const resp = await api.listRuns()
    runs.value = resp.runs || []
    await loadStats()
  } finally {
    loading.value = false
  }
}

function openDetail(runId) {
  detailRunId.value = runId
  detailOpen.value = true
}

async function deleteRun(record) {
  try {
    await api.deleteRun(record.run_id)
    message.success(t('deleteRun'))
    runs.value = runs.value.filter((r) => r.run_id !== record.run_id)
    await loadStats()
  } catch (e) {
    message.error(e.message)
  }
}

onMounted(loadRuns)
</script>

<style scoped>
.dashboard-page {
  height: 100%;
  overflow: auto;
  padding: 20px;
}
.stats-row {
  margin-bottom: 16px;
}
.stat-card {
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.records-card {
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  margin-bottom: 16px;
}
.records-card:last-child {
  margin-bottom: 0;
}
</style>

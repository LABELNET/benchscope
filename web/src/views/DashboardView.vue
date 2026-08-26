<template>
  <div class="dashboard-page">
    <!-- 第一行：左 2 列（统计）+ 右 2 列（环境信息） -->
    <a-row :gutter="16" class="env-row">
      <!-- 左 2 列：Total Perfs / Total Acc / Running Tasks / 测试环境状态 -->
      <a-col :xs="24" :lg="12">
        <a-card size="small" class="dash-card">
          <template #title>{{ t('overview') }}</template>
          <div class="stat-grid2">
            <div class="stat-box">
              <div class="stat-num">{{ stats.total_runs }}</div>
              <div class="stat-label">{{ t('totalPerfsRecords') }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-num">{{ stats.total_acc_runs ?? 0 }}</div>
              <div class="stat-label">{{ t('totalAccRecords') }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-num stat-num-dash">—</div>
              <div class="stat-label">{{ t('maxPerfRecords') }} <span class="stat-sub">(RUN ID)</span></div>
            </div>
            <div class="stat-box">
              <div class="stat-num stat-num-dash">—</div>
              <div class="stat-label">{{ t('maxAccRecords') }} <span class="stat-sub">(RUN ID)</span></div>
            </div>
            <div class="stat-box">
              <div class="stat-num" :style="{ color: stats.running_tasks > 0 ? 'var(--ant-color-success, #52c41a)' : undefined }">
                {{ stats.running_tasks }}
              </div>
              <div class="stat-label">{{ t('runningTasks') }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-status" :class="envReady ? 'ok' : 'bad'">
                <span class="status-dot"></span>
                {{ envReady ? t('online') : t('offline') }}
              </div>
              <div class="stat-label">
                {{ t('envStatusLabel') }}
                <span v-if="envReady && config.status?.models?.length" class="stat-sub">({{ config.status.models.length }} {{ t('models') }})</span>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>

      <!-- 右 2 列：硬件 / 操作系统 / 网络 / 框架版本 -->
      <a-col :xs="24" :lg="12">
        <a-card size="small" class="dash-card">
          <template #title>{{ t('envInfo') }}</template>          <div class="env-grid2">
            <!-- 硬件环境 -->
            <div class="env-box">
              <div class="env-box-title">{{ t('hardware') }}</div>
              <div class="env-row-item"><span>{{ t('host') }}</span><b>{{ envInfo.hardware?.host || dash }}</b></div>
              <div class="env-row-item"><span>CPU</span><b>{{ envInfo.hardware?.cpu || dash }}</b></div>
              <div class="env-row-item"><span>{{ t('memory') }}</span><b>{{ envInfo.hardware?.memory || dash }}</b></div>
              <div class="env-row-item"><span>GPU</span><b>{{ envInfo.hardware?.gpu || dash }}</b></div>
            </div>
            <!-- 操作系统 -->
            <div class="env-box">
              <div class="env-box-title">{{ t('os') }}</div>
              <div class="env-row-item"><span>{{ t('os') }}</span><b>{{ envInfo.os?.name || dash }}</b></div>
              <div class="env-row-item"><span>{{ t('osVersion') }}</span><b>{{ envInfo.os?.version || dash }}</b></div>
              <div class="env-row-item"><span>{{ t('kernel') }}</span><b>{{ envInfo.os?.kernel || dash }}</b></div>
            </div>
            <!-- 网络环境 -->
            <div class="env-box">
              <div class="env-box-title">{{ t('network') }}</div>
              <div v-if="envInfo.network?.length" class="env-row-item">
                <span>{{ t('ifaceIp') }}</span>
                <b class="net-list">
                  <span v-for="(n, i) in envInfo.network" :key="i" class="net-item">{{ n.iface }} - {{ n.ip }}</span>
                </b>
              </div>
              <div v-else class="env-row-item"><span>{{ t('ifaceIp') }}</span><b>{{ dash }}</b></div>
            </div>
            <!-- 框架版本 -->
            <div class="env-box">
              <div class="env-box-title">{{ t('frameworkVersions') }}</div>
              <div class="env-row-item"><span>Python</span><b>{{ envInfo.versions?.python || dash }}</b></div>
              <div class="env-row-item"><span>Pytorch</span><b>{{ envInfo.versions?.pytorch || dash }}</b></div>
              <div class="env-row-item"><span>vLLM</span><b>{{ envInfo.versions?.vllm || dash }}</b></div>
              <div class="env-row-item"><span>SGLang</span><b>{{ envInfo.versions?.sglang || dash }}</b></div>
              <div class="env-row-item"><span>benchscope</span><b>{{ envInfo.versions?.benchscope || dash }}</b></div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- Perf Records -->
    <a-card size="small" class="records-card">
      <template #title>{{ t('perfTestRecords') }}</template>
      <template #extra>
        <a-space>
          <a-button type="link" size="small" @click="loadRuns">
            <template #icon><reload-outlined /></template>
            {{ t('refresh') }}
          </a-button>
          <a-button type="link" size="small" @click="onMore">{{ t('more') }}</a-button>
        </a-space>
      </template>

      <a-table
        class="plain-table"
        :columns="columns"
        :data-source="perfRuns"
        :loading="loading"
        size="small"
        row-key="run_id"
        :bordered="false"
        :pagination="false"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'run_id'">
            <span class="cell-text">{{ record.run_id }}</span>
          </template>
          <template v-if="column.key === 'model'">
            <span class="cell-text">{{ record.meta?.model || '-' }}</span>
          </template>
          <template v-if="column.key === 'framework'">
            <span class="cell-framework" :class="record.meta?.framework === 'vLLM' ? 'fw-vllm' : 'fw-sglang'">{{ record.meta?.framework || '-' }}</span>
          </template>
          <template v-if="column.key === 'status'">
            <span class="cell-status" :class="'st-' + (record.meta?.status || '')">{{ statusText(record.meta?.status) }}</span>
          </template>
          <template v-if="column.key === 'time'">
            <span class="cell-text">{{ record.meta?.started_at || '-' }}</span>
          </template>
          <template v-if="column.key === 'actions'">
            <span class="cell-action" @click="openDetail(record.run_id)">{{ t('detail') }}</span>
            <a-popconfirm :title="t('deleteRunConfirm')" @confirm="deleteRun(record)">
              <span class="cell-action act-danger">{{ t('deleteRun') }}</span>
            </a-popconfirm>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- Eval Records（v5.0 预留） -->
    <a-card size="small" class="records-card">
      <template #title>{{ t('accTestRecords') }}</template>
      <template #extra>
        <a-space>
          <a-button type="link" size="small" @click="loadAccRuns">
            <template #icon><reload-outlined /></template>
            {{ t('refresh') }}
          </a-button>
          <a-button type="link" size="small" @click="onMore">{{ t('more') }}</a-button>
        </a-space>
      </template>
      <a-table
        class="plain-table"
        :columns="accColumns"
        :data-source="accRuns"
        :loading="accLoading"
        size="small"
        row-key="run_id"
        :bordered="false"
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
import { useConfigStore } from '@/store/config'
import { t } from '@/i18n'
import RunDetailPanel from '@/components/RunDetailPanel.vue'

const config = useConfigStore()

const dash = '—'
const loading = ref(false)
const accLoading = ref(false)
const runs = ref([])
const accRuns = ref([]) // 精度记录 v5.0 预留
const envInfo = ref({})
const detailOpen = ref(false)
const detailRunId = ref('')

const stats = ref({ total_runs: 0, total_acc_runs: 0, running_tasks: 0 })

const envReady = computed(() => config.status?.inference === 'ready')

// 最多 8 条最新记录，不分页
const perfRuns = computed(() => runs.value.slice(0, 8))

const columns = [
  { title: 'Run ID', key: 'run_id', width: 140 },
  { title: 'Model', key: 'model', width: 180 },
  { title: 'Framework', key: 'framework', width: 100 },
  { title: 'Status', key: 'status', width: 100 },
  { title: 'Time', key: 'time', width: 180 },
  { title: '', key: 'actions', width: 160 },
]

const accColumns = [
  { title: 'Run ID', key: 'run_id', width: 140 },
  { title: 'Model', key: 'model', width: 180 },
  { title: 'Framework', key: 'framework', width: 100 },
  { title: 'Status', key: 'status', width: 100 },
  { title: 'Time', key: 'time', width: 180 },
  { title: '', key: 'actions', width: 160 },
]

function statusText(s) {
  return s === 'done' ? t('done') : s === 'error' ? t('error') : s === 'stopped' ? t('stopped') : t('running')
}

async function loadStats() {
  try {
    stats.value = await api.getDashboardStats()
  } catch {
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

async function loadAccRuns() {
  accLoading.value = true
  try {
    // v5.0 精度记录接口预留：暂无数据
    accRuns.value = []
  } finally {
    accLoading.value = false
  }
}

async function loadEnv() {
  try {
    envInfo.value = await api.getDashboardEnv()
  } catch { /* 环境信息不可用时保持为空 */ }
}

function onMore() {
  message.info(t('notImplemented'))
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

onMounted(async () => {
  await loadRuns()
  await loadEnv()
  config.refreshStatus()
})
</script>

<style scoped>
.dashboard-page {
  height: 100%;
  overflow: auto;
  padding: 20px;
}
.env-row {
  margin-bottom: 16px;
}
.dash-card {
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  height: 100%;
}

/* 左 2 列：统计 2 列 x 3 行（6 宫格） */
.stat-grid2 {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.stat-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 16px 8px;
  border: 1px solid var(--ant-color-border, #f0f0f0);
  border-radius: 10px;
  background: var(--ant-color-bg-layout, #fafafa);
  text-align: center;
}
.stat-num {
  font-size: 26px;
  font-weight: 700;
  color: var(--ant-color-primary, #1677ff);
  line-height: 1;
}
.stat-num-dash {
  color: var(--ant-color-text-tertiary, #999);
}
.stat-label {
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
}
.stat-sub {
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
}
.stat-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 20px;
  font-weight: 700;
  line-height: 1;
}
.stat-status.ok { color: var(--ant-color-success, #52c41a); }
.stat-status.bad { color: var(--ant-color-error, #f5222d); }
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--ant-color-text-quaternary, #d9d9d9);
}
.stat-status.ok .status-dot { background: #52c41a; }
.stat-status.bad .status-dot { background: #ff4d4f; }

/* 右 2 列：环境信息 2x2 */
.env-grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.env-box {
  border: 1px solid var(--ant-color-border, #f0f0f0);
  border-radius: 10px;
  padding: 12px 14px;
  background: var(--ant-color-bg-layout, #fafafa);
  min-width: 0;
}
.env-box-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ant-color-text, #333);
  margin-bottom: 8px;
}
.env-row-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  padding: 3px 0;
  font-size: 12px;
}
.env-row-item > span {
  color: var(--ant-color-text-tertiary, #999);
  flex-shrink: 0;
}
.env-row-item > b {
  font-weight: 500;
  color: var(--ant-color-text, #333);
  text-align: right;
  word-break: break-all;
  min-width: 0;
}
.net-list {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

/* 记录面板 */
.records-card {
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  margin-bottom: 16px;
}
.records-card:last-child {
  margin-bottom: 0;
}

/* 表格纯文本样式：无按钮/无边框，小字号，仅状态与操作列着色 */
.plain-table :deep(.ant-table) {
  font-size: 12px;
}
.plain-table :deep(.ant-table-thead > tr > th) {
  font-size: 12px;
}
.cell-text {
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
}
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
  margin-right: 12px;
  font-size: 12px;
}
.cell-action.act-danger {
  color: #ff4d4f;
}
</style>

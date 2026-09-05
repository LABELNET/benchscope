<template>
  <div class="dashboard-page">
    <!-- 第一行：左 2 列（统计）+ 右 2 列（环境信息） -->
    <a-row :gutter="16" class="env-row">
      <!-- 左 2 列：Total Perfs / Total Acc -->
      <a-col :xs="24" :lg="12">
        <a-card size="small" class="dash-card">
          <template #title>{{ t('overview') }}</template>
          <div class="stat-grid2">
            <div class="stat-box">
              <div class="stat-num">{{ stats.total_runs }}</div>
              <div class="stat-label">{{ t('perfCount') }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-num">{{ stats.total_acc_runs ?? 0 }}</div>
              <div class="stat-label">{{ t('accCount') }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-num">{{ sessionCount }}</div>
              <div class="stat-label">{{ t('sessions') }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-num">{{ skillCount }}</div>
              <div class="stat-label">{{ t('skills') }} <span class="stat-sub">({{ t('builtin') }})</span></div>
            </div>
            <div class="stat-box">
              <div class="stat-num">{{ modelDownloadCount }}</div>
              <div class="stat-label">{{ t('modelsTab') }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-num">{{ datasetDownloadCount }}</div>
              <div class="stat-label">{{ t('datasetsTab') }}</div>
            </div>
          </div>
          <!-- Providers：整行 1 个（内含 Provider 数量 + Provider Models 2 个小格） -->
          <div class="prov-box">
            <div class="stat-box prov-col">
              <div class="stat-num">{{ providerCount }}</div>
              <div class="stat-label">{{ t('providerCount') }}</div>
            </div>
            <div class="stat-box prov-col">
              <div class="stat-num">{{ providerModelCount }}</div>
              <div class="stat-label">{{ t('providerModelCount') }}</div>
            </div>
          </div>
        </a-card>
      </a-col>

      <!-- 右 2 列：硬件 / 操作系统 / 网络 / 框架版本 -->
      <a-col :xs="24" :lg="12">
        <a-card size="small" class="dash-card">
          <template #title>{{ t('envInfo') }}</template>
          <div class="env-grid2">
            <!-- 硬件环境 -->
            <div class="env-box">
              <div class="env-box-title">{{ t('hardware') }}</div>
              <div class="env-row-item"><a-typography-text type="secondary">{{ t('host') }}</a-typography-text><b>{{ envInfo.hardware?.host || dash }}</b></div>
              <div class="env-row-item"><a-typography-text type="secondary">CPU</a-typography-text><b>{{ envInfo.hardware?.cpu || dash }}</b></div>
              <div class="env-row-item"><a-typography-text type="secondary">{{ t('memory') }}</a-typography-text><b>{{ envInfo.hardware?.memory || dash }}</b></div>
              <div class="env-row-item"><a-typography-text type="secondary">GPU</a-typography-text><b>{{ envInfo.hardware?.gpu || dash }}</b></div>
            </div>
            <!-- 操作系统 -->
            <div class="env-box">
              <div class="env-box-title">{{ t('os') }}</div>
              <div class="env-row-item"><a-typography-text type="secondary">{{ t('os') }}</a-typography-text><b>{{ envInfo.os?.name || dash }}</b></div>
              <div class="env-row-item"><a-typography-text type="secondary">{{ t('osVersion') }}</a-typography-text><b>{{ envInfo.os?.version || dash }}</b></div>
              <div class="env-row-item"><a-typography-text type="secondary">{{ t('kernel') }}</a-typography-text><b>{{ envInfo.os?.kernel || dash }}</b></div>
            </div>
            <!-- 网络环境 -->
            <div class="env-box">
              <div class="env-box-title">{{ t('network') }}</div>
              <template v-if="envInfo.network?.length">
                <div v-for="n in envInfo.network" :key="n.iface" class="net-block">
                  <div class="net-iface">{{ n.iface }}</div>
                  <div class="env-row-item"><a-typography-text type="secondary">{{ t('netUuid') }}</a-typography-text><b>{{ n.mac || dash }}</b></div>
                  <div class="env-row-item"><a-typography-text type="secondary">{{ t('netIp') }}</a-typography-text><b>{{ n.ip || dash }}</b></div>
                  <div class="env-row-item"><a-typography-text type="secondary">{{ t('netSubnet') }}</a-typography-text><b>{{ n.subnet || dash }}</b></div>
                  <div class="env-row-item"><a-typography-text type="secondary">{{ t('netMask') }}</a-typography-text><b>{{ n.mask || dash }}</b></div>
                </div>
              </template>
              <div v-else class="env-row-item"><a-typography-text type="secondary">{{ t('network') }}</a-typography-text><b>{{ dash }}</b></div>
            </div>
            <!-- 框架版本 -->
            <div class="env-box">
              <div class="env-box-title">{{ t('frameworkVersions') }}</div>
              <div class="env-row-item"><a-typography-text type="secondary">Python</a-typography-text><b>{{ envInfo.versions?.python || dash }}</b></div>
              <div class="env-row-item"><a-typography-text type="secondary">Pytorch</a-typography-text><b>{{ envInfo.versions?.pytorch || dash }}</b></div>
              <div class="env-row-item"><a-typography-text type="secondary">vLLM</a-typography-text><b>{{ envInfo.versions?.vllm || dash }}</b></div>
              <div class="env-row-item"><a-typography-text type="secondary">SGLang</a-typography-text><b>{{ envInfo.versions?.sglang || dash }}</b></div>
              <div class="env-row-item"><a-typography-text type="secondary">benchscope</a-typography-text><b>{{ envInfo.versions?.benchscope || dash }}</b></div>
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
            <!-- Detail 跳转 Datas/Perfs 并选中对应任务 -->
            <span class="cell-action" @click="goRunDetail(record.run_id)">{{ t('detail') }}</span>
          </template>
        </template>
      </a-table>
      <!-- 面板 footer：右侧灰色小字 -->
      <div class="records-footer">{{ t('latest8Hint') }}</div>
    </a-card>

    <!-- Eval Records 面板暂时隐藏（敬请期待），如需恢复从 git 历史取回 -->
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { api } from '@/api'
import { useConfigStore } from '@/store/config'
import { t } from '@/i18n'

const config = useConfigStore()
const router = useRouter()
const loading = ref(false)
const accLoading = ref(false)
const runs = ref([])
const accRuns = ref([]) // 精度记录 v5.0 预留
const envInfo = ref({})

// Overview 计数
const sessionCount = ref(0)
const skillCount = ref(0)
const modelDownloadCount = ref(0)   // Models 下载数（暂未实现，默认 0）
const datasetDownloadCount = ref(0) // Datasets 下载数（暂未实现，默认 0）
const providerCount = ref(0)
const providerModelCount = ref(0)

const stats = ref({ total_runs: 0, total_acc_runs: 0, running_tasks: 0 })

const dash = '—'

// 最多 8 条最新记录，不分页
const perfRuns = computed(() => runs.value.slice(0, 8))

const columns = [
  { title: 'Run ID', key: 'run_id', width: 140 },
  { title: 'Model', key: 'model', width: 180 },
  { title: 'Framework', key: 'framework', width: 100 },
  { title: 'Status', key: 'status', width: 100 },
  { title: 'Time', key: 'time', width: 180 },
  { title: '', key: 'actions', width: 90 },
]

const accColumns = [
  { title: 'Run ID', key: 'run_id', width: 140 },
  { title: 'Model', key: 'model', width: 180 },
  { title: 'Accuracy', key: 'accuracy', width: 100 },
  { title: 'Status', key: 'status', width: 100 },
  { title: 'Time', key: 'time', width: 180 },
  { title: '', key: 'actions', width: 90 },
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
    runs.value = (resp.runs || []).filter((r) => !isEvalRun(r))
    await loadStats()
  } finally {
    loading.value = false
  }
}

// Overview 计数：Sessions / Skills / Providers（Models、Datasets 下载数暂未实现，默认 0）
async function loadOverviewCounts() {
  const [sess, sk, prov] = await Promise.allSettled([
    api.listSessions(),
    api.getSkills(),
    api.listProviders(),
  ])
  if (sess.status === 'fulfilled') sessionCount.value = (sess.value.sessions || []).length
  if (sk.status === 'fulfilled') skillCount.value = (sk.value.skills || []).length
  if (prov.status === 'fulfilled') {
    const providers = prov.value.providers || []
    providerCount.value = providers.length
    // Provider Models：并行探测各 Provider 的模型数
    const results = await Promise.allSettled(
      providers.map((p) => api.testConnection({
        base_url: p.base_url,
        endpoint: p.endpoint || '/v1/chat/completions',
        api_key: p.api_key || '',
        extra_headers: p.extra_headers || {},
      })),
    )
    providerModelCount.value = results.reduce(
      (sum, r) => sum + (r.status === 'fulfilled' ? (r.value?.models || []).length : 0),
      0,
    )
  }
}

function isEvalRun(record) {
  return (record.dir || '').includes('/evals') || record.meta?.kind === 'eval'
}

async function loadAccRuns() {
  accLoading.value = true
  try {
    const resp = await api.listRuns()
    accRuns.value = (resp.runs || []).filter(isEvalRun).slice(0, 8)
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
  // 联动 Datas 页面：Perf Records 的「更多」跳转到记录管理页
  router.push('/datas/perfs')
}

function onEvalMore() {
  // Eval Records「更多」跳转 Datas/evals
  router.push('/datas/evals')
}

function goEvalDetail(runId) {
  // Eval 详情跳转 Datas/evals 对比面板（记录列表）
  router.push('/datas/evals')
}

function goRunDetail(runId) {
  // Detail 点击跳转到 Datas/Perfs 页面并自动选中对应任务
  router.push({ path: '/datas/perfs', query: { run_id: runId } })
}

onMounted(async () => {
  await loadRuns()
  await loadAccRuns()
  await loadEnv()
  config.refreshStatus()
  loadOverviewCounts()
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
/* Providers：整行 1 个，内含 2 个小格（Provider 数量 / Provider Models） */
.prov-box {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}
.prov-col {
  height: 100%;
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
  font-size: 12px;
  font-weight: 600;
  color: var(--ant-color-text, #333);
  margin-bottom: 8px;
}
.env-row-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  padding: 2px 0;
  font-size: 11px;
}
.env-row-item :deep(.ant-typography) {
  font-size: 11px;
  line-height: 1.5;
}
.env-row-item > span {
  color: var(--ant-color-text-tertiary, #999);
  flex-shrink: 0;
}
.env-row-item > b {
  font-weight: 500;
  font-size: 11px;
  color: var(--ant-color-text, #333);
  text-align: right;
  word-break: break-all;
  min-width: 0;
}
.net-block {
  margin-bottom: 6px;
}
.net-block + .net-block {
  border-top: 1px dashed var(--ant-color-border, #f0f0f0);
  padding-top: 6px;
}
.net-iface {
  font-size: 11px;
  font-weight: 600;
  color: var(--ant-color-primary, #1677ff);
  margin-bottom: 2px;
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

/* 记录面板 footer：右侧灰色小字 */
.records-footer {
  margin-top: 8px;
  text-align: right;
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
}
</style>

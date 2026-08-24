<template>
  <div class="task-detail-page">
    <!-- 顶部：返回 + 状态栏 -->
    <div class="top-bar">
      <a-button type="link" @click="$router.push('/performance')" style="padding: 0">{{ t('backToList') }}</a-button>
      <div class="top-bar-right" v-if="task">
        <a-space>
          <a-badge :status="statusBadge(task.status)" :text="statusText(task.status)" />
          <a-tag :color="task.framework === 'vllm' ? 'blue' : 'purple'">{{ task.framework_name || task.framework }}</a-tag>
          <span class="model-name">{{ task.model }}</span>
        </a-space>
        <a-space style="margin-left: 16px">
          <a-button v-if="canStart" type="primary" size="small" @click="startTask">
            <template #icon><play-circle-outlined /></template>
            {{ t('startTest') }}
          </a-button>
          <a-button v-if="task.status === 'running'" size="small" danger @click="stopTask">
            <template #icon><stop-outlined /></template>
            {{ t('stopTest') }}
          </a-button>
          <a-button v-if="task.status === 'error' || task.status === 'stopped'" size="small" @click="startTask">
            <template #icon><reload-outlined /></template>
            {{ t('retryTest') }}
          </a-button>
          <a-popconfirm :title="t('deleteTask') + '?'" @confirm="deleteAndBack">
            <a-button size="small" danger ghost>
              <template #icon><delete-outlined /></template>
            </a-button>
          </a-popconfirm>
        </a-space>
      </div>
    </div>

    <a-spin :spinning="!task && loading">
      <a-empty v-if="!task && !loading" :description="t('noData')" />

      <div v-if="task" class="content-area">
        <!-- 状态信息条 -->
        <a-card size="small" class="status-card">
          <a-row :gutter="16">
            <a-col :span="6">
              <a-statistic :title="t('taskStatus')" :value="statusText(task.status)" :value-style="{ fontSize: '16px' }" />
            </a-col>
            <a-col :span="6">
              <a-statistic :title="t('serviceStatus')" :value="serviceReady ? t('online') : t('offline')" :value-style="{ fontSize: '16px', color: serviceReady ? '#52c41a' : '#f5222d' }" />
            </a-col>
            <a-col :span="6">
              <a-statistic :title="t('progress')" :value="`${doneCount} / ${totalCount}`" :value-style="{ fontSize: '16px' }" />
            </a-col>
            <a-col :span="6">
              <a-statistic :title="t('elapsed')" :value="elapsedText" :value-style="{ fontSize: '16px' }" />
            </a-col>
          </a-row>
          <a-progress v-if="totalCount > 0" :percent="percent" :status="percent >= 100 ? 'success' : task.status === 'running' ? 'active' : 'normal'" style="margin-top: 12px" />
          <!-- 命令预览 -->
          <a-collapse ghost style="margin-top: 8px" v-model:activeKey="cmdCollapseKeys">
            <a-collapse-panel key="cmd" :header="t('commandPreview')">
              <pre class="cmd-preview">{{ commandPreview }}</pre>
            </a-collapse-panel>
          </a-collapse>
        </a-card>

        <!-- 下方：左1/4 右3/4 -->
        <div class="split-layout">
          <!-- 左侧：进度 + 终端 -->
          <div class="left-panel">
            <a-card size="small" :title="t('progress')" class="panel-card">
              <div class="progress-detail">
                <div v-for="(c, i) in task.cases || []" :key="i" class="case-item">
                  <span class="case-label">{{ c.label }}</span>
                  <span class="case-meta" v-if="c.input_len">{{ c.input_len }}/{{ c.output_len }}</span>
                  <a-tag v-for="conc in task.concurrency_list || []" :key="conc" :color="caseConcDone(c.label, conc) ? 'green' : caseConcRunning(c.label, conc) ? 'processing' : 'default'" size="small">
                    {{ conc }}
                  </a-tag>
                </div>
              </div>
            </a-card>
            <a-card size="small" :title="t('terminal')" class="panel-card" style="margin-top: 8px">
              <div class="terminal-box" ref="termBox">
                <div v-for="(line, i) in activeLogs" :key="i" class="term-line">{{ line }}</div>
              </div>
            </a-card>
          </div>

          <!-- 右侧：实时结果 + 曲线 -->
          <div class="right-panel">
            <a-card size="small" :title="t('realtimeResults')" class="panel-card">
              <RealtimeResultPanel :rows="task.rows || []" :threshold="task.tpot_threshold_ms" :running="task.status === 'running'" />
            </a-card>
          </div>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { DeleteOutlined, PlayCircleOutlined, ReloadOutlined, StopOutlined } from '@ant-design/icons-vue'
import { useTestStore } from '@/store/test'
import { useConfigStore } from '@/store/config'
import { t } from '@/i18n'
import RealtimeResultPanel from '@/components/RealtimeResultPanel.vue'

const props = defineProps({ taskId: String })
const route = useRoute()
const router = useRouter()
const test = useTestStore()
const config = useConfigStore()
const termBox = ref(null)
const loading = ref(false)
const cmdCollapseKeys = ref([])

const taskId = computed(() => props.taskId || route.params.taskId)
const task = computed(() => test.tasks[taskId.value] || null)
const activeLogs = computed(() => test.logLines[taskId.value] || [])
const serviceReady = computed(() => config.status?.inference === 'ready')

const totalCount = computed(() => {
  if (!task.value) return 0
  return (task.value.cases?.length || 0) * (task.value.concurrency_list?.length || 0)
})
const doneCount = computed(() => {
  if (!task.value) return 0
  return (task.value.rows || []).filter((r) => r.metrics || r.error).length
})
const percent = computed(() => (totalCount.value ? Math.round((doneCount.value / totalCount.value) * 100) : 0))
const canStart = computed(() => {
  if (!task.value) return false
  const s = task.value.status
  return s === 'pending' || s === 'stopped' || s === 'error'
})

const commandPreview = computed(() => {
  if (!task.value) return ''
  const tk = task.value
  const parts = [tk.framework === 'vllm' ? 'vllm bench serve' : 'python -m sglang.bench_serving']
  parts.push(`--model ${tk.model}`)
  if (tk.dataset?.type) parts.push(`--dataset ${tk.dataset.type}`)
  if (tk.concurrency_list?.length) parts.push(`--concurrency ${tk.concurrency_list.join(',')}`)
  if (tk.request_rate && tk.request_rate !== 'inf') parts.push(`--request-rate ${tk.request_rate}`)
  return parts.join(' \\\n  ')
})

// 运行时长
const now = ref(Date.now())
let timer = null
watch(() => task.value?.status, (v) => {
  if (timer) clearInterval(timer)
  if (v === 'running') {
    now.value = Date.now()
    timer = setInterval(() => (now.value = Date.now()), 1000)
  }
}, { immediate: true })
onBeforeUnmount(() => { if (timer) clearInterval(timer) })

const elapsedText = computed(() => {
  if (!task.value?.started_at) return '-'
  const start = new Date(task.value.started_at).getTime()
  if (isNaN(start)) return '-'
  const end = task.value.finished_at ? new Date(task.value.finished_at).getTime() : now.value
  const sec = Math.max(0, Math.floor((end - start) / 1000))
  return `${Math.floor(sec / 60)}分${sec % 60}秒`
})

function statusBadge(s) {
  return s === 'running' ? 'processing' : s === 'done' ? 'success' : s === 'error' ? 'error' : s === 'stopped' ? 'warning' : 'default'
}
function statusText(s) {
  const map = { pending: t('pending'), running: t('running'), done: t('done'), stopped: t('stopped'), error: t('error') }
  return map[s] || s
}
function caseConcDone(label, conc) {
  return (task.value?.rows || []).some((r) => r.label === label && r.concurrency === conc && (r.metrics || r.error))
}
function caseConcRunning(label, conc) {
  return false // simplified
}

async function loadTask() {
  loading.value = true
  try {
    await test.loadTasks()
    test.setActiveTask(taskId.value)
  } finally { loading.value = false }
}

async function startTask() {
  try {
    await test.startTask(taskId.value)
    message.success('Task started')
  } catch (e) { message.error(e.message) }
}
async function stopTask() {
  try {
    await test.stopTask(taskId.value)
    message.info('Stop requested')
  } catch (e) { message.error(e.message) }
}
async function deleteAndBack() {
  try {
    await test.deleteTask(taskId.value)
    router.push('/performance')
  } catch (e) { message.error(e.message) }
}

// 自动滚动终端
watch(() => activeLogs.value.length, async () => {
  await nextTick()
  if (termBox.value) termBox.value.scrollTop = termBox.value.scrollHeight
})

onMounted(() => {
  loadTask()
  config.refreshStatus()
})
onBeforeUnmount(() => { test.setActiveTask(null) })
</script>

<style scoped>
.task-detail-page {
  height: 100%;
  overflow: auto;
  padding: 16px 20px;
}
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.top-bar-right {
  display: flex;
  align-items: center;
}
.model-name {
  font-weight: 600;
  font-size: 14px;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status-card {
  margin-bottom: 12px;
  border-radius: 8px;
}
.cmd-preview {
  background: #f5f5f5;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 120px;
  overflow: auto;
}
.split-layout {
  display: flex;
  gap: 12px;
  min-height: calc(100vh - 320px);
}
.left-panel {
  width: 25%;
  min-width: 260px;
  flex-shrink: 0;
}
.right-panel {
  flex: 1;
  min-width: 0;
}
.panel-card {
  border-radius: 8px;
}
.progress-detail {
  max-height: 280px;
  overflow: auto;
}
.case-item {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 12px;
}
.case-label {
  font-weight: 600;
  min-width: 60px;
}
.case-meta {
  color: #999;
  font-size: 11px;
}
.terminal-box {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.5;
  max-height: 320px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.term-line {
  min-height: 16px;
}
</style>

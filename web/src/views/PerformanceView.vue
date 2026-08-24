<template>
  <div class="perf-page">
    <div class="perf-header">
      <h3 style="margin: 0">{{ t('taskList') }}</h3>
      <a-space>
        <a-button @click="loadTasks">
          <template #icon><reload-outlined /></template>
          {{ t('refresh') }}
        </a-button>
        <a-button type="primary" @click="showCreate = true">
          <template #icon><plus-outlined /></template>
          {{ t('newTask') }}
        </a-button>
      </a-space>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && !tasks.length" :description="t('noData')" style="padding: 60px 0" />
      <a-row :gutter="[16, 16]" v-else>
        <a-col :xs="24" :sm="12" :lg="8" :xl="6" v-for="task in tasks" :key="task.task_id">
          <a-card hoverable class="task-card" @click="$router.push(`/performance/${task.task_id}`)">
            <template #actions>
              <a-button v-if="task.status === 'pending' || task.status === 'stopped' || task.status === 'error'" type="link" size="small" @click.stop="startTask(task.task_id)">
                <play-circle-outlined /> {{ t('startTest') }}
              </a-button>
              <a-button v-if="task.status === 'running'" type="link" size="small" danger @click.stop="stopTask(task.task_id)">
                <stop-outlined /> {{ t('stopTest') }}
              </a-button>
              <a-button type="link" size="small" danger @click.stop="deleteTask(task.task_id)">
                <delete-outlined />
              </a-button>
            </template>
            <div class="card-top">
              <a-badge :status="statusBadge(task.status)" />
              <span class="task-id">{{ task.task_id }}</span>
              <a-tag :color="task.framework === 'vllm' ? 'blue' : 'purple'" style="margin-left: auto">{{ task.framework_name || task.framework }}</a-tag>
            </div>
            <div class="card-model">{{ task.model || '-' }}</div>
            <div class="card-meta">
              <span>{{ datasetLabel(task.dataset) }}</span>
              <span v-if="task.status === 'running'">
                {{ doneCount(task) }} / {{ totalCount(task) }}
              </span>
            </div>
            <a-progress v-if="totalCount(task) > 0" :percent="Math.round((doneCount(task) / totalCount(task)) * 100)" :size="'small'" :status="task.status === 'running' ? 'active' : task.status === 'done' ? 'success' : 'normal'" />
            <div class="card-time">{{ task.created_at || '' }}</div>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>

    <!-- 新建任务抽屉 -->
    <a-drawer v-model:open="showCreate" :title="t('newTask')" width="640" :destroy-on-close="true">
      <TaskCreateForm @created="onCreated" />
    </a-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { DeleteOutlined, PlayCircleOutlined, PlusOutlined, ReloadOutlined, StopOutlined } from '@ant-design/icons-vue'
import { useTestStore } from '@/store/test'
import { t } from '@/i18n'
import TaskCreateForm from '@/components/performance/TaskCreateForm.vue'

const test = useTestStore()
const loading = ref(false)
const showCreate = ref(false)

const tasks = computed(() => test.taskList)

function statusBadge(s) {
  return s === 'running' ? 'processing' : s === 'done' ? 'success' : s === 'error' ? 'error' : s === 'stopped' ? 'warning' : 'default'
}
function datasetLabel(ds) {
  if (!ds) return '-'
  const type = ds.type || 'random'
  if (type === 'random') {
    const pairs = ds.length_pairs || []
    return `Random (${pairs.length})`
  }
  return type === 'sharegpt' ? 'ShareGPT' : 'Custom'
}
function totalCount(task) {
  return (task.cases?.length || 0) * (task.concurrency_list?.length || 0)
}
function doneCount(task) {
  return (task.rows || []).filter((r) => r.metrics || r.error).length
}

async function loadTasks() {
  loading.value = true
  try { await test.loadTasks() } finally { loading.value = false }
}

async function startTask(taskId) {
  try {
    await test.startTask(taskId)
    message.success('Task started')
  } catch (e) { message.error(e.message) }
}

async function stopTask(taskId) {
  try {
    await test.stopTask(taskId)
    message.info('Stop requested')
  } catch (e) { message.error(e.message) }
}

async function deleteTask(taskId) {
  try {
    await test.deleteTask(taskId)
    message.success('Deleted')
  } catch (e) { message.error(e.message) }
}

function onCreated(taskId) {
  showCreate.value = false
  loadTasks()
}

onMounted(loadTasks)
</script>

<style scoped>
.perf-page {
  height: 100%;
  overflow: auto;
  padding: 20px;
}
.perf-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.task-card {
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.card-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.task-id {
  font-weight: 600;
  font-size: 13px;
}
.card-model {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
}
.card-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--ant-color-text-secondary, rgba(0, 0, 0, 0.45));
  margin-bottom: 6px;
}
.card-time {
  font-size: 12px;
  color: var(--ant-color-text-secondary, rgba(0, 0, 0, 0.45));
  margin-top: 4px;
}
</style>

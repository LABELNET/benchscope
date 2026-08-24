<template>
  <div class="create-task-page">
    <div class="create-header">
      <a-button type="link" @click="goBack">
        <template #icon><arrow-left-outlined /></template>
        {{ t('backToTasks') }}
      </a-button>
      <h3 style="margin: 0">{{ t('createTask') }}</h3>
    </div>
    <div class="create-body">
      <TaskCreateForm @created="onCreated" @cancel="goBack" />
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { ArrowLeftOutlined } from '@ant-design/icons-vue'
import { t } from '@/i18n'
import TaskCreateForm from '@/components/performance/TaskCreateForm.vue'

const router = useRouter()

function goBack() {
  router.push('/performance')
}

function onCreated(taskId) {
  router.push(`/performance/${taskId}`)
}
</script>

<style scoped>
.create-task-page {
  height: 100%;
  overflow: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.create-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  width: 100%;
  max-width: 720px;
}
.create-body {
  width: 100%;
  max-width: 720px;
  background: var(--ant-color-bg-container, #fff);
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
</style>

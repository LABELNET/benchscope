<template>
  <a-layout class="page-layout">
    <a-layout-sider width="260" theme="light" class="record-sider">
      <RunRecordList v-model="selectedRunId" framework="" />
    </a-layout-sider>
    <a-layout-content class="page-content">
      <RunDetailPanel :run-id="selectedRunId" />
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { ref } from 'vue'
import RunRecordList from '@/components/RunRecordList.vue'
import RunDetailPanel from '@/components/RunDetailPanel.vue'

const selectedRunId = ref('')
</script>

<style scoped>
.page-layout {
  height: 100%;
}
.record-sider {
  border-right: 1px solid #f0f0f0;
  height: 100%;
  overflow: auto;
}
.page-content {
  height: 100%;
  background: #f5f5f5;
}
</style>

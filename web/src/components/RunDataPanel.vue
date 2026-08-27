<template>
  <div class="run-data-panel">
    <!-- 按 cases 分组信息分 tab，tab 标题为分组标识；默认/Mean/Median/P99 由父级 header 控制 -->
    <a-tabs v-model:activeKey="activeGroup" class="data-tabs" size="small">
      <a-tab-pane v-for="g in groups" :key="g.key" :tab="g.label">
        <MetricsTable
          :rows="groupRows(g.key)"
          :threshold="threshold"
          :request-rate="requestRate"
          :output-threshold="outputThreshold"
          :preset="mode"
          :max-rows="100"
          :default-hidden="['label', 'concurrency', 'successful', 'status']"
        />
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import MetricsTable from '@/components/MetricsTable.vue'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  threshold: { type: Number, default: null },
  requestRate: { type: [String, Number], default: 'inf' },
  outputThreshold: { type: Number, default: null },
  mode: { type: String, default: 'default' },
})
const emit = defineEmits(['update:mode'])

// cases 分组信息：caseKey（label#g{case_id} 或 label）
const groups = computed(() => {
  const map = new Map()
  for (const row of props.rows) {
    const raw = row.label || row.case || 'unknown'
    const hasGid = row.case_id !== undefined && row.case_id !== null
    const key = hasGid ? `${raw}#g${row.case_id}` : raw
    if (!map.has(key)) map.set(key, { key, label: key, count: 0 })
    map.get(key).count++
  }
  return Array.from(map.values())
})

const activeGroup = ref('')
// 分组变化时默认激活第一个组
watch(groups, (gs) => {
  if (!activeGroup.value || !gs.some((g) => g.key === activeGroup.value)) {
    activeGroup.value = gs[0]?.key || ''
  }
}, { immediate: true })

function groupRows(key) {
  return props.rows.filter((row) => {
    const raw = row.label || row.case || 'unknown'
    const hasGid = row.case_id !== undefined && row.case_id !== null
    const k = hasGid ? `${raw}#g${row.case_id}` : raw
    return k === key
  })
}
</script>

<style scoped>
.run-data-panel {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.data-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 4px;
}
/* 分组 Tab 过多时：横向可滚动（不换行/不溢出） */
.data-tabs :deep(.ant-tabs-nav-wrap) {
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: thin;
}
.data-tabs :deep(.ant-tabs-nav-list) {
  flex-wrap: nowrap;
  white-space: nowrap;
}
</style>

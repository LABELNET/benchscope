<template>
  <div class="run-data-panel">
    <!-- 按 cases 分组信息分 tab，tab 标题为分组标识；默认/Mean/Median/P99 由父级 header 控制 -->
    <a-tabs v-model:activeKey="activeGroup" class="data-tabs" size="small">
      <a-tab-pane v-for="g in groups" :key="g.key" :tab="g.label">
        <!-- 每组阈值条件信息（跟随 Groups 独立配置；0 表示未配置不显示；完整文本 hover title） -->
        <div v-if="groupThresholds[g.key]" class="group-threshold-bar" :title="groupThresholds[g.key]">{{ groupThresholds[g.key] }}</div>
        <MetricsTable
          :rows="groupRows(g.key)"
          :threshold="threshold"
          :request-rate="requestRate"
          :group-thresholds="groupThresholds"
          :preset="mode"
          :max-rows="100"
          :default-hidden="['label', 'concurrency', 'successful', 'status']"
          :show-detail="showDetail"
          @detail="(row) => emit('detail', row)"
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
  mode: { type: String, default: 'default' },
  // 分组阈值信息：分组 key → 阈值条件文本（跟随 Groups 每组独立配置；0 表示未配置不显示）
  groupThresholds: { type: Object, default: () => ({}) },
  // 显示 detail/详情 固定列
  showDetail: { type: Boolean, default: false },
})
const emit = defineEmits(['update:mode', 'detail'])

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
/* 分组阈值条：每组独立配置，宽度不够伪隐藏（省略号 + title 完整文本） */
.group-threshold-bar {
  font-size: 10px;
  color: var(--ant-color-text-tertiary, #999);
  background: var(--ant-color-success-bg, #f6ffed);
  border: 1px dashed var(--ant-color-success-border, #b7eb8f);
  border-radius: 4px;
  padding: 2px 8px;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

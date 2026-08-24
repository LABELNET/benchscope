<template>
  <div>
    <a-space style="margin-bottom: 8px" wrap>
      <a-tag color="blue"><template #icon><appstore-outlined /></template>用例 {{ caseCount }} 个</a-tag>
      <a-tag color="green"><template #icon><check-circle-outlined /></template>已出结果 {{ rows.length }} 条</a-tag>
      <a-tag :color="running ? 'processing' : 'default'">
        <template #icon><sync-outlined :spin="running" /></template>
        {{ running ? '测试进行中…' : '空闲' }}
      </a-tag>
      <span v-if="threshold" style="color: #999; font-size: 12px">
        TPOT 阈值 {{ threshold }}ms：绿色=低于阈值，金色=最佳并发
      </span>
    </a-space>

    <MetricsTable :rows="rows" :threshold="threshold" :pagination="{ pageSize: 20, showSizeChanger: true }" />

    <a-divider style="margin: 12px 0">实时曲线（横轴：并发数）</a-divider>
    <MetricsCharts :rows="rows" :metric-defs="metricDefs" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  AppstoreOutlined,
  CheckCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons-vue'
import MetricsTable from '@/components/MetricsTable.vue'
import MetricsCharts from '@/components/MetricsCharts.vue'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  threshold: { type: Number, default: null },
  running: { type: Boolean, default: false },
})

// README：6 条曲线 = output 吞吐 / total 吞吐 / TTFT mean / TPOT mean / TTFT P99 / TPOT P99
const metricDefs = [
  { key: 'output_mean', label: 'Output 吞吐 (tok/s)' },
  { key: 'total_mean', label: 'Total 吞吐 (tok/s)' },
  { key: 'ttft_mean', label: 'TTFT mean 耗时 (ms)' },
  { key: 'tpot_mean', label: 'TPOT mean 耗时 (ms)' },
  { key: 'ttft_p99', label: 'TTFT P99 耗时 (ms)' },
  { key: 'tpot_p99', label: 'TPOT P99 耗时 (ms)' },
]

const caseCount = computed(() => {
  const set = new Set(props.rows.map((r) => r.label || r.case))
  return set.size
})
</script>

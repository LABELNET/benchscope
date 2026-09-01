<template>
  <div>
    <div style="margin-bottom: 8px; color: var(--ant-color-text-tertiary); font-size: 12px">
      {{ threshold ? `TPOT 阈值 ${threshold}ms，金色行为最佳并发` : '未设置 TPOT 阈值' }}
    </div>
    <MetricsTable :rows="tableRows" :threshold="threshold" :pagination="{ pageSize: 20, showSizeChanger: true }" />
    <div style="margin-top: 12px; font-weight: 600">曲线（横轴：并发数）</div>
    <MetricsCharts :rows="tableRows" :metric-defs="defs" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MetricsTable from '@/components/MetricsTable.vue'
import MetricsCharts from '@/components/MetricsCharts.vue'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  best: { type: Object, default: () => ({}) },
  threshold: { type: [Number, String], default: null },
})

// README 51：output/peakoutput/total/ttft/itl/tpot 六曲线
const defs = [
  { key: 'output_mean', label: 'Output 吞吐 (tok/s)' },
  { key: 'peakoutput_mean', label: 'Peak Output 吞吐 (tok/s)' },
  { key: 'total_mean', label: 'Total 吞吐 (tok/s)' },
  { key: 'ttft_mean', label: 'TTFT mean 耗时 (ms)' },
  { key: 'itl_mean', label: 'ITL mean 耗时 (ms)' },
  { key: 'tpot_mean', label: 'TPOT mean 耗时 (ms)' },
]

const tableRows = computed(() => {
  const bestMap = {}
  for (const label of Object.keys(props.best || {})) {
    const b = props.best[label]
    if (b && b.row) bestMap[`${label}-${b.concurrency}`] = true
  }
  return props.rows.map((r) => ({
    label: r.label,
    case_id: r.case_id,  // 相同 label 的多组可区分（图表按 case_id 分组）
    concurrency: r.concurrency,
    best: !!bestMap[`${r.label}-${r.concurrency}`],
    metrics: {
      output_mean: r.output,
      peakoutput_mean: r.peakoutput,
      total_mean: r.total,
      ttft_mean: r.ttft,
      tpot_mean: r.tpot,
      itl_mean: r.itl,
    },
  }))
})
</script>

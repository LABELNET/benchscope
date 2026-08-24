<template>
  <div>
    <MetricsCharts :rows="chartRows" :metric-defs="defs" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MetricsCharts from '@/components/MetricsCharts.vue'

const props = defineProps({
  records: { type: Array, default: () => [] },
})

const chartRows = computed(() =>
  props.records.map((r) => ({
    label: r.label,
    concurrency: r.concurrency,
    metrics: {
      output_mean: r.output_mean,
      total_mean: r.total_mean,
      ttft_mean: r.ttft_mean,
      tpot_mean: r.tpot_mean,
      ttft_p99: r.ttft_p99,
      tpot_p99: r.tpot_p99,
    },
  })),
)

// README 21：Output 吞吐 / Total 吞吐 / TTFT mean / TPOT mean / TTFT P99 / TPOT P99
const defs = [
  { key: 'output_mean', label: 'Output 吞吐 (tok/s)' },
  { key: 'total_mean', label: 'Total 吞吐 (tok/s)' },
  { key: 'ttft_mean', label: 'TTFT mean 耗时 (ms)' },
  { key: 'tpot_mean', label: 'TPOT mean 耗时 (ms)' },
  { key: 'ttft_p99', label: 'TTFT P99 耗时 (ms)' },
  { key: 'tpot_p99', label: 'TPOT P99 耗时 (ms)' },
]
</script>

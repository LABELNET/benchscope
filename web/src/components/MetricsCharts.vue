<template>
  <a-row :gutter="12">
    <a-col v-for="m in metricDefs" :key="m.key" :xs="24" :sm="12" :lg="8" style="margin-bottom: 12px">
      <div :style="{ height: height, width: '100%' }">
        <div class="chart-title">{{ m.label }}</div>
        <div :ref="(el) => setRef(m.key, el)" :style="{ height: chartHeight, width: '100%' }"></div>
      </div>
    </a-col>
  </a-row>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  metricDefs: { type: Array, default: () => [] },
  height: { type: String, default: '300px' },
})

const chartHeight = '260px'
const chartEls = {}
const charts = {}
const observers = []

function setRef(key, el) {
  if (!el) return
  chartEls[key] = el
  if (!charts[key]) {
    charts[key] = echarts.init(el)
    observers.push(new ResizeObserver(() => charts[key] && charts[key].resize()))
    observers[observers.length - 1].observe(el)
  }
}

function update() {
  for (const def of props.metricDefs) {
    const chart = charts[def.key]
    if (!chart) continue
    const seriesMap = {}
    for (const row of props.rows) {
      const m = row.metrics || {}
      const value = def.value ? def.value(m) : m[def.key]
      if (value === undefined || value === null) continue
      const label = row.label || row.case || 'unknown'
      if (!seriesMap[label]) seriesMap[label] = []
      seriesMap[label].push({ concurrency: row.concurrency, value: Number(value) })
    }
    const labels = Object.keys(seriesMap)
    const option = {
      color: ['#1677ff', '#52c41a', '#faad14', '#f5222d', '#13c2c2', '#722ed1', '#eb2f96', '#fa8c16'],
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255,255,255,0.96)',
        borderColor: '#f0f0f0',
        textStyle: { color: 'rgba(0,0,0,0.88)', fontSize: 12 },
        valueFormatter: (v) => (v === null || v === undefined ? '-' : Number(v).toFixed(2)),
      },
      legend: labels.length > 1 ? { data: labels, type: 'scroll', top: 0, textStyle: { fontSize: 12 } } : undefined,
      grid: { left: 54, right: 16, top: labels.length > 1 ? 32 : 20, bottom: 28 },
      xAxis: {
        type: 'category',
        name: '并发数',
        nameTextStyle: { fontSize: 11, color: 'rgba(0,0,0,0.45)' },
        axisLine: { lineStyle: { color: '#d9d9d9' } },
        axisLabel: { fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        scale: true,
        splitLine: { lineStyle: { type: 'dashed', color: '#f0f0f0' } },
        axisLabel: { fontSize: 11 },
      },
      series: labels.map((label) => {
        const pts = seriesMap[label].sort((a, b) => a.concurrency - b.concurrency)
        return {
          name: label,
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 2 },
          data: pts.map((p) => p.value),
          markPoint: {
            data: [{ type: 'max', name: '峰值' }],
            symbolSize: 44,
            label: { fontSize: 10 },
          },
        }
      }),
    }
    const xData = []
    for (const label of labels) {
      for (const p of seriesMap[label]) if (!xData.includes(p.concurrency)) xData.push(p.concurrency)
    }
    option.xAxis.data = xData.sort((a, b) => a - b)
    chart.setOption(option, true)
  }
}

watch(() => props.rows, update, { deep: true })
watch(() => props.metricDefs, update, { deep: true })
onMounted(update)

onBeforeUnmount(() => {
  observers.forEach((o) => o.disconnect())
  Object.values(charts).forEach((c) => c.dispose())
})
</script>

<style scoped>
.chart-title {
  font-size: 13px;
  color: #333;
  font-weight: 600;
  margin-bottom: 4px;
  padding-left: 4px;
}
</style>

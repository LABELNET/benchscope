<template>
  <div class="charts-wrapper">
    <a-row :gutter="8">
      <a-col v-for="m in metricDefs" :key="m.key" :xs="12" :sm="8" :md="8" style="margin-bottom: 8px">
        <div class="chart-container">
          <div class="chart-title">{{ m.label }}</div>
          <div :ref="(el) => setRef(m.key, el)" class="chart-canvas"></div>
        </div>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  metricDefs: { type: Array, default: () => [] },
  height: { type: String, default: '300px' },
})

const chartHeight = '180px'
const chartEls = {}
const charts = {}
const observers = []

function setRef(key, el) {
  if (!el) return
  chartEls[key] = el
  if (!charts[key]) {
    charts[key] = echarts.init(el)
    charts[key].group = 'perf-charts'
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
      color: def.color ? [def.color] : ['#1677ff', '#52c41a', '#faad14', '#f5222d', '#13c2c2', '#722ed1', '#eb2f96', '#fa8c16'],
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'line', snap: true, lineStyle: { color: '#1677ff', width: 1, type: 'dashed' } },
        backgroundColor: 'rgba(255,255,255,0.96)',
        borderColor: '#f0f0f0',
        textStyle: { color: 'rgba(0,0,0,0.88)', fontSize: 12 },
        valueFormatter: (v) => (v === null || v === undefined ? '-' : Number(v).toFixed(2)),
      },
      legend: labels.length > 1 ? { data: labels, type: 'scroll', top: 0, textStyle: { fontSize: 12 } } : undefined,
      grid: { left: 54, right: 40, top: labels.length > 1 ? 40 : 28, bottom: 28 },
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
            symbol: 'pin',
            symbolSize: 38,
            label: { fontSize: 10, color: '#fff' },
            data: [{ type: 'max', name: '峰值' }],
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
onMounted(() => {
  update()
  // 联动:同组的所有图表 hover 时同步显示 tooltip / axisPointer
  echarts.connect('perf-charts')
})

onBeforeUnmount(() => {
  observers.forEach((o) => o.disconnect())
  Object.values(charts).forEach((c) => c.dispose())
})
</script>

<style scoped>
.charts-wrapper {
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
}
.chart-container {
  height: 100%;
}
.chart-title {
  font-size: 11px;
  color: var(--ant-color-text-secondary, #666);
  font-weight: 600;
  margin-bottom: 2px;
  padding-left: 4px;
}
.chart-canvas {
  height: 180px;
  width: 100%;
}
</style>

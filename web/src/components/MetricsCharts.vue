<template>
  <div class="charts-grid">
    <div v-for="col in 4" :key="col" class="chart-col">
      <div class="chart-col-title">{{ columnTitles[col - 1] }}</div>
      <div v-for="rowIdx in 3" :key="rowIdx" class="chart-cell">
        <div class="chart-cell-title">{{ cellDefs[(col - 1) * 3 + (rowIdx - 1)].label }}</div>
        <div :ref="(el) => setRef(cellDefs[(col - 1) * 3 + (rowIdx - 1)].key, el)" class="chart-canvas"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import * as echarts from 'echarts'
import { t } from '@/i18n'

const props = defineProps({
  rows: { type: Array, default: () => [] },
})

// 12 张图：4 列 × 3 行。每列对应一个指标组。
//   列 1 吞吐 (tok/s)  - Output / Peak / Total
//   列 2 TTFT (ms)     - Mean / Median / P99
//   列 3 TPOT (ms)     - Mean / Median / P99
//   列 4 ITL (ms)      - Mean / Median / P99
// 每列内置 8 种线条颜色：同一列内同一 case 颜色相同（列内 3 张图共用该列调色板），不同列之间颜色不同
const COLUMN_PALETTES = [
  ['#1677ff', '#69b1ff', '#0958d9', '#3c9ae8', '#40a9ff', '#003eb3', '#1d39c4', '#2f54eb'],
  ['#52c41a', '#95de64', '#389e0d', '#73d13d', '#237804', '#a0d911', '#135200', '#5b8c00'],
  ['#fa8c16', '#ffc53d', '#d46b08', '#ffa940', '#ad4e00', '#faad14', '#873800', '#d48806'],
  ['#722ed1', '#b37feb', '#531dab', '#9254de', '#391085', '#c773e0', '#22075e', '#7c2ae9'],
]
const cellDefs = computed(() => [
  { key: 'output_mean', label: t('outputThroughputCol'), yUnit: 'tok/s', col: 0 },
  { key: 'peakoutput_mean', label: t('peakOutputThroughputCol'), yUnit: 'tok/s', col: 0 },
  { key: 'total_mean', label: t('totalThroughputCol'), yUnit: 'tok/s', col: 0 },
  { key: 'ttft_mean', label: t('meanTtftCol'), yUnit: 'ms', col: 1 },
  { key: 'ttft_median', label: t('medianTtftCol'), yUnit: 'ms', col: 1 },
  { key: 'ttft_p99', label: t('p99TtftCol'), yUnit: 'ms', col: 1 },
  { key: 'tpot_mean', label: t('meanTpotCol'), yUnit: 'ms', col: 2 },
  { key: 'tpot_median', label: t('medianTpotCol'), yUnit: 'ms', col: 2 },
  { key: 'tpot_p99', label: t('p99TpotCol'), yUnit: 'ms', col: 2 },
  { key: 'itl_mean', label: t('meanItlCol'), yUnit: 'ms', col: 3 },
  { key: 'itl_median', label: t('medianItlCol'), yUnit: 'ms', col: 3 },
  { key: 'itl_p99', label: t('p99ItlCol'), yUnit: 'ms', col: 3 },
])

const columnTitles = computed(() => [
  t('throughput'),
  t('timeToFirstToken'),
  t('timePerOutputToken'),
  t('interTokenLatency'),
])

const chartEls = {}
const charts = {}
const observers = []

function setRef(key, el) {
  if (!el) return
  chartEls[key] = el
  if (!charts[key]) {
    charts[key] = echarts.init(el)
    charts[key].group = 'perf-charts'
    const ob = new ResizeObserver(() => charts[key] && charts[key].resize())
    ob.observe(el)
    observers.push(ob)
  }
}

function buildOption(def) {
  // 每个 case 一个序列；x 轴为请求数（record.concurrency）
  const seriesMap = {}
  const xSet = new Set()
  for (const row of props.rows) {
    const m = row.metrics || {}
    const v = m[def.key]
    if (v === undefined || v === null) continue
    const label = row.label || row.case || 'unknown'
    if (!seriesMap[label]) seriesMap[label] = []
    seriesMap[label].push({ x: Number(row.concurrency), y: Number(v) })
    xSet.add(Number(row.concurrency))
  }
  const labels = Object.keys(seriesMap)
  const xData = Array.from(xSet).sort((a, b) => a - b)
  const hasData = labels.length > 0
  const palette = COLUMN_PALETTES[def.col] || COLUMN_PALETTES[0]
  return {
    color: palette,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line', snap: true, lineStyle: { color: '#1677ff', width: 1, type: 'dashed' } },
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#f0f0f0',
      textStyle: { color: 'rgba(0,0,0,0.88)', fontSize: 11 },
      valueFormatter: (v) => (v === null || v === undefined ? '-' : Number(v).toFixed(2)),
    },
    legend: labels.length > 1 ? { data: labels, type: 'scroll', top: 0, textStyle: { fontSize: 10 } } : undefined,
    grid: { left: 46, right: 12, top: labels.length > 1 ? 28 : 12, bottom: 22 },
    xAxis: {
      type: 'category',
      data: xData,
      name: t('xRequests'),
      nameLocation: 'middle',
      nameGap: 14,
      nameTextStyle: { fontSize: 10, color: 'rgba(0,0,0,0.45)' },
      axisLine: { lineStyle: { color: '#d9d9d9' } },
      axisLabel: { fontSize: 10 },
      splitLine: { show: true, lineStyle: { type: 'dashed', color: '#f0f0f0' } },
    },
    yAxis: {
      type: 'value',
      scale: hasData,
      min: hasData ? undefined : 0,
      max: hasData ? undefined : 100,
      name: def.yUnit,
      nameTextStyle: { fontSize: 10, color: 'rgba(0,0,0,0.45)' },
      splitLine: { show: true, lineStyle: { type: 'dashed', color: '#f0f0f0' } },
      axisLabel: { fontSize: 10 },
    },
    series: hasData ? labels.map((label) => {
      const pts = seriesMap[label].sort((a, b) => a.x - b.x)
      return {
        name: label,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { width: 1.5 },
        data: pts.map((p) => p.y),
      }
    }) : [{ type: 'line', data: [], animation: false }],
  }
}

function update() {
  for (const def of cellDefs.value) {
    const chart = charts[def.key]
    if (!chart) continue
    chart.setOption(buildOption(def), true)
  }
}

watch(() => props.rows, update, { deep: true })
watch(cellDefs, update, { deep: true })

onMounted(() => {
  // 等 DOM 渲染（v-for 动态 setRef）后再 update
  setTimeout(() => {
    update()
    // 联动：同组的所有图表 hover 时同步显示 tooltip / axisPointer
    echarts.connect('perf-charts')
  }, 0)
})

onBeforeUnmount(() => {
  observers.forEach((o) => o.disconnect())
  Object.values(charts).forEach((c) => c.dispose())
})
</script>

<style scoped>
.charts-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.chart-col {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.chart-col-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--ant-color-text, #000);
  text-align: center;
  padding: 4px 0;
  border-bottom: 1px solid var(--ant-color-border, #f0f0f0);
  margin-bottom: 4px;
}
.chart-cell {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chart-cell-title {
  font-size: 11px;
  color: var(--ant-color-text-secondary, #666);
  font-weight: 600;
  margin-bottom: 2px;
  padding-left: 4px;
}
.chart-canvas {
  height: 160px;
  width: 100%;
}
</style>

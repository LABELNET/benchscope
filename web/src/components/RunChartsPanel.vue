<template>
  <div class="run-charts-panel">
    <!-- 条件行：内容第一行左侧（默认 + cases 分组信息，可增删组） -->
    <div v-if="groups.length > 1" class="condition-row">
      <span class="cond-label">{{ t('groups') }}</span>
      <a-button size="small" type="text" class="cond-btn" :class="{ 'is-on': allGroupsOn }" @click="setGroupsAll(true)">
        {{ t('defaultBtn') }}
      </a-button>
      <a-button
        v-for="g in groups"
        :key="g.key"
        size="small"
        type="text"
        class="cond-btn"
        :class="{ 'is-on': enabledGroups[g.key] }"
        @click="toggleGroup(g.key)"
      >
        {{ g.label }}
      </a-button>
    </div>

    <!-- 图表：每行 3 个，共 4 行（Throughput / TTFT / TPOT / ITL） -->
    <div class="charts-rows">
      <div v-for="row in visibleRows" :key="row.key" class="chart-row">
        <div class="chart-row-title">{{ row.title }}</div>
        <div class="chart-row-grid">
          <div v-for="cell in row.cells" :key="cell.key" class="chart-cell">
            <div class="chart-cell-title">{{ cell.label }}</div>
            <div :ref="(el) => setRef(cell.key, el)" class="chart-canvas"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { t } from '@/i18n'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  visible: {
    type: Object,
    default: () => ({ throughput: true, ttft: true, tpot: true, itl: true }),
  },
  // 联动开关：开启时鼠标进入任一图，同组所有统计图浮动信息（tooltip）联动显示
  linked: { type: Boolean, default: true },
})
const emit = defineEmits(['update:visible'])

const GROUP = 'run-charts'

// 每行 3 个，共 4 行：行 = 指标组（Throughput / TTFT / TPOT / ITL），列 = 统计口径
const ROW_DEFS = [
  { key: 'throughput', title: t('throughput'), cells: [
    { key: 'output_mean', label: t('outputThroughputCol'), yUnit: 'tok/s' },
    { key: 'peakoutput_mean', label: t('peakOutputThroughputCol'), yUnit: 'tok/s' },
    { key: 'total_mean', label: t('totalThroughputCol'), yUnit: 'tok/s' },
  ] },
  { key: 'ttft', title: t('timeToFirstToken'), cells: [
    { key: 'ttft_mean', label: t('meanTtftCol'), yUnit: 'ms' },
    { key: 'ttft_median', label: t('medianTtftCol'), yUnit: 'ms' },
    { key: 'ttft_p99', label: t('p99TtftCol'), yUnit: 'ms' },
  ] },
  { key: 'tpot', title: t('timePerOutputToken'), cells: [
    { key: 'tpot_mean', label: t('meanTpotCol'), yUnit: 'ms' },
    { key: 'tpot_median', label: t('medianTpotCol'), yUnit: 'ms' },
    { key: 'tpot_p99', label: t('p99TpotCol'), yUnit: 'ms' },
  ] },
  { key: 'itl', title: t('interTokenLatency'), cells: [
    { key: 'itl_mean', label: t('meanItlCol'), yUnit: 'ms' },
    { key: 'itl_median', label: t('medianItlCol'), yUnit: 'ms' },
    { key: 'itl_p99', label: t('p99ItlCol'), yUnit: 'ms' },
  ] },
]

// 行显示状态由父级 header 控制（默认全部显示；TTFT/TPOT/ITL 可点击隐藏/恢复）
const visibleRows = computed(() => ROW_DEFS.filter((r) => props.visible[r.key]))

// cases 分组信息：caseKey（label#g{case_id}），仅多组时显示条件行
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

// 组启用状态：默认全启用；点击组取消该组数据，再点击恢复
const enabledGroups = reactive({})
function initGroups() {
  for (const g of groups.value) enabledGroups[g.key] = true
}
const allGroupsOn = computed(() => groups.value.every((g) => enabledGroups[g.key]))
function toggleGroup(key) {
  enabledGroups[key] = !enabledGroups[key]
}
function setGroupsAll(v) {
  for (const g of groups.value) enabledGroups[g.key] = v
}

// 过滤后的 rows：仅启用组的数据参与图表
const filteredRows = computed(() => {
  if (groups.value.length <= 1) return props.rows
  return props.rows.filter((row) => {
    const raw = row.label || row.case || 'unknown'
    const hasGid = row.case_id !== undefined && row.case_id !== null
    const key = hasGid ? `${raw}#g${row.case_id}` : raw
    return enabledGroups[key] !== false
  })
})

// 图表渲染（复用 perf 统计图的构建逻辑）
const PALETTES = [
  ['#1677ff', '#69b1ff', '#0958d9', '#3c9ae8', '#40a9ff', '#003eb3', '#1d39c4', '#2f54eb'],
  ['#52c41a', '#95de64', '#389e0d', '#73d13d', '#237804', '#a0d911', '#135200', '#5b8c00'],
  ['#fa8c16', '#ffc53d', '#d46b08', '#ffa940', '#ad4e00', '#faad14', '#873800', '#d48806'],
  ['#722ed1', '#b37feb', '#531dab', '#9254de', '#391085', '#c773e0', '#22075e', '#7c2ae9'],
]
const ROW_PALETTE_INDEX = { throughput: 0, ttft: 1, tpot: 2, itl: 3 }

const chartEls = {}
const charts = {}
const observers = []

function setRef(key, el) {
  if (chartEls[key] === el) return
  // DOM 变化（行隐藏/恢复、面板重建）：dispose 旧实例，绑定新 DOM 重建
  if (charts[key]) {
    charts[key].dispose()
    delete charts[key]
  }
  if (!el) return
  chartEls[key] = el
  charts[key] = echarts.init(el)
  charts[key].group = 'run-charts'
  const ob = new ResizeObserver(() => charts[key] && charts[key].resize())
  ob.observe(el)
  observers.push(ob)
}

function buildOption(def, rows) {
  const seriesMap = {}
  const xSet = new Set()
  for (const row of rows) {
    const m = row.metrics || {}
    const v = m[def.key]
    if (v === undefined || v === null) continue
    const rawLabel = row.label || row.case || 'unknown'
    const hasGid = row.case_id !== undefined && row.case_id !== null
    const label = hasGid ? `${rawLabel}#g${row.case_id}` : rawLabel
    if (!seriesMap[label]) seriesMap[label] = []
    seriesMap[label].push({ x: Number(row.concurrency), y: Number(v) })
    xSet.add(Number(row.concurrency))
  }
  const labels = Object.keys(seriesMap)
  const xData = Array.from(xSet).sort((a, b) => a - b)
  const hasData = labels.length > 0
  const rowKey = ROW_DEFS.find((r) => r.cells.some((c) => c.key === def.key))?.key || 'throughput'
  const palette = PALETTES[ROW_PALETTE_INDEX[rowKey]] || PALETTES[0]
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
    // 图例：位于 Y 轴右侧、曲线图内部，竖排对齐；颜色标记与文字缩小、透明度 60%
    legend: labels.length > 1 ? {
      data: labels,
      type: 'scroll',
      orient: 'vertical',
      left: 48,          // 紧贴 Y 轴刻度右侧（图内）
      top: 12,
      align: 'left',
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 5,
      itemStyle: { opacity: 0.6 },
      textStyle: { fontSize: 9, opacity: 0.6 },
    } : undefined,
    grid: { left: 46, right: 12, top: 12, bottom: 22 },
    xAxis: {
      type: 'category',
      data: xData,
      name: t('xRequests'),
      nameLocation: 'end',
      nameGap: -10,
      nameTextStyle: { fontSize: 10, color: 'rgba(0,0,0,0.45)', align: 'right' },
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
  for (const row of ROW_DEFS) {
    if (!props.visible[row.key]) continue
    for (const cell of row.cells) {
      const chart = charts[cell.key]
      if (!chart) continue
      chart.setOption(buildOption(cell, filteredRows.value), true)
    }
  }
}

watch(() => props.rows, () => { initGroups(); update() }, { deep: true, flush: 'post' })
watch(enabledGroups, update, { deep: true, flush: 'post' })
watch(() => props.visible, update, { deep: true, flush: 'post' })
watch(groups, initGroups, { deep: true })

// 联动开关：开启 connect 同组图表（hover 联动 tooltip），关闭 disconnect
watch(
  () => props.linked,
  (v) => {
    if (v) echarts.connect(GROUP)
    else echarts.disconnect(GROUP)
  },
)

onMounted(() => {
  initGroups()
  setTimeout(() => {
    update()
    if (props.linked) echarts.connect(GROUP)
  }, 0)
})

onBeforeUnmount(() => {
  observers.forEach((o) => o.disconnect())
  Object.values(charts).forEach((c) => c.dispose())
})
</script>

<style scoped>
.run-charts-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cond-btn {
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
  border-radius: 4px;
}
.cond-btn.is-on {
  color: #1677ff;
  font-weight: 600;
  background: rgba(22, 119, 255, 0.08);
}
.condition-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 4px;
  padding: 2px 0;
  flex-wrap: wrap;
}
.cond-label {
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
}
.charts-rows {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.chart-row {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chart-row-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--ant-color-text, #000);
  text-align: center;
  padding: 4px 0;
  border-bottom: 1px solid var(--ant-color-border, #f0f0f0);
  margin-bottom: 4px;
}
.chart-row-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
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

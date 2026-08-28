<template>
  <div class="metrics-table">
    <a-table
      :columns="visibleColumns"
      :data-source="tableData"
      :row-key="rowKey"
      :pagination="false"
      size="small"
      :scroll="{ y: scrollY, x: tableWidth }"
      :row-class-name="rowClass"
      bordered
    >
      <template #bodyCell="{ column, record }">
        <template v-if="record.group">
          <span v-if="column.key === 'label'" class="group-title">
            <span class="group-label">{{ record.label }}</span>
            <span class="group-count">{{ record.groupCount }} {{ t('rows') }}</span>
            <span v-if="groupThresholds[record.label]" class="group-threshold" :title="groupThresholds[record.label]">{{ groupThresholds[record.label] }}</span>
          </span>
          <template v-else></template>
        </template>
        <template v-else-if="column.key === 'label'">
          {{ record.label }}
          <span v-if="record.input_len" class="case-meta">({{ record.input_len }}/{{ record.output_len }})</span>
        </template>
        <template v-else-if="column.key === 'requests'">
          <span class="num-cell">{{ record.concurrency }}</span>
        </template>
        <template v-else-if="column.key === 'concurrency'">
          <span class="num-cell">{{ concurrencyText(record) }}</span>
        </template>
        <template v-else-if="column.key === 'successful'">
          {{ successRate(record) }}
        </template>
        <template v-else-if="column.key === 'output_mean'">
          <span>{{ num(record.metrics?.output_mean ?? record.metrics?.output) }}</span>
        </template>
        <template v-else-if="column.key === 'status'">
          <span class="status-tags">
            <a-tag v-if="record.error" color="red" size="small">{{ t('failed') }}</a-tag>
            <template v-else>
              <a-tag color="green" size="small">{{ t('success') }}</a-tag>
              <a-tag v-if="record.bestPerf" color="gold" size="small">{{ t('bestPerf') }}</a-tag>
              <a-tag v-if="record.best" color="gold" size="small">{{ t('best') }}</a-tag>
            </template>
          </span>
        </template>
      </template>
    </a-table>
    <div class="table-footer">
      <span class="row-count">{{ rows.length }} {{ t('rows') }}</span>
      <div class="footer-actions">
        <a-dropdown :trigger="['click']">
          <a-button size="small" type="text">
            <template #icon><setting-outlined /></template>
            {{ t('columnSettings') }}
          </a-button>
          <template #overlay>
            <a-menu>
              <a-menu-item-group v-for="grp in columnGroups" :key="grp.group" :title="grp.label">
                <a-menu-item v-for="col in grp.items" :key="col.key">
                  <a-checkbox
                    :checked="visibleKeys.includes(col.key)"
                    @change="(e) => toggleCol(col.key, e.target.checked)"
                  >{{ col.title }}</a-checkbox>
                </a-menu-item>
              </a-menu-item-group>
            </a-menu>
          </template>
        </a-dropdown>
        <a-button v-if="exportable" size="small" type="text" :loading="exporting" @click="exportExcel">
          <template #icon><download-outlined /></template>
          {{ t('download') }}
        </a-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { DownloadOutlined, SettingOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import http from '@/api'
import { t } from '@/i18n'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  threshold: { type: Number, default: null },
  requestRate: { type: [String, Number], default: 'inf' },
  maxRows: { type: Number, default: 16 },
  // 按该字段分组显示：每个组插入一行组标题；组内数据保持传入顺序
  groupBy: { type: String, default: null },
  // 分组标题行阈值信息：分组 label → 阈值条件文本（跟随 Groups 每组独立配置；0 表示未配置不显示）
  groupThresholds: { type: Object, default: () => ({}) },
  // 导出 Excel：需要任务 ID（写入任务记录缓存目录）；exportable 控制下载按钮显示
  taskId: { type: String, default: '' },
  exportable: { type: Boolean, default: false },
  // 列预设：default=默认列；mean/median/p99=仅显示对应统计口径列（变化时重置列选择）
  preset: { type: String, default: 'default' },
  // 默认隐藏的列键（仍可在列控制中开启）；如 Datas Perf Datas 隐藏 Case/Concurrency/Successful
  defaultHidden: { type: Array, default: () => [] },
})

// 列定义：key + title + 数据路径 + 默认可见
const ALL_COLUMNS = computed(() => [
  // 任务相关
  { key: 'label', title: t('caseCol'), group: 'task', width: 150, fixed: 'left', default: true },
  { key: 'requests', title: t('requestsCol'), group: 'task', width: 80, default: true },
  { key: 'concurrency', title: t('concurrencyCol'), group: 'task', width: 90, default: true },
  { key: 'successful', title: t('successfulCol'), group: 'task', width: 90, default: true },
  { key: 'successful_requests', title: t('successfulRequestsCol'), group: 'task', width: 110, default: false },
  { key: 'failed_requests', title: t('failedRequestsCol'), group: 'task', width: 100, default: false },
  { key: 'benchmark_duration', title: t('benchmarkDurationCol'), group: 'task', width: 130, default: false },
  { key: 'total_input_tokens', title: t('totalInputTokensCol'), group: 'task', width: 110, default: false },
  { key: 'total_generated_tokens', title: t('totalGeneratedTokensCol'), group: 'task', width: 130, default: false },
  // 吞吐
  { key: 'request_throughput', title: t('requestThroughputCol'), group: 'throughput', width: 140, default: false },
  { key: 'output_mean', title: t('outputThroughputCol'), group: 'throughput', width: 140, default: true },
  { key: 'peakoutput_mean', title: t('peakOutputThroughputCol'), group: 'throughput', width: 150, default: true },
  { key: 'peak_concurrent', title: t('peakConcurrentCol'), group: 'throughput', width: 130, default: false },
  { key: 'total_mean', title: t('totalThroughputCol'), group: 'throughput', width: 140, default: true },
  // TTFT
  { key: 'ttft_mean', title: t('meanTtftCol'), group: 'ttft', width: 110, default: true },
  { key: 'ttft_median', title: t('medianTtftCol'), group: 'ttft', width: 120, default: true },
  { key: 'ttft_p99', title: t('p99TtftCol'), group: 'ttft', width: 100, default: true },
  // TPOT
  { key: 'tpot_mean', title: t('meanTpotCol'), group: 'tpot', width: 110, default: true },
  { key: 'tpot_median', title: t('medianTpotCol'), group: 'tpot', width: 120, default: true },
  { key: 'tpot_p99', title: t('p99TpotCol'), group: 'tpot', width: 100, default: true },
  // ITL
  { key: 'itl_mean', title: t('meanItlCol'), group: 'itl', width: 110, default: false },
  { key: 'itl_median', title: t('medianItlCol'), group: 'itl', width: 120, default: false },
  { key: 'itl_p99', title: t('p99ItlCol'), group: 'itl', width: 100, default: false },
  // 状态
  { key: 'status', title: t('statusCol'), group: 'task', width: 180, fixed: 'right', default: true },
])

const visibleKeys = ref(ALL_COLUMNS.value.filter((c) => c.default).map((c) => c.key))

// 列预设：默认=与实时数据一致；mean/median/p99=仅显示对应统计口径（Requests/Concurrency/Output/Peak/Total + 各自TTFT/TPOT/ITL + Status）
const PRESET_KEYS = {
  default: null,
  // 各统计口径统一保留 用例/请求/并发/成功 标识列，与 Performance 实时页默认列集保持一致
  mean: ['label', 'requests', 'concurrency', 'successful', 'output_mean', 'peakoutput_mean', 'total_mean', 'ttft_mean', 'tpot_mean', 'itl_mean', 'status'],
  median: ['label', 'requests', 'concurrency', 'successful', 'output_mean', 'peakoutput_mean', 'total_mean', 'ttft_median', 'tpot_median', 'itl_median', 'status'],
  p99: ['label', 'requests', 'concurrency', 'successful', 'output_mean', 'peakoutput_mean', 'total_mean', 'ttft_p99', 'tpot_p99', 'itl_p99', 'status'],
}
watch(
  () => props.preset,
  (p) => {
    // 默认列：排除 defaultHidden 指定的列键（仍可经列控制开启）
    const baseKeys = () =>
      ALL_COLUMNS.value
        .filter((c) => c.default && !props.defaultHidden.includes(c.key))
        .map((c) => c.key)
    if (p === 'default' || !PRESET_KEYS[p]) {
      visibleKeys.value = baseKeys()
      return
    }
    visibleKeys.value = PRESET_KEYS[p].filter(
      (k) => ALL_COLUMNS.value.some((c) => c.key === k) && !props.defaultHidden.includes(k),
    )
  },
  { immediate: true },
)

function toggleCol(key, checked) {
  if (checked && !visibleKeys.value.includes(key)) visibleKeys.value.push(key)
  else if (!checked) visibleKeys.value = visibleKeys.value.filter((k) => k !== key)
}

const visibleColumns = computed(() => {
  const keys = visibleKeys.value
  const cols = ALL_COLUMNS.value
    .filter((c) => keys.includes(c.key))
    .map((c) => {
      // 默认列：单行不换行；可选列：允许换行
      const isDefault = ALL_COLUMNS.value.find((x) => x.key === c.key)?.default
      const col = {
        title: c.title,
        key: c.key,
        width: c.width,
        ellipsis: false,
        // 默认列单行不换行,可选列可换行
        className: isDefault ? 'col-default' : 'col-optional',
      }
      if (c.fixed) col.fixed = c.fixed
      if (c.key !== 'label' && c.key !== 'requests' && c.key !== 'concurrency' && c.key !== 'successful' && c.key !== 'status') {
        col.dataIndex = ['metrics', c.key]
        col.customRender = ({ text }) => num(text)
      }
      return col
    })
  // Case(label) 列被隐藏（如 Datas Perf Datas）时，自动固定首个可见任务列（Requests）
  if (cols.length && !cols.some((c) => c.fixed === 'left')) {
    cols[0] = { ...cols[0], fixed: 'left' }
  }
  return cols
})

const columnGroups = computed(() => {
  const groupMap = {}
  for (const c of ALL_COLUMNS.value) {
    if (!groupMap[c.group]) groupMap[c.group] = []
    groupMap[c.group].push(c)
  }
  const labels = { task: t('task'), throughput: t('throughput'), ttft: t('timeToFirstToken'), tpot: t('timePerOutputToken'), itl: t('interTokenLatency') }
  return Object.keys(groupMap).map((g) => ({ group: g, label: labels[g] || g, items: groupMap[g] }))
})

const tableWidth = computed(() => visibleColumns.value.reduce((sum, c) => sum + (c.width || 80), 0))

// 表格数据：默认仅显示前 maxRows 行；分组模式下按 groupBy 分组，每组前插入一行组标题（扁平结构，避免触发树形缩进）
const tableData = computed(() => {
  if (!props.groupBy) return props.rows.slice(0, props.maxRows)
  const map = new Map()
  for (const r of props.rows) {
    const key = String(r[props.groupBy] ?? '-')
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(r)
  }
  const out = []
  for (const [label, items] of map.entries()) {
    out.push({ key: `group-${label}`, group: true, label, groupCount: items.length })
    out.push(...items.slice(0, props.maxRows))
  }
  return out
})

// 竖向滚动高度：分组模式按总行数（含组标题行）动态计算，最多 24 行
const scrollY = computed(() => {
  if (!props.groupBy) return 16 * 28 + 36
  const groups = new Set(props.rows.map((r) => String(r[props.groupBy] ?? '-'))).size
  const n = Math.min(props.rows.length + groups, 24)
  return n * 28 + 36
})

function num(v) {
  if (v === undefined || v === null || v === '') return '-'
  const n = Number(v)
  if (isNaN(n)) return '-'
  return Number.isInteger(n) ? String(n) : n.toFixed(2)
}

function concurrencyText(record) {
  const rate = String(props.requestRate || 'inf').toLowerCase()
  if (rate === 'inf' || rate === 'infinity') return 'Inf'
  if (rate === 'follow') return String(record.concurrency)
  // 否则展示 metrics 中的实际并发度,缺失时回退到 record.concurrency
  const m = record.metrics || {}
  if (m.concurrency !== undefined && m.concurrency !== null) return String(m.concurrency)
  return String(record.concurrency)
}

function successRate(record) {
  const m = record.metrics || {}
  const ok = m.successful_requests
  const fail = m.failed_requests || 0
  if (ok === undefined || ok === null) {
    if (record.error) return '0%'
    return '-'
  }
  const total = Number(ok) + Number(fail)
  if (!total) return '-'
  return Math.round((Number(ok) / total) * 100) + '%'
}

function rowKey(record) {
  if (record.group) return record.key
  return `${record.label || record.case || ''}-${record.concurrency}`
}

function rowClass(record) {
  // 组标题行
  if (record.group) return 'row-group'
  // BestPerf（任务阈值）行金色高亮；Best（本地面板阈值）行绿色高亮
  if (record.bestPerf) return 'row-bestperf'
  if (record.best) return 'row-best'
  return ''
}

// 导出 Excel：将当前表格内容（含分组标题行）发送后端生成 xlsx 并下载，同时写入任务记录缓存目录
const exporting = ref(false)

function cellText(key, record) {
  switch (key) {
    case 'label':
      if (record.group) return record.label
      return record.input_len ? `${record.label} (${record.input_len}/${record.output_len})` : record.label
    case 'requests':
      return String(record.concurrency)
    case 'concurrency':
      return concurrencyText(record)
    case 'successful':
      return successRate(record)
    case 'status': {
      if (record.error) return t('failed')
      let s = t('success')
      if (record.bestPerf) s += ' ' + t('bestPerf')
      if (record.best) s += ' ' + t('best')
      return s
    }
    default:
      return num(record.metrics?.[key])
  }
}

async function exportExcel() {
  if (!props.taskId) {
    message.warning(t('noTask'))
    return
  }
  exporting.value = true
  try {
    const headers = visibleColumns.value.map((c) => c.title)
    const rows = tableData.value.map((r) => ({
      group: !!r.group,
      values: visibleColumns.value.map((c) => cellText(c.key, r)),
    }))
    const blob = await http.post(`/api/tasks/${props.taskId}/export`, { headers, rows }, { responseType: 'blob' })
    const d = new Date()
    const pad = (n) => String(n).padStart(2, '0')
    const fname = `realtime_${props.taskId}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}.xlsx`
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fname
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    message.success(t('exported'))
  } catch (e) {
    message.error(e?.message || t('exportFailed'))
  } finally {
    exporting.value = false
  }
}
</script>

<style>
.metrics-table .ant-table-thead .ant-table-cell {
  white-space: normal !important;
  word-break: break-word;
  font-size: 12px !important;
  padding: 2px 4px !important;
}
.metrics-table .ant-table-tbody .ant-table-cell {
  font-size: 12px !important;
  padding: 1px 4px !important;
}
/* 默认列：单行不换行 */
.metrics-table .ant-table-tbody .ant-table-cell.col-default {
  white-space: nowrap !important;
}
/* 可选列：允许换行 */
.metrics-table .ant-table-tbody .ant-table-cell.col-optional {
  white-space: normal !important;
  word-break: break-word;
}
.metrics-table .num-cell {
  font-weight: 600;
}
.metrics-table .status-tags {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}
.metrics-table .case-meta {
  color: #999;
  font-size: 11px;
  margin-left: 4px;
}
/* 组标题行：横跨的分组条 */
.metrics-table .group-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.metrics-table .group-label {
  font-weight: 600;
  color: #1677ff;
}
.metrics-table .group-count {
  font-size: 11px;
  font-weight: 400;
  color: var(--ant-color-text-secondary, #666);
}
/* 组标题行阈值信息：跟随 Groups 每组独立配置；宽度不够伪隐藏（省略号 + title 完整文本） */
.metrics-table .group-threshold {
  font-size: 11px;
  font-weight: 400;
  color: var(--ant-color-text-tertiary, #999);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex-shrink: 1;
  max-width: 300px;
}
.metrics-table .row-group > td {
  background-color: #e6f4ff !important;
  color: #000;
  font-weight: 600;
  border-bottom: 1px solid #91caff !important;
}
.metrics-table .row-group:hover > td {
  background-color: #bae0ff !important;
}
/* 仅 Best 行高亮绿色,其他行默认灰底黑字 */
.metrics-table .ant-table-tbody > tr > td {
  background-color: #fafafa;
  color: #000;
}
.metrics-table .ant-table-tbody > tr:hover > td {
  background-color: #f5f5f5 !important;
}
.metrics-table .row-best > td {
  background-color: #d9f7be !important;
  color: #000;
}
.metrics-table .row-best:hover > td {
  background-color: #c5e8ad !important;
}
.metrics-table .row-bestperf > td {
  background-color: #fff1b8 !important;
  color: #000;
}
.metrics-table .row-bestperf:hover > td {
  background-color: #ffe58f !important;
}
.metrics-table .table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 4px 0;
  margin-top: 4px;
}
.metrics-table .footer-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}
.metrics-table .row-count {
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
}
</style>

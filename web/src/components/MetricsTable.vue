<template>
  <div class="metrics-table">
    <a-table
      :columns="visibleColumns"
      :data-source="cappedRows"
      :row-key="rowKey"
      :pagination="false"
      size="small"
      :scroll="{ y: 16 * 28 + 36, x: tableWidth }"
      :row-class-name="rowClass"
      bordered
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'label'">
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
        <template v-else-if="column.key === 'status'">
          <span class="status-tags">
            <a-tag v-if="record.error" color="red" size="small">{{ t('failed') }}</a-tag>
            <template v-else>
              <a-tag color="green" size="small">{{ t('success') }}</a-tag>
              <a-tag v-if="record.best" color="gold" size="small">{{ t('best') }}</a-tag>
            </template>
          </span>
        </template>
      </template>
    </a-table>
    <div class="table-footer">
      <span class="row-count">{{ rows.length }} {{ t('rows') }}</span>
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
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { SettingOutlined } from '@ant-design/icons-vue'
import { t } from '@/i18n'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  threshold: { type: Number, default: null },
  requestRate: { type: [String, Number], default: 'inf' },
  maxRows: { type: Number, default: 16 },
})

// 列定义：key + title + 数据路径 + 默认可见
const ALL_COLUMNS = computed(() => [
  // 任务相关
  { key: 'label', title: t('caseCol'), group: 'task', width: 90, fixed: 'left', default: true },
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
  { key: 'status', title: t('statusCol'), group: 'task', width: 80, fixed: 'right', default: true },
])

const visibleKeys = ref(ALL_COLUMNS.value.filter((c) => c.default).map((c) => c.key))

function toggleCol(key, checked) {
  if (checked && !visibleKeys.value.includes(key)) visibleKeys.value.push(key)
  else if (!checked) visibleKeys.value = visibleKeys.value.filter((k) => k !== key)
}

const visibleColumns = computed(() => {
  const keys = visibleKeys.value
  return ALL_COLUMNS.value
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

// 仅显示前 maxRows 行（竖向滚动由表格内部 scroll.y 处理）
const cappedRows = computed(() => props.rows.slice(0, props.maxRows))

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
  return ((Number(ok) / total) * 100).toFixed(2) + '%'
}

function rowKey(record) {
  return `${record.label || record.case || ''}-${record.concurrency}`
}

function rowClass(record) {
  // 仅 Best 行高亮绿色,其他行均为默认灰底黑字
  if (record.best) return 'row-best'
  return ''
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
.metrics-table .table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 4px 0;
  margin-top: 4px;
}
.metrics-table .row-count {
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
}
</style>

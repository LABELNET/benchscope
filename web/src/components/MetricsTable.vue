<template>
  <div class="metrics-table">
    <a-table
      :columns="columns"
      :data-source="rows"
      :row-key="rowKey"
      :pagination="pagination"
      size="small"
      :scroll="{ x: 728 }"
      :row-class-name="rowClass"
      bordered
    >
    <template #bodyCell="{ column, record }">
      <template v-if="column.key === 'concurrency'">
        <span :style="{ fontWeight: 600 }">{{ record.concurrency }}</span>
      </template>
      <template v-else-if="column.key === 'status'">
        <a-tag v-if="record.error" color="red" size="small">{{ t('failed') }}</a-tag>
        <template v-else>
          <a-tag color="green" size="small">{{ t('success') }}</a-tag>
          <a-tag v-if="record.best" color="gold" size="small">{{ t('best') }}</a-tag>
        </template>
      </template>
      <template v-else-if="column.key === 'label'">
        {{ record.label }}
        <span v-if="record.input_len" style="color: #999; font-size: 11px">
          ({{ record.input_len }}/{{ record.output_len }})
        </span>
      </template>
    </template>
  </a-table>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { t } from '@/i18n'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  threshold: { type: Number, default: null },
  pagination: { type: [Boolean, Object], default: false },
})

const columns = computed(() => [
  { title: t('caseCol'), key: 'label', width: 76, fixed: 'left' },
  { title: t('concurrency'), key: 'concurrency', width: 48, fixed: 'left' },
  { title: 'Output', dataIndex: ['metrics', 'output_mean'], key: 'output', width: 60, customRender: num },
  { title: 'Peak', dataIndex: ['metrics', 'peakoutput_mean'], key: 'peak', width: 56, customRender: num },
  { title: 'Total', dataIndex: ['metrics', 'total_mean'], key: 'total', width: 60, customRender: num },
  { title: 'TTFT', dataIndex: ['metrics', 'ttft_mean'], key: 'ttft_mean', width: 54, customRender: num },
  { title: 'TPOT', dataIndex: ['metrics', 'tpot_mean'], key: 'tpot_mean', width: 54, customRender: num },
  { title: 'ITL', dataIndex: ['metrics', 'itl_mean'], key: 'itl_mean', width: 48, customRender: num },
  { title: 'T·P99', dataIndex: ['metrics', 'ttft_p99'], key: 'ttft_p99', width: 54, customRender: num },
  { title: 'P·P99', dataIndex: ['metrics', 'tpot_p99'], key: 'tpot_p99', width: 54, customRender: num },
  { title: 'I·P99', dataIndex: ['metrics', 'itl_p99'], key: 'itl_p99', width: 48, customRender: num },
  { title: 'QPS', key: 'single_user', width: 44, customRender: singleUser },
  { title: t('statusCol'), key: 'status', width: 72, fixed: 'right' },
])

function num({ text }) {
  if (text === undefined || text === null) return '-'
  return Number(text).toFixed(2)
}
function singleUser({ record }) {
  const v = record.metrics?.single_user
  if (v === undefined || v === null) return '-'
  return Number(v).toFixed(2)
}

function rowKey(record) {
  return `${record.label || record.case || ''}-${record.concurrency}`
}

function rowClass(record) {
  if (record.error) return 'row-error'
  if (record.best) return 'row-best'
  const tpot = record.metrics?.tpot_mean
  if (tpot !== undefined && tpot !== null && props.threshold) {
    if (Number(tpot) < Number(props.threshold)) return 'row-near-threshold'
  }
  return ''
}
</script>

<style>
.metrics-table .ant-table-thead .ant-table-cell {
  font-size: 11px !important;
  padding: 3px 4px !important;
  white-space: nowrap;
}
.metrics-table .ant-table-tbody .ant-table-cell {
  font-size: 10px !important;
  padding: 1px 4px !important;
  white-space: nowrap;
}
.row-near-threshold > td {
  background-color: #f6ffed !important;
}
.row-best > td {
  background-color: #d9f7be !important;
  font-weight: 600;
}
.row-error > td {
  background-color: #fff1f0 !important;
}
</style>

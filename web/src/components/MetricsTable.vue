<template>
  <a-table
    :columns="columns"
    :data-source="rows"
    :row-key="rowKey"
    :pagination="pagination"
    size="small"
    :scroll="{ x: 1400 }"
    :row-class-name="rowClass"
    bordered
  >
    <template #bodyCell="{ column, record }">
      <template v-if="column.key === 'concurrency'">
        <span :style="{ fontWeight: 600 }">{{ record.concurrency }}</span>
      </template>
      <template v-else-if="column.key === 'status'">
        <a-tag v-if="record.error" color="red">失败</a-tag>
        <a-tag v-else-if="record.best" color="gold">最佳</a-tag>
        <a-tag v-else color="green">成功</a-tag>
      </template>
      <template v-else-if="column.key === 'label'">
        {{ record.label }}
        <span v-if="record.input_len" style="color: #999; font-size: 12px">
          ({{ record.input_len }}/{{ record.output_len }})
        </span>
      </template>
    </template>
  </a-table>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  threshold: { type: Number, default: null },
  pagination: { type: [Boolean, Object], default: false },
})

const columns = computed(() => [
  { title: '用例 Case', key: 'label', width: 180, fixed: 'left' },
  { title: '并发数 Concurrency', key: 'concurrency', width: 110, fixed: 'left' },
  { title: 'Output 吞吐 Output tok/s', dataIndex: ['metrics', 'output_mean'], key: 'output', width: 130, customRender: num },
  { title: 'Peak Output 吞吐 Peak tok/s', dataIndex: ['metrics', 'peakoutput_mean'], key: 'peak', width: 140, customRender: num },
  { title: 'Total 吞吐 Total tok/s', dataIndex: ['metrics', 'total_mean'], key: 'total', width: 130, customRender: num },
  { title: 'TTFT mean (ms)', dataIndex: ['metrics', 'ttft_mean'], key: 'ttft_mean', width: 120, customRender: num },
  { title: 'TPOT mean (ms)', dataIndex: ['metrics', 'tpot_mean'], key: 'tpot_mean', width: 120, customRender: num },
  { title: 'ITL mean (ms)', dataIndex: ['metrics', 'itl_mean'], key: 'itl_mean', width: 120, customRender: num },
  { title: 'TTFT P99 (ms)', dataIndex: ['metrics', 'ttft_p99'], key: 'ttft_p99', width: 120, customRender: num },
  { title: 'TPOT P99 (ms)', dataIndex: ['metrics', 'tpot_p99'], key: 'tpot_p99', width: 120, customRender: num },
  { title: 'ITL P99 (ms)', dataIndex: ['metrics', 'itl_p99'], key: 'itl_p99', width: 120, customRender: num },
  { title: '单用户 QPS (1000/TPOT)', key: 'single_user', width: 150, customRender: singleUser },
  { title: '状态 Status', key: 'status', width: 90, fixed: 'right' },
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
.row-near-threshold > td {
  background-color: #e6fffb !important;
}
.row-best > td {
  background-color: #fffbe6 !important;
  font-weight: 600;
}
.row-error > td {
  background-color: #fff1f0 !important;
}
</style>

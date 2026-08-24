<template>
  <div class="record-list">
    <div class="record-head">
      <span class="record-title">测试记录</span>
      <a-select
        v-if="!fixedFramework"
        v-model:value="frameworkFilter"
        size="small"
        style="width: 110px"
        :options="[
          { value: '', label: '全部' },
          { value: 'vllm', label: 'vLLM' },
          { value: 'sglang', label: 'SGLang' },
        ]"
      />
      <a-tag v-else size="small" color="blue">{{ frameworkName(fixedFramework) }}</a-tag>
    </div>
    <a-spin :spinning="loading">
      <a-list size="small" bordered :data-source="filteredRuns">
        <template #renderItem="{ item }">
          <a-list-item
            style="cursor: pointer"
            :class="{ 'record-selected': item.run_id === modelValue }"
            @click="$emit('update:modelValue', item.run_id)"
          >
            <a-list-item-meta>
              <template #title>
                <span style="font-weight: 600; font-size: 13px">{{ item.run_id }}</span>
                <a-tag size="small" :color="statusColor(item.meta?.status)" style="margin-left: 6px">
                  {{ statusText(item.meta?.status) }}
                </a-tag>
              </template>
              <template #description>
                <div style="font-size: 12px; line-height: 1.6">
                  <div>{{ item.meta?.framework || '-' }} · {{ item.meta?.model || '-' }}</div>
                  <div>{{ item.meta?.started_at || '' }} · {{ item.files.length }} 文件</div>
                </div>
              </template>
            </a-list-item-meta>
          </a-list-item>
        </template>
        <template #empty>
          <div style="padding: 12px; color: #999">暂无日志记录</div>
        </template>
      </a-list>
    </a-spin>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '@/api'
import { useTestStore } from '@/store/test'

const props = defineProps({
  modelValue: { type: String, default: '' },
  framework: { type: String, default: '' }, // '' 可筛选；'vllm'/'sglang' 固定
})
const emit = defineEmits(['update:modelValue'])

const test = useTestStore()
const fixedFramework = computed(() => props.framework)
const frameworkFilter = ref(props.framework || '')
const runs = ref([])
const loading = ref(false)

const filteredRuns = computed(() => {
  const fw = fixedFramework.value || frameworkFilter.value
  if (!fw) return runs.value
  const name = fw === 'vllm' ? 'vLLM' : 'SGLang'
  return runs.value.filter((r) => (r.meta?.framework || '') === name)
})

function frameworkName(fw) {
  return fw === 'vllm' ? 'vLLM' : 'SGLang'
}
function statusColor(s) {
  return s === 'done' ? 'green' : s === 'error' ? 'red' : s === 'stopped' ? 'orange' : 'blue'
}
function statusText(s) {
  return s === 'done' ? '完成' : s === 'error' ? '失败' : s === 'stopped' ? '已停止' : '运行中'
}

async function load() {
  loading.value = true
  try {
    const resp = await api.listRuns()
    runs.value = resp.runs || []
  } finally {
    loading.value = false
  }
}

// 默认选中当前测试进程 / 列表第一条
watch(
  filteredRuns,
  (list) => {
    if (!list.length) {
      if (props.modelValue) emit('update:modelValue', '')
      return
    }
    const cur = props.modelValue && list.some((r) => r.run_id === props.modelValue)
    if (!cur) {
      const preferred = test.lastRunId && list.some((r) => r.run_id === test.lastRunId)
        ? test.lastRunId
        : list[0].run_id
      emit('update:modelValue', preferred)
    }
  },
  { immediate: true },
)

watch(() => test.lastRunId, load)
watch(frameworkFilter, () => {})
onMounted(load)
</script>

<style scoped>
.record-list {
  padding: 12px 8px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.record-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  padding: 0 8px;
}
.record-title {
  font-weight: 600;
  font-size: 14px;
}
.record-selected {
  background: #e6f4ff;
}
</style>

<template>
  <div>
    <!-- 状态提示 -->
    <a-alert
      v-if="running"
      type="info"
      show-icon
      :message="`测试进行中：${currentCaseText}（并发 ${currentConc ?? '-'}）`"
      :description="`已出结果 ${doneCount}/${totalItems}，运行 ${elapsedText}，请勿关闭页面`"
      style="margin-bottom: 12px"
    />
    <a-alert
      v-else-if="runStatus === 'done'"
      type="success"
      show-icon
      message="测试完成"
      :description="summaryText"
      style="margin-bottom: 12px"
    />
    <a-alert
      v-else-if="runStatus === 'stopped'"
      type="warning"
      show-icon
      message="测试已取消"
      :description="`已出结果 ${doneCount}/${totalItems}`"
      style="margin-bottom: 12px"
    />
    <a-alert
      v-else-if="runStatus === 'error'"
      type="error"
      show-icon
      message="测试执行出错"
      :description="test.error"
      style="margin-bottom: 12px"
    />
    <a-alert
      v-else
      type="info"
      show-icon
      message="等待开始测试"
      description="配置好测试参数后，点击「开始测试」执行性能压测"
      style="margin-bottom: 12px"
    />

    <div class="progress-row">
      <a-progress
        v-if="totalItems > 0"
        type="circle"
        :size="64"
        :percent="percent"
        :status="percent >= 100 ? 'success' : running ? 'active' : 'normal'"
      />
      <div class="progress-info">
        <a-space wrap>
          <a-tag v-if="runId" color="blue">Run {{ runId }}</a-tag>
          <a-tag v-if="modelName">{{ modelName }}</a-tag>
          <a-tag v-if="frameworkName" color="purple">{{ frameworkName }}</a-tag>
          <a-tag v-if="gpuLabel">GPU: {{ gpuLabel }}</a-tag>
        </a-space>
        <div class="progress-stats">
          <span>进度：<b>{{ doneCount }}</b> / {{ totalItems }}</span>
          <span v-if="running">当前：{{ currentCaseText }} @ 并发 {{ currentConc ?? '-' }}</span>
        </div>
      </div>
      <div class="progress-actions">
        <a-checkbox v-model:checked="form.force" style="margin-right: 4px">离线强制开始</a-checkbox>
        <a-button
          type="primary"
          size="large"
          :loading="starting"
          :disabled="running"
          @click="$emit('start')"
        >
          <template #icon><play-circle-outlined /></template>
          开始测试
        </a-button>
        <a-button size="large" danger :disabled="!running" @click="$emit('stop')">
          <template #icon><stop-outlined /></template>
          取消测试
        </a-button>
      </div>
    </div>

    <!-- 实时日志尾巴（默认展开） -->
    <a-collapse v-if="logTail.length" ghost style="margin-top: 12px" v-model:activeKey="logKeys">
      <a-collapse-panel key="log" :header="`实时输出（${logTail.length} 行，仅尾部）`">
        <pre class="log-console" ref="logBox">{{ logTail.join('') }}</pre>
      </a-collapse-panel>
    </a-collapse>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { PlayCircleOutlined, StopOutlined } from '@ant-design/icons-vue'
import { useTestStore } from '@/store/test'
import { useTestForm } from '@/store/form'

const props = defineProps({
  starting: { type: Boolean, default: false },
})
const emit = defineEmits(['start', 'stop'])

const test = useTestStore()
const form = useTestForm()
const logBox = ref(null)
const logKeys = ref(['log'])

const running = computed(() => test.running)
const runStatus = computed(() => test.run?.status || 'idle')
const runId = computed(() => test.lastRunId || test.run?.run_id || '')
const modelName = computed(() => test.run?.model || '')
const frameworkName = computed(() => test.run?.framework_name || '')
const gpuLabel = computed(() => {
  const g = test.run?.gpu
  if (!g) return ''
  if (g.name) return `${g.name}×${g.count}`
  return `×${g.count}`
})
const cases = computed(() => test.run?.cases || [])
const concList = computed(() => test.run?.concurrency_list || [])
const totalItems = computed(() => cases.value.length * concList.value.length)
const doneCount = computed(() => test.rows.filter((r) => r.metrics || r.error).length)
const percent = computed(() => (totalItems.value ? Math.round((doneCount.value / totalItems.value) * 100) : 0))

const currentCase = computed(() => test.currentCase || '')
const currentConc = computed(() => test.currentConc ?? null)
const currentCaseText = computed(() => {
  const c = cases.value.find((x) => x.label === currentCase.value)
  if (!c) return currentCase.value || '-'
  return c.input_len ? `${c.label}（${c.input_len}/${c.output_len}）` : c.label
})
const logTail = computed(() => test.logLines.slice(-120))

const summaryText = computed(() => {
  const s = test.run?.summary
  if (s?.xlsx) return `共 ${s.rows} 条结果，汇总文件：${s.xlsx}`
  if (doneCount.value) return `共 ${doneCount.value} 条结果（无 xlsx 汇总，可能全部失败）`
  return '未产生结果'
})

// 运行时长
const now = ref(Date.now())
let timer = null
watch(
  running,
  (v) => {
    if (timer) clearInterval(timer)
    if (v) {
      now.value = Date.now()
      timer = setInterval(() => (now.value = Date.now()), 1000)
    }
  },
  { immediate: true },
)
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
const elapsedText = computed(() => {
  const started = test.run?.started_at
  if (!started) return '-'
  const s = dayjs(started, 'YYYY-MM-DD HH:mm:ss')
  const diff = Math.max(0, now.value - s.valueOf())
  const sec = Math.floor(diff / 1000)
  return `${Math.floor(sec / 60)}分${sec % 60}秒`
})

// 自动滚动日志
watch(
  () => test.logLines.length,
  async () => {
    await nextTick()
    if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight
  },
)
</script>

<style scoped>
.progress-row {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}
.progress-info {
  flex: 1;
  min-width: 240px;
}
.progress-stats {
  margin-top: 6px;
  color: rgba(0, 0, 0, 0.65);
  font-size: 13px;
  display: flex;
  gap: 16px;
}
.progress-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.log-console {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  max-height: 220px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
</style>

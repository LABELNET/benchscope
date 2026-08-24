<template>
  <div class="run-detail">
    <a-empty v-if="!runId" description="请选择左侧测试记录" style="padding-top: 80px" />
    <template v-else>
      <a-card size="small" class="detail-meta" :bordered="true">
        <a-space wrap>
          <a-tag color="blue">{{ summary.meta?.framework_name || meta?.framework || '-' }}</a-tag>
          <a-tag>{{ summary.meta?.model || meta?.model || '-' }}</a-tag>
          <a-tag v-if="meta?.gpu">GPU: {{ meta.gpu }}</a-tag>
          <a-tag v-if="meta?.precision">精度: {{ meta.precision }}</a-tag>
          <a-tag>{{ meta?.started_at || '' }} → {{ meta?.finished_at || '' }}</a-tag>
          <a-tag :color="statusColor(meta?.status)">{{ statusText(meta?.status) }}</a-tag>
          <a-button size="small" type="primary" ghost @click="downloadFile(xlsxName)">下载 xlsx 汇总</a-button>
          <a-button size="small" @click="refresh">刷新</a-button>
        </a-space>
      </a-card>

      <a-tabs v-model:activeKey="activeTab" class="detail-tabs">
        <a-tab-pane key="summary" tab="指标汇总">
          <RunSummaryBlock :records="summary.records || []" />
        </a-tab-pane>
        <a-tab-pane key="mean" tab="均值分析 Mean">
          <AnalysisBlock :rows="summary.records_mean || []" :best="summary.best_mean || {}" :threshold="summary.threshold" />
        </a-tab-pane>
        <a-tab-pane key="p99" tab="P99 分析">
          <AnalysisBlock :rows="summary.records_p99 || []" :best="summary.best_p99 || {}" :threshold="summary.threshold" />
        </a-tab-pane>
        <a-tab-pane key="files" tab="日志文件">
          <a-table
            :columns="fileColumns"
            :data-source="files"
            size="small"
            :pagination="false"
            row-key="name"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'actions'">
                <a-button size="small" type="link" @click="previewFile(record.name)">预览</a-button>
                <a-button size="small" type="link" @click="downloadFile(record.name)">下载</a-button>
              </template>
            </template>
          </a-table>
          <a-modal
            v-model:open="previewOpen"
            :title="`预览：${previewName}`"
            width="900px"
            :footer="null"
          >
            <div style="color: #999; font-size: 12px; margin-bottom: 6px">
              共 {{ previewInfo.total_lines }} 行，显示末尾
              {{ previewInfo.truncated > 0 ? `（省略前 ${previewInfo.truncated} 行）` : '全部' }}
            </div>
            <pre class="preview-pre">{{ previewInfo.content }}</pre>
          </a-modal>
        </a-tab-pane>
      </a-tabs>
    </template>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { api } from '@/api'
import RunSummaryBlock from '@/components/RunSummaryBlock.vue'
import AnalysisBlock from '@/components/AnalysisBlock.vue'

const props = defineProps({
  runId: { type: String, default: '' },
})

const summary = reactive({ records: [], records_mean: [], records_p99: [], best_mean: {}, best_p99: {}, threshold: null })
const meta = ref({})
const files = ref([])
const activeTab = ref('summary')
const previewOpen = ref(false)
const previewName = ref('')
const previewInfo = reactive({ content: '', total_lines: 0, truncated: 0 })

const fileColumns = [
  { title: '文件名', dataIndex: 'name', key: 'name' },
  { title: '大小', dataIndex: 'size', key: 'size', width: 110, customRender: ({ text }) => fmtSize(text) },
  { title: '操作', key: 'actions', width: 140 },
]

const xlsxName = computed(() => files.value.find((f) => f.name.endsWith('.xlsx'))?.name || '')

function fmtSize(n) {
  if (n === undefined || n === null) return '-'
  if (n > 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + ' MB'
  if (n > 1024) return (n / 1024).toFixed(1) + ' KB'
  return n + ' B'
}
function statusColor(s) {
  return s === 'done' ? 'green' : s === 'error' ? 'red' : s === 'stopped' ? 'orange' : 'blue'
}
function statusText(s) {
  return s === 'done' ? '完成' : s === 'error' ? '失败' : s === 'stopped' ? '已停止' : '运行中'
}

async function refresh() {
  if (!props.runId) return
  try {
    const [s, runInfo] = await Promise.all([
      api.runSummary(props.runId),
      api.getRun(props.runId).catch(() => null),
    ])
    Object.assign(summary, s)
    meta.value = s.meta || {}
    files.value = (runInfo?.files || []).map((f) => ({ name: f[0], size: f[1] }))
  } catch (e) {
    message.error(e.message)
  }
}

async function previewFile(name) {
  previewName.value = name
  previewInfo.content = ''
  try {
    const resp = await api.previewFile(props.runId, name)
    previewInfo.content = resp.content
    previewInfo.total_lines = resp.total_lines
    previewInfo.truncated = resp.truncated
    previewOpen.value = true
  } catch (e) {
    message.error(e.message)
  }
}

function downloadFile(name) {
  if (!name) {
    message.warning('该运行暂无 xlsx 汇总（可能没有成功记录）')
    return
  }
  window.open(api.downloadUrl(props.runId, name), '_blank')
}

watch(() => props.runId, () => refresh(), { immediate: true })
</script>

<style scoped>
.run-detail {
  padding: 16px;
  height: 100%;
  overflow: auto;
}
.detail-meta {
  margin-bottom: 8px;
  border-radius: 8px;
}
.detail-tabs {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 0 12px 12px;
}
.preview-pre {
  max-height: 520px;
  overflow: auto;
  background: #f6f8fa;
  padding: 12px;
  font-size: 12px;
  white-space: pre-wrap;
  margin: 0;
}
</style>

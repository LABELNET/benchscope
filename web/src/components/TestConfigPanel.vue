<template>
  <a-form layout="vertical">
    <!-- 基础配置 -->
    <a-row :gutter="16">
      <a-col :span="6">
        <a-form-item label="模型精度 Precision">
          <a-input v-model:value="form.precision" placeholder="如 W8A8（可空）" />
        </a-form-item>
      </a-col>
      <a-col :span="6">
        <a-form-item label="TPOT 阈值 (ms)">
          <a-input-number v-model:value="form.tpot_threshold_ms" :min="1" style="width: 100%" />
          <div style="color: #999; font-size: 12px">接近该阈值的行高亮</div>
        </a-form-item>
      </a-col>
      <a-col :span="12">
        <a-form-item label="测试模型 Model">
          <a-input :value="form.model" disabled placeholder="在「① 推理服务」面板选择模型" addon-after="去选择" @click="$emit('pick-model')" />
          <div style="color: #999; font-size: 12px">
            模型与 Tokenizer 在「① 推理服务」面板选择；服务地址等配置在「服务设置」中维护
          </div>
        </a-form-item>
      </a-col>
    </a-row>

    <!-- 数据集（由 tab 决定类型） -->
    <a-form-item v-if="datasetType === 'random'" label="输入/输出长度组合（random 数据集）">
      <div style="display: flex; flex-wrap: wrap; gap: 8px">
        <a-checkable-tag
          v-for="pair in presetPairs"
          :key="pair.label"
          :checked="isPairChecked(pair)"
          @change="togglePair(pair)"
        >
          {{ pair.label }}（{{ pair.input }}/{{ pair.output }}）
        </a-checkable-tag>
      </div>
      <div style="display: flex; gap: 8px; margin-top: 8px; align-items: center">
        <span>自定义：</span>
        <a-input-number v-model:value="customPair.input" :min="1" placeholder="输入长度" style="width: 140px" />
        <span>/</span>
        <a-input-number v-model:value="customPair.output" :min="1" placeholder="输出长度" style="width: 140px" />
        <a-button size="small" type="dashed" @click="addCustomPair">
          <template #icon><plus-outlined /></template>
          添加
        </a-button>
      </div>
      <div style="color: #999; font-size: 12px; margin-top: 4px">
        已选：{{ selectedPairs.map((p) => p.label).join('、') || '（未选择，无法开始）' }}
      </div>
    </a-form-item>

    <a-form-item v-else-if="datasetType === 'sharegpt'" label="ShareGPT 数据集">
      <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap">
        <a-badge
          :status="sharegpt.state === 'done' ? 'success' : sharegpt.state === 'downloading' ? 'processing' : sharegpt.state === 'error' ? 'error' : 'default'"
          :text="sharegptText"
        />
        <a-button size="small" :loading="sharegpt.state === 'downloading'" @click="downloadSharegpt">
          <template #icon><download-outlined /></template>
          下载 / 检查（modelscope）
        </a-button>
        <span v-if="sharegpt.path" class="path-text">{{ sharegpt.path }}</span>
      </div>
      <div style="color: #999; font-size: 12px; margin-top: 4px">
        来源：https://www.modelscope.cn/datasets/gliang1001/ShareGPT_V3_unfiltered_cleaned_split ，未指定路径时测试开始前自动下载。
      </div>
    </a-form-item>

    <a-form-item v-else label="自定义数据集（与 sharegpt 功能一致）">
      <a-select
        v-model:value="dataset.path"
        placeholder="选择已上传的数据集，或填写服务器本地路径"
        style="margin-bottom: 8px; width: 100%"
        :options="datasets.map((d) => ({ value: d.path, label: `${d.name}（${d.path}）` }))"
        allow-clear
      />
      <div style="display: flex; gap: 8px">
        <a-input v-model:value="localDatasetPath" placeholder="服务器本地 jsonl 路径，如 /data/sharegpt.jsonl" />
        <a-upload :before-upload="beforeUpload" :show-upload-list="false">
          <a-button size="small">
            <template #icon><upload-outlined /></template>
            上传文件
          </a-button>
        </a-upload>
      </div>
    </a-form-item>

    <!-- 并发与速率 -->
    <a-row :gutter="16">
      <a-col :span="12">
        <a-form-item label="测试请求并发数（--max-concurrency = --num-prompts）">
          <ConcurrencyEditor v-model:value="form.concurrency_list" />
        </a-form-item>
      </a-col>
      <a-col :span="6">
        <a-form-item label="请求速率 Request rate">
          <a-select v-model:value="form.request_rate" @change="onRateChange">
            <a-select-option value="inf">inf（不限速，推荐）</a-select-option>
            <a-select-option value="custom">自定义（req/s）</a-select-option>
          </a-select>
          <a-input-number
            v-if="form.request_rate === 'custom'"
            v-model:value="customRate"
            :min="0.01"
            style="width: 100%; margin-top: 6px"
          />
        </a-form-item>
      </a-col>
      <a-col :span="6">
        <a-form-item label="GPU（部署信息）">
          <div style="display: flex; gap: 8px">
            <a-input v-model:value="form.gpu.name" placeholder="型号（自动获取优先）" />
            <a-input-number v-model:value="form.gpu.count" :min="1" style="width: 90px" />
          </div>
          <a-tag v-if="gpuAuto" color="green" style="margin-top: 4px">
            <template #icon><thunderbolt-outlined /></template>
            自动检测：{{ gpuAuto.name }} × {{ gpuAuto.count }}
          </a-tag>
          <div v-else style="color: #999; font-size: 12px; margin-top: 4px">未检测到 nvidia-smi，请手动填写</div>
        </a-form-item>
      </a-col>
    </a-row>

    <!-- 框架参数 -->
    <a-form-item :label="`框架参数（${frameworkName} bench）`">
      <a-collapse ghost :bordered="false">
        <a-collapse-panel key="common" header="常用参数">
          <a-row :gutter="16">
            <a-col v-for="p in commonParams" :key="p.key" :span="6">
              <a-form-item :label="p.label">
                <a-switch v-if="p.type === 'bool'" v-model:checked="form.curated[p.key]" :checked-children="'开'" :un-checked-children="'关'" />
                <a-select
                  v-else-if="p.type === 'select'"
                  v-model:value="form.curated[p.key]"
                  :options="p.options.map((o) => ({ value: o, label: o }))"
                  style="width: 100%"
                />
                <a-input-number
                  v-else-if="p.type === 'int' || p.type === 'float'"
                  v-model:value="form.curated[p.key]"
                  :step="p.type === 'float' ? 0.1 : 1"
                  style="width: 100%"
                />
                <a-input v-else v-model:value="form.curated[p.key]" />
                <div style="color: #999; font-size: 12px">{{ p.help }}</div>
              </a-form-item>
            </a-col>
          </a-row>
        </a-collapse-panel>
        <a-collapse-panel key="advanced" header="高级参数">
          <a-row :gutter="16">
            <a-col v-for="p in advancedParams" :key="p.key" :span="6">
              <a-form-item :label="p.label">
                <a-switch v-if="p.type === 'bool'" v-model:checked="form.curated[p.key]" :checked-children="'开'" :un-checked-children="'关'" />
                <a-select
                  v-else-if="p.type === 'select'"
                  v-model:value="form.curated[p.key]"
                  :options="p.options.map((o) => ({ value: o, label: o }))"
                  style="width: 100%"
                />
                <a-input-number
                  v-else-if="p.type === 'int' || p.type === 'float'"
                  v-model:value="form.curated[p.key]"
                  :step="p.type === 'float' ? 0.1 : 1"
                  style="width: 100%"
                />
                <a-input v-else v-model:value="form.curated[p.key]" />
                <div style="color: #999; font-size: 12px">{{ p.help }}</div>
              </a-form-item>
            </a-col>
          </a-row>
        </a-collapse-panel>
      </a-collapse>
    </a-form-item>

    <a-form-item label="其他参数（自由添加）">
      <FreeArgsEditor v-model:value="form.extra_args" />
    </a-form-item>

    <a-form-item>
      <div style="display: flex; gap: 12px; align-items: center; justify-content: flex-end">
        <span style="color: #999; font-size: 12px; margin-right: auto">开始 / 取消测试请在「测试进度」面板操作</span>
        <a-button type="primary" ghost @click="preview">
          <template #icon><eye-outlined /></template>
          命令预览
        </a-button>
      </div>
    </a-form-item>

    <!-- 命令预览 -->
    <a-modal v-model:open="previewOpen" title="命令预览（首个用例）" width="860px" :footer="null">
      <pre style="max-height: 480px; overflow: auto; background: #f6f8fa; padding: 12px; font-size: 12px; white-space: pre-wrap">{{ previewText }}</pre>
    </a-modal>
  </a-form>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import {
  DownloadOutlined,
  EyeOutlined,
  PlusOutlined,
  ThunderboltOutlined,
  UploadOutlined,
} from '@ant-design/icons-vue'
import ConcurrencyEditor from '@/components/ConcurrencyEditor.vue'
import FreeArgsEditor from '@/components/FreeArgsEditor.vue'
import { api } from '@/api'
import { useConfigStore } from '@/store/config'
import { useTestForm } from '@/store/form'

const props = defineProps({
  framework: { type: String, default: 'vllm' },
  datasetType: { type: String, default: 'random' }, // random | sharegpt | custom
})

const config = useConfigStore()
const form = useTestForm()

const frameworkName = computed(() => (props.framework === 'vllm' ? 'vLLM' : 'SGLang'))
const models = computed(() => config.status?.models || [])
const gpuAuto = computed(() => (config.gpu?.auto_detected ? config.gpu.auto_detected : null))

const presetPairs = [
  { label: '3K1K', input: 3072, output: 1024 },
  { label: '1K1K', input: 1024, output: 1024 },
  { label: '256X256', input: 256, output: 256 },
]

// 数据集本地状态（按 tab 独立保存）
const dataset = reactive({ type: props.datasetType, length_pairs: [...presetPairs], path: '' })
const customPair = reactive({ input: 1024, output: 512 })
const localDatasetPath = ref('')
const paramsSchema = ref([])
const datasets = ref([])
const sharegpt = reactive({ state: 'idle', path: null, error: null })
const previewOpen = ref(false)
const previewText = ref('')
const customRate = ref(100)

const selectedPairs = computed(() => dataset.length_pairs.filter((p) => p.checked !== false))
const commonParams = computed(() => paramsSchema.value.filter((p) => !p.advanced))
const advancedParams = computed(() => paramsSchema.value.filter((p) => p.advanced))

function isPairChecked(pair) {
  return dataset.length_pairs.some((p) => p.label === pair.label)
}
function togglePair(pair) {
  const idx = dataset.length_pairs.findIndex((p) => p.label === pair.label)
  if (idx >= 0) dataset.length_pairs.splice(idx, 1)
  else dataset.length_pairs.push({ ...pair, checked: true })
}
function addCustomPair() {
  if (!customPair.input || !customPair.output) {
    message.warning('请输入输入/输出长度')
    return
  }
  const label = `${customPair.input}X${customPair.output}`
  if (dataset.length_pairs.some((p) => p.label === label)) {
    message.warning('该长度组合已存在')
    return
  }
  dataset.length_pairs.push({ label, input: customPair.input, output: customPair.output, checked: true })
}

function onRateChange(v) {
  if (v === 'custom') form.request_rate = String(customRate.value)
  else form.request_rate = 'inf'
}

async function downloadSharegpt() {
  try {
    await api.sharegptDownload()
    sharegpt.state = 'downloading'
    pollSharegpt()
  } catch (e) {
    message.error(e.message)
  }
}
async function pollSharegpt() {
  try {
    const s = await api.sharegptStatus()
    sharegpt.state = s.state
    sharegpt.path = s.path
    sharegpt.error = s.error
    if (s.state === 'downloading') setTimeout(pollSharegpt, 2000)
  } catch {
    /* 忽略 */
  }
}
const sharegptText = computed(() => {
  if (sharegpt.state === 'done') return '已就绪'
  if (sharegpt.state === 'downloading') return '下载中…'
  if (sharegpt.state === 'error') return `下载失败：${sharegpt.error}`
  return '未下载'
})

function beforeUpload(file) {
  const hide = message.loading(`上传 ${file.name} 中…`, 0)
  api
    .uploadDataset(file)
    .then(async (resp) => {
      message.success('上传成功')
      await loadDatasets()
      dataset.path = resp.path
    })
    .catch((e) => message.error(e.message))
    .finally(() => hide())
  return false
}
async function loadDatasets() {
  try {
    const resp = await api.listDatasets()
    datasets.value = resp.datasets || []
  } catch {
    datasets.value = []
  }
}

async function buildPayload() {
  // 校验
  if (!form.model) {
    message.warning('请选择测试模型（推理服务面板或此处）')
    return null
  }
  const datasetOut = { type: props.datasetType }
  if (props.datasetType === 'random') {
    if (!selectedPairs.value.length) {
      message.warning('请至少选择一个输入/输出长度组合')
      return null
    }
    datasetOut.length_pairs = selectedPairs.value.map((p) => [p.input, p.output, p.label])
  } else if (props.datasetType === 'custom') {
    const path = dataset.path || localDatasetPath.value
    if (!path) {
      message.warning('请选择或填写自定义数据集路径')
      return null
    }
    datasetOut.path = path
  }
  if (!form.concurrency_list.length) {
    message.warning('请至少添加一个并发数')
    return null
  }
  if (!form.force && !models.value.length) {
    message.warning('推理服务离线，请确认服务可用或勾选“强制开始”')
    return null
  }
  const gpu = {
    auto: form.gpu.auto,
    name: form.gpu.name || gpuAuto.value?.name || '',
    count: form.gpu.count || gpuAuto.value?.count || 8,
  }
  const curatedOut = {}
  for (const [k, v] of Object.entries(form.curated)) {
    if (v !== undefined && v !== null && v !== '') curatedOut[k] = v
  }
  return {
    framework: props.framework,
    model: form.model,
    tokenizer: form.tokenizer,
    dataset: datasetOut,
    concurrency_list: form.concurrency_list,
    gpu,
    request_rate: form.request_rate === 'inf' ? 'inf' : Number(form.request_rate),
    tpot_threshold_ms: form.tpot_threshold_ms,
    precision: form.precision,
    curated: curatedOut,
    extra_args: form.extra_args.filter((a) => a.flag),
    force: form.force,
  }
}

async function preview() {
  const payload = await buildPayload()
  if (!payload) return
  try {
    const resp = await api.previewTest(payload)
    const lines = resp.commands || []
    previewText.value = lines.map((l) => `[${l.case} | 并发=${l.concurrency}]\n${l.cmd}`).join('\n\n')
    previewOpen.value = true
  } catch (e) {
    message.error(e.message)
  }
}

async function initParams() {
  await config.loadParams(props.framework)
  paramsSchema.value = config.params[props.framework]
  form.initCurated(paramsSchema.value)
}

onMounted(async () => {
  form.initFromConfig(config.config, config.gpu)
  await initParams()
  loadDatasets()
  pollSharegpt()
})

watch(
  () => props.framework,
  async () => {
    // 切换框架时清空该框架的 curated 并重新按默认值初始化
    for (const k of Object.keys(form.curated)) delete form.curated[k]
    await initParams()
  },
)

defineExpose({ buildPayload, preview })
</script>

<style scoped>
.path-text {
  color: #999;
  font-size: 12px;
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

<template>
  <a-steps :current="step" size="small" style="margin-bottom: 20px">
    <a-step title="模型与框架" />
    <a-step title="测试参数" />
    <a-step title="确认" />
  </a-steps>

  <!-- Step 1: 模型与框架 -->
  <div v-if="step === 0">
    <a-form layout="vertical">
      <a-form-item label="模型">
        <a-select v-model:value="form.model" show-search placeholder="选择模型" style="width: 100%" :options="modelOptions" />
      </a-form-item>
      <a-form-item label="框架">
        <a-radio-group v-model:value="form.framework" button-style="solid">
          <a-radio-button value="vllm">vLLM</a-radio-button>
          <a-radio-button value="sglang">SGLang</a-radio-button>
        </a-radio-group>
      </a-form-item>
      <a-form-item label="精度（可选）">
        <a-input v-model:value="form.precision" placeholder="如 W8A8" />
      </a-form-item>
    </a-form>
  </div>

  <!-- Step 2: 测试参数 -->
  <div v-if="step === 1">
    <a-form layout="vertical">
      <a-form-item label="数据集类型">
        <a-radio-group v-model:value="datasetType" button-style="solid">
          <a-radio-button value="random">Random</a-radio-button>
          <a-radio-button value="sharegpt">ShareGPT</a-radio-button>
          <a-radio-button value="custom">Custom</a-radio-button>
        </a-radio-group>
      </a-form-item>

      <a-form-item v-if="datasetType === 'random'" label="输入/输出长度组合">
        <div style="display: flex; flex-wrap: wrap; gap: 8px">
          <a-checkable-tag v-for="pair in presetPairs" :key="pair.label" :checked="isPairChecked(pair)" @change="togglePair(pair)">{{ pair.label }}（{{ pair.input }}/{{ pair.output }}）</a-checkable-tag>
        </div>
        <div style="display: flex; gap: 8px; margin-top: 8px; align-items: center">
          <span>自定义：</span>
          <a-input-number v-model:value="customPair.input" :min="1" placeholder="输入" style="width: 120px" />
          <span>/</span>
          <a-input-number v-model:value="customPair.output" :min="1" placeholder="输出" style="width: 120px" />
          <a-button size="small" type="dashed" @click="addPair"><plus-outlined /></a-button>
        </div>
      </a-form-item>

      <a-form-item v-else-if="datasetType === 'sharegpt'" label="ShareGPT 数据集">
        <a-button :loading="sgDownloading" @click="downloadSg">下载 / 检查（modelscope）</a-button>
        <span v-if="sgPath" style="color: #999; font-size: 12px; margin-left: 8px">{{ sgPath }}</span>
      </a-form-item>

      <a-form-item v-else label="自定义数据集路径">
        <a-input v-model:value="customPath" placeholder="服务器本地 jsonl 路径" />
      </a-form-item>

      <a-form-item label="并发数">
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px">
          <a-tag v-for="(c, i) in form.concurrency_list" :key="i" closable color="blue" @close="form.concurrency_list.splice(i, 1)">{{ c }}</a-tag>
        </div>
        <a-input v-model:value="concDraft" placeholder="添加并发数，回车确认" style="width: 200px" @pressEnter="addConc" />
      </a-form-item>

      <a-collapse ghost>
        <a-collapse-panel key="adv" header="高级参数">
          <a-row :gutter="12">
            <a-col :span="8">
              <a-form-item label="请求速率">
                <a-select v-model:value="form.request_rate">
                  <a-select-option value="inf">inf</a-select-option>
                  <a-select-option value="custom">自定义</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="TPOT 阈值 (ms)">
                <a-input-number v-model:value="form.tpot_threshold_ms" :min="1" style="width: 100%" />
              </a-form-item>
            </a-col>
          </a-row>
        </a-collapse-panel>
      </a-collapse>
    </a-form>
  </div>

  <!-- Step 3: 确认 -->
  <div v-if="step === 2">
    <a-descriptions :column="1" bordered size="small">
      <a-descriptions-item label="模型">{{ form.model }}</a-descriptions-item>
      <a-descriptions-item label="框架">{{ form.framework }}</a-descriptions-item>
      <a-descriptions-item label="数据集">{{ datasetType }}{{ datasetType === 'random' ? ` (${selectedPairs.length} 组合)` : '' }}</a-descriptions-item>
      <a-descriptions-item label="并发数">{{ form.concurrency_list.join(', ') }}</a-descriptions-item>
      <a-descriptions-item label="请求速率">{{ form.request_rate }}</a-descriptions-item>
    </a-descriptions>
    <div style="margin-top: 16px">
      <a-checkbox v-model:checked="autoStart">{{ t('createAndStart') }}</a-checkbox>
    </div>
  </div>

  <div style="display: flex; justify-content: space-between; margin-top: 24px">
    <a-button v-if="step > 0" @click="step--">{{ t('prev') }}</a-button>
    <span v-else />
    <a-button v-if="step < 2" type="primary" @click="nextStep" :disabled="step === 0 && !form.model">{{ t('next') }}</a-button>
    <a-button v-else type="primary" :loading="creating" @click="create">{{ t('confirm') }}</a-button>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { useTestStore } from '@/store/test'
import { useConfigStore } from '@/store/config'
import { api } from '@/api'
import { t } from '@/i18n'

const emit = defineEmits(['created'])
const test = useTestStore()
const config = useConfigStore()

const step = ref(0)
const creating = ref(false)
const autoStart = ref(true)
const datasetType = ref('random')
const concDraft = ref('')
const customPath = ref('')
const sgDownloading = ref(false)
const sgPath = ref('')

const form = reactive({
  model: '',
  framework: 'vllm',
  precision: '',
  concurrency_list: [1, 4, 8, 16, 32, 40, 64, 128],
  request_rate: 'inf',
  tpot_threshold_ms: 100,
})

const presetPairs = [
  { label: '3K1K', input: 3072, output: 1024 },
  { label: '1K1K', input: 1024, output: 1024 },
  { label: '256X256', input: 256, output: 256 },
]
const selectedPairs = reactive([...presetPairs])
const customPair = reactive({ input: 1024, output: 512 })

const modelOptions = computed(() => (config.status?.models || []).map((m) => ({ value: m, label: m })))

function isPairChecked(pair) { return selectedPairs.some((p) => p.label === pair.label) }
function togglePair(pair) {
  const idx = selectedPairs.findIndex((p) => p.label === pair.label)
  if (idx >= 0) selectedPairs.splice(idx, 1)
  else selectedPairs.push({ ...pair })
}
function addPair() {
  if (!customPair.input || !customPair.output) return
  const label = `${customPair.input}X${customPair.output}`
  if (selectedPairs.some((p) => p.label === label)) return
  selectedPairs.push({ label, input: customPair.input, output: customPair.output })
}
function addConc() {
  const v = String(concDraft.value).trim()
  if (!v) return
  const nums = v.split(/[,，\s]+/).filter(Boolean).map(Number).filter((n) => Number.isInteger(n) && n > 0)
  for (const n of nums) { if (!form.concurrency_list.includes(n)) form.concurrency_list.push(n) }
  form.concurrency_list.sort((a, b) => a - b)
  concDraft.value = ''
}

async function downloadSg() {
  sgDownloading.value = true
  try {
    await api.sharegptDownload()
    const poll = async () => {
      const s = await api.sharegptStatus()
      if (s.state === 'downloading') { setTimeout(poll, 2000); return }
      sgPath.value = s.path || ''
      sgDownloading.value = false
    }
    await poll()
  } catch (e) { message.error(e.message); sgDownloading.value = false }
}

function nextStep() {
  if (step.value === 0 && !form.model) { message.warning('请选择模型'); return }
  step.value++
}

async function create() {
  creating.value = true
  try {
    const dataset = { type: datasetType.value }
    if (datasetType.value === 'random') {
      if (!selectedPairs.length) { message.warning('请选择至少一个长度组合'); creating.value = false; return }
      dataset.length_pairs = selectedPairs.map((p) => [p.input, p.output, p.label])
    } else if (datasetType.value === 'sharegpt') {
      dataset.path = sgPath.value || undefined
    } else {
      if (!customPath.value) { message.warning('请填写数据集路径'); creating.value = false; return }
      dataset.path = customPath.value
    }

    const payload = {
      framework: form.framework,
      model: form.model,
      precision: form.precision,
      dataset,
      concurrency_list: form.concurrency_list,
      request_rate: form.request_rate,
      tpot_threshold_ms: form.tpot_threshold_ms,
      gpu: config.gpu?.config || { auto: true, name: '', count: 8 },
      curated: {},
      extra_args: [],
    }
    const resp = await test.createTask(payload)
    if (autoStart.value && resp.task_id) {
      await test.startTask(resp.task_id)
    }
    emit('created', resp.task_id)
  } catch (e) { message.error(e.message) } finally { creating.value = false }
}
</script>

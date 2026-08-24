<template>
  <a-steps :current="step" size="small" style="margin-bottom: 20px">
    <a-step :title="t('stepModelFramework')" />
    <a-step :title="t('stepTestParams')" />
    <a-step :title="t('stepConfirm')" />
  </a-steps>

  <!-- Step 1: Model & Framework -->
  <div v-if="step === 0">
    <a-form layout="vertical">
      <a-form-item :label="t('model')">
        <a-select v-model:value="form.model" show-search :placeholder="t('selectModel')" style="width: 100%" :options="modelOptions" />
      </a-form-item>
      <a-form-item :label="t('framework')">
        <a-radio-group v-model:value="form.framework" button-style="solid" @change="onFrameworkChange">
          <a-radio-button value="vllm">vLLM</a-radio-button>
          <a-radio-button value="sglang">SGLang</a-radio-button>
        </a-radio-group>
      </a-form-item>
      <a-form-item :label="t('precision')">
        <a-input v-model:value="form.precision" :placeholder="t('precisionPlaceholder')" />
      </a-form-item>
    </a-form>
  </div>

  <!-- Step 2: Test Parameters -->
  <div v-if="step === 1">
    <a-form layout="vertical">
      <a-form-item :label="t('datasetType')">
        <a-radio-group v-model:value="datasetType" button-style="solid">
          <a-radio-button value="random">Random</a-radio-button>
          <a-radio-button value="sharegpt">ShareGPT</a-radio-button>
          <a-radio-button value="custom">{{ t('custom') }}</a-radio-button>
        </a-radio-group>
      </a-form-item>

      <a-form-item v-if="datasetType === 'random'" :label="t('inputOutputPairs')">
        <div style="display: flex; flex-wrap: wrap; gap: 8px">
          <a-checkable-tag v-for="pair in presetPairs" :key="pair.label" :checked="isPairChecked(pair)" @change="togglePair(pair)">{{ pair.label }} ({{ pair.input }}/{{ pair.output }})</a-checkable-tag>
        </div>
        <div style="display: flex; gap: 8px; margin-top: 8px; align-items: center">
          <span>{{ t('custom') }}:</span>
          <a-input-number v-model:value="customPair.input" :min="1" :placeholder="t('customInput')" style="width: 120px" />
          <span>/</span>
          <a-input-number v-model:value="customPair.output" :min="1" :placeholder="t('customOutput')" style="width: 120px" />
          <a-button size="small" type="dashed" @click="addPair"><plus-outlined /></a-button>
        </div>
      </a-form-item>

      <a-form-item v-else-if="datasetType === 'sharegpt'" :label="t('sharegptDataset')">
        <a-button :loading="sgDownloading" @click="downloadSg">{{ t('downloadCheck') }}</a-button>
        <span v-if="sgPath" style="color: #999; font-size: 12px; margin-left: 8px">{{ sgPath }}</span>
      </a-form-item>

      <a-form-item v-else :label="t('customDatasetPath')">
        <a-input v-model:value="customPath" :placeholder="t('customDatasetPlaceholder')" />
      </a-form-item>

      <a-form-item :label="t('concurrency')">
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px">
          <a-tag v-for="(c, i) in form.concurrency_list" :key="i" closable color="blue" @close="form.concurrency_list.splice(i, 1)">{{ c }}</a-tag>
        </div>
        <a-input v-model:value="concDraft" :placeholder="t('addConcurrency')" style="width: 200px" @pressEnter="addConc" />
      </a-form-item>

      <a-collapse v-model:activeKey="advOpenKeys" ghost>
        <a-collapse-panel key="adv" :header="t('advancedParams')">
          <!-- 通用参数 -->
          <a-row :gutter="12">
            <a-col :span="8">
              <a-form-item :label="t('requestRate')">
                <a-select v-model:value="form.request_rate">
                  <a-select-option value="inf">inf</a-select-option>
                  <a-select-option value="custom">{{ t('custom') }}</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item :label="t('tpotThreshold')">
                <a-input-number v-model:value="form.tpot_threshold_ms" :min="1" style="width: 100%" />
              </a-form-item>
            </a-col>
          </a-row>
          <!-- 框架高级参数 -->
          <a-divider style="margin: 8px 0" />
          <a-row :gutter="12">
            <a-col :span="8" v-for="param in normalParams" :key="param.key">
              <a-form-item :label="param.label" :tooltip="param.help">
                <!-- bool -->
                <a-switch v-if="param.type === 'bool'" v-model:checked="curated[param.key]" />
                <!-- select -->
                <a-select v-else-if="param.type === 'select'" v-model:value="curated[param.key]" style="width: 100%" :options="(param.options || []).map(o => ({ value: o, label: o }))" />
                <!-- int -->
                <a-input-number v-else-if="param.type === 'int'" v-model:value="curated[param.key]" style="width: 100%" />
                <!-- float -->
                <a-input-number v-else-if="param.type === 'float'" v-model:value="curated[param.key]" :step="0.1" style="width: 100%" />
                <!-- str -->
                <a-input v-else v-model:value="curated[param.key]" />
              </a-form-item>
            </a-col>
          </a-row>
          <!-- 高级参数折叠 -->
          <a-collapse v-if="advancedParams.length" v-model:activeKey="moreAdvOpenKeys" ghost style="background: transparent">
            <a-collapse-panel key="more" header="More">
              <a-row :gutter="12">
                <a-col :span="8" v-for="param in advancedParams" :key="param.key">
                  <a-form-item :label="param.label" :tooltip="param.help">
                    <a-switch v-if="param.type === 'bool'" v-model:checked="curated[param.key]" />
                    <a-select v-else-if="param.type === 'select'" v-model:value="curated[param.key]" style="width: 100%" :options="(param.options || []).map(o => ({ value: o, label: o }))" />
                    <a-input-number v-else-if="param.type === 'int'" v-model:value="curated[param.key]" style="width: 100%" />
                    <a-input-number v-else-if="param.type === 'float'" v-model:value="curated[param.key]" :step="0.1" style="width: 100%" />
                    <a-input v-else v-model:value="curated[param.key]" />
                  </a-form-item>
                </a-col>
              </a-row>
            </a-collapse-panel>
          </a-collapse>
        </a-collapse-panel>
      </a-collapse>
    </a-form>
  </div>

  <!-- Step 3: Confirm -->
  <div v-if="step === 2">
    <a-descriptions :column="1" bordered size="small">
      <a-descriptions-item :label="t('model')">{{ form.model }}</a-descriptions-item>
      <a-descriptions-item :label="t('framework')">{{ form.framework }}</a-descriptions-item>
      <a-descriptions-item v-if="form.precision" :label="t('precision')">{{ form.precision }}</a-descriptions-item>
      <a-descriptions-item :label="t('datasetType')">
        {{ datasetType }}
        <template v-if="datasetType === 'random'">
          <div style="margin-top: 4px">
            <a-tag v-for="p in selectedPairs" :key="p.label" color="blue" style="margin: 2px">{{ p.label }} ({{ p.input }}/{{ p.output }})</a-tag>
          </div>
        </template>
        <template v-else-if="datasetType === 'sharegpt'">
          <span v-if="sgPath" style="color: #999; font-size: 12px">{{ sgPath }}</span>
        </template>
        <template v-else>
          <span v-if="customPath" style="color: #999; font-size: 12px">{{ customPath }}</span>
        </template>
      </a-descriptions-item>
      <a-descriptions-item :label="t('concurrency')">{{ form.concurrency_list.join(', ') }}</a-descriptions-item>
      <a-descriptions-item :label="t('requestRate')">{{ form.request_rate }}</a-descriptions-item>
      <a-descriptions-item v-if="hasCuratedValues" :label="t('advancedParams')">
        <div v-for="param in allActiveParams" :key="param.key" style="font-size: 12px; margin-bottom: 2px">
          <span style="color: #666">{{ param.label }}:</span>
          <span style="margin-left: 4px">{{ formatCuratedValue(param) }}</span>
        </div>
      </a-descriptions-item>
    </a-descriptions>
    <div style="margin-top: 16px">
      <a-checkbox v-model:checked="autoStart">{{ t('createAndStart') }}</a-checkbox>
    </div>
  </div>

  <div style="display: flex; justify-content: space-between; margin-top: 24px">
    <div>
      <a-button v-if="step > 0" @click="step--">{{ t('prev') }}</a-button>
    </div>
    <a-space>
      <a-button @click="onCancel">{{ t('cancel') }}</a-button>
      <a-button v-if="step < 2" type="primary" @click="nextStep" :disabled="step === 0 && !form.model">{{ t('next') }}</a-button>
      <a-button v-else type="primary" :loading="creating" @click="create">{{ t('confirmCreate') }}</a-button>
    </a-space>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { useTestStore } from '@/store/test'
import { useConfigStore } from '@/store/config'
import { api } from '@/api'
import { t } from '@/i18n'

const emit = defineEmits(['created', 'cancel'])
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
const advOpenKeys = ref([])
const moreAdvOpenKeys = ref([])

const form = reactive({
  model: '',
  framework: 'vllm',
  precision: '',
  concurrency_list: [1, 4, 8, 16, 32, 40, 64, 128],
  request_rate: 'inf',
  tpot_threshold_ms: 100,
})

const curated = reactive({})
const paramDefs = ref([])
const paramsLoaded = ref(false)

const presetPairs = [
  { label: '3K1K', input: 3072, output: 1024 },
  { label: '1K1K', input: 1024, output: 1024 },
  { label: '256X256', input: 256, output: 256 },
]
const selectedPairs = reactive([...presetPairs])
const customPair = reactive({ input: 1024, output: 512 })

const modelOptions = computed(() => (config.status?.models || []).map((m) => ({ value: m, label: m })))

const normalParams = computed(() => paramDefs.value.filter(p => !p.advanced))
const advancedParams = computed(() => paramDefs.value.filter(p => p.advanced))
const allActiveParams = computed(() => paramDefs.value.filter(p => {
  const v = curated[p.key]
  if (p.type === 'bool') return v === true
  return v !== undefined && v !== null && v !== '' && v !== p.default
}))
const hasCuratedValues = computed(() => allActiveParams.value.length > 0)

function formatCuratedValue(param) {
  const v = curated[param.key]
  if (param.type === 'bool') return v ? 'Yes' : 'No'
  return String(v ?? param.default ?? '-')
}

async function loadParams(fw) {
  try {
    const resp = await api.getParams(fw)
    paramDefs.value = resp.params || []
    // 初始化 curated 默认值
    for (const p of paramDefs.value) {
      if (curated[p.key] === undefined) {
        curated[p.key] = p.default !== undefined ? p.default : (p.type === 'bool' ? false : '')
      }
    }
    paramsLoaded.value = true
  } catch {
    paramDefs.value = []
  }
}

function onFrameworkChange() {
  paramsLoaded.value = false
  // 重置非默认 curated 值
  for (const key of Object.keys(curated)) {
    delete curated[key]
  }
  loadParams(form.framework)
}

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
  if (step.value === 0 && !form.model) { message.warning(t('selectModelWarning')); return }
  // 进入 step 1 时加载参数
  if (step.value === 0) {
    loadParams(form.framework)
  }
  step.value++
}

async function create() {
  creating.value = true
  try {
    const dataset = { type: datasetType.value }
    if (datasetType.value === 'random') {
      if (!selectedPairs.length) { message.warning(t('selectPairWarning')); creating.value = false; return }
      dataset.length_pairs = selectedPairs.map((p) => [p.input, p.output, p.label])
    } else if (datasetType.value === 'sharegpt') {
      dataset.path = sgPath.value || undefined
    } else {
      if (!customPath.value) { message.warning(t('fillPathWarning')); creating.value = false; return }
      dataset.path = customPath.value
    }

    // 构建 curated：只包含非默认值
    const curatedPayload = {}
    for (const p of paramDefs.value) {
      const v = curated[p.key]
      const isDefault = v === p.default || (p.type === 'bool' && v === false)
      if (!isDefault && v !== undefined && v !== null && v !== '') {
        curatedPayload[p.key] = v
      }
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
      curated: curatedPayload,
      extra_args: [],
    }
    const resp = await test.createTask(payload)
    if (autoStart.value && resp.task_id) {
      await test.startTask(resp.task_id)
    }
    emit('created', resp.task_id)
  } catch (e) { message.error(e.message) } finally { creating.value = false }
}

function onCancel() {
  emit('cancel')
}

// 初始化加载参数
loadParams(form.framework)
</script>

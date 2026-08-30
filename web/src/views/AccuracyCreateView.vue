<template>
  <div class="acc-create-page">
    <a-card size="small" :title="t('accCreateTask')">
      <template #extra>
        <a-button size="small" @click="router.push('/accuracy')">{{ t('back') }}</a-button>
      </template>

      <a-steps :current="step" size="small" class="steps">
        <a-step :title="t('accStepDataset')" />
        <a-step :title="t('accStepModel')" />
        <a-step :title="t('accStepPreview')" />
      </a-steps>

      <!-- Step1 数据集 -->
      <div v-show="step === 0" class="step-body">
        <a-form layout="vertical" class="narrow">
          <a-form-item :label="t('accDatasetSource')">
            <a-radio-group v-model:value="dsSource" button-style="solid">
              <a-radio-button value="builtin">{{ t('accDatasetBuiltin') }}</a-radio-button>
              <a-radio-button value="path">{{ t('accDatasetPath') }}</a-radio-button>
            </a-radio-group>
          </a-form-item>

          <template v-if="dsSource === 'builtin'">
            <a-form-item :label="t('accDataset')">
              <a-select
                v-model:value="form.datasetId" show-search :filter-option="filterOption"
                :placeholder="t('accDatasetPick')" :options="datasetOptions"
              />
            </a-form-item>
            <div v-if="pickedDataset" class="ds-meta">
              <a-descriptions size="small" :column="3">
                <a-descriptions-item :label="t('accDatasetCat')">{{ pickedDataset.category_name }}</a-descriptions-item>
                <a-descriptions-item :label="t('accDatasetScorer')">{{ pickedDataset.eval?.scorer }}</a-descriptions-item>
                <a-descriptions-item :label="t('accDatasetSize')">{{ pickedDataset.total_samples || pickedDataset.total || '—' }}</a-descriptions-item>
              </a-descriptions>
              <a-space>
                <a-button size="small" :loading="previewing" @click="doPreview">{{ t('accPreviewBtn') }}</a-button>
                <a-tag v-if="pickedDataset.downloaded" color="green">{{ t('accDatasetReady') }}</a-tag>
                <a-tag v-else color="orange">{{ t('accDatasetNeedDownload') }}</a-tag>
              </a-space>
            </div>
          </template>

          <template v-else>
            <a-form-item :label="t('accDatasetPathLabel')" :help="t('accDatasetPathHelp')">
              <a-input v-model:value="form.datasetPath" allow-clear placeholder="/path/to/custom.jsonl" />
            </a-form-item>
            <a-button size="small" :disabled="!form.datasetPath" :loading="previewing" @click="doPreview">{{ t('accPreviewBtn') }}</a-button>
          </template>

          <a-form-item :label="t('accLimit')" :help="t('accLimitHelp')" style="margin-top:16px">
            <a-input-number v-model:value="form.limit" :min="0" style="width:180px" />
          </a-form-item>
        </a-form>

        <a-card v-if="previewData" size="small" :title="t('accPreviewTitle')" class="preview-card">
          <a-table
            :columns="previewColumns" :data-source="previewData.samples"
            :pagination="false" size="small" row-key="sample_id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'question'"><span class="clamp2">{{ record.question }}</span></template>
              <template v-else-if="column.key === 'prompt'"><span class="clamp2">{{ record.prompt }}</span></template>
              <template v-else-if="column.key === 'answer'"><span class="clamp2">{{ record.answer }}</span></template>
            </template>
          </a-table>
        </a-card>
      </div>

      <!-- Step2 模式与引擎 -->
      <div v-show="step === 1" class="step-body">
        <a-form layout="vertical" class="narrow">
          <a-form-item :label="t('accMode')">
            <a-radio-group v-model:value="form.mode" button-style="solid">
              <a-radio-button value="serving">{{ t('accModeServing') }}</a-radio-button>
              <a-radio-button value="native">{{ t('accModeNative') }}</a-radio-button>
            </a-radio-group>
            <div class="hint">{{ form.mode === 'serving' ? t('accModeServingHint') : t('accModeNativeHint') }}</div>
          </a-form-item>

          <a-form-item :label="t('accEngine')">
            <a-select v-model:value="form.engineId" :options="engineOptions" @change="onEngineChange" />
            <div v-if="envCheck" class="env-block">
              <div v-for="c in envCheck.checks" :key="c.name" class="env-item">
                <a-tag :color="c.ok ? 'green' : 'red'">{{ c.ok ? 'OK' : 'FAIL' }}</a-tag>
                <span>{{ c.name }}</span>
                <span class="hint">{{ c.required }} · {{ c.installed ?? '—' }}</span>
              </div>
            </div>
          </a-form-item>

          <!-- Serving：Provider 选择 -->
          <template v-if="form.mode === 'serving'">
            <a-form-item :label="t('accProvider')">
              <a-select v-model:value="form.providerId" :options="providerOptions" @change="onProviderChange" />
            </a-form-item>
          </template>

          <a-form-item :label="t('accModel')">
            <a-radio-group v-model:value="modelSource" size="small" style="margin-bottom:8px">
              <a-radio value="catalog">{{ t('accModelCatalog') }}</a-radio>
              <a-radio value="custom">{{ t('accModelCustom') }}</a-radio>
            </a-radio-group>
            <a-select
              v-if="modelSource === 'catalog'" v-model:value="form.model" show-search
              :filter-option="filterOption" :placeholder="t('accModelPick')" :options="modelOptions"
            />
            <a-input v-else v-model:value="form.model" allow-clear :placeholder="t('accModelCustomHint')" />
          </a-form-item>

          <a-form-item :label="t('accLoraPath')" :help="t('accLoraHelp')">
            <a-input v-model:value="form.loraPath" allow-clear placeholder="/path/to/lora_adapter（可选）" />
          </a-form-item>
          <a-form-item v-if="form.mode === 'serving'" :label="t('accLoraName')" :help="t('accLoraNameHelp')">
            <a-input v-model:value="form.loraName" allow-clear placeholder="adapter-name（可选）" />
          </a-form-item>

          <a-row :gutter="12">
            <a-col :span="6">
              <a-form-item :label="t('accSeed')">
                <a-input-number v-model:value="form.seed" style="width:100%" />
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item :label="t('accTemperature')">
                <a-input-number v-model:value="form.temperature" :min="0" :max="2" :step="0.1" style="width:100%" />
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item label="top_p">
                <a-input-number v-model:value="form.topP" :min="0" :max="1" :step="0.1" style="width:100%" />
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item :label="t('accMaxTokens')">
                <a-input-number v-model:value="form.maxTokens" :min="1" style="width:100%" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="12">
            <a-col :span="6" v-if="form.mode === 'serving'">
              <a-form-item :label="t('accConcurrency')">
                <a-input-number v-model:value="form.concurrency" :min="1" style="width:100%" />
              </a-form-item>
            </a-col>
            <a-col :span="6" v-if="pickedScorer === 'judge'">
              <a-form-item :label="t('accJudgeModel')">
                <a-input v-model:value="form.judgeModel" allow-clear placeholder="judge model" />
              </a-form-item>
            </a-col>
          </a-row>
        </a-form>
      </div>

      <!-- Step3 预览与启动 -->
      <div v-show="step === 2" class="step-body">
        <a-descriptions size="small" bordered :column="2" class="narrow">
          <a-descriptions-item :label="t('accDataset')">{{ datasetLabel }}</a-descriptions-item>
          <a-descriptions-item :label="t('accMode')">{{ form.mode === 'native' ? 'Native 原生（本地权重）' : 'Serving 链路（OpenAI 兼容）' }}</a-descriptions-item>
          <a-descriptions-item :label="t('accEngine')">{{ form.engineId }}</a-descriptions-item>
          <a-descriptions-item :label="t('accModel')">{{ form.model || '—' }}<a-tag v-if="form.loraPath" color="purple" style="margin-left:6px">LoRA</a-tag></a-descriptions-item>
          <a-descriptions-item :label="t('accLoraPath')">{{ form.loraPath || '—' }}</a-descriptions-item>
          <a-descriptions-item :label="t('accSeed')">{{ form.seed }} · temp {{ form.temperature }} · top_p {{ form.topP }} · max {{ form.maxTokens }}</a-descriptions-item>
        </a-descriptions>
        <div class="cmd-box">
          <div class="hint">{{ t('accCmdHint') }}</div>
          <pre class="cmd">{{ previewCommand }}</pre>
        </div>

        <div v-if="estimate" class="est-box">
          <a-alert type="warning" show-icon>
            <template #message>{{ t('accEstimateTitle') }}</template>
            <template #description>
              <div>{{ t('accEstimateDataset') }}：{{ datasetLabel }}</div>
              <div>{{ t('accEstimateTotal') }}：<b>{{ estimate.total_tokens }}</b>（{{ t('accEstimateIn') }} {{ estimate.prompt_tokens }} / {{ t('accEstimateOut') }} {{ estimate.completion_tokens }}）</div>
              <div>{{ t('accEstimateSamples') }}：{{ estimate.total_samples }} · {{ estimate.source_label }}</div>
            </template>
          </a-alert>
        </div>
      </div>

      <div class="actions">
        <a-button v-if="step > 0" @click="step--">{{ t('prev') }}</a-button>
        <a-button v-if="step === 0" type="primary" :disabled="!step1Ready" @click="step = 1">{{ t('next') }}</a-button>
        <a-button v-if="step === 1" type="primary" :disabled="!step2Ready" @click="toStep3">{{ t('next') }}</a-button>
        <a-button v-if="step === 2" type="primary" :loading="starting" @click="startWithConfirm">{{ t('accStartTask') }}</a-button>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Modal, message } from 'ant-design-vue'
import { api } from '@/api'
import { t } from '@/i18n'
import { useAccuracyStore } from '@/store/accuracy'

const router = useRouter()
const store = useAccuracyStore()

const step = ref(0)
const dsSource = ref('builtin')
const modelSource = ref('catalog')
const starting = ref(false)
const previewing = ref(false)
const previewData = ref(null)
const estimate = ref(null)

const datasets = ref([])
const engines = ref([])
const providers = ref([])
const catalogModels = ref([])
const envCheck = ref(null)

const form = ref({
  name: '',
  datasetId: undefined,
  datasetPath: '',
  limit: 0,
  mode: 'serving',
  engineId: 'benchscope',
  providerId: undefined,
  model: '',
  loraPath: '',
  loraName: '',
  seed: 1234,
  temperature: 0.0,
  topP: 1.0,
  maxTokens: 512,
  concurrency: 4,
  judgeModel: '',
})

const pickedDataset = computed(() => datasets.value.find((d) => d.id === form.value.datasetId) || null)
const pickedScorer = computed(() => pickedDataset.value?.eval?.scorer || 'math')
const datasetLabel = computed(() => (dsSource.value === 'path' ? form.value.datasetPath : (form.value.datasetId || '')))

const datasetOptions = computed(() => datasets.value.map((d) => ({
  value: d.id,
  label: `${d.name}（${d.category_name}${d.total_samples ? ` · ${d.total_samples}` : ''}）`,
})))

const engineOptions = computed(() => engines.value.map((e) => ({
  value: e.id,
  label: `${e.name} · ${e.eval === 'native' ? 'Native' : e.eval === 'mock' ? 'Mock' : 'Serving'}`,
  disabled: envCheck.value && envCheck.value.engine_id === e.id && !envCheck.value.ok && e.id === form.value.engineId,
})))

const providerOptions = computed(() => providers.value.map((p) => ({ value: p.id, label: `${p.name}（${p.base_url}）` })))

const modelOptions = computed(() => catalogModels.value.map((m) => ({ value: m, label: m })))

const previewColumns = computed(() => [
  { title: '#', dataIndex: 'sample_id', key: 'sample_id', width: 140 },
  { title: t('accDatasetQuestion'), key: 'question', ellipsis: true },
  { title: t('accPromptCol'), key: 'prompt', ellipsis: true },
  { title: t('accAnswerCol'), key: 'answer', width: 160 },
])

const previewCommand = computed(() => {
  const f = form.value
  const ds = dsSource.value === 'path' ? f.datasetPath : f.datasetId
  const parts = [
    'benchscope', 'eval',
    '--engine', f.engineId,
    '--model', f.model || '<model>',
    '--dataset', ds || '<dataset>',
  ]
  if (f.loraPath) parts.push('--lora-path', f.loraPath)
  if (f.loraName) parts.push('--lora-name', f.loraName)
  if (f.limit) parts.push('--limit', String(f.limit))
  if (f.seed) parts.push('--seed', String(f.seed))
  if (f.judgeModel) parts.push('--judge-model', f.judgeModel)
  return parts.join(' ')
})

const step1Ready = computed(() => (dsSource.value === 'builtin' ? !!form.value.datasetId : !!form.value.datasetPath))
const step2Ready = computed(() => {
  if (!form.value.model) return false
  if (envCheck.value && envCheck.value.engine_id === form.value.engineId && !envCheck.value.ok) return false
  if (pickedScorer.value === 'judge' && form.value.mode === 'serving' && !form.value.judgeModel) return false
  return true
})

function filterOption(input, option) {
  return (option?.label || option?.value || '').toLowerCase().includes(input.toLowerCase())
}

async function doPreview() {
  previewing.value = true
  previewData.value = null
  try {
    const ref = dsSource.value === 'path' ? { path: form.value.datasetPath } : { id: form.value.datasetId }
    previewData.value = await api.previewAccDataset(ref)
  } catch (e) { message.error(e.message) } finally { previewing.value = false }
}

async function onEngineChange() {
  envCheck.value = null
  try { envCheck.value = await api.checkAccEngineEnv(form.value.engineId) } catch { /* ignore */ }
}

function onProviderChange() { /* Provider 变更仅影响 api 覆盖 */ }

async function toStep3() {
  step.value = 2
  estimate.value = null
  if (form.value.mode === 'serving') {
    try {
      estimate.value = await api.estimateAcc({
        dataset_id: dsSource.value === 'builtin' ? form.value.datasetId : '',
        path: dsSource.value === 'path' ? form.value.datasetPath : '',
        limit: form.value.limit || 0,
        mode: 'serving',
        max_tokens: form.value.maxTokens,
      })
    } catch (e) { message.warning(`${t('accEstimateFail')}: ${e.message}`) }
  }
}

function startWithConfirm() {
  if (form.value.mode === 'serving' && estimate.value && estimate.value.total_tokens > 0) {
    // Serving 链路精度：Token 消耗预估强提醒（固定文案，确认后才可执行）
    Modal.confirm({
      title: t('accReminderTitle'),
      content: t('accReminderBody')
        .replace('{dataset}', datasetLabel.value)
        .replace('{tokens}', String(estimate.value.total_tokens)),
      okText: t('accReminderConfirm'),
      cancelText: t('cancel'),
      onOk: () => start(),
    })
  } else {
    start()
  }
}

async function start() {
  starting.value = true
  try {
    const provider = providers.value.find((p) => p.id === form.value.providerId)
    const payload = {
      name: form.value.name || `${form.value.model} · ${datasetLabel.value}`,
      mode: form.value.mode,
      engine_id: form.value.engineId,
      model: form.value.model,
      lora_name: form.value.loraName || '',
      lora_path: form.value.loraPath || '',
      dataset: dsSource.value === 'path' ? { path: form.value.datasetPath } : { id: form.value.datasetId },
      limit: form.value.limit || 0,
      seed: form.value.seed || 0,
      temperature: form.value.temperature,
      top_p: form.value.topP,
      max_tokens: form.value.maxTokens,
      concurrency: form.value.concurrency || 4,
      judge_model: form.value.judgeModel || '',
      api: provider ? { base_url: provider.base_url, endpoint: provider.endpoint, api_key: provider.api_key, extra_headers: provider.extra_headers || {} } : {},
    }
    await store.createTask(payload)
    message.success(t('accStartOk'))
    router.push('/accuracy')
  } catch (e) { message.error(e.message) } finally { starting.value = false }
}

onMounted(async () => {
  try {
    const [ds, eg, pv, catalog] = await Promise.all([
      api.listAccDatasets(), api.listAccEngines(), api.listProviders(), api.getModelCatalog().catch(() => null),
    ])
    datasets.value = ds.datasets || []
    engines.value = (eg.engines || []).filter((e) => e.eval)
    providers.value = pv.providers || []
    const groups = catalog?.groups || []
    for (const g of groups) for (const p of g.providers || []) for (const m of p.models || []) catalogModels.value.push(m)
    if (!form.value.engineId && engines.value.length) form.value.engineId = engines.value[0].id
    if (form.value.engineId) onEngineChange()
    const active = providers.value.find((p) => p.id === pv.active_provider) || providers.value[0]
    if (active) form.value.providerId = active.id
  } catch (e) { message.error(e.message) }
})
</script>

<style scoped>
.acc-create-page { height: 100%; overflow: auto; padding: 16px 20px; }
.steps { margin: 8px 0 20px; }
.step-body { min-height: 320px; }
.narrow { max-width: 760px; }
.hint { font-size: 12px; color: var(--ant-color-text-secondary); margin-top: 4px; }
.ds-meta { margin-top: 4px; display: flex; flex-direction: column; gap: 8px; }
.env-block { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
.env-item { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.env-item .hint { margin: 0; }
.preview-card { max-width: 860px; margin-top: 12px; }
.cmd-box { max-width: 760px; margin-top: 16px; }
.cmd {
  background: var(--ant-color-bg-layout, #141414); color: #d6deeb;
  font-size: 12px; padding: 10px; border-radius: 6px; overflow: auto;
  white-space: pre-wrap; word-break: break-all; margin: 6px 0 0;
}
.est-box { max-width: 760px; margin-top: 16px; }
.actions { margin-top: 20px; display: flex; gap: 8px; }
</style>

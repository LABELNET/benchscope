<template>
  <div class="settings-page">
    <a-card size="small" class="settings-card">
      <template #title>{{ t('general') }}</template>
      <a-form layout="vertical">
        <a-row :gutter="16">
          <a-col :span="6">
            <a-form-item :label="t('theme')">
              <a-radio-group v-model:value="form.theme" button-style="solid">
                <a-radio-button value="light">{{ t('light') }}</a-radio-button>
                <a-radio-button value="dark">{{ t('dark') }}</a-radio-button>
                <a-radio-button value="system">{{ t('system') }}</a-radio-button>
              </a-radio-group>
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item :label="t('language')">
              <a-radio-group v-model:value="form.locale" button-style="solid" @change="onLocaleChange">
                <a-radio-button value="zh">{{ t('chinese') }}</a-radio-button>
                <a-radio-button value="en">English</a-radio-button>
              </a-radio-group>
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item :label="t('defaultFramework')">
              <a-radio-group v-model:value="form.framework" button-style="solid">
                <a-radio-button value="vllm">vLLM</a-radio-button>
                <a-radio-button value="sglang">SGLang</a-radio-button>
              </a-radio-group>
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item :label="`${t('tpotThreshold')} (ms)`">
              <a-input-number v-model:value="form.tpot_threshold_ms" :min="1" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item :label="t('logsDir')">
              <a-input v-model:value="form.logs_dir" placeholder="./logs" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item :label="t('datasetsDir')">
              <a-input v-model:value="form.datasets_dir" placeholder="./datasets" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item :label="t('requestRate')">
              <a-select v-model:value="form.request_rate">
                <a-select-option value="inf">inf</a-select-option>
                <a-select-option value="custom">Custom</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item :label="`vLLM ${t('benchCommand')}`">
              <a-input v-model:value="form.bench_commands.vllm" placeholder="vllm bench serve" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item :label="`SGLang ${t('benchCommand')}`">
              <a-input v-model:value="form.bench_commands.sglang" placeholder="python -m sglang.bench_serving" />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-card>

    <a-card size="small" class="settings-card">
      <template #title>{{ t('apiConfig') }}</template>
      <template #extra>
        <a-button type="link" size="small" :loading="testing" @click="testConnection">
          <template #icon><api-outlined /></template>
          {{ t('testConnection') }}
        </a-button>
      </template>
      <a-form layout="vertical">
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item :label="t('baseUrl')">
              <a-input v-model:value="form.api.base_url" placeholder="http://192.168.1.67:8000" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item :label="t('endpoint')">
              <a-input v-model:value="form.api.endpoint" placeholder="/v1/chat/completions" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item :label="t('apiKey')">
              <a-input-password v-model:value="form.api.api_key" placeholder="Bearer token" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item :label="t('extraHeaders')">
          <a-input v-model:value="extraHeadersText" placeholder='{"X-Custom": "value"}' />
        </a-form-item>
        <span v-if="connResult" style="margin-right: 12px">
          <a-tag :color="connResult.ok ? 'green' : 'red'">
            {{ connResult.ok ? t('connectionOk') : t('connectionFail') }}
          </a-tag>
          <span v-if="connResult.ok">{{ connResult.models?.length || 0 }} {{ t('models') }}</span>
          <span v-else style="color: #999">{{ connResult.error }}</span>
        </span>
      </a-form>
    </a-card>

    <a-card size="small" class="settings-card">
      <template #title>{{ t('modelManagement') }}</template>
      <template #extra>
        <a-button type="primary" size="small" @click="showAddModel = true">
          <template #icon><plus-outlined /></template>
          {{ t('addModel') }}
        </a-button>
      </template>

      <a-row :gutter="16" style="margin-bottom: 12px">
        <a-col :span="12">
          <a-descriptions size="small" :column="2">
            <a-descriptions-item :label="t('gpuInfo')" :span="2">
              <a-tag v-if="gpuDetected" color="green">
                {{ gpuDetected.name }} × {{ gpuDetected.count }}
              </a-tag>
              <span v-else style="color: #999">{{ t('autoDetected') }}: nvidia-smi not found</span>
              <a-button size="small" type="link" @click="refreshGpu">{{ t('refresh') }}</a-button>
            </a-descriptions-item>
          </a-descriptions>
        </a-col>
      </a-row>

      <a-table :columns="modelColumns" :data-source="modelList" size="small" :pagination="false" row-key="name">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'actions'">
            <a-button type="link" size="small" danger @click="removeModel(record.name)">{{ t('delete') }}</a-button>
          </template>
        </template>
      </a-table>
    </a-card>

    <div class="save-bar">
      <a-button type="primary" size="large" @click="saveAll">
        <template #icon><save-outlined /></template>
        {{ t('save') }}
      </a-button>
    </div>

    <!-- 添加模型弹窗 -->
    <a-modal v-model:open="showAddModel" :title="t('addModel')" @ok="addModel">
      <a-form layout="vertical">
        <a-form-item label="Model Name">
          <a-input v-model:value="newModel.name" placeholder="e.g. Qwen3.5-4B" />
        </a-form-item>
        <a-form-item :label="t('baseUrl')">
          <a-input v-model:value="newModel.base_url" placeholder="http://..." />
        </a-form-item>
        <a-form-item :label="t('framework')">
          <a-radio-group v-model:value="newModel.framework" button-style="solid">
            <a-radio-button value="vllm">vLLM</a-radio-button>
            <a-radio-button value="sglang">SGLang</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item :label="t('precision')">
          <a-input v-model:value="newModel.precision" placeholder="e.g. W8A8" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { ApiOutlined, PlusOutlined, SaveOutlined } from '@ant-design/icons-vue'
import { api } from '@/api'
import { useConfigStore } from '@/store/config'
import { t, setLocale } from '@/i18n'

const config = useConfigStore()
const loading = ref(false)
const testing = ref(false)
const connResult = ref(null)
const showAddModel = ref(false)
const gpuDetected = ref(null)
const modelList = ref([])
const extraHeadersText = ref('{}')

const form = reactive({
  theme: 'light',
  locale: 'zh',
  framework: 'vllm',
  api: { base_url: '', endpoint: '/v1/chat/completions', api_key: '', extra_headers: {} },
  gpu: { auto: true, name: '', count: 8 },
  logs_dir: './logs',
  datasets_dir: './datasets',
  tpot_threshold_ms: 100,
  request_rate: 'inf',
  bench_commands: { vllm: 'vllm bench serve', sglang: 'python -m sglang.bench_serving' },
})

const newModel = reactive({ name: '', base_url: '', framework: 'vllm', precision: '' })

const modelColumns = [
  { title: 'Name', dataIndex: 'name', key: 'name' },
  { title: 'Base URL', dataIndex: 'base_url', key: 'base_url' },
  { title: 'Framework', dataIndex: 'framework', key: 'framework' },
  { title: 'Precision', dataIndex: 'precision', key: 'precision' },
  { title: '', key: 'actions', width: 80 },
]

onMounted(async () => {
  loading.value = true
  try {
    await config.load()
    const c = config.config || {}
    Object.assign(form, {
      theme: c.theme || 'light',
      locale: c.locale || 'zh',
      framework: c.framework || 'vllm',
      api: {
        base_url: c.api?.base_url || '',
        endpoint: c.api?.endpoint || '/v1/chat/completions',
        api_key: c.api?.api_key || '',
        extra_headers: c.api?.extra_headers || {},
      },
      gpu: { auto: c.gpu?.auto ?? true, name: c.gpu?.name || '', count: c.gpu?.count || 8 },
      logs_dir: c.logs_dir || './logs',
      datasets_dir: c.datasets_dir || './datasets',
      tpot_threshold_ms: c.tpot_threshold_ms ?? 100,
      request_rate: c.request_rate || 'inf',
      bench_commands: {
        vllm: c.bench_commands?.vllm || 'vllm bench serve',
        sglang: c.bench_commands?.sglang || 'python -m sglang.bench_serving',
      },
    })
    extraHeadersText.value = JSON.stringify(c.api?.extra_headers || {}, null, 2)
    if (config.gpu?.auto_detected) gpuDetected.value = config.gpu.auto_detected
    await loadModels()
  } finally {
    loading.value = false
  }
})

function onLocaleChange() {
  setLocale(form.locale)
}

async function testConnection() {
  testing.value = true
  connResult.value = null
  try {
    let extra = {}
    try { extra = JSON.parse(extraHeadersText.value || '{}') } catch { message.error('Invalid JSON') }
    connResult.value = await api.testConnection({
      base_url: form.api.base_url, endpoint: form.api.endpoint,
      api_key: form.api.api_key, extra_headers: extra,
    })
  } finally { testing.value = false }
}

async function refreshGpu() {
  try {
    const resp = await api.getGpu()
    gpuDetected.value = resp.auto_detected
    if (resp.config) Object.assign(form.gpu, resp.config)
  } catch { /* ignore */ }
}

async function loadModels() {
  try {
    const resp = await api.getModels()
    const models = resp.models || []
    modelList.value = models.map((m) => typeof m === 'string' ? { name: m, base_url: form.api.base_url, framework: form.framework, precision: '' } : m)
  } catch {
    modelList.value = (config.status?.models || []).map((m) => ({ name: m, base_url: form.api.base_url, framework: form.framework, precision: '' }))
  }
}

function addModel() {
  if (!newModel.name) { message.warning('Please enter model name'); return }
  modelList.value.push({ ...newModel })
  Object.assign(newModel, { name: '', base_url: '', framework: 'vllm', precision: '' })
  showAddModel.value = false
}

function removeModel(name) {
  modelList.value = modelList.value.filter((m) => m.name !== name)
}

async function saveAll() {
  try {
    let extra = {}
    try { extra = JSON.parse(extraHeadersText.value || '{}') } catch { message.error('Invalid JSON') }
    await config.save({
      theme: form.theme,
      locale: form.locale,
      framework: form.framework,
      api: { ...form.api, extra_headers: extra },
      gpu: form.gpu,
      logs_dir: form.logs_dir,
      datasets_dir: form.datasets_dir,
      tpot_threshold_ms: form.tpot_threshold_ms,
      request_rate: form.request_rate,
      bench_commands: form.bench_commands,
    })
    message.success(t('saved'))
    config.refreshStatus()
  } catch (e) {
    message.error(e.message)
  }
}
</script>

<style scoped>
.settings-page {
  height: 100%;
  overflow: auto;
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}
.settings-card {
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  margin-bottom: 16px;
}
.save-bar {
  text-align: center;
  padding: 16px 0 32px;
}
</style>

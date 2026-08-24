<template>
  <a-card size="small" class="panel" title="服务设置 Service Settings">
    <template #extra>
      <a-button type="link" size="small" :loading="testing" @click="testConnection">
        <template #icon><api-outlined /></template>
        测试连接
      </a-button>
    </template>
    <a-spin :spinning="loading">
      <a-form layout="vertical">
        <a-divider orientation="left">
          <api-outlined style="color: #1677ff" /> 推理服务 API 配置
        </a-divider>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="默认框架 Default Framework">
              <a-radio-group v-model:value="form.framework" button-style="solid">
                <a-radio-button value="vllm">vLLM</a-radio-button>
                <a-radio-button value="sglang">SGLang</a-radio-button>
              </a-radio-group>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="Base URL（OpenAI 兼容）">
              <a-input v-model:value="form.api.base_url" placeholder="http://192.168.1.67:8000" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="Endpoint">
              <a-input v-model:value="form.api.endpoint" placeholder="/v1/chat/completions" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="API Key（可选）">
              <a-input-password v-model:value="form.api.api_key" placeholder="Bearer token" />
            </a-form-item>
          </a-col>
          <a-col :span="16">
            <a-form-item label="额外请求头（JSON，可选）">
              <a-input v-model:value="extraHeadersText" placeholder='{"X-Custom": "value"}' />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item>
          <span v-if="connResult" style="margin-right: 12px">
            <a-tag :color="connResult.ok ? 'green' : 'red'">
              {{ connResult.ok ? '连接成功' : '连接失败' }}
            </a-tag>
            <span v-if="connResult.ok">{{ connResult.models?.length || 0 }} 个模型</span>
            <span v-else style="color: #999">{{ connResult.error }}</span>
          </span>
        </a-form-item>

        <a-divider orientation="left">
          <desktop-outlined style="color: #1677ff" /> GPU / 目录 / 阈值
        </a-divider>
        <a-row :gutter="16">
          <a-col :span="6">
            <a-form-item label="GPU 自动检测">
              <a-switch v-model:checked="form.gpu.auto" />
              <div v-if="gpuDetected" style="color: #999; font-size: 12px; margin-top: 4px">
                检测到：{{ gpuDetected.name }} × {{ gpuDetected.count }}
              </div>
            </a-form-item>
          </a-col>
          <a-col :span="5">
            <a-form-item label="GPU 型号（回退）">
              <a-input v-model:value="form.gpu.name" />
            </a-form-item>
          </a-col>
          <a-col :span="4">
            <a-form-item label="GPU 数量">
              <a-input-number v-model:value="form.gpu.count" :min="1" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="9">
            <a-form-item label="TPOT 阈值 (ms)（默认）">
              <a-input-number v-model:value="form.tpot_threshold_ms" :min="1" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="日志目录 logs_dir">
              <a-input v-model:value="form.logs_dir" placeholder="./logs" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="数据集缓存目录 datasets_dir">
              <a-input v-model:value="form.datasets_dir" placeholder="./datasets" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="请求速率 Request rate（默认）">
              <a-select v-model:value="form.request_rate">
                <a-select-option value="inf">inf（不限速）</a-select-option>
                <a-select-option value="custom">自定义</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider orientation="left">
          <code-outlined style="color: #1677ff" /> bench 执行命令
        </a-divider>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="vLLM bench 命令模板">
              <a-input v-model:value="form.bench_commands.vllm" placeholder="vllm bench serve" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="SGLang bench 命令模板">
              <a-input v-model:value="form.bench_commands.sglang" placeholder="python -m sglang.bench_serving" />
            </a-form-item>
          </a-col>
        </a-row>
        <div style="color: #999; font-size: 12px; margin-bottom: 12px">
          说明：bench 工具在 benchscope 所在机器以子进程运行（需安装 vllm / sglang CLI），推理服务端只需提供 OpenAI 兼容 API，无需安装插件。
        </div>

        <a-form-item>
          <a-button type="primary" size="large" @click="save">
            <template #icon><save-outlined /></template>
            保存配置
          </a-button>
        </a-form-item>
      </a-form>
    </a-spin>
  </a-card>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  ApiOutlined,
  CodeOutlined,
  DesktopOutlined,
  SaveOutlined,
} from '@ant-design/icons-vue'
import { api } from '@/api'
import { useConfigStore } from '@/store/config'

const config = useConfigStore()
const loading = ref(false)
const testing = ref(false)
const connResult = ref(null)
const gpuDetected = ref(null)

const form = reactive({
  framework: 'vllm',
  api: { base_url: '', endpoint: '/v1/chat/completions', api_key: '', extra_headers: {} },
  gpu: { auto: true, name: '', count: 8 },
  logs_dir: './logs',
  datasets_dir: './datasets',
  tpot_threshold_ms: 100,
  request_rate: 'inf',
  bench_commands: { vllm: 'vllm bench serve', sglang: 'python -m sglang.bench_serving' },
})
const extraHeadersText = ref('{}')

onMounted(async () => {
  loading.value = true
  try {
    await config.load()
    Object.assign(form, {
      framework: config.config?.framework || 'vllm',
      api: {
        base_url: config.config?.api?.base_url || '',
        endpoint: config.config?.api?.endpoint || '/v1/chat/completions',
        api_key: config.config?.api?.api_key || '',
        extra_headers: config.config?.api?.extra_headers || {},
      },
      gpu: {
        auto: config.config?.gpu?.auto ?? true,
        name: config.config?.gpu?.name || '',
        count: config.config?.gpu?.count || 8,
      },
      logs_dir: config.config?.logs_dir || './logs',
      datasets_dir: config.config?.datasets_dir || './datasets',
      tpot_threshold_ms: config.config?.tpot_threshold_ms ?? 100,
      request_rate: config.config?.request_rate || 'inf',
      bench_commands: {
        vllm: config.config?.bench_commands?.vllm || 'vllm bench serve',
        sglang: config.config?.bench_commands?.sglang || 'python -m sglang.bench_serving',
      },
    })
    extraHeadersText.value = JSON.stringify(config.config?.api?.extra_headers || {}, null, 2)
    if (config.gpu?.auto_detected) gpuDetected.value = config.gpu.auto_detected
  } finally {
    loading.value = false
  }
})

async function testConnection() {
  testing.value = true
  connResult.value = null
  try {
    let extra = {}
    try {
      extra = JSON.parse(extraHeadersText.value || '{}')
    } catch {
      message.error('额外请求头不是合法 JSON')
      return
    }
    connResult.value = await api.testConnection({
      base_url: form.api.base_url,
      endpoint: form.api.endpoint,
      api_key: form.api.api_key,
      extra_headers: extra,
    })
  } finally {
    testing.value = false
  }
}

async function save() {
  try {
    let extra = {}
    try {
      extra = JSON.parse(extraHeadersText.value || '{}')
    } catch {
      message.error('额外请求头不是合法 JSON')
      return
    }
    const patch = {
      framework: form.framework,
      api: { ...form.api, extra_headers: extra },
      gpu: form.gpu,
      logs_dir: form.logs_dir,
      datasets_dir: form.datasets_dir,
      tpot_threshold_ms: form.tpot_threshold_ms,
      request_rate: form.request_rate,
      bench_commands: form.bench_commands,
    }
    await config.save(patch)
    message.success('配置已保存')
    config.refreshStatus()
  } catch (e) {
    message.error(`保存失败：${e.message}`)
  }
}
</script>

<style scoped>
.panel {
  max-width: 1200px;
  margin: 0 auto;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
</style>

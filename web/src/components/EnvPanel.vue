<template>
  <div>
    <a-row :gutter="16">
      <!-- 服务信息 -->
      <a-col :xs="24" :md="10">
        <a-descriptions size="small" :column="2">
          <a-descriptions-item label="Base URL" :span="2">
            <a-typography-link copyable :copyable="{ tooltips: ['复制', '已复制'] }">{{ apiBase }}</a-typography-link>
          </a-descriptions-item>
          <a-descriptions-item label="Endpoint">{{ endpoint }}</a-descriptions-item>
          <a-descriptions-item label="模型数量">
            <a-badge :count="modelCount" :number-style="{ backgroundColor: inferenceReady ? '#1677ff' : '#bbb' }" />
          </a-descriptions-item>
          <a-descriptions-item label="最近检测">{{ status.last_check || '-' }}</a-descriptions-item>
          <a-descriptions-item label="执行方式">
            <a-tag color="geekblue" style="margin-left: 0">本机子进程执行 bench</a-tag>
          </a-descriptions-item>
        </a-descriptions>
      </a-col>

      <!-- 模型选择 -->
      <a-col :xs="24" :md="14">
        <a-row :gutter="16">
          <a-col :span="16">
            <div class="field-label"><robot-outlined style="color: #1677ff" /> 测试模型 Model</div>
            <a-select
              v-if="models.length"
              v-model:value="form.model"
              :options="models.map((m) => ({ value: m, label: m }))"
              show-search
              placeholder="选择模型（来自 /v1/models）"
              style="width: 100%"
              :allow-clear="true"
            />
            <a-input v-else v-model:value="form.model" placeholder="推理环境离线，可手动输入模型名（需勾选强制开始）" />
          </a-col>
          <a-col :span="8">
            <div class="field-label">Tokenizer（可空）</div>
            <a-input v-model:value="form.tokenizer" placeholder="默认同模型" size="middle" />
          </a-col>
        </a-row>
        <a-alert
          v-if="!models.length"
          type="warning"
          show-icon
          :message="`模型列表不可用：${status.error || '推理环境离线'}`"
          style="margin-top: 8px; font-size: 12px"
        />
      </a-col>
    </a-row>

    <!-- 底部操作（右下角） -->
    <div class="env-footer">
      <span v-if="connMsg" class="conn-msg" :class="connOk ? 'ok' : 'bad'">
        <template v-if="connOk">
          <check-circle-filled /> 连接成功（{{ connModels }} 个模型）
        </template>
        <template v-else>
          <close-circle-filled /> 连接失败：{{ connMsg }}
        </template>
      </span>
      <a-space>
        <a-button size="middle" @click="refresh">
          <template #icon><reload-outlined /></template>
          刷新状态
        </a-button>
        <a-button size="middle" type="primary" :loading="testing" @click="testConn">
          <template #icon><api-outlined /></template>
          测试连接
        </a-button>
        <a-button size="middle" type="link" @click="$router.push('/settings')">
          <template #icon><setting-outlined /></template>
          服务设置
        </a-button>
      </a-space>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  ApiOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  ReloadOutlined,
  RobotOutlined,
  SettingOutlined,
} from '@ant-design/icons-vue'
import { api } from '@/api'
import { useConfigStore } from '@/store/config'
import { useTestForm } from '@/store/form'

const config = useConfigStore()
const form = useTestForm()

const apiBase = computed(() => config.apiBase)
const endpoint = computed(() => config.config?.api?.endpoint || '/v1/chat/completions')
const status = computed(() => config.status || {})
const inferenceReady = computed(() => status.value.inference === 'ready')
const models = computed(() => status.value.models || [])
const modelCount = computed(() => models.value.length)

const testing = ref(false)
const connMsg = ref('')
const connOk = ref(false)
const connModels = ref(0)

onMounted(() => {
  if (!models.value.length) config.refreshStatus()
})

async function refresh() {
  await config.refreshStatus()
  message.success('状态已刷新')
}

async function testConn() {
  testing.value = true
  connMsg.value = ''
  try {
    const resp = await api.testConnection({
      base_url: apiBase.value,
      endpoint: endpoint.value,
      api_key: config.config?.api?.api_key || '',
      extra_headers: config.config?.api?.extra_headers || {},
    })
    connOk.value = resp.ok
    connModels.value = resp.models?.length || 0
    connMsg.value = resp.ok ? '' : resp.error || '未知错误'
    if (resp.ok) await config.refreshStatus()
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.field-label {
  font-size: 13px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.65);
  margin-bottom: 6px;
}
.env-footer {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid #f5f5f5;
  padding-top: 12px;
}
.conn-msg {
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-right: auto;
}
.conn-msg.ok {
  color: #52c41a;
}
.conn-msg.bad {
  color: #ff4d4f;
}
</style>

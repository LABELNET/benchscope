<template>
  <div class="settings-page">
    <!-- 左侧菜单 -->
    <div class="settings-sidebar">
      <div class="sidebar-title">{{ t('settings') }}</div>
      <div class="sidebar-menu">
        <div
          v-for="item in menuItems"
          :key="item.key"
          class="menu-item"
          :class="{ active: activeTab === item.key }"
          @click="activeTab = item.key"
        >
          <component :is="item.icon" class="menu-icon" />
          <span>{{ item.label }}</span>
        </div>
      </div>
    </div>

    <!-- 右侧内容 -->
    <div class="settings-content">
      <!-- General -->
      <div v-if="activeTab === 'general'" class="tab-content">
        <div class="content-section">
          <div class="section-row">
            <span class="section-label">{{ t('language') }}</span>
            <a-select v-model:value="form.locale" @change="onLocaleChange" style="width: 160px" :options="localeOptions" />
          </div>
        </div>

        <div class="content-section">
          <div class="section-label">{{ t('appearance') }}</div>
          <div class="appearance-cards">
            <div
              v-for="opt in themeOptions"
              :key="opt.value"
              class="theme-card"
              :class="{ active: form.theme === opt.value }"
              @click="selectTheme(opt.value)"
            >
              <component :is="opt.icon" class="theme-icon" />
              <span class="theme-label">{{ opt.label }}</span>
            </div>
          </div>
        </div>

        <!-- 其他设置 -->
        <div class="content-section">
          <div class="section-label">{{ t('otherSettings') }}</div>
          <div class="section-row">
            <span class="section-label" style="font-weight: 400">{{ t('defaultFramework') }}</span>
            <a-select v-model:value="form.framework" style="width: 200px" :options="frameworkOptions" @change="saveField('framework')" />
          </div>
          <div class="section-row">
            <span class="section-label" style="font-weight: 400">{{ t('tpotThreshold') }}</span>
            <a-input-number v-model:value="form.tpot_threshold_ms" :min="0" addon-after="ms" style="width: 200px" @change="saveField('tpot_threshold_ms')" />
          </div>
          <div class="section-row">
            <span class="section-label" style="font-weight: 400">{{ t('logsDir') }}</span>
            <a-input v-model:value="form.logs_dir" placeholder="./logs" style="width: 360px" @change="saveField('logs_dir')" />
          </div>
          <div class="section-row">
            <span class="section-label" style="font-weight: 400">{{ t('datasetsDir') }}</span>
            <a-input v-model:value="form.datasets_dir" placeholder="./datasets" style="width: 360px" @change="saveField('datasets_dir')" />
          </div>
          <div class="section-row">
            <span class="section-label" style="font-weight: 400">{{ t('requestRate') }}</span>
            <div style="display: flex; gap: 8px; align-items: center">
              <a-select v-model:value="requestRateMode" style="width: 160px" :options="requestRateOptions" @change="saveRequestRate" />
              <a-input-number v-if="requestRateMode === 'custom'" v-model:value="requestRateValue" :min="0" addon-after="req/s" style="width: 180px" @change="saveRequestRate" />
            </div>
          </div>
          <div class="section-row">
            <span class="section-label" style="font-weight: 400">{{ t('benchShellInit') }}</span>
            <a-input
              v-model:value="form.bench_shell_init"
              :placeholder="t('benchShellInitPlaceholder')"
              style="width: 480px"
              @change="saveField('bench_shell_init')"
            />
          </div>
        </div>
      </div>

      <!-- Models -->
      <div v-if="activeTab === 'models'" class="tab-content">
        <h3 style="margin: 0 0 8px">{{ t('modelsTitle') }}</h3>
        <p class="section-desc">{{ t('modelsDesc') }}</p>

        <!-- Provider table -->
        <div class="provider-table-wrapper">
          <a-table :columns="providerColumns" :data-source="providers" size="small" :pagination="false" row-key="name">
            <template #bodyCell="{ column, record, index }">
              <template v-if="column.key === 'status'">
                <span class="provider-status-dot" :class="record.connected ? 'connected' : 'disconnected'"></span>
                <span class="provider-status-text">{{ record.connected ? t('connectionOk') : t('connectionFail') }}</span>
              </template>
              <template v-if="column.key === 'actions'">
                <a-button type="link" size="small" @click="editProvider(index)">{{ t('edit') }}</a-button>
                <a-button type="link" size="small" @click="testProvider(index)">{{ t('testConnection') }}</a-button>
                <a-button type="link" size="small" danger @click="removeProvider(index)">{{ t('delete') }}</a-button>
              </template>
            </template>
          </a-table>
        </div>

        <div style="margin-top: 16px">
          <a-button class="add-provider-btn" @click="showAddCustom = true">
            <template #icon><plus-outlined /></template>
            {{ t('addCustomProvider') }}
          </a-button>
        </div>
      </div>

      <!-- Plugins -->
      <div v-if="activeTab === 'plugins'" class="tab-content">
        <h3 style="margin: 0 0 8px">{{ t('plugins') }}</h3>
        <p class="section-desc">{{ t('pluginsDesc') }}</p>
        <a-empty :description="t('noData')" />
      </div>
    </div>

    <!-- Add/Edit custom provider modal -->
    <a-modal v-model:open="showAddCustom" :title="editIndex >= 0 ? t('editProvider') : t('addCustomProvider')" @ok="saveProvider" :ok-text="t('okText')" :cancel-text="t('cancel')">
      <a-form layout="vertical">
        <a-form-item :label="t('providerName')">
          <a-input v-model:value="newCustom.name" :placeholder="t('providerNamePlaceholder')" />
        </a-form-item>
        <a-form-item :label="t('baseUrl')">
          <a-input v-model:value="newCustom.base_url" :placeholder="t('baseUrlPlaceholder')" />
        </a-form-item>
        <a-form-item :label="t('endpoint')">
          <a-input v-model:value="newCustom.endpoint" :placeholder="t('endpointPlaceholder')" />
        </a-form-item>
        <a-form-item :label="t('apiKey')">
          <a-input-password v-model:value="newCustom.api_key" :placeholder="t('apiKeyPlaceholder')" />
        </a-form-item>
        <a-form-item :label="t('framework')">
          <a-radio-group v-model:value="newCustom.framework" button-style="solid">
            <a-radio-button value="vllm">vLLM</a-radio-button>
            <a-radio-button value="sglang">SGLang</a-radio-button>
          </a-radio-group>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  SettingOutlined, DatabaseOutlined, ApiOutlined,
  PlusOutlined,
  BulbOutlined, CloudOutlined, DesktopOutlined,
} from '@ant-design/icons-vue'
import { api } from '@/api'
import { useConfigStore } from '@/store/config'
import { t, setLocale } from '@/i18n'

const config = useConfigStore()
const activeTab = ref('general')
const testing = ref(false)
const showAddCustom = ref(false)
const editIndex = ref(-1)
const providers = ref([])

const form = reactive({
  theme: 'light',
  locale: 'en',
  framework: 'vllm',
  tpot_threshold_ms: 100,
  logs_dir: './logs',
  datasets_dir: './datasets',
  request_rate: 'inf',
  api: { base_url: '', endpoint: '/v1/chat/completions', api_key: '', extra_headers: {} },
})

const requestRateMode = ref('inf')
const requestRateValue = ref(10)

const newCustom = reactive({ name: '', base_url: 'http://127.0.0.1:8000', endpoint: '/v1/chat/completions', api_key: '', framework: 'vllm' })

const menuItems = computed(() => [
  { key: 'general', icon: SettingOutlined, label: t('general') },
  { key: 'models', icon: DatabaseOutlined, label: t('modelsTab') },
  { key: 'plugins', icon: ApiOutlined, label: t('plugins') },
])

const localeOptions = computed(() => [
  { value: 'en', label: 'English' },
  { value: 'zh', label: '中文' },
])

const themeOptions = computed(() => [
  { value: 'light', icon: BulbOutlined, label: t('light') },
  { value: 'dark', icon: CloudOutlined, label: t('dark') },
  { value: 'system', icon: DesktopOutlined, label: t('system') },
])

const frameworkOptions = computed(() => [
  { label: 'vLLM', value: 'vllm' },
  { label: 'SGLang', value: 'sglang' },
])

const requestRateOptions = computed(() => [
  { label: t('requestRateInf'), value: 'inf' },
  { label: t('requestRateCustom'), value: 'custom' },
])

const providerColumns = computed(() => [
  { title: t('providerNameCol'), dataIndex: 'name', key: 'name' },
  { title: t('baseUrl'), dataIndex: 'base_url', key: 'base_url' },
  { title: t('frameworkCol'), dataIndex: 'framework', key: 'framework' },
  { title: t('statusCol'), key: 'status', width: 120 },
  { title: '', key: 'actions', width: 200 },
])

onMounted(async () => {
  try {
    await config.load()
    const c = config.config || {}
    Object.assign(form, {
      theme: c.theme || 'light',
      locale: c.locale || 'en',
      framework: c.framework || 'vllm',
      tpot_threshold_ms: c.tpot_threshold_ms ?? 100,
      logs_dir: c.logs_dir || './logs',
      datasets_dir: c.datasets_dir || './datasets',
      request_rate: c.request_rate || 'inf',
      api: {
        base_url: c.api?.base_url || '',
        endpoint: c.api?.endpoint || '/v1/chat/completions',
        api_key: c.api?.api_key || '',
        extra_headers: c.api?.extra_headers || {},
      },
    })
    // Sync request rate mode/value
    const rr = c.request_rate
    if (rr === 'inf' || rr === undefined || rr === null || rr === '') {
      requestRateMode.value = 'inf'
      requestRateValue.value = 10
    } else {
      requestRateMode.value = 'custom'
      requestRateValue.value = Number(rr) || 10
    }
    // Load providers from config
    if (c.providers?.length) {
      providers.value = c.providers.map(p => ({ ...p, connected: false }))
    } else {
      const defaultUrl = form.api.base_url || 'http://127.0.0.1:8000'
      providers.value = [{ name: 'Default', base_url: defaultUrl, api_key: form.api.api_key, framework: form.framework, connected: false }]
    }
    // 自动测试所有 provider 连接
    autoTestAll()
  } catch { /* ignore */ }
})

function onLocaleChange() {
  setLocale(form.locale)
  // 持久化到后端（无需手动保存）
  config.save({ locale: form.locale }).catch(() => {})
}

function selectTheme(theme) {
  form.theme = theme
  // 立即应用到 config store，触发 App.vue 的 resolvedTheme 更新
  config.$patch({
    config: { ...(config.config || {}), theme },
  })
  // 持久化到后端（无需手动保存）
  config.save({ theme }).catch(() => {})
}

async function testProvider(index) {
  const provider = providers.value[index]
  testing.value = true
  try {
    const result = await api.testConnection({
      base_url: provider.base_url,
      endpoint: provider.endpoint || '/v1/chat/completions',
      api_key: provider.api_key || '',
      extra_headers: {},
    })
    providers.value[index] = { ...provider, connected: result.ok }
    if (result.ok) {
      message.success(`${provider.name} ${t('connectionOk')}`)
    } else {
      message.error(`${provider.name} ${t('connectionFail')}`)
    }
  } catch (e) {
    providers.value[index] = { ...provider, connected: false }
    message.error(e.message)
  } finally {
    testing.value = false
  }
}

function removeProvider(index) {
  providers.value.splice(index, 1)
  persistProviders()
}

function editProvider(index) {
  editIndex.value = index
  const p = providers.value[index]
  Object.assign(newCustom, { name: p.name, base_url: p.base_url, endpoint: p.endpoint || '/v1/chat/completions', api_key: p.api_key || '', framework: p.framework || 'vllm' })
  showAddCustom.value = true
}

function saveProvider() {
  if (!newCustom.name) { message.warning(t('enterProviderNameWarn')); return }
  if (editIndex.value >= 0) {
    providers.value[editIndex.value] = { ...providers.value[editIndex.value], ...newCustom }
  } else {
    providers.value.push({ ...newCustom, connected: false })
  }
  Object.assign(newCustom, { name: '', base_url: 'http://127.0.0.1:8000', endpoint: '/v1/chat/completions', api_key: '', framework: 'vllm' })
  editIndex.value = -1
  showAddCustom.value = false
  persistProviders()
}

function persistProviders() {
  config.save({ providers: providers.value.map(({ connected, ...rest }) => rest) }).catch(() => {})
}

function saveField(key) {
  config.save({ [key]: form[key] }).catch(() => {})
}

function saveRequestRate() {
  const v = requestRateMode.value === 'inf' ? 'inf' : String(requestRateValue.value ?? 0)
  form.request_rate = v
  config.save({ request_rate: v }).catch(() => {})
}

async function autoTestAll() {
  for (let i = 0; i < providers.value.length; i++) {
    try {
      const provider = providers.value[i]
      const result = await api.testConnection({
        base_url: provider.base_url,
        endpoint: provider.endpoint || '/v1/chat/completions',
        api_key: provider.api_key || '',
        extra_headers: {},
      })
      providers.value[i] = { ...provider, connected: result.ok }
    } catch {
      providers.value[i] = { ...providers.value[i], connected: false }
    }
  }
}
</script>

<style scoped>
.settings-page {
  display: flex;
  height: 100%;
  overflow: hidden;
  background: var(--ant-color-bg-container, #fff);
}

/* ===== 左侧菜单 ===== */
.settings-sidebar {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid var(--ant-color-border, #f0f0f0);
  background: var(--ant-color-bg-layout, #fafafa);
  padding: 24px 12px;
}

.sidebar-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--ant-color-text, #333);
  padding: 0 12px 20px;
}

.sidebar-menu {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  color: var(--ant-color-text-secondary, #555);
  transition: all 0.2s;
}

.menu-item:hover {
  background: var(--ant-color-fill-secondary, #f0f0f0);
  color: var(--ant-color-text, #333);
}

.menu-item.active {
  background: var(--ant-color-primary-bg, #e6f4ff);
  color: var(--ant-color-primary, #1677ff);
  font-weight: 500;
}

.menu-icon {
  font-size: 18px;
}

/* ===== 右侧内容 ===== */
.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 32px 40px;
  max-width: 800px;
}

.tab-content {
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.content-section {
  margin-bottom: 28px;
}

.section-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--ant-color-border, #f0f0f0);
}

.section-label {
  font-size: 14px;
  color: var(--ant-color-text, #333);
  font-weight: 500;
}

.section-desc {
  font-size: 14px;
  color: var(--ant-color-text-tertiary, #999);
  margin: 0 0 24px;
}

/* ===== Appearance cards ===== */
.appearance-cards {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}

.theme-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 16px;
  border: 1px solid var(--ant-color-border, #e8e8e8);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--ant-color-bg-container, #fff);
}

.theme-card:hover {
  border-color: var(--ant-color-primary, #1677ff);
  box-shadow: 0 2px 8px rgba(22, 119, 255, 0.1);
}

.theme-card.active {
  border-color: var(--ant-color-primary, #1677ff);
  background: var(--ant-color-primary-bg, #f0f5ff);
}

.theme-icon {
  font-size: 22px;
  color: var(--ant-color-text-secondary, #666);
}

.theme-label {
  font-size: 14px;
  color: var(--ant-color-text, #333);
}

/* ===== Provider table ===== */
.provider-table-wrapper {
  margin-top: 16px;
  border: 1px solid var(--ant-color-border, #f0f0f0);
  border-radius: 8px;
  overflow: hidden;
}

.provider-status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}

.provider-status-dot.connected {
  background: #52c41a;
}

.provider-status-dot.disconnected {
  background: var(--ant-color-text-quaternary, #d9d9d9);
}

.provider-status-text {
  font-size: 13px;
  color: var(--ant-color-text-secondary, #666);
}

.add-provider-btn {
  flex: 1;
  height: 48px;
  border: 1px dashed var(--ant-color-border, #d9d9d9);
  border-radius: 10px;
  font-size: 14px;
  color: var(--ant-color-text-secondary, #666);
  background: var(--ant-color-bg-layout, #fafafa);
}

.add-provider-btn:hover {
  border-color: var(--ant-color-primary, #1677ff);
  color: var(--ant-color-primary, #1677ff);
  background: var(--ant-color-primary-bg, #f0f5ff);
}

</style>

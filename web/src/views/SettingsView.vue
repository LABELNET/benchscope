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
              @click="form.theme = opt.value"
            >
              <component :is="opt.icon" class="theme-icon" />
              <span class="theme-label">{{ opt.label }}</span>
            </div>
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

      <!-- Save bar -->
      <div class="save-bar">
        <a-button type="primary" size="large" @click="saveAll">
          <template #icon><save-outlined /></template>
          {{ t('save') }}
        </a-button>
      </div>
    </div>

    <!-- Add custom provider modal -->
    <a-modal v-model:open="showAddCustom" :title="t('addCustomProvider')" @ok="addCustomProvider" ok-text="OK" cancel-text="Cancel">
      <a-form layout="vertical">
        <a-form-item :label="t('providerName')">
          <a-input v-model:value="newCustom.name" placeholder="e.g. My Provider" />
        </a-form-item>
        <a-form-item :label="t('baseUrl')">
          <a-input v-model:value="newCustom.base_url" placeholder="http://..." />
        </a-form-item>
        <a-form-item :label="t('endpoint')">
          <a-input v-model:value="newCustom.endpoint" placeholder="/v1/chat/completions" />
        </a-form-item>
        <a-form-item :label="t('apiKey')">
          <a-input-password v-model:value="newCustom.api_key" placeholder="sk-..." />
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
  PlusOutlined, SaveOutlined,
  BulbOutlined, CloudOutlined, DesktopOutlined,
} from '@ant-design/icons-vue'
import { api } from '@/api'
import { useConfigStore } from '@/store/config'
import { t, setLocale } from '@/i18n'

const config = useConfigStore()
const activeTab = ref('general')
const testing = ref(false)
const showAddCustom = ref(false)
const providers = ref([])

const form = reactive({
  theme: 'light',
  locale: 'en',
  framework: 'vllm',
  api: { base_url: '', endpoint: '/v1/chat/completions', api_key: '', extra_headers: {} },
})

const newCustom = reactive({ name: '', base_url: '', endpoint: '/v1/chat/completions', api_key: '', framework: 'vllm' })

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

const providerColumns = [
  { title: 'Provider Name', dataIndex: 'name', key: 'name' },
  { title: 'Base URL', dataIndex: 'base_url', key: 'base_url' },
  { title: 'Framework', dataIndex: 'framework', key: 'framework' },
  { title: 'Status', key: 'status', width: 120 },
  { title: '', key: 'actions', width: 140 },
]

onMounted(async () => {
  try {
    await config.load()
    const c = config.config || {}
    Object.assign(form, {
      theme: c.theme || 'light',
      locale: c.locale || 'en',
      framework: c.framework || 'vllm',
      api: {
        base_url: c.api?.base_url || '',
        endpoint: c.api?.endpoint || '/v1/chat/completions',
        api_key: c.api?.api_key || '',
        extra_headers: c.api?.extra_headers || {},
      },
    })
    // Load providers from config
    if (c.providers?.length) {
      providers.value = c.providers.map(p => ({ ...p, connected: false }))
    } else if (form.api.base_url) {
      providers.value = [{ name: 'Default', base_url: form.api.base_url, api_key: form.api.api_key, framework: form.framework, connected: config.status?.inference === 'ready' }]
    }
  } catch { /* ignore */ }
})

function onLocaleChange() {
  setLocale(form.locale)
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
}

function addCustomProvider() {
  if (!newCustom.name) { message.warning('Please enter provider name'); return }
  providers.value.push({ ...newCustom, connected: false })
  Object.assign(newCustom, { name: '', base_url: '', endpoint: '/v1/chat/completions', api_key: '', framework: 'vllm' })
  showAddCustom.value = false
}

async function saveAll() {
  try {
    await config.save({
      theme: form.theme,
      locale: form.locale,
      framework: form.framework,
      api: { ...form.api, extra_headers: {} },
      providers: providers.value,
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
  display: flex;
  height: 100%;
  overflow: hidden;
  background: #fff;
}

/* ===== 左侧菜单 ===== */
.settings-sidebar {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid #f0f0f0;
  background: #fafafa;
  padding: 24px 12px;
}

.sidebar-title {
  font-size: 20px;
  font-weight: 700;
  color: #333;
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
  color: #555;
  transition: all 0.2s;
}

.menu-item:hover {
  background: #f0f0f0;
  color: #333;
}

.menu-item.active {
  background: #e6f4ff;
  color: #1677ff;
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
  border-bottom: 1px solid #f0f0f0;
}

.section-label {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.section-desc {
  font-size: 14px;
  color: #999;
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
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
}

.theme-card:hover {
  border-color: #1677ff;
  box-shadow: 0 2px 8px rgba(22, 119, 255, 0.1);
}

.theme-card.active {
  border-color: #1677ff;
  background: #f0f5ff;
}

.theme-icon {
  font-size: 22px;
  color: #666;
}

.theme-label {
  font-size: 14px;
  color: #333;
}

/* ===== Provider table ===== */
.provider-table-wrapper {
  margin-top: 16px;
  border: 1px solid #f0f0f0;
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
  background: #d9d9d9;
}

.provider-status-text {
  font-size: 13px;
  color: #666;
}

.add-provider-btn {
  flex: 1;
  height: 48px;
  border: 1px dashed #d9d9d9;
  border-radius: 10px;
  font-size: 14px;
  color: #666;
  background: #fafafa;
}

.add-provider-btn:hover {
  border-color: #1677ff;
  color: #1677ff;
  background: #f0f5ff;
}

/* ===== Save bar ===== */
.save-bar {
  text-align: center;
  padding: 24px 0 32px;
  border-top: 1px solid #f0f0f0;
  margin-top: 16px;
}
</style>

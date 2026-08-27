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
      <!-- General：Language + Cache Paths 两个面板 -->
      <div v-if="activeTab === 'general'" class="tab-content">
        <a-card size="small" :bordered="true" class="panel-card">
          <template #title>{{ t('language') }}</template>
          <div class="panel-row">
            <a-select v-model:value="form.locale" @change="onLocaleChange" style="width: 200px" :options="localeOptions" />
          </div>
        </a-card>

        <a-card size="small" :bordered="true" class="panel-card">
          <template #title>
            <span>{{ t('cachePaths') }}</span>
            <a-tag v-if="perfRunning" color="orange" class="running-tag">{{ t('runningLocked') }}</a-tag>
          </template>
          <div v-for="d in dirs" :key="d.key" class="panel-row dir-row">
            <div class="dir-info">
              <span class="dir-label">{{ d.label }}</span>
              <span class="field-desc">{{ d.desc }}</span>
            </div>
            <div class="dir-right">
              <template v-if="editingKey === d.key">
                <a-input
                  v-model:value="editValue"
                  size="small"
                  class="dir-input"
                  :disabled="d.locked"
                  @pressEnter="saveDir(d)"
                  @blur="cancelEdit()"
                />
                <a-button
                  type="primary"
                  size="small"
                  :loading="savingDirKey === d.key"
                  :disabled="d.locked"
                  @mousedown.prevent
                  @click="saveDir(d)"
                >{{ t('save') }}</a-button>
              </template>
              <span
                v-else
                class="dir-value"
                :class="{ editable: !d.locked }"
                @click="d.locked ? notifyLocked() : startEdit(d)"
              >
                {{ d.value }}
                <a-tag v-if="!d.exists" color="red" size="small">{{ t('dirMissing') }}</a-tag>
              </span>
            </div>
          </div>
        </a-card>
      </div>

      <!-- Environment：本地测试环境面板 -->
      <div v-if="activeTab === 'environment'" class="tab-content">
        <a-card size="small" :bordered="true" class="panel-card">
          <template #title>Envs</template>
          <template #extra>
            <span class="env-status" :class="envReady ? 'ok' : 'bad'">
              <span class="env-dot"></span>
              {{ envReady ? t('online') : t('offline') }}
              <span v-if="envReady && config.status?.models?.length" class="env-models">
                {{ config.status.models.length }} {{ t('models') }}
              </span>
            </span>
          </template>

          <div class="panel-row">
            <span class="panel-label">{{ t('framework') }}</span>
            <a-radio-group v-model:value="form.framework" :disabled="!envEditMode" button-style="solid">
              <a-radio-button value="vllm">vLLM</a-radio-button>
              <a-radio-button value="sglang">SGLang</a-radio-button>
            </a-radio-group>
          </div>
          <div class="panel-row">
            <span class="panel-label">{{ t('baseUrl') }}</span>
            <a-input v-model:value="form.api.base_url" :disabled="!envEditMode" placeholder="http://127.0.0.1:8000" style="width: 380px" />
          </div>
          <div class="panel-row">
            <span class="panel-label">{{ t('apiKey') }}</span>
            <a-input-password v-model:value="form.api.api_key" :disabled="!envEditMode" :placeholder="t('apiKeyPlaceholder')" style="width: 380px" />
          </div>

          <div class="env-footer">
            <a-button v-if="!envEditMode" type="primary" @click="envEditMode = true">{{ t('edit') }}</a-button>
            <a-button v-else type="primary" :loading="saving" @click="saveEnvironment">{{ t('save') }}</a-button>
            <a-button :loading="testing" @click="testEnvironment">{{ t('testConnection') }}</a-button>
          </div>
        </a-card>
      </div>

      <!-- Datasets：内置数据集 -->
      <div v-if="activeTab === 'datasets'" class="tab-content">
        <h3 style="margin: 0 0 8px">{{ t('builtinDatasets') }}</h3>
        <p class="section-desc">{{ t('datasetsHint') }}</p>

        <a-spin :spinning="datasetsLoading">
          <div v-if="datasets.length" class="ds-list">
            <div v-for="ds in datasets" :key="ds.id" class="ds-card">
              <div class="ds-head">
                <span class="ds-name">{{ ds.name }}</span>
                <span v-if="ds.status?.cached" class="ds-status cached">{{ t('datasetCached') }}</span>
                <span v-else class="ds-status">{{ t('datasetNotCached') }}</span>
              </div>
              <p class="ds-desc">{{ ds.description }}</p>
              <div class="ds-row">
                <span class="ds-label">{{ t('accessLink') }}</span>
                <a class="ds-link" :href="ds.url" target="_blank" rel="noopener noreferrer">{{ ds.url }}</a>
              </div>
              <div class="ds-row column">
                <span class="ds-label">{{ t('downloadCmd') }}</span>
                <a-typography-text code copyable class="ds-cmd">{{ ds.download }}</a-typography-text>
              </div>
              <div class="ds-footer">
                <a-button type="primary" size="small" :loading="downloadingId === ds.id" @click="downloadDataset(ds)">
                  {{ t('download') }}
                </a-button>
              </div>
            </div>
          </div>
          <a-empty v-else-if="!datasetsLoading" :description="t('noData')" />
        </a-spin>
      </div>

      <!-- Models：内置模型下载链接宫格 -->
      <div v-if="activeTab === 'models'" class="tab-content">
        <h3 style="margin: 0 0 8px">{{ t('builtinModels') }}</h3>
        <p class="section-desc">{{ t('modelsGridHint') }}</p>

        <div class="model-grid">
          <div v-for="m in modelCatalog" :key="m.id" class="model-card" @click="openModel(m)">
            <div class="model-avatar" :style="{ background: m.color }">{{ m.short }}</div>
            <div class="model-info">
              <div class="model-name">{{ m.name }}</div>
              <div class="model-intro">{{ m.intro[locale] }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Plugins：占位 -->
      <div v-if="activeTab === 'plugins'" class="tab-content">
        <h3 style="margin: 0 0 8px">{{ t('plugins') }}</h3>
        <p class="section-desc">{{ t('pluginsDesc') }}</p>
        <a-empty :description="t('noData')" />
      </div>
    </div>

    <!-- Data 目录迁移进度弹窗 -->
    <a-modal v-model:open="migrateOpen" :footer="null" :closable="false" :keyboard="false" :mask-closable="false" :width="420">
      <div class="migrate-box">
        <a-spin :spinning="migratePhase !== 'restarting'" />
        <div class="migrate-title">{{ migratePhase === 'restarting' ? t('restarting') : t('migrating') }}</div>
        <a-progress :percent="migratePercent" :status="migratePhase === 'restarting' ? 'active' : 'normal'" />
        <div class="migrate-msg">{{ migrateMessage }}</div>
      </div>
    </a-modal>

    <!-- 模型详情右侧面板 -->
    <a-drawer
      v-model:open="drawerOpen"
      :width="440"
      placement="right"
      :title="selectedModel?.name || ''"
    >
      <div v-if="selectedModel" class="model-detail">
        <div class="detail-logo" :style="{ background: selectedModel.color }">{{ selectedModel.short }}</div>
        <h3 class="detail-name">{{ selectedModel.name }}</h3>
        <div class="detail-org">{{ selectedModel.org }}</div>
        <p class="detail-intro">{{ selectedModel.intro[locale] }}</p>

        <div class="detail-row">
          <span class="detail-label">{{ t('supportedPrecision') }}</span>
          <span class="detail-tags">
            <a-tag v-for="p in selectedModel.precision" :key="p" color="blue">{{ p }}</a-tag>
          </span>
        </div>
        <div class="detail-row">
          <span class="detail-label">{{ t('accessLink') }}</span>
          <a class="detail-link" :href="selectedModel.homepage" target="_blank" rel="noopener noreferrer">{{ selectedModel.homepage }}</a>
        </div>
        <div class="detail-row column">
          <span class="detail-label">{{ t('downloadCmd') }}</span>
          <a-typography-text code copyable class="download-cmd">{{ selectedModel.download }}</a-typography-text>
        </div>
      </div>

      <template #footer>
        <div class="drawer-footer">
          <a-button type="primary" @click="deployModel">{{ t('deploy') }}</a-button>
        </div>
      </template>
    </a-drawer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { message, notification, Modal } from 'ant-design-vue'
import {
  SettingOutlined, DesktopOutlined, DatabaseOutlined, ApiOutlined,
  CloudDownloadOutlined,
} from '@ant-design/icons-vue'
import { api, wsUrl } from '@/api'
import { useConfigStore } from '@/store/config'
import { t, setLocale, i18nState } from '@/i18n'
import { modelCatalog } from '@/data/modelCatalog'

const config = useConfigStore()
const activeTab = ref('general')
const envEditMode = ref(false)
const testing = ref(false)
const saving = ref(false)
const drawerOpen = ref(false)
const selectedModel = ref(null)
const datasets = ref([])
const datasetsLoading = ref(false)
const downloadingId = ref('')

// ---- Cache Paths 目录管理 ----
const dirs = ref([])
const perfRunning = ref(false)
const editingKey = ref('')
const editValue = ref('')
const savingDirKey = ref('')
// Data 目录迁移/重启
const migrateOpen = ref(false)
const migratePhase = ref('connecting')
const migrateProgress = ref({ done: 0, total: 0 })
const migrateMessage = ref('')
let migrateSocket = null

const migratePercent = computed(() => {
  const { done, total } = migrateProgress.value
  if (!total) return migratePhase.value === 'migrating' ? 0 : 100
  return Math.min(100, Math.round((done / total) * 100))
})

const form = reactive({
  locale: 'en',
  logs_dir: './logs',
  datasets_dir: './datasets',
  data_dir: '~/.benchscope',
  models_dir: '~/.benchscope/models',
  framework: 'vllm',
  api: { base_url: '', endpoint: '/v1/chat/completions', api_key: '', extra_headers: {} },
})

const menuItems = computed(() => [
  { key: 'general', icon: SettingOutlined, label: t('general') },
  { key: 'environment', icon: DesktopOutlined, label: t('environment') },
  { key: 'datasets', icon: CloudDownloadOutlined, label: t('datasetsTab') },
  { key: 'models', icon: DatabaseOutlined, label: t('modelsTab') },
  { key: 'plugins', icon: ApiOutlined, label: t('plugins') },
])

const localeOptions = computed(() => [
  { value: 'en', label: 'English' },
  { value: 'zh', label: '中文' },
])

const locale = computed(() => i18nState.locale)

const envReady = computed(() => config.status?.inference === 'ready')

onMounted(async () => {
  try {
    await config.load()
    const c = config.config || {}
    Object.assign(form, {
      locale: c.locale || 'en',
      logs_dir: c.logs_dir || './logs',
      datasets_dir: c.datasets_dir || './datasets',
      data_dir: c.data_dir || '~/.benchscope',
      models_dir: c.models_dir || '~/.benchscope/models',
      framework: c.framework || 'vllm',
      api: {
        base_url: c.api?.base_url || 'http://127.0.0.1:8000',
        endpoint: c.api?.endpoint || '/v1/chat/completions',
        api_key: c.api?.api_key || '',
        extra_headers: c.api?.extra_headers || {},
      },
    })
    loadDirs()
    loadDatasets()
  } catch { /* ignore */ }
})

async function loadDirs() {
  try {
    const resp = await api.getDirs()
    dirs.value = resp.dirs || []
    perfRunning.value = !!resp.perf_running
  } catch {
    dirs.value = []
  }
}

function startEdit(d) {
  editingKey.value = d.key
  editValue.value = d.value
}

function cancelEdit() {
  editingKey.value = ''
  editValue.value = ''
}

function notifyLocked() {
  notification.warning({
    message: t('lockedTitle'),
    description: t('lockedDesc'),
    placement: 'topRight',
    duration: 4,
  })
}

async function saveDir(d) {
  const val = (editValue.value || '').trim()
  if (!val) {
    message.warning(t('dirEmpty'))
    return
  }
  if (val === d.value) {
    cancelEdit()
    return
  }
  savingDirKey.value = d.key
  try {
    const resp = await api.updateDirs({ [d.key]: val })
    cancelEdit()
    message.success(t('saved'))
    await loadDirs()
    // Data 根目录修改后需重启服务生效
    if (d.key === 'data_dir' && resp.requires_restart) {
      Modal.confirm({
        title: t('restartTitle'),
        content: t('restartContent'),
        okText: t('confirm'),
        cancelText: t('cancel'),
        onOk: () => askMigrate(),
      })
    }
  } catch (e) {
    message.error(e.message || t('saveFail'))
    loadDirs() // 若因任务运行中拒绝，刷新锁定状态
  } finally {
    savingDirKey.value = ''
  }
}

function askMigrate() {
  Modal.confirm({
    title: t('migrateTitle'),
    content: t('migrateContent'),
    okText: t('migrateYes'),
    cancelText: t('migrateNo'),
    onOk: () => restartWithMigrate(true),
    onCancel: () => restartWithMigrate(false),
  })
}

function restartWithMigrate(migrate) {
  if (migrate) {
    migrateOpen.value = true
    migratePhase.value = 'connecting'
    migrateProgress.value = { done: 0, total: 0 }
    migrateMessage.value = t('migrating')
    openMigrateSocket()
  }
  api.restartService(migrate).catch((e) => {
    message.error(e.message || t('restartFail'))
    if (migrate) {
      migrateOpen.value = false
      closeMigrateSocket()
    }
  })
}

function openMigrateSocket() {
  try {
    migrateSocket = new WebSocket(wsUrl())
  } catch { return }
  migrateSocket.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data)
      if (msg.type !== 'migration') return
      migratePhase.value = msg.phase
      if (msg.phase === 'migrating') {
        migrateProgress.value = { done: msg.done || 0, total: msg.total || 0 }
        migrateMessage.value = msg.message || t('migrating')
      } else if (msg.phase === 'restarting') {
        migrateMessage.value = t('restarting')
      }
    } catch { /* ignore */ }
  }
}

function closeMigrateSocket() {
  if (migrateSocket) {
    try { migrateSocket.close() } catch { /* ignore */ }
    migrateSocket = null
  }
}

onBeforeUnmount(() => {
  closeMigrateSocket()
})

async function loadDatasets() {
  datasetsLoading.value = true
  try {
    const resp = await api.getDatasets()
    datasets.value = resp.datasets || []
  } catch {
    datasets.value = []
  } finally {
    datasetsLoading.value = false
  }
}

async function downloadDataset(ds) {
  downloadingId.value = ds.id
  try {
    await api.downloadDataset(ds.id)
    message.success(`${ds.name} ${t('saved')}`)
    await loadDatasets()
  } catch (e) {
    message.error(e.message || t('connectionFail'))
  } finally {
    downloadingId.value = ''
  }
}

function onLocaleChange() {
  setLocale(form.locale)
  config.save({ locale: form.locale }).catch(() => {})
}

function saveField(key) {
  config.save({ [key]: form[key] }).catch(() => {})
}

async function saveEnvironment() {
  saving.value = true
  try {
    await config.save({
      framework: form.framework,
      api: { ...form.api, extra_headers: form.api.extra_headers || {} },
    })
    message.success(t('saved'))
    envEditMode.value = false
    config.refreshStatus()
  } catch (e) {
    message.error(e.message || t('connectionFail'))
  } finally {
    saving.value = false
  }
}

async function testEnvironment() {
  testing.value = true
  try {
    const result = await api.testConnection({
      base_url: form.api.base_url,
      endpoint: form.api.endpoint || '/v1/chat/completions',
      api_key: form.api.api_key || '',
      extra_headers: form.api.extra_headers || {},
    })
    if (result.ok) {
      message.success(t('connectionOk'))
      config.refreshStatus()
    } else {
      message.error(result.error || t('connectionFail'))
    }
  } catch (e) {
    message.error(e.message || t('connectionFail'))
  } finally {
    testing.value = false
  }
}

function openModel(m) {
  selectedModel.value = m
  drawerOpen.value = true
}

function deployModel() {
  message.info(t('notImplemented'))
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
  max-width: 960px;
}

.tab-content {
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.panel-card {
  margin-bottom: 20px;
  border-radius: 12px;
}

.panel-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
}

.panel-row + .panel-row {
  border-top: 1px solid var(--ant-color-border, #f0f0f0);
}

.panel-label {
  font-size: 12px;
  color: var(--ant-color-text, #333);
  font-weight: 500;
}

.field-desc {
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
}

/* ===== Cache Paths 目录管理 ===== */
.running-tag {
  margin-left: 8px;
}

.dir-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.dir-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.dir-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ant-color-text, #333);
}

.dir-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.dir-input {
  width: 340px;
}

.dir-value {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--ant-color-primary, #1677ff);
  font-weight: 500;
  cursor: default;
  user-select: text;
}

.dir-value.editable {
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: rgba(22, 119, 255, 0.35);
  text-underline-offset: 3px;
}

.dir-value.editable:hover {
  color: var(--ant-color-primary-hover, #4096ff);
}

/* ===== 迁移进度弹窗 ===== */
.migrate-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 12px 8px;
}

.migrate-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--ant-color-text, #333);
}

.migrate-msg {
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
  word-break: break-all;
}

.section-desc {
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
  margin: 0 0 24px;
}

/* ===== Environment ===== */
.env-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
}

.env-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ant-color-text-quaternary, #d9d9d9);
}

.env-status.ok .env-dot { background: #52c41a; }
.env-status.bad .env-dot { background: #ff4d4f; }

.env-models {
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
}

.env-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--ant-color-border, #f0f0f0);
}

/* ===== Models 宫格 ===== */
.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
}

.model-card {
  display: flex;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--ant-color-border, #e8e8e8);
  border-radius: 12px;
  cursor: pointer;
  background: var(--ant-color-bg-container, #fff);
  transition: all 0.2s;
}

.model-card:hover {
  border-color: var(--ant-color-primary, #1677ff);
  box-shadow: 0 2px 8px rgba(22, 119, 255, 0.12);
  transform: translateY(-2px);
}

.model-avatar {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 15px;
  flex-shrink: 0;
}

.model-info {
  min-width: 0;
}

.model-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ant-color-text, #333);
}

.model-intro {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--ant-color-text-secondary, #666);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ===== 模型详情抽屉 ===== */
.model-detail {
  padding: 8px 4px;
}

.detail-logo {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 14px;
}

.detail-name {
  margin: 0 0 4px;
  font-size: 20px;
}

.detail-org {
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
  margin-bottom: 12px;
}

.detail-intro {
  font-size: 12px;
  line-height: 1.7;
  color: var(--ant-color-text, #333);
  margin-bottom: 16px;
}

.detail-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid var(--ant-color-border, #f0f0f0);
}

.detail-row.column {
  flex-direction: column;
  align-items: flex-start;
}

.detail-label {
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
  flex-shrink: 0;
  min-width: 88px;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.detail-link {
  font-size: 13px;
  word-break: break-all;
}

.download-cmd {
  font-size: 12px;
  word-break: break-all;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
}

/* ===== Datasets 内置数据集 ===== */
.ds-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ds-card {
  border: 1px solid var(--ant-color-border, #e8e8e8);
  border-radius: 10px;
  padding: 14px 16px;
  background: var(--ant-color-bg-container, #fff);
}
.ds-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}
.ds-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ant-color-text, #333);
}
.ds-status {
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
  border: 1px solid var(--ant-color-border-secondary, #d9d9d9);
  border-radius: 8px;
  padding: 0 8px;
  line-height: 18px;
}
.ds-status.cached {
  color: var(--ant-color-success, #52c41a);
  border-color: #95de64;
}
.ds-desc {
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
  margin: 0 0 8px;
}
.ds-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 4px 0;
  font-size: 12px;
}
.ds-row.column {
  flex-direction: column;
  align-items: flex-start;
}
.ds-label {
  color: var(--ant-color-text-tertiary, #999);
  flex-shrink: 0;
  min-width: 64px;
}
.ds-link {
  word-break: break-all;
  font-size: 12px;
}
.ds-cmd {
  font-size: 12px;
  word-break: break-all;
}
.ds-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
</style>

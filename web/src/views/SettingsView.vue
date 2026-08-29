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

    <!-- 右侧内容（Bench Engines 栏整页为可滑动列表，故切换为「填满高度 + 内部滚动」） -->
    <div class="settings-content" :class="{ 'content-fill': activeTab === 'benches' }">
      <!-- General：Language + Cache Paths 两个面板 -->
      <div v-if="activeTab === 'general'" class="tab-content narrow">
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
              <span class="dir-label">{{ dirLabel(d) }}</span>
              <span class="field-desc">{{ dirDesc(d) }}</span>
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
      <div v-if="activeTab === 'environment'" class="tab-content narrow">
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

      <!-- Datasets：内置数据集（左侧分类 + 每行一个数据集） -->
      <div v-if="activeTab === 'datasets'" class="tab-content">
        <h3 style="margin: 0 0 8px">{{ t('builtinDatasets') }}</h3>
        <p class="section-desc">{{ t('datasetsHint') }}</p>

        <a-spin :spinning="datasetsLoading">
          <div v-if="datasets.length" class="catalog-layout">
            <div class="catalog-sidebar">
              <div class="catalog-group">
                <div class="catalog-group-title">{{ t('category') }}</div>
                <div class="catalog-items">
                  <div
                    class="catalog-item"
                    :class="{ active: activeDsCat === 'all' }"
                    @click="activeDsCat = 'all'"
                  >
                    <span>{{ t('allCategories') }}</span>
                    <span class="catalog-count">{{ datasets.length }}</span>
                  </div>
                  <div
                    v-for="c in datasetCats"
                    :key="c.key"
                    class="catalog-item"
                    :class="{ active: activeDsCat === c.key }"
                    @click="activeDsCat = c.key"
                  >
                    <span>{{ catName(c) }}</span>
                    <span class="catalog-count">{{ catCount(c.key) }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="catalog-content">
              <div v-for="ds in filteredDatasets" :key="ds.id" class="ds-row-item">
                <div class="ds-row-main">
                  <div class="ds-row-head">
                    <span class="ds-name">{{ ds.name }}</span>
                    <a-tag v-if="ds.status?.cached" color="green" size="small">{{ t('datasetCached') }}</a-tag>
                    <a-tag v-else size="small">{{ t('datasetNotCached') }}</a-tag>
                  </div>
                  <p class="ds-desc">{{ ds.description }}</p>
                  <div class="ds-row-links">
                    <span class="ds-label">{{ t('accessLink') }}</span>
                    <a class="ds-link" :href="ds.url" target="_blank" rel="noopener noreferrer">{{ ds.url }}</a>
                  </div>
                  <div class="ds-row-links column">
                    <span class="ds-label">{{ t('downloadCmd') }}</span>
                    <a-typography-text code copyable class="ds-cmd">{{ ds.download }}</a-typography-text>
                  </div>
                </div>
                <div class="ds-row-actions">
                  <a-button type="primary" size="small" :loading="downloadingId === ds.id" @click="downloadDataset(ds)">
                    {{ t('download') }}
                  </a-button>
                </div>
              </div>
            </div>
          </div>
          <a-empty v-else-if="!datasetsLoading" :description="t('noData')" />
        </a-spin>
      </div>

      <!-- Models：厂商目录（左侧分组副侧边栏 + 右侧厂商模型列表） -->
      <div v-if="activeTab === 'models'" class="tab-content">
        <h3 style="margin: 0 0 8px">{{ t('builtinModels') }}</h3>
        <p class="section-desc">{{ t('modelsCatalogHint') }}</p>

        <a-spin :spinning="catalogLoading">
          <div v-if="modelGroups.length" class="catalog-layout">
            <div class="catalog-sidebar">
              <div v-for="g in modelGroups" :key="g.key" class="catalog-group">
                <div class="catalog-group-title clickable" @click="toggleGroup(g.key)">
                  <span class="group-caret" :class="{ collapsed: isCollapsed(g.key) }">▸</span>
                  <span>{{ groupName(g) }}</span>
                  <span class="catalog-count">{{ g.providers.length }}</span>
                </div>
                <div v-show="!isCollapsed(g.key)" class="catalog-items">
                  <div
                    v-for="p in g.providers"
                    :key="p.key"
                    class="catalog-item"
                    :class="{ active: selectedProvider?.key === p.key }"
                    @click="selectProvider(p)"
                  >
                    <span>{{ p.name }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="catalog-content">
              <template v-if="selectedProvider">
                <div class="provider-head">
                  <h3 class="provider-title">{{ selectedProvider.name }}</h3>
                  <a
                    v-if="selectedProvider.homepage"
                    class="provider-homepage"
                    :href="selectedProvider.homepage"
                    target="_blank"
                    rel="noopener noreferrer"
                  >{{ t('homepage') }}</a>
                </div>
                <div v-if="selectedProvider.models?.length" class="provider-models">
                  <div
                    v-for="m in selectedProvider.models"
                    :key="m"
                    class="provider-model-item"
                    :class="{ clickable: !!matchCatalog(m) }"
                    @click="openProviderModel(m)"
                  >
                    <span class="pm-name">{{ m }}</span>
                    <a-tag v-if="matchCatalog(m)" color="blue" size="small">{{ t('details') }}</a-tag>
                  </div>
                </div>
                <a-empty v-else :description="t('noModels')" />
              </template>
              <a-empty v-else :description="t('selectProvider')" />
            </div>
          </div>
          <a-empty v-else-if="!catalogLoading" :description="t('noData')" />
        </a-spin>
      </div>

      <!-- Bench Engines：整页为引擎列表（可滑动），操作入口在右上角 -->
      <div v-if="activeTab === 'benches'" class="tab-content bench-tab">
        <div class="bench-topbar">
          <div class="bench-topbar-left">
            <h3 class="bench-tab-title">{{ t('benchesTab') }}</h3>
            <p class="section-desc">{{ t('benchesDesc') }}</p>
          </div>
          <!-- 右上角文字按钮：Create / Upload / Comparison -->
          <div class="bench-actions">
            <a-button class="bench-text-btn" type="link" size="small" @click="openCreate">
              {{ t('benchCreateEngine') }}
            </a-button>
            <a-button class="bench-text-btn" type="link" size="small" @click="openUpload">
              {{ t('benchUploadEngine') }}
            </a-button>
            <a-button class="bench-text-btn" type="link" size="small" @click="compareOpen = true">
              {{ t('benchCompareBtn') }}
            </a-button>
          </div>
        </div>

        <a-spin :spinning="benchesLoading">
          <!-- 引擎列表（整页可滑动） -->
          <div class="bench-list-scroll">
            <div v-if="benches.length" class="bench-list">
              <div
                v-for="eng in benches"
                :key="eng.id"
                class="bench-card"
                :class="{ 'bench-default': eng.id === defaultEngineId }"
              >
                <div class="bench-head">
                  <span class="bench-name">{{ benchName(eng) }}</span>
                  <a-tag v-if="eng.id === defaultEngineId" color="blue" size="small">{{ t('benchDefault') }}</a-tag>
                  <a-tag :color="eng.kind === 'builtin' ? 'purple' : 'cyan'" size="small">{{ eng.kind }}</a-tag>
                  <a-tag v-if="eng.env?.ok" color="green" size="small">{{ t('benchEnvReady') }}</a-tag>
                  <a-tag v-else color="red" size="small">{{ t('benchEnvMissing') }}</a-tag>
                </div>
                <div class="bench-meta">
                  <span class="bench-label">{{ t('benchVersion') }}</span>
                  <span class="bench-value">{{ eng.version || '-' }}</span>
                </div>
                <p class="bench-desc">{{ benchDesc(eng) }}</p>

                <div v-if="benchHighlights(eng).length" class="bench-highlights">
                  <div class="bench-label">{{ t('benchHighlights') }}</div>
                  <ul class="bench-ul">
                    <li v-for="(h, i) in benchHighlights(eng)" :key="i">{{ h }}</li>
                  </ul>
                </div>

                <!-- 环境要求与校验结果 -->
                <div v-if="eng.requires?.length" class="bench-env">
                  <div class="bench-label">{{ t('benchRequires') }}</div>
                  <div class="bench-env-table">
                    <div v-for="c in eng.env?.checks || []" :key="c.name" class="bench-env-row">
                      <span class="env-name">{{ c.name }}</span>
                      <span class="env-req">{{ t('benchRequiredVersion') }}: {{ c.required }}</span>
                      <span class="env-installed">
                        {{ t('benchInstalled') }}:
                        <span :class="c.ok ? 'env-ok' : 'env-bad'">{{ c.installed || t('benchNotInstalled') }}</span>
                      </span>
                      <a-tag :color="c.ok ? 'green' : 'red'" size="small">{{ c.ok ? 'OK' : 'FAIL' }}</a-tag>
                    </div>
                    <div v-for="c in (eng.env?.checks || []).filter((x) => !x.ok && x.hint)" :key="`hint-${c.name}`" class="bench-hint">
                      {{ t('benchInstallHint') }}: {{ c.hint }}
                    </div>
                  </div>
                </div>
                <div v-else class="bench-env-none">{{ t('benchNoRequires') }}</div>
              </div>
            </div>
            <a-empty v-if="!benchesLoading && !benches.length" :description="t('noData')" />
          </div>
        </a-spin>
      </div>

      <!-- Plugins：占位 -->
      <div v-if="activeTab === 'plugins'" class="tab-content narrow">
        <h3 style="margin: 0 0 8px">{{ t('plugins') }}</h3>
        <p class="section-desc">{{ t('pluginsDesc') }}</p>
        <a-empty :description="t('noData')" />
      </div>
    </div>

    <!-- ===================== Bench Engines 弹窗 ===================== -->

    <!-- Create Engine：教程 + 上游链接 + 可复制提示词（不展示引擎定义原文） -->
    <a-modal v-model:open="createOpen" class="bench-modal">
      <template #title>
        <div class="bench-modal-head">
          <span class="bench-modal-title">{{ t('benchCreateEngine') }}</span>
          <span class="bench-modal-hint">{{ t('benchCreateHint') }}</span>
        </div>
      </template>

      <!-- 步骤教程 -->
      <div class="add-block">
        <div class="bench-label">{{ t('benchTutorialTitle') }}</div>
        <ol class="bench-ol">
          <li v-for="(s, i) in createSteps" :key="i">{{ s }}</li>
        </ol>
      </div>

      <!-- 上游链接 -->
      <div class="add-block">
        <div class="bench-label">{{ t('benchUpstreamLinks') }}</div>
        <ul class="bench-ul">
          <li v-for="(info, fw) in authoring.upstream || {}" :key="fw">
            <a :href="info.repo" target="_blank" rel="noopener">{{ info.repo }}</a>
            <span class="add-hint"> · {{ info.command }} · {{ info.bench_entry }}</span>
          </li>
        </ul>
        <p class="add-hint">{{ t('benchUpstreamHint') }}</p>
      </div>

      <!-- AI 提示词（可复制） -->
      <div class="add-block">
        <div class="bench-label">{{ t('benchPromptTitle') }}</div>
        <p class="add-hint">{{ t('benchPromptDesc') }}</p>
        <pre class="bench-yaml-view">{{ authoring.prompt || t('benchLoading') }}</pre>
      </div>

      <template #footer>
        <div class="bench-modal-footer">
          <a-button type="link" size="small" @click="copyPrompt">{{ t('benchCopyPrompt') }}</a-button>
          <a-button type="link" size="small" @click="createOpen = false">{{ t('cancel') }}</a-button>
        </div>
      </template>
    </a-modal>

    <!-- Upload Engine：上传引擎包（yaml 定义 / tar.gz 技能包） -->
    <a-modal v-model:open="uploadOpen" class="bench-modal">
      <template #title>
        <div class="bench-modal-head">
          <span class="bench-modal-title">{{ t('benchUploadEngine') }}</span>
          <span class="bench-modal-hint">{{ t('benchUploadHintText') }}</span>
        </div>
      </template>

      <a-upload-dragger
        :show-upload-list="false"
        :before-upload="beforeUploadEngine"
        accept=".yaml,.yml,.tar.gz,.tgz"
      >
        <p class="ant-upload-text">{{ t('benchUploadDrag') }}</p>
        <p class="ant-upload-hint">{{ t('benchUploadHint') }}</p>
      </a-upload-dragger>

      <div v-if="uploadName" class="upload-file">
        <span class="bench-label">{{ t('benchUploadFile') }}</span>
        <span class="upload-name">{{ uploadName }}</span>
        <a-button type="link" size="small" @click="clearUpload">{{ t('cancel') }}</a-button>
      </div>

      <!-- 上传校验 / 导入结果 -->
      <div v-if="uploadResult" class="import-result">
        <div class="check-row">
          <span class="check-item">{{ t('benchUploadAdded') }}</span>
          <span class="check-msg env-ok">{{ (uploadResult.added || []).join(', ') || '-' }}</span>
        </div>
        <div class="check-row">
          <span class="check-item">{{ t('benchUploadUpdated') }}</span>
          <span class="check-msg">{{ (uploadResult.updated || []).join(', ') || '-' }}</span>
        </div>
        <div
          v-for="c in uploadResult.checks || []"
          :key="c.item"
          class="check-row"
        >
          <span class="check-item">{{ c.item }}</span>
          <a-tag :color="c.ok ? 'green' : 'red'" size="small">{{ c.ok ? 'OK' : 'FAIL' }}</a-tag>
          <span class="check-msg" :class="c.ok ? 'env-ok' : 'env-bad'">{{ c.message }}</span>
        </div>
      </div>

      <template #footer>
        <div class="bench-modal-footer">
          <a-button
            type="link"
            size="small"
            :loading="uploading"
            :disabled="!uploadFile"
            @click="submitUpload"
          >
            {{ t('benchUploadApply') }}
          </a-button>
          <a-button type="link" size="small" @click="uploadOpen = false">{{ t('cancel') }}</a-button>
        </div>
      </template>
    </a-modal>

    <!-- Engine Comparison：对比表 -->
    <a-modal v-model:open="compareOpen" class="bench-modal">
      <template #title>
        <div class="bench-modal-head">
          <span class="bench-modal-title">{{ t('benchCompareTable') }}</span>
          <span class="bench-modal-hint">{{ t('benchCompareHint') }}</span>
        </div>
      </template>

      <div v-if="benchComparison.length" class="bench-compare">
        <table class="compare-table">
          <thead>
            <tr>
              <th class="compare-dim"></th>
              <th v-for="eng in benches" :key="eng.id">{{ benchName(eng) }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in benchComparison" :key="row.dimension">
              <td class="compare-dim">{{ compTitle(row) }}</td>
              <td v-for="eng in benches" :key="eng.id">{{ compValue(row, eng.id) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <a-empty v-else :description="t('noData')" />

      <template #footer>
        <div class="bench-modal-footer">
          <a-button type="link" size="small" @click="compareOpen = false">{{ t('cancel') }}</a-button>
        </div>
      </template>
    </a-modal>

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
  CloudDownloadOutlined, ThunderboltOutlined,
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
// Bench 引擎
const benches = ref([])
const benchComparison = ref([])
const defaultEngineId = ref('benchscope')
const benchesLoading = ref(false)
// 引擎定义 yaml（查看 / 编辑，用户可扩展引擎与版本）

// 自定义引擎（Create：教程 + 上游链接 + 可复制提示词；Upload：上传引擎包）
const authoring = ref({})
const createOpen = ref(false)
const uploadOpen = ref(false)
const compareOpen = ref(false)
// 引擎包上传
const uploadFile = ref(null)
const uploadName = ref('')
const uploading = ref(false)
const uploadResult = ref(null)
// Datasets 左侧分类
const datasetCats = ref([])
const activeDsCat = ref('all')
// Models 厂商目录
const catalogLoading = ref(false)
const modelGroups = ref([])
const collapsedGroups = ref([])
const selectedProvider = ref(null)

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
  { key: 'models', icon: DatabaseOutlined, label: t('modelsTab') },
  { key: 'datasets', icon: CloudDownloadOutlined, label: t('datasetsTab') },
  { key: 'benches', icon: ThunderboltOutlined, label: t('benchesTab') },
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
    loadModelCatalog()
    loadBenches()
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
    datasetCats.value = resp.categories || []
  } catch {
    datasets.value = []
  } finally {
    datasetsLoading.value = false
  }
}

// ---- Bench 引擎 ----
async function loadBenches() {
  benchesLoading.value = true
  try {
    const resp = await api.getBenchEngines()
    benches.value = resp.engines || []
    benchComparison.value = resp.comparison || []
    defaultEngineId.value = resp.default_engine_id || 'benchscope'
    await loadAuthoring()
  } catch {
    benches.value = []
    benchComparison.value = []
  } finally {
    benchesLoading.value = false
  }
}

// 自定义引擎开发指引（提示词 + 上游链接）
async function loadAuthoring() {
  try {
    authoring.value = await api.getBenchAuthoring() || {}
  } catch {
    authoring.value = {}
  }
}

// 复制 AI 提示词
async function copyPrompt() {
  const text = authoring.value?.prompt || ''
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    message.success(t('benchCopySuccess'))
  } catch {
    message.warning(t('benchCopyFail'))
  }
}

// ---- 引擎文案双语（英文默认，*_zh 为中文） ----
function benchName(eng) {
  return locale.value === 'zh' ? eng?.name_zh || eng?.name : eng?.name
}
function benchDesc(eng) {
  return locale.value === 'zh' ? eng?.description_zh || eng?.description : eng?.description
}
function benchHighlights(eng) {
  return locale.value === 'zh'
    ? eng?.highlights_zh || eng?.highlights || []
    : eng?.highlights || []
}
function compTitle(row) {
  return locale.value === 'zh' ? row?.dimension_zh || row?.dimension : row?.dimension
}
function compValue(row, id) {
  return locale.value === 'zh'
    ? row?.values_zh?.[id] || row?.values?.[id] || '-'
    : row?.values?.[id] || '-'
}

// ---- Create Engine 弹窗 ----
const createSteps = computed(() => [
  t('benchTutorialStep1'),
  t('benchTutorialStep2'),
  t('benchTutorialStep3'),
  t('benchTutorialStep4'),
])

async function openCreate() {
  if (!authoring.value?.prompt) await loadAuthoring()
  createOpen.value = true
}

// ---- Upload Engine 弹窗 ----
function openUpload() {
  uploadResult.value = null
  uploadOpen.value = true
}

function beforeUploadEngine(file) {
  const name = (file?.name || '').toLowerCase()
  if (!name.endsWith('.yaml') && !name.endsWith('.yml') && !name.endsWith('.tar.gz') && !name.endsWith('.tgz')) {
    message.warning(t('benchUploadTypeWarn'))
    return false
  }
  uploadFile.value = file
  uploadName.value = file.name
  uploadResult.value = null
  return false // 阻止自动上传，由「导入」按钮触发
}

function clearUpload() {
  uploadFile.value = null
  uploadName.value = ''
  uploadResult.value = null
}

async function submitUpload() {
  if (!uploadFile.value) return
  uploading.value = true
  try {
    const resp = await api.uploadBenchEngine(uploadFile.value)
    uploadResult.value = {
      ok: true,
      added: resp.added || [],
      updated: resp.updated || [],
      checks: resp.checks || [],
    }
    message.success(t('benchUploadSuccess'))
    await loadBenches()
    clearUpload()
  } catch (e) {
    const detail = e?.response?.data?.detail
    uploadResult.value = { ok: false, added: [], updated: [], checks: detail?.checks || [] }
    message.error(detail || t('benchUploadFail'))
  } finally {
    uploading.value = false
  }
}

// ---- Models 厂商目录 ----
async function loadModelCatalog() {
  catalogLoading.value = true
  try {
    const resp = await api.getModelCatalog()
    modelGroups.value = resp.groups || []
    // 默认展开全部组，选中第一个厂商
    collapsedGroups.value = []
    const first = modelGroups.value[0]?.providers?.[0]
    if (first) selectedProvider.value = first
  } catch {
    modelGroups.value = []
  } finally {
    catalogLoading.value = false
  }
}

function groupName(g) {
  return locale.value === 'zh' ? g.name_zh : g.name_en
}

function toggleGroup(key) {
  const i = collapsedGroups.value.indexOf(key)
  if (i >= 0) collapsedGroups.value.splice(i, 1)
  else collapsedGroups.value.push(key)
}

function isCollapsed(key) {
  return collapsedGroups.value.includes(key)
}

function selectProvider(p) {
  selectedProvider.value = p
}

function matchCatalog(modelName) {
  const name = String(modelName || '').toLowerCase()
  return modelCatalog.find((m) => m.name.toLowerCase() === name || m.id.toLowerCase() === name) || null
}

function openProviderModel(modelName) {
  const hit = matchCatalog(modelName)
  if (hit) openModel(hit)
}

// ---- Datasets 分类 ----
function catName(c) {
  return locale.value === 'zh' ? c.name_zh : c.name_en
}

function catCount(key) {
  return datasets.value.filter((d) => d.category === key).length
}

const filteredDatasets = computed(() => {
  if (activeDsCat.value === 'all') return datasets.value
  return datasets.value.filter((d) => d.category === activeDsCat.value)
})

// ---- Cache Paths 双语 ----
function dirLabel(d) {
  return locale.value === 'zh' ? d.label_zh || d.label : d.label_en || d.label
}

function dirDesc(d) {
  return locale.value === 'zh' ? d.desc_zh || d.desc : d.desc_en || d.desc
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

<style scoped>.settings-page{
  display: flex;
  height: 100%;
  overflow: hidden;
  background: var(--ant-color-bg-container, #fff);
}/* ===== 左侧菜单 ===== */.settings-sidebar{
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid var(--ant-color-border, #f0f0f0);
  background: var(--ant-color-bg-layout, #fafafa);
  padding: 24px 12px;
}.sidebar-title{
  font-size: 20px;
  font-weight: 700;
  color: var(--ant-color-text, #333);
  padding: 0 12px 20px;
}.sidebar-menu{
  display: flex;
  flex-direction: column;
  gap: 4px;
}.menu-item{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  color: var(--ant-color-text-secondary, #555);
  transition: all 0.2s;
}.menu-item:hover{
  background: var(--ant-color-fill-secondary, #f0f0f0);
  color: var(--ant-color-text, #333);
}.menu-item.active{
  background: var(--ant-color-primary-bg, #e6f4ff);
  color: var(--ant-color-primary, #1677ff);
  font-weight: 500;
}.menu-icon{
  font-size: 18px;
}/* ===== 右侧内容 ===== */.settings-content{
  flex: 1;
  overflow-y: auto;
  padding: 32px 40px 18px;
}.tab-content{
  animation: fadeIn 0.2s ease;
}/* 填满高度：内容区不自滚，由内部列表区滚动（Bench Engines） */.settings-content.content-fill{
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 22px;
  padding-bottom: 18px;
}.settings-content.content-fill > .bench-tab{
  flex: 1;
  min-height: 0;
}/* a-spin 包裹层必须传递高度约束，否则内部滚动容器拿不到限高而无法滚动 */.settings-content.content-fill :deep(.ant-spin-nested-loading),
.settings-content.content-fill :deep(.ant-spin-container){
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}/* 窄面板（General / Environment / Plugins）：减小面板宽度，滚动条保持在页面最右侧 */.tab-content.narrow{
  max-width: 720px;
}@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}.panel-card{
  margin-bottom: 20px;
  border-radius: 12px;
}.panel-row{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
}.panel-row + .panel-row{
  border-top: 1px solid var(--ant-color-border, #f0f0f0);
}.panel-label{
  font-size: 12px;
  color: var(--ant-color-text, #333);
  font-weight: 500;
}.field-desc{
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
}/* ===== Cache Paths 目录管理 ===== */.running-tag{
  margin-left: 8px;
}.dir-row{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}.dir-info{
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}.dir-label{
  font-size: 13px;
  font-weight: 600;
  color: var(--ant-color-text, #333);
}.dir-right{
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}.dir-input{
  width: 340px;
}.dir-value{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--ant-color-primary, #1677ff);
  font-weight: 500;
  cursor: default;
  user-select: text;
}.dir-value.editable{
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: rgba(22, 119, 255, 0.35);
  text-underline-offset: 3px;
}.dir-value.editable:hover{
  color: var(--ant-color-primary-hover, #4096ff);
}/* ===== 迁移进度弹窗 ===== */.migrate-box{
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 12px 8px;
}.migrate-title{
  font-size: 15px;
  font-weight: 600;
  color: var(--ant-color-text, #333);
}.migrate-msg{
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
  word-break: break-all;
}.section-desc{
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
  margin: 0 0 24px;
}/* ===== Environment ===== */.env-status{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
}.env-dot{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ant-color-text-quaternary, #d9d9d9);
}.env-status.ok .env-dot{ background: #52c41a; }.env-status.bad .env-dot{ background: #ff4d4f; }.env-models{
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
}.env-footer{
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--ant-color-border, #f0f0f0);
}/* ===== Models / Datasets 副侧边栏布局 ===== */.catalog-layout{
  display: flex;
  align-items: flex-start;
  gap: 0;
  border: 1px solid var(--ant-color-border, #e8e8e8);
  border-radius: 12px;
  overflow: hidden;
}.catalog-sidebar{
  width: 210px;
  flex-shrink: 0;
  border-right: 1px solid var(--ant-color-border, #f0f0f0);
  background: var(--ant-color-bg-layout, #fafafa);
  max-height: calc(100vh - 220px);
  overflow-y: auto;
  padding: 8px 0;
}.catalog-group{
  margin-bottom: 4px;
}.catalog-group-title{
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ant-color-text, #333);
}.catalog-group-title.clickable{
  cursor: pointer;
  user-select: none;
}.catalog-group-title.clickable:hover{
  background: var(--ant-color-fill-secondary, #f0f0f0);
}.group-caret{
  display: inline-block;
  font-size: 10px;
  transition: transform 0.2s;
  color: var(--ant-color-text-tertiary, #999);
}.group-caret.collapsed{
  transform: rotate(90deg);
}.catalog-items{
  padding-bottom: 6px;
}.catalog-item{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 14px 7px 30px;
  font-size: 13px;
  color: var(--ant-color-text-secondary, #555);
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}.catalog-item:hover{
  background: var(--ant-color-fill-secondary, #f0f0f0);
  color: var(--ant-color-text, #333);
}.catalog-item.active{
  background: var(--ant-color-primary-bg, #e6f4ff);
  color: var(--ant-color-primary, #1677ff);
  font-weight: 500;
}.catalog-count{
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
  flex-shrink: 0;
}.catalog-item.active .catalog-count{
  color: var(--ant-color-primary, #1677ff);
}.catalog-content{
  flex: 1;
  min-width: 0;
  padding: 16px 20px;
}/* 厂商模型列表 */.provider-head{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}.provider-title{
  margin: 0;
  font-size: 16px;
}.provider-homepage{
  font-size: 12px;
}.provider-models{
  display: flex;
  flex-direction: column;
  gap: 8px;
}.provider-model-item{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid var(--ant-color-border, #e8e8e8);
  border-radius: 8px;
  background: var(--ant-color-bg-container, #fff);
  transition: all 0.15s;
}.provider-model-item:hover{
  border-color: var(--ant-color-primary, #1677ff);
}.provider-model-item.clickable{
  cursor: pointer;
}.pm-name{
  font-size: 13px;
  font-weight: 500;
  color: var(--ant-color-text, #333);
}/* ===== Datasets 行式数据集 ===== */.ds-row-item{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--ant-color-border-secondary, #f0f0f0);
}.ds-row-item:last-child{
  border-bottom: none;
}.ds-row-main{
  flex: 1;
  min-width: 0;
}.ds-row-head{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}.ds-row-links{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 2px 0;
  font-size: 12px;
}.ds-row-links.column{
  flex-direction: column;
  align-items: flex-start;
}.ds-row-actions{
  flex-shrink: 0;
  padding-top: 2px;
}/* ===== 模型详情抽屉 ===== */.model-detail{
  padding: 8px 4px;
}.detail-logo{
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
}.detail-name{
  margin: 0 0 4px;
  font-size: 20px;
}.detail-org{
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
  margin-bottom: 12px;
}.detail-intro{
  font-size: 12px;
  line-height: 1.7;
  color: var(--ant-color-text, #333);
  margin-bottom: 16px;
}.detail-row{
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid var(--ant-color-border, #f0f0f0);
}.detail-row.column{
  flex-direction: column;
  align-items: flex-start;
}.detail-label{
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
  flex-shrink: 0;
  min-width: 88px;
}.detail-tags{
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}.detail-link{
  font-size: 13px;
  word-break: break-all;
}.download-cmd{
  font-size: 12px;
  word-break: break-all;
}.drawer-footer{
  display: flex;
  justify-content: flex-end;
}/* ===== Datasets 内置数据集 ===== */.ds-list{
  display: flex;
  flex-direction: column;
  gap: 12px;
}.ds-card{
  border: 1px solid var(--ant-color-border, #e8e8e8);
  border-radius: 10px;
  padding: 14px 16px;
  background: var(--ant-color-bg-container, #fff);
}.ds-head{
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}.ds-name{
  font-size: 14px;
  font-weight: 600;
  color: var(--ant-color-text, #333);
}.ds-status{
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
  border: 1px solid var(--ant-color-border-secondary, #d9d9d9);
  border-radius: 8px;
  padding: 0 8px;
  line-height: 18px;
}.ds-status.cached{
  color: var(--ant-color-success, #52c41a);
  border-color: #95de64;
}.ds-desc{
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
  margin: 0 0 8px;
}.ds-row{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 4px 0;
  font-size: 12px;
}.ds-row.column{
  flex-direction: column;
  align-items: flex-start;
}.ds-label{
  color: var(--ant-color-text-tertiary, #999);
  flex-shrink: 0;
  min-width: 64px;
}.ds-link{
  word-break: break-all;
  font-size: 12px;
}.ds-cmd{
  font-size: 12px;
  word-break: break-all;
}.ds-footer{
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}/* ---------------- Bench 引擎面板 ---------------- *//* 整页即引擎列表：顶部操作栏固定，列表区可滑动 */.bench-tab{
  display: flex;
  flex-direction: column;
  min-height: 0;
}.bench-topbar{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--ant-color-border-secondary, #f0f0f0);
}.bench-topbar-left{
  min-width: 0;
}.bench-tab-title{
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 600;
}.bench-actions{
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}/* 右上角文字按钮 */.bench-text-btn{
  padding: 0 8px;
  font-size: 12.5px;
  height: 24px;
}.bench-list-scroll{
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 2px 8px;
}/* 弹窗内区块 */:global(.bench-modal-desc){
  font-size: 12.5px;
  color: var(--ant-color-text-tertiary, #8c8c8c);
  margin: 0 0 12px;
  line-height: 1.7;
}/* 弹框宽度统一为 1/2 浏览器宽度（设上下限保证可用性）
   注意：a-modal 的 class 直接落在 .ant-modal 上，故选择器为 .bench-modal 本身；
   弹框被 Teleport 到 body，不带本组件 data-v 属性，故规则必须用 :global() */:global(.bench-modal){
  width: 50vw !important;
  min-width: 480px;
  max-width: 960px;
}/* header：标题 + 提示文案 */:global(.bench-modal-head){
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-right: 24px;
}:global(.bench-modal-title){
  font-size: 15px;
  font-weight: 600;
  line-height: 1.4;
}:global(.bench-modal-hint){
  font-size: 12px;
  font-weight: 400;
  color: var(--ant-color-text-tertiary, #8c8c8c);
  line-height: 1.5;
}/* footer：文字操作按钮，右对齐 */:global(.bench-modal-footer){
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
}:global(.bench-ol){
  margin: 6px 0 0;
  padding-left: 20px;
  font-size: 12.5px;
  line-height: 1.9;
  color: var(--ant-color-text-secondary, #666);
}:global(.upload-file){
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  font-size: 12.5px;
}:global(.upload-name){
  font-family: 'SFMono-Regular', Consolas, monospace;
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
  word-break: break-all;
}.bench-list{
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}.bench-card{
  border: 1px solid var(--ant-color-border-secondary, #f0f0f0);
  border-radius: 8px;
  padding: 12px 14px;
  background: var(--ant-color-bg-container, #fff);
}.bench-card.bench-default{
  border-color: var(--ant-color-primary, #1677ff);
}.bench-head{
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}.bench-name{
  font-size: 14px;
  font-weight: 600;
}.bench-meta{
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  margin-bottom: 6px;
}:global(.bench-label){
  color: var(--ant-color-text-tertiary, #999);
  font-size: 12px;
  flex-shrink: 0;
}.bench-value{
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
}.bench-desc{
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
  margin: 0 0 8px;
  line-height: 1.6;
}.bench-highlights{
  margin-bottom: 8px;
}:global(.bench-ul){
  margin: 4px 0 0;
  padding-left: 18px;
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
  line-height: 1.7;
}.bench-env{
  border-top: 1px dashed var(--ant-color-border-secondary, #f0f0f0);
  padding-top: 8px;
}.bench-env-none{
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
  border-top: 1px dashed var(--ant-color-border-secondary, #f0f0f0);
  padding-top: 8px;
}.bench-env-table{
  margin-top: 4px;
}.bench-env-row{
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  padding: 2px 0;
  flex-wrap: wrap;
}.env-name{
  min-width: 70px;
  font-weight: 500;
}.env-req,
.env-installed{
  color: var(--ant-color-text-secondary, #666);
}:global(.env-ok){
  color: var(--ant-color-success, #52c41a);
}:global(.env-bad){
  color: var(--ant-color-error, #ff4d4f);
}.bench-hint{
  font-size: 11px;
  color: var(--ant-color-warning, #faad14);
  margin-top: 2px;
  word-break: break-all;
}:global(.bench-compare){
  margin-top: 4px;
}.compare-title{
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 8px;
}:global(.compare-table){
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}:global(.compare-table th), :global(.compare-table td){
  border: 1px solid var(--ant-color-border-secondary, #f0f0f0);
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
}:global(.compare-table th){
  background: var(--ant-color-fill-tertiary, #fafafa);
  font-weight: 600;
}:global(.compare-table td.compare-dim), :global(.compare-table th.compare-dim){
  background: var(--ant-color-fill-tertiary, #fafafa);
  color: var(--ant-color-text-secondary, #666);
  white-space: nowrap;
  width: 130px;
}/* 添加自定义引擎（提示词 / 上游链接 / 导入校验） */.bench-add{
  margin-top: 16px;
  padding: 12px 14px;
  border: 1px solid var(--ant-color-primary-border, #91caff);
  border-radius: 8px;
  background: var(--ant-color-primary-bg, #e6f4ff);
}.bench-add-head{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}.bench-add-body{
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 8px;
}:global(.add-block){
  background: var(--ant-color-bg-container, #fff);
  border-radius: 6px;
  padding: 10px 12px;
}:global(.add-block-head){
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 4px;
}:global(.add-hint){
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
  margin: 4px 0 0;
  line-height: 1.6;
  word-break: break-all;
}:global(.add-actions){
  display: flex;
  gap: 8px;
  margin-top: 8px;
}:global(.import-result){
  margin-top: 8px;
  border-top: 1px dashed var(--ant-color-border-secondary, #f0f0f0);
  padding-top: 6px;
}:global(.check-row){
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  padding: 2px 0;
  flex-wrap: wrap;
}:global(.check-item){
  min-width: 92px;
  font-weight: 500;
}:global(.check-msg){
  color: var(--ant-color-text-secondary, #666);
  word-break: break-all;
}.bench-hint-ok{
  font-size: 11px;
  color: var(--ant-color-success, #52c41a);
  margin-top: 4px;
}/* 引擎定义 yaml（查看 / 编辑） */.bench-yaml{
  margin-top: 16px;
  border-top: 1px solid var(--ant-color-border-secondary, #f0f0f0);
  padding-top: 12px;
}.bench-yaml-head{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}.bench-yaml-desc{
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
  margin: 4px 0 8px;
  line-height: 1.6;
}:global(.bench-yaml-view){
  max-height: 260px;
  overflow: auto;
  background: var(--ant-color-fill-tertiary, #fafafa);
  border: 1px solid var(--ant-color-border-secondary, #f0f0f0);
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 11px;
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}.bench-yaml-editor{
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 11px;
  line-height: 1.6;
}</style>

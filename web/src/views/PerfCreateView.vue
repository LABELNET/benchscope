<template>
  <div class="perf-create-page">
    <div class="create-panel">
      <!-- 面板 header：左=返回箭头+标题，右=Mode 标识 -->
      <div class="panel-header">
        <div class="header-left">
          <a-button type="text" class="back-btn" @click="goBack">
            <template #icon><arrow-left-outlined /></template>
          </a-button>
          <span class="header-title">{{ t('perfCreateTitle') }}</span>
        </div>
        <div class="header-right">
          <span class="mode-tag">{{ mode === 'threshold' ? t('thresholdMode') : t('concurrencyMode') }}</span>
        </div>
      </div>

      <!-- Step 低于面板 header -->
      <div class="step-bar">
        <a-steps :current="step - 1" size="small" class="step-nav">
          <a-step :title="t('stepCondition')" />
          <a-step :title="t('stepParams')" />
          <a-step :title="t('stepLaunch')" />
        </a-steps>
      </div>

      <!-- Step 1: 性能条件 -->
      <div v-show="step === 1" class="panel-body">
        <!-- 引擎选择 + 环境校验（原生引擎环境不满足时禁止进入下一步） -->
        <div class="bench-picker">
          <div class="bench-picker-head">
            <span class="bench-picker-label">{{ t('benchSelectLabel') }}</span>
            <a-select
              v-model:value="engineId"
              size="small"
              style="width: 260px"
              :options="engineOptions"
              @change="onEngineChange"
            />
            <a-spin v-if="envChecking" size="small" />
            <a-tag v-else-if="envResult" :color="envResult.ok ? 'green' : 'red'" size="small">
              {{ envResult.ok ? t('benchEnvReady') : t('benchEnvMissing') }}
            </a-tag>
          </div>
          <p class="bench-picker-desc">{{ t('benchSelectDesc') }}</p>
          <p v-if="selectedEngine?.description" class="bench-picker-desc bench-engine-desc">
            {{ selectedEngine.description }}
          </p>
          <!-- 环境校验明细（原生引擎） -->
          <div v-if="envResult && !envResult.ok && envResult.checks?.length" class="bench-env-detail">
            <div v-for="c in envResult.checks" :key="c.name" class="bench-env-row">
              <span class="env-name">{{ c.name }}</span>
              <span class="env-req">{{ t('benchRequiredVersion') }}: {{ c.required }}</span>
              <span class="env-installed">
                {{ t('benchInstalled') }}:
                <span :class="c.ok ? 'env-ok' : 'env-bad'">{{ c.installed || t('benchNotInstalled') }}</span>
              </span>
              <a-tag :color="c.ok ? 'green' : 'red'" size="small">{{ c.ok ? 'OK' : 'FAIL' }}</a-tag>
            </div>
            <div v-for="c in envResult.checks.filter((x) => !x.ok && x.hint)" :key="`h-${c.name}`" class="bench-hint">
              {{ t('benchInstallHint') }}: {{ c.hint }}
            </div>
          </div>
        </div>
        <BaseEnvPanel
          v-model:model="model"
          :framework="framework"
          :base-url="baseUrl"
          :models="modelOptions"
          :inference="inference"
          :loading="modelsLoading"
          @model-change="onModelChange"
          @refresh="loadModels"
          @go-settings="goSettings"
        />
        <ConditionPanel
          :mode="mode"
          :conditions="conditions"
          @add="addCondition"
          @remove="removeCondition"
        />
      </div>

      <!-- Step 2: 性能参数（跟随 Step1 所选引擎，只显示该引擎的参数） -->
      <div v-show="step === 2" class="panel-body">
        <div class="params-engine">
          <span class="params-engine-label">{{ t('benchSelectedEngine') }}</span>
          <a-tag :color="selectedEngine?.kind === 'builtin' ? 'purple' : 'cyan'" size="small">
            {{ engineName }}
          </a-tag>
          <span v-if="selectedEngine?.version" class="params-engine-meta">
            v{{ selectedEngine.version }}
          </span>
        </div>
        <p class="params-engine-desc">{{ t('paramsEngineHint').replace('{engine}', engineName) }}</p>
        <a-spin :spinning="paramsLoading">
          <ParamGroupPanel
            v-if="engineParams.lines?.length"
            :version="engineParams.version"
            :version-label="t('benchParamsVersion')"
            :lines="engineParams.lines"
            :specs="paramSpecs"
            @save="syncEngineParams"
            @update:version="(v) => { engineParams.version = v; syncEngineParams() }"
          />
          <a-empty v-else :description="t('noData')" />
        </a-spin>
      </div>

      <!-- Step 3: 启动测试 -->
      <div v-show="step === 3" class="panel-body">
        <div class="launch-block">
          <div class="launch-head">
            <span class="launch-title">{{ t('previewConditionsTitle') }}</span>
          </div>
          <pre class="cond-text">{{ previewConditions || t('loading') }}</pre>
        </div>
        <div class="launch-block">
          <div class="launch-head">
            <span class="launch-title">{{ t('previewCommandTitle') }}</span>
            <a-tag :color="selectedEngine?.kind === 'builtin' ? 'purple' : 'cyan'" size="small">
              {{ engineName }}
            </a-tag>
            <a-button size="small" type="text" :disabled="!previewCommand" @click="copyCommand">
              {{ t('copy') }}
            </a-button>
          </div>
          <pre class="cmd-text">{{ previewCommand || t('loading') }}</pre>
          <div v-if="selectedEngine?.kind === 'builtin'" class="cmd-hint">{{ t('commandHintBuiltin') }}</div>
          <div v-else-if="mode === 'threshold'" class="cmd-hint">{{ t('commandHint') }}</div>
        </div>
      </div>

      <!-- footer 操作按钮：右侧 -->
      <div class="panel-footer">
        <a-space>
          <a-button size="small" @click="cancel">{{ t('cancel') }}</a-button>
          <template v-if="step === 1">
            <a-button size="small" type="primary" :loading="step1Saving" @click="nextToParams">{{ t('nextStep') }}</a-button>
          </template>
          <template v-else-if="step === 2">
            <a-button size="small" @click="step = 1">{{ t('prev') }}</a-button>
            <a-button size="small" type="primary" :loading="step2Saving" @click="nextToLaunch">{{ t('nextStep') }}</a-button>
          </template>
          <template v-else>
            <a-button size="small" type="primary" :loading="submitting" @click="submit">{{ t('launch') }}</a-button>
          </template>
        </a-space>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeftOutlined } from '@ant-design/icons-vue'
import { api } from '@/api'
import { useConfigStore } from '@/store/config'
import { useTestStore } from '@/store/test'
import { t, i18nState } from '@/i18n'
import BaseEnvPanel from '@/components/performance/BaseEnvPanel.vue'
import ConditionPanel from '@/components/performance/ConditionPanel.vue'
import ParamGroupPanel from '@/components/performance/ParamGroupPanel.vue'

const route = useRoute()
const router = useRouter()
const config = useConfigStore()
const test = useTestStore()

const mode = computed(() => (route.query.mode === 'threshold' ? 'threshold' : 'concurrency'))
const step = ref(1)

// framework 改由所选引擎决定（Environment 不再单独配置框架）
const framework = computed(() => selectedEngine.value?.framework || config.config?.framework || 'vllm')

// 引擎显示名（英文默认，中文取 name_zh）
const engineName = computed(() => {
  const e = selectedEngine.value
  return (i18nState.locale === 'zh' ? e?.name_zh || e?.name : e?.name) || engineId.value
})
const frameworkName = computed(() => (framework.value === 'sglang' ? 'SGLang' : 'vLLM'))
const baseUrl = computed(() => config.config?.api?.base_url || '')
const inference = computed(() => config.status?.inference || 'offline')
const modelsLoading = ref(false)
const model = ref('')
const modelOptions = ref([])

// 条件组
let seq = 0
const conditions = ref([
  {
    id: ++seq,
    inputLen: 1024,
    outputLen: 1024,
    dataset: 'Random',
    requestRates: [1, 2, 4, 8, 16, 32, 40, 64, 128],
    rateMode: 'inf',
    ttftStatistic: 'mean',
    ttftThreshold: 0,
    tpotStatistic: 'mean',
    tpotThreshold: 100,
    outThroughput: 0,
  },
])

// Step2 参数 yaml（跟随 Step1 所选引擎：每个引擎一套参数，互不干扰）
const engineParams = ref({ version: '', lines: [], content: '' })
const paramsLoading = ref(false)

// ---- Bench 引擎选择 + 环境校验 ----
const engineId = ref('benchscope')
const engines = ref([])
const defaultEngineId = ref('benchscope')
const envResult = ref(null)
const envChecking = ref(false)
// 引擎参数定义（下拉选项 + 描述信息）
const paramSpecs = ref({})

const engineOptions = computed(() =>
  engines.value.map((e) => ({ value: e.id, label: `${e.name}（${e.kind}${e.version && e.version !== 'stable' ? ' ' + e.version : ''}）` }))
)
const selectedEngine = computed(() => engines.value.find((e) => e.id === engineId.value) || null)

async function loadEngines() {
  try {
    const resp = await api.getBenchEngines()
    engines.value = resp.engines || []
    defaultEngineId.value = resp.default_engine_id || 'benchscope'
    if (!engines.value.some((e) => e.id === engineId.value)) {
      engineId.value = defaultEngineId.value
    }
    await checkEngineEnv()
    await loadParamSpecs()
    await loadEngineParams()
  } catch {
    engines.value = []
    envResult.value = null
    paramSpecs.value = {}
    engineParams.value = { version: '', lines: [], content: '' }
  }
}

async function loadParamSpecs() {
  if (!engineId.value) {
    paramSpecs.value = {}
    return
  }
  try {
    const resp = await api.getBenchParams(engineId.value)
    paramSpecs.value = resp.params || {}
  } catch {
    paramSpecs.value = {}
  }
}

// 引擎参数清单（Step2：只显示当前引擎的参数）
async function loadEngineParams() {
  if (!engineId.value) {
    engineParams.value = { version: '', lines: [], content: '' }
    return
  }
  paramsLoading.value = true
  try {
    const resp = await api.getBenchParamsYaml(engineId.value)
    engineParams.value = {
      version: resp.version || '',
      lines: resp.lines || [],
      content: resp.content || '',
    }
  } catch {
    engineParams.value = { version: '', lines: [], content: '' }
  } finally {
    paramsLoading.value = false
  }
}

async function checkEngineEnv() {
  if (!engineId.value) return
  envChecking.value = true
  try {
    const resp = await api.checkBenchEnv(engineId.value)
    envResult.value = { ok: !!resp.ok, checks: resp.checks || [] }
  } catch {
    envResult.value = null
  } finally {
    envChecking.value = false
  }
}

// 切换引擎 → 环境校验、参数定义、参数清单三者同步刷新（后续步骤跟随当前引擎）
function onEngineChange() {
  checkEngineEnv()
  loadParamSpecs()
  loadEngineParams()
}

// Step3 预览：任务详情文本 + 示例命令
const previewCommand = ref('')
const step1Saving = ref(false)
const step2Saving = ref(false)
const submitting = ref(false)

const previewConditions = computed(() => {
  const lines = []
  lines.push(`${t('benchSelectedEngine')}: ${engineName.value}`)
  lines.push(`${t('frameworkLabel')}: ${frameworkName.value}`)
  lines.push(`${t('modelLabel')}: ${model.value || '-'}`)
  lines.push(`${t('baseUrlLabel')}: ${baseUrl.value || '-'}`)
  const ds = conditions.value
    .map((c) => `${c.dataset} ${c.inputLen}x${c.outputLen}`)
    .join(', ')
  lines.push(`${t('datasetLabel')}: ${ds || '-'}`)
  if (mode.value === 'concurrency') {
    const g = conditions.value[0]
    lines.push(`${t('requestCounts')}: [${(g?.requestRates || []).join(', ')}]`)
    lines.push(`${t('requestRate')}: ${g?.rateMode === 'follow' ? 'Follow' : 'Inf'}`)
  } else {
    const g = conditions.value[0]
    const statLabel = (s) => (s === 'median' ? t('median') : s === 'p99' ? t('p99') : t('mean'))
    lines.push(`${t('requestRate')}: ${g?.rateMode === 'follow' ? 'Follow' : 'Inf'}`)
    lines.push(`${t('ttftThresholdLabel')} (${statLabel(g?.ttftStatistic)}): ≤ ${g?.ttftThreshold ?? 0} ms`)
    lines.push(`${t('tpotThresholdLabel')} (${statLabel(g?.tpotStatistic)}): ≤ ${g?.tpotThreshold ?? 0} ms`)
    lines.push(`${t('outputThroughputLabel')}: ≤ ${g?.outThroughput ?? 0} tok/s`)
  }
  return lines.join('\n')
})

function addCondition() {
  const last = conditions.value[conditions.value.length - 1]
  conditions.value.push({
    id: ++seq,
    inputLen: last?.inputLen || 1024,
    outputLen: last?.outputLen || 1024,
    dataset: 'Random',
    requestRates: last ? [...last.requestRates] : [1, 2, 4, 8, 16, 32, 40, 64, 128],
    rateMode: 'inf',
    ttftStatistic: 'mean',
    ttftThreshold: 0,
    tpotStatistic: 'mean',
    tpotThreshold: 100,
    outThroughput: 0,
  })
}

function removeCondition(idx) {
  conditions.value.splice(idx, 1)
}

async function loadModels() {
  modelsLoading.value = true
  try {
    const resp = await api.getModels()
    modelOptions.value = resp.models || []
    if (!model.value && modelOptions.value.length) {
      model.value = modelOptions.value[0]
    }
  } catch (e) {
    message.error(e.message || '加载模型列表失败')
    modelOptions.value = []
  } finally {
    modelsLoading.value = false
  }
}

function onModelChange() {
  config.refreshStatus()
}

// 引擎参数仅在内存中修改（不写入 yaml 文件），修改结果用于预览命令与任务执行
function buildEngineParamsContent() {
  const p = engineParams.value
  const body = (p.lines || []).map((l) => `${l.key}: ${l.value}`).join('\n')
  return `version: ${p.version || ''}\n${body ? body + '\n' : ''}`
}

function syncEngineParams() {
  engineParams.value.content = buildEngineParamsContent()
}

async function copyCommand() {
  if (!previewCommand.value) return
  try {
    await navigator.clipboard.writeText(previewCommand.value)
    message.success(t('copied'))
  } catch {
    message.warning(t('copyFailed'))
  }
}

// 校验 Step1
function validateStep1() {
  if (!model.value) {
    message.warning(t('selectModelWarning'))
    return false
  }
  if (!conditions.value.length) {
    message.warning(t('noCondition'))
    return false
  }
  const g = conditions.value[0]
  if (mode.value === 'concurrency' && (!g.requestRates || !g.requestRates.length)) {
    message.warning(t('requestCounts'))
    return false
  }
  if (mode.value === 'threshold') {
    // 每组独立校验：TTFT / TPOT / Output token throughput 三者不能同时为 0
    for (const c of conditions.value) {
      const tt = Number(c.ttftThreshold)
      const tp = Number(c.tpotThreshold)
      const ot = Number(c.outThroughput)
      if (
        !Number.isInteger(tt) || tt < 0 ||
        !Number.isInteger(tp) || tp < 0 ||
        !Number.isInteger(ot) || ot < 0
      ) {
        message.warning(t('thresholdRequired'))
        return false
      }
      if (tt === 0 && tp === 0 && ot === 0) {
        message.warning(t('thresholdAllZeroWarning'))
        return false
      }
    }
  }
  return true
}

async function nextToParams() {
  // 环境校验：原生引擎（vllm/sglang）环境不满足时禁止进入参数选择
  if (!envResult.value || !envResult.value.ok) {
    message.warning(t('benchEnvBlocked').replace('{name}', engineName.value))
    return
  }
  if (!validateStep1()) return
  step1Saving.value = true
  try {
    // 进入 Step2 前确保当前引擎的参数清单已就绪（切换引擎后保持同步）
    if (!engineParams.value.lines?.length) await loadEngineParams()
    syncEngineParams()
    step.value = 2
  } finally {
    step1Saving.value = false
  }
}

async function nextToLaunch() {
  step2Saving.value = true
  try {
    // 用当前引擎的最新参数生成预览命令（命令随引擎变化）
    syncEngineParams()
    await loadPreview()
    step.value = 3
  } finally {
    step2Saving.value = false
  }
}

function buildPayload() {
  const g = conditions.value[0]
  return {
    framework: framework.value,
    engine_id: engineId.value,
    model: model.value,
    tokenizer: '',
    dataset: {
      type: 'random',
      // [inputLen, outputLen, label, case_id, thresholds]：阈值信息在每组请求配置中，不跟随主任务；
      // case_id 为唯一组 id，保证相同条件（如 1024x1024）的多组不叠加
      length_pairs: conditions.value.map((c) => [
        c.inputLen, c.outputLen, `${c.inputLen}x${c.outputLen}`, c.id,
        {
          ttft_statistic: mode.value === 'threshold' ? c.ttftStatistic || 'mean' : 'mean',
          ttft_threshold_ms: mode.value === 'threshold' ? Number(c.ttftThreshold) || 0 : 0,
          tpot_statistic: mode.value === 'threshold' ? c.tpotStatistic || 'mean' : 'mean',
          tpot_threshold_ms: mode.value === 'threshold' ? Number(c.tpotThreshold) || 0 : 0,
          output_throughput_threshold: mode.value === 'threshold' ? Number(c.outThroughput) || 0 : 0,
        },
      ]),
    },
    concurrency_list: mode.value === 'threshold' ? [1] : [...(g.requestRates || [])],
    gpu: {},
    request_rate: g.rateMode === 'follow' ? 'follow' : 'inf',
    ttft_threshold_ms: mode.value === 'threshold' ? Number(g.ttftThreshold) || 0 : 0,
    ttft_statistic: mode.value === 'threshold' ? g.ttftStatistic || 'mean' : 'mean',
    tpot_threshold_ms: mode.value === 'threshold' ? Number(g.tpotThreshold) || 0 : 0,
    tpot_statistic: mode.value === 'threshold' ? g.tpotStatistic || 'mean' : 'mean',
    output_throughput_threshold: mode.value === 'threshold' ? Number(g.outThroughput) || 0 : 0,
    mode: mode.value,
    // 当前所选引擎的参数清单（自研引擎据此构造执行选项，原生引擎据此附加 --key=value）
    engine_params_yaml: buildEngineParamsContent(),
    params_yaml: {
      vllm: '',
      sglang: '',
    },
  }
}

async function loadPreview() {
  try {
    const resp = await api.previewTask(buildPayload())
    const lines = resp?.commands || []
    previewCommand.value = lines.length ? lines[0].cmd : ''
  } catch (e) {
    previewCommand.value = ''
    message.error(e.message || '生成预览命令失败')
  }
}

function cancel() {
  goBack()
}

function goBack() {
  router.push('/performance')
}

function goSettings() {
  router.push('/settings')
}

async function submit() {
  if (!validateStep1()) return
  Modal.confirm({
    title: t('startTestConfirm'),
    okText: t('launch'),
    cancelText: t('cancel'),
    onOk: async () => {
      submitting.value = true
      try {
        syncEngineParams()
        const resp = await test.createTask(buildPayload())
        await test.startTask(resp.task_id)
        test.setActiveTask(resp.task_id)
        message.success(t('startTest'))
        router.push('/performance')
      } catch (e) {
        message.error(e.message || '启动测试失败')
      } finally {
        submitting.value = false
      }
    },
  })
}

onMounted(async () => {
  if (!config.config) {
    await config.load()
  } else {
    config.refreshStatus()
  }
  await Promise.all([loadModels(), loadEngines()])
})
</script>

<style scoped>
.perf-create-page {
  height: 100%;
  width: 50%;
  min-width: 520px;
  max-width: 760px;
  margin: 0 auto;
  padding: 16px 0 40px;
  overflow-y: auto;
  overflow-x: hidden;
}
.create-panel {
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}
/* 面板 header */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 4px;
}
.back-btn {
  padding: 4px 6px;
}
.header-title {
  font-size: 16px;
  font-weight: 600;
}
.header-right {
  display: flex;
  align-items: center;
}
.mode-tag {
  display: inline-block;
  padding: 1px 10px;
  font-size: 12px;
  font-weight: 500;
  color: #1677ff;
  background: #e6f4ff;
  border-radius: 10px;
}
/* Step 低于 header */
.step-bar {
  padding: 12px 16px 4px;
}
.step-nav {
  max-width: 460px;
  margin: 0 auto;
}
/* 内容区（缩小显示） */
.panel-body {
  padding: 12px 16px 16px;
  min-height: 300px;
}
.panel-body :deep(.panel-section) {
  margin-bottom: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
}
.panel-body :deep(.section-title) {
  font-size: 13px;
}
.panel-body :deep(.env-label),
.panel-body :deep(.cond-label) {
  width: 120px;
  font-size: 12.5px;
}
.panel-body :deep(.env-value) {
  font-size: 12.5px;
}
.panel-body :deep(.env-row) {
  padding: 5px 0;
}
.panel-body :deep(.cond-row) {
  padding: 4px 0;
}
/* footer 右侧按钮 */
.panel-footer {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  background: rgba(0, 0, 0, 0.015);
}
/* Step2 参数面板：显示当前引擎（参数随引擎切换） */
.params-engine {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 4px;
  background: rgba(22, 119, 255, 0.04);
  border: 1px solid rgba(22, 119, 255, 0.12);
  border-radius: 8px;
}
.params-engine-label {
  font-size: 12px;
  font-weight: 600;
}
.params-engine-meta {
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
}
.params-engine-desc {
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
  margin: 4px 0 10px;
  line-height: 1.6;
}
/* 引擎选择 + 环境校验（Step1 顶部） */
.bench-picker {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.bench-picker-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.bench-picker-label {
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}
.bench-picker-desc {
  font-size: 11px;
  color: #999;
  margin: 6px 0 0;
  line-height: 1.6;
}
.bench-engine-desc {
  color: #666;
}
.bench-env-detail {
  margin-top: 8px;
  border-top: 1px dashed rgba(0, 0, 0, 0.08);
  padding-top: 6px;
}
.bench-env-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  padding: 2px 0;
  flex-wrap: wrap;
}
.bench-env-row .env-name {
  min-width: 64px;
  font-weight: 500;
}
.bench-env-row .env-req,
.bench-env-row .env-installed {
  color: #666;
}
.bench-env-row .env-ok {
  color: #52c41a;
}
.bench-env-row .env-bad {
  color: #ff4d4f;
}
.bench-hint {
  font-size: 11px;
  color: #faad14;
  word-break: break-all;
}

/* Step2 tabs 内容区紧凑显示 */
.panel-body :deep(.ant-tabs-nav) {
  margin-bottom: 10px;
}
.panel-body :deep(.ant-tabs-content-holder) {
  font-size: 12.5px;
}
.launch-block {
  padding: 8px 4px;
}
.launch-block + .launch-block {
  margin-top: 14px;
}
.launch-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.launch-head .ant-btn {
  margin-left: auto;
}
.launch-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
}
.cond-text {
  background: #fafafa;
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 12.5px;
  line-height: 1.8;
  overflow: auto;
  word-break: break-all;
  white-space: pre-wrap;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}
.cmd-text {
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 8px;
  padding: 14px;
  font-size: 12px;
  line-height: 1.7;
  overflow: auto;
  word-break: break-all;
  white-space: pre-wrap;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}
.cmd-hint {
  margin-top: 10px;
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
}
</style>

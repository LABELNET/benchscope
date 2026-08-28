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

      <!-- Step 2: 性能参数 -->
      <div v-show="step === 2" class="panel-body">
        <a-tabs v-model:activeKey="paramsTab" type="card" size="small">
          <a-tab-pane key="vllm" :tab="t('paramsVllm')" :disabled="framework !== 'vllm'">
            <div v-if="framework !== 'vllm'" class="params-lock">{{ t('paramsReadOnly').replace('{fw}', frameworkName) }}</div>
            <ParamGroupPanel
              v-else
              :version="paramsYaml.vllm.version"
              :version-label="versionLabel('vllm')"
              :lines="paramsYaml.vllm.lines"
              @save="syncParams('vllm')"
              @update:version="(v) => { paramsYaml.vllm.version = v; syncParams('vllm') }"
            />
          </a-tab-pane>
          <a-tab-pane key="sglang" :tab="t('paramsSglang')" :disabled="framework !== 'sglang'">
            <div v-if="framework !== 'sglang'" class="params-lock">{{ t('paramsReadOnly').replace('{fw}', frameworkName) }}</div>
            <ParamGroupPanel
              v-else
              :version="paramsYaml.sglang.version"
              :version-label="versionLabel('sglang')"
              :lines="paramsYaml.sglang.lines"
              @save="syncParams('sglang')"
              @update:version="(v) => { paramsYaml.sglang.version = v; syncParams('sglang') }"
            />
          </a-tab-pane>
        </a-tabs>
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
          </div>
          <pre class="cmd-text">{{ previewCommand || t('loading') }}</pre>
          <div v-if="mode === 'threshold'" class="cmd-hint">{{ t('commandHint') }}</div>
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
import { t } from '@/i18n'
import BaseEnvPanel from '@/components/performance/BaseEnvPanel.vue'
import ConditionPanel from '@/components/performance/ConditionPanel.vue'
import ParamGroupPanel from '@/components/performance/ParamGroupPanel.vue'

const route = useRoute()
const router = useRouter()
const config = useConfigStore()
const test = useTestStore()

const mode = computed(() => (route.query.mode === 'threshold' ? 'threshold' : 'concurrency'))
const step = ref(1)
const paramsTab = ref('vllm')

const framework = computed(() => config.config?.framework || 'vllm')
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

// Step2 参数 yaml
const paramsYaml = ref({ vllm: { version: '', lines: [], content: '' }, sglang: { version: '', lines: [], content: '' } })

// Step3 预览：任务详情文本 + 示例命令
const previewCommand = ref('')
const step1Saving = ref(false)
const step2Saving = ref(false)
const submitting = ref(false)

const previewConditions = computed(() => {
  const lines = []
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

function versionLabel(fw) {
  return fw === 'sglang' ? t('sglangVersionLabel') : t('vllmVersionLabel')
}

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

async function loadParamsYaml() {
  for (const fw of ['vllm', 'sglang']) {
    try {
      const resp = await api.getParamsYaml(fw)
      // 防御性去重：重复 key 只保留最后一个值
      const seen = {}
      const lines = []
      for (const l of resp.lines || []) {
        if (l.key in seen) lines[seen[l.key]].value = l.value
        else {
          seen[l.key] = lines.length
          lines.push(l)
        }
      }
      paramsYaml.value[fw] = { version: resp.version, lines, content: resp.content }
    } catch {
      paramsYaml.value[fw] = { version: '', lines: [], content: '' }
    }
  }
}

function buildContent(fw) {
  const p = paramsYaml.value[fw]
  const body = (p.lines || []).map((l) => `${l.key}: ${l.value}`).join('\n')
  return `version: ${p.version || ''}\n${body ? body + '\n' : ''}`
}

// 参数表单仅在内存中修改（不写入 yaml 文件），修改结果用于前后命令生成
function syncParams(fw) {
  paramsYaml.value[fw].content = buildContent(fw)
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
  if (!validateStep1()) return
  step1Saving.value = true
  try {
    // 同步内存参数（变更跟随进入后续步骤，不写入文件）
    syncParams(framework.value)
    step.value = 2
    paramsTab.value = framework.value
  } finally {
    step1Saving.value = false
  }
}

async function nextToLaunch() {
  step2Saving.value = true
  try {
    // 同步两框架内存参数，保证命令预览使用最新值（不写入文件）
    syncParams('vllm')
    syncParams('sglang')
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
    params_yaml: {
      vllm: buildContent('vllm'),
      sglang: buildContent('sglang'),
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
        syncParams('vllm')
        syncParams('sglang')
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
  await Promise.all([loadModels(), loadParamsYaml()])
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
.params-lock {
  padding: 32px 0;
  text-align: center;
  color: #999;
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
  margin-bottom: 8px;
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

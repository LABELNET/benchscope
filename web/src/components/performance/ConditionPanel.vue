<template>
  <div class="condition-panel panel-section">
    <div class="section-head">
      <span class="section-title">{{ t('conditionTitle') }}</span>
      <a-button type="text" size="small" :title="t('addCondition')" @click="emit('add')">
        <template #icon><plus-outlined /></template>
      </a-button>
    </div>

    <div v-for="(g, idx) in conditions" :key="g.id" class="cond-group">
      <div class="cond-head">
        <span class="cond-name">
          {{ t('inputLabel') }}
          <a-input
            class="inline-edit"
            :value="String(g.inputLen)"
            :maxlength="6"
            @change="setLen(idx, 'inputLen', $event.target.value)"
            @blur="normalizeLen(idx)"
          />
          {{ t('outputLabel') }}
          <a-input
            class="inline-edit"
            :value="String(g.outputLen)"
            :maxlength="6"
            @change="setLen(idx, 'outputLen', $event.target.value)"
            @blur="normalizeLen(idx)"
          />
          <span class="cond-name-highlight">{{ g.inputLen }}x{{ g.outputLen }}</span>
        </span>
        <a-button type="text" size="small" danger :title="t('deleteCondition')" @click="emit('remove', idx)">
          <template #icon><delete-outlined /></template>
        </a-button>
      </div>

      <div class="cond-row">
        <span class="cond-label">{{ t('datasetLabel') }}</span>
        <span class="cond-field">
          <a-select v-model:value="g.dataset" style="width: 220px" :options="datasetOptions" />
        </span>
      </div>

      <div v-if="mode === 'concurrency'" class="cond-row">
        <span class="cond-label">{{ t('requestCounts') }}</span>
        <span class="cond-field">
          <a-select
            v-model:value="g.requestRates"
            mode="tags"
            :token-separators="[',', '，', ' ']"
            style="width: 460px"
            :open="false"
            :max-tag-count="16"
            @change="normalizeRequestRates(idx)"
          />
        </span>
        <span class="cond-hint">{{ t('requestCountsHint') }}</span>
      </div>

      <div class="cond-row">
        <span class="cond-label">{{ t('requestRate') }}</span>
        <span class="cond-field">
          <a-radio-group v-model:value="g.rateMode" button-style="solid">
            <a-radio-button value="inf">Inf</a-radio-button>
            <a-radio-button value="follow">Follow</a-radio-button>
          </a-radio-group>
          <span v-if="g.rateMode === 'follow'" class="cond-hint">{{ t('followHint') }}</span>
        </span>
      </div>

      <template v-if="mode === 'threshold'">
        <div class="cond-row">
          <span class="cond-label">{{ t('ttftThresholdLabel') }}</span>
          <span class="cond-field threshold-field">
            <a-select v-model:value="g.ttftStatistic" size="small" style="width: 96px" :options="statOptions" />
            <span class="threshold-sign">≤</span>
            <a-input-number v-model:value="g.ttftThreshold" :min="0" :precision="0" :parser="intParser" style="width: 110px" />
            <span class="threshold-unit">ms</span>
          </span>
        </div>
        <div class="cond-row">
          <span class="cond-label">{{ t('tpotThresholdLabel') }}</span>
          <span class="cond-field threshold-field">
            <a-select v-model:value="g.tpotStatistic" size="small" style="width: 96px" :options="statOptions" />
            <span class="threshold-sign">≤</span>
            <a-input-number v-model:value="g.tpotThreshold" :min="0" :precision="0" :parser="intParser" style="width: 110px" />
            <span class="threshold-unit">ms</span>
          </span>
        </div>
        <div class="cond-row">
          <span class="cond-label">{{ t('outputThroughputLabel') }}</span>
          <span class="cond-field threshold-field">
            <span class="threshold-sign">≤</span>
            <a-input-number v-model:value="g.outThroughput" :min="0" :precision="0" :parser="intParser" style="width: 110px" />
            <span class="threshold-unit">tok/s</span>
          </span>
        </div>
      </template>
    </div>

    <a-empty v-if="!conditions.length" :image="simpleImage" :description="t('noCondition')" />
  </div>
</template>

<script setup>
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { Empty } from 'ant-design-vue'
import { t } from '@/i18n'

const props = defineProps({
  mode: { type: String, default: 'concurrency' },
  conditions: { type: Array, default: () => [] },
})

const emit = defineEmits(['add', 'remove', 'update'])

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE
const datasetOptions = [{ value: 'Random', label: 'Random' }]
const statOptions = [
  { value: 'mean', label: t('mean') },
  { value: 'median', label: t('median') },
  { value: 'p99', label: t('p99') },
]

function setLen(idx, field, raw) {
  const num = parseInt(String(raw).replace(/\D/g, ''), 10)
  const g = props.conditions[idx]
  if (!g) return
  g[field] = Number.isFinite(num) ? num : 0
}

function normalizeLen(idx) {
  const g = props.conditions[idx]
  if (!g) return
  if (!g.inputLen || g.inputLen <= 0) g.inputLen = 1024
  if (!g.outputLen || g.outputLen <= 0) g.outputLen = 1024
  emit('update', idx)
}

function normalizeRequestRates(idx) {
  const g = props.conditions[idx]
  if (!g) return
  const nums = (g.requestRates || [])
    .map((v) => parseInt(String(v).trim(), 10))
    .filter((v) => Number.isFinite(v) && v > 0)
  g.requestRates = [...new Set(nums)].sort((a, b) => a - b)
  emit('update', idx)
}

function intParser(value) {
  return String(value || '').replace(/[^\d]/g, '')
}
</script>

<style scoped>
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
}
.cond-group {
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 12px;
  background: rgba(0, 0, 0, 0.015);
}
.cond-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.cond-name {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  font-size: 13px;
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
}
.inline-edit {
  width: 72px;
  text-align: center;
  font-weight: 600;
  color: #1677ff;
}
.cond-name-highlight {
  font-weight: 600;
  color: #1677ff;
  margin-left: 6px;
}
.cond-row {
  display: flex;
  align-items: center;
  padding: 6px 0;
}
.cond-label {
  width: 200px;
  flex: none;
  color: var(--ant-color-text-secondary, #666);
  font-size: 13px;
}
.cond-field {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.cond-hint {
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
  margin-left: 8px;
}
.threshold-field {
  font-size: 13px;
}
.threshold-sign {
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
}
.threshold-unit {
  color: var(--ant-color-text-secondary, #666);
}
</style>

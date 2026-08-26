<template>
  <div class="base-env-panel panel-section">
    <div class="section-head">
      <span class="section-title">{{ t('baseTitle') }}</span>
      <a-button v-if="!online" type="link" size="small" class="settings-link" @click="emit('go-settings')">
        <template #icon><setting-outlined /></template>
        {{ t('goSettings') }}
      </a-button>
    </div>

    <div class="env-row">
      <span class="env-label">{{ t('framework') }}</span>
      <span class="env-value">{{ frameworkName }}</span>
    </div>

    <div class="env-row">
      <span class="env-label">{{ t('baseUrl') }}</span>
      <span class="env-value mono">{{ baseUrl || '-' }}</span>
    </div>

    <div class="env-row">
      <span class="env-label">{{ t('model') }}</span>
      <span class="env-value">
        <a-select
          :value="model"
          :options="modelOptions"
          style="width: 360px"
          :loading="loading"
          :placeholder="t('selectModel')"
          allow-clear
          @change="emit('update:model', $event); emit('model-change', $event)"
        />
        <a-button type="text" size="small" :loading="loading" :title="t('more')" @click="emit('refresh')">
          <template #icon><reload-outlined /></template>
        </a-button>
      </span>
    </div>

    <div class="env-row">
      <span class="env-label">{{ t('modelStatus') }}</span>
      <span class="env-value">
        <a-badge :status="online ? 'success' : 'error'" :text="online ? t('online') : t('offline')" />
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ReloadOutlined, SettingOutlined } from '@ant-design/icons-vue'
import { t } from '@/i18n'

const props = defineProps({
  framework: { type: String, default: 'vllm' },
  baseUrl: { type: String, default: '' },
  model: { type: String, default: '' },
  models: { type: Array, default: () => [] },
  inference: { type: String, default: 'offline' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:model', 'model-change', 'refresh', 'go-settings'])

const frameworkName = computed(() => (props.framework === 'sglang' ? 'SGLang' : 'vLLM'))
const online = computed(() => props.inference === 'ready')
const modelOptions = computed(() => props.models.map((m) => ({ value: m, label: m })))
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
.settings-link {
  font-size: 13px;
}
.env-row {
  display: flex;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.06);
}
.env-row:last-child {
  border-bottom: none;
}
.env-label {
  width: 140px;
  flex: none;
  color: var(--ant-color-text-secondary, #666);
  font-size: 13px;
}
.env-value {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}
.env-value.mono {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  word-break: break-all;
}
</style>

<template>
  <a-tooltip :title="extra || label">
    <span class="status-badge" :class="ready ? 'ok' : 'bad'">
      <component :is="ready ? CheckCircleFilled : CloseCircleFilled" class="status-icon" />
      <span v-if="!noLabel" class="status-label">{{ label }}</span>
    </span>
  </a-tooltip>
</template>

<script setup>
import { CheckCircleFilled, CloseCircleFilled } from '@ant-design/icons-vue'

defineProps({
  label: { type: String, required: true },
  ready: { type: Boolean, default: false },
  extra: { type: String, default: '' },
  // 仅显示状态颜色（图标），不显示文字
  noLabel: { type: Boolean, default: false },
})
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: help;
}
.status-icon {
  font-size: 16px;
}
.status-badge.ok .status-icon {
  color: var(--ant-color-success, #52c41a);
}
.status-badge.bad .status-icon {
  color: var(--ant-color-error, #ff4d4f);
}
.status-label {
  color: var(--ant-color-text-secondary, rgba(0, 0, 0, 0.65));
  font-size: 12px;
}
</style>

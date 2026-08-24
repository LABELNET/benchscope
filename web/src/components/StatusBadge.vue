<template>
  <a-tooltip :title="extra || label">
    <span class="status-badge" :class="ready ? 'ok' : 'bad'">
      <component :is="ready ? CheckCircleFilled : CloseCircleFilled" class="status-icon" />
      <span class="status-label">{{ label }}：{{ ready ? '就绪' : '离线' }}</span>
    </span>
  </a-tooltip>
</template>

<script setup>
import { CheckCircleFilled, CloseCircleFilled } from '@ant-design/icons-vue'

defineProps({
  label: { type: String, required: true },
  ready: { type: Boolean, default: false },
  extra: { type: String, default: '' },
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
  color: #52c41a;
}
.status-badge.bad .status-icon {
  color: #ff4d4f;
}
.status-label {
  color: rgba(0, 0, 0, 0.65);
  font-size: 13px;
}
</style>

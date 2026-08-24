<template>
  <div class="subtabs">
    <div class="group">
      <button
        v-for="t in dataTabs"
        :key="t.key"
        class="subtab"
        :class="{ active: modelValue === t.key }"
        @click="$emit('update:modelValue', t.key)"
      >
        <component :is="t.icon" class="subtab-icon" /> {{ t.label }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ExperimentOutlined, FileAddOutlined, MessageOutlined } from '@ant-design/icons-vue'

defineProps({
  modelValue: { type: String, default: 'random' },
})
const emit = defineEmits(['update:modelValue'])

const dataTabs = [
  { key: 'random', label: 'Random', icon: ExperimentOutlined },
  { key: 'sharegpt', label: 'ShareGPT', icon: MessageOutlined },
  { key: 'custom', label: 'Custom', icon: FileAddOutlined },
]
</script>

<style scoped>
.subtabs {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  padding: 0 8px;
  height: 44px;
}
.group {
  display: flex;
  gap: 4px;
}
.subtab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 0 16px;
  height: 44px;
  font-size: 14px;
  color: rgba(0, 0, 0, 0.65);
  cursor: pointer;
  transition: color 0.2s;
}
.subtab-icon {
  font-size: 14px;
}
.subtab:hover {
  color: #1677ff;
}
.subtab.active {
  color: #1677ff;
  border-bottom-color: #1677ff;
  font-weight: 600;
}
</style>

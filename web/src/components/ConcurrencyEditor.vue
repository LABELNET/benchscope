<template>
  <div>
    <div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 8px">
      <a-tag
        v-for="(item, i) in modelValue"
        :key="i"
        closable
        color="blue"
        style="font-size: 14px; padding: 2px 10px"
        @close="remove(i)"
      >
        {{ item }}
      </a-tag>
      <a-input
        v-model:value="draft"
        placeholder="添加并发数，回车确认"
        style="width: 160px"
        @pressEnter="add"
        @blur="add"
      />
      <a-button size="small" type="dashed" @click="add">添加</a-button>
      <a-button size="small" @click="reset">恢复默认 1,4,8,16,32,40,64,128</a-button>
    </div>
    <div style="color: #999; font-size: 12px">
      测试时每个并发数分别执行一次 bench；--max-concurrency 与 --num-prompts 保持一致。
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

const draft = ref('')

function add() {
  const v = String(draft.value).trim()
  if (v === '') return
  const nums = v.split(/[,，\s]+/).filter(Boolean).map(Number).filter((n) => Number.isInteger(n) && n > 0)
  if (!nums.length) return
  const merged = [...props.modelValue]
  for (const n of nums) {
    if (!merged.includes(n)) merged.push(n)
  }
  merged.sort((a, b) => a - b)
  emit('update:modelValue', merged)
  draft.value = ''
}

function remove(i) {
  const merged = props.modelValue.filter((_, idx) => idx !== i)
  emit('update:modelValue', merged)
}

function reset() {
  emit('update:modelValue', [1, 4, 8, 16, 32, 40, 64, 128])
}
</script>

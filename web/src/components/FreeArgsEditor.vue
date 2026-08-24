<template>
  <div>
    <div v-for="(arg, i) in modelValue" :key="i" style="display: flex; gap: 8px; margin-bottom: 6px">
      <a-input v-model:value="arg.flag" placeholder="参数名，如 --top-p" style="width: 220px" />
      <a-input v-model:value="arg.value" placeholder="参数值（布尔开关可留空）" style="width: 220px" />
      <a-button size="small" danger @click="remove(i)">删除</a-button>
    </div>
    <a-button size="small" type="dashed" @click="add">+ 添加其他参数</a-button>
    <div style="color: #999; font-size: 12px; margin-top: 4px">
      自由添加 vLLM / SGLang bench 的其他参数，直接拼接到命令末尾。
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

function add() {
  emit('update:modelValue', [...props.modelValue, { flag: '', value: '' }])
}

function remove(i) {
  emit('update:modelValue', props.modelValue.filter((_, idx) => idx !== i))
}
</script>

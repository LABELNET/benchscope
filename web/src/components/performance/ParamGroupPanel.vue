<template>
  <div class="param-group-list">
    <div class="param-hint">{{ t('paramsEditHint') }}</div>

    <!-- 版本行：独立高亮 -->
    <div v-if="version" class="param-row version-row" :class="{ editing: editingVersion }" @click="startEditVersion">
      <span class="param-key">{{ versionLabel }}</span>
      <div class="param-value">
        <a-input
          v-if="editingVersion"
          ref="versionInputRef"
          size="small"
          v-model:value="versionValue"
          class="edit-input"
          @click.stop
          @press-enter="commitVersion"
          @blur="commitVersion"
          @keydown.esc.prevent="cancelVersion"
        />
        <span v-else class="param-chip chip-version">{{ version }}</span>
      </div>
    </div>

    <!-- 自动分组 -->
    <div v-for="group in groups" :key="group.id" class="param-group">
      <div class="param-group-head">
        <span class="group-dot" :class="group.id"></span>
        <span class="group-title">{{ t(titleKey(group.id)) }}</span>
        <span class="group-count">{{ group.rows.length }}</span>
      </div>
      <div class="param-group-body">
        <div
          v-for="(line, i) in group.rows"
          :key="line.key + i"
          class="param-row-wrap"
        >
          <div
            class="param-row"
            :class="{ editing: editingKey === line.key }"
            @click="startEdit(line)"
          >
            <span class="param-key" :title="specOf(line).label || line.key">
              {{ specOf(line).label || line.key }}
            </span>
            <div class="param-value">
              <!-- 有下拉选项：用 select 选择（选中后展示描述） -->
              <a-select
                v-if="optionsOf(line).length"
                size="small"
                :value="line.value"
                :options="optionsOf(line)"
                class="param-select"
                @click.stop
                @change="(val) => onSelect(line, val)"
              />
              <a-switch
                v-else-if="isBool(line.value)"
                size="small"
                :checked="line.value === 'true'"
                class="param-switch"
                @click.stop
                @change="(checked) => onSwitch(line, checked)"
              />
              <a-input
                v-else-if="editingKey === line.key"
                ref="editInputRef"
                size="small"
                v-model:value="editValue"
                class="edit-input"
                @click.stop
                @press-enter="commit(line)"
                @blur="commit(line)"
                @keydown.esc.prevent="cancel(line)"
              />
              <span v-else class="param-chip" :class="chipClass(line.value)">{{ line.value }}</span>
            </div>
          </div>
          <!-- 描述信息：优先展示「当前选中值」的选项描述，否则展示参数说明 -->
          <div v-if="descOf(line)" class="param-desc">{{ descOf(line) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { t } from '@/i18n'

const props = defineProps({
  version: { type: String, default: '' },
  versionLabel: { type: String, default: '' },
  lines: { type: Array, default: () => [] },
  // 参数定义：{ <yaml_key>: { label, help, type, options: [{value,label,description}] } }
  specs: { type: Object, default: () => ({}) },
})

// 参数定义辅助：下拉选项 / 描述信息
function specOf(line) {
  return props.specs?.[line.key] || {}
}
function optionsOf(line) {
  const opts = specOf(line).options || []
  return opts
    .filter((o) => o && typeof o === 'object')
    .map((o) => ({ value: String(o.value), label: o.label || String(o.value) }))
}
function descOf(line) {
  const spec = specOf(line)
  // 选中值有选项级描述时优先展示，否则展示参数说明
  const hit = (spec.options || []).find((o) => o && String(o.value) === String(line.value))
  return (hit && hit.description) || spec.help || ''
}
function onSelect(line, val) {
  line.value = String(val)
  emit('save')
}
const emit = defineEmits(['save', 'update:version'])

// 自动分组规则：未知 key 归入「其他」
const GROUPS = [
  { id: 'server', keys: ['backend', 'endpoint'] },
  {
    id: 'sampling',
    keys: ['temperature', 'top-p', 'top-k', 'min-p', 'frequency-penalty', 'presence-penalty'],
  },
  {
    id: 'resource',
    keys: ['max-model-len', 'gpu-memory-utilization', 'mem-fraction-static', 'sharegpt-output-len'],
  },
  {
    id: 'benchmark',
    keys: ['trust-remote-code', 'ignore-eos', 'burstiness', 'seed', 'num-warmups', 'metric-percentiles'],
  },
]

function titleKey(id) {
  const map = {
    server: 'paramGroupServer',
    sampling: 'paramGroupSampling',
    resource: 'paramGroupResource',
    benchmark: 'paramGroupBenchmark',
    other: 'paramGroupOther',
  }
  return map[id] || 'paramGroupOther'
}

const groups = computed(() => {
  const result = []
  const used = new Set()
  for (const g of GROUPS) {
    const rows = props.lines.filter((l) => g.keys.includes(l.key))
    if (rows.length) {
      result.push({ ...g, rows })
      rows.forEach((r) => used.add(r.key))
    }
  }
  const other = props.lines.filter((l) => !used.has(l.key))
  if (other.length) result.push({ id: 'other', rows: other })
  return result
})

// 值类型判断
function isBool(v) {
  return v === 'true' || v === 'false'
}
function isNum(v) {
  return (
    typeof v === 'string' &&
    v.trim() !== '' &&
    !isNaN(Number(v.trim())) &&
    /^-?\d*\.?\d+$/.test(v.trim())
  )
}

function chipClass(v) {
  if (isBool(v)) return ''
  if (isNum(v)) return 'chip-num'
  return 'chip-str'
}

// 行内编辑状态
const editingKey = ref(null)
const editValue = ref('')
const editBackup = ref('')
const editInputRef = ref(null)

function startEdit(line) {
  if (isBool(line.value)) return
  editingVersion.value = false
  editingKey.value = line.key
  editValue.value = line.value
  editBackup.value = line.value
  nextTick(() => {
    editInputRef.value?.focus?.()
  })
}
function commit(line) {
  if (editingKey.value !== line.key) return
  line.value = editValue.value.trim()
  editingKey.value = null
  emit('save')
}
function cancel(line) {
  if (editingKey.value !== line.key) return
  line.value = editBackup.value
  editingKey.value = null
}
function onSwitch(line, checked) {
  line.value = checked ? 'true' : 'false'
  emit('save')
}

// 版本行编辑
const editingVersion = ref(false)
const versionValue = ref('')
const versionInputRef = ref(null)
function startEditVersion() {
  editingKey.value = null
  editingVersion.value = true
  versionValue.value = props.version
  nextTick(() => {
    versionInputRef.value?.focus?.()
  })
}
function commitVersion() {
  if (!editingVersion.value) return
  editingVersion.value = false
  const v = versionValue.value.trim()
  if (v && v !== props.version) {
    emit('update:version', v)
  }
}
function cancelVersion() {
  editingVersion.value = false
}
</script>

<style scoped>
.param-group-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.param-hint {
  font-size: 12px;
  color: var(--ant-color-text-tertiary, #999);
  padding: 2px 2px 0;
}
.param-group {
  border: 1px solid rgba(0, 0, 0, 0.07);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.param-group-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #fafafa;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}
.group-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}
.group-dot.server {
  background: #1677ff;
}
.group-dot.sampling {
  background: #722ed1;
}
.group-dot.resource {
  background: #13c2c2;
}
.group-dot.benchmark {
  background: #fa8c16;
}
.group-dot.other {
  background: #999;
}
.group-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
}
.group-count {
  margin-left: auto;
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
  background: rgba(0, 0, 0, 0.04);
  border-radius: 8px;
  padding: 0 7px;
  line-height: 16px;
}
.param-group-body {
  padding: 4px 12px;
}
.param-row-wrap {
  border-bottom: 1px dashed rgba(0, 0, 0, 0.05);
}
.param-group-body .param-row-wrap:last-child {
  border-bottom: none;
}
.param-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 5px 0;
  cursor: text;
}
/* 参数描述（选项级描述优先，其次参数说明） */
.param-desc {
  font-size: 11px;
  line-height: 1.6;
  color: var(--ant-color-text-tertiary, #8c8c8c);
  padding: 0 0 6px 2px;
  word-break: break-word;
}
.param-select {
  min-width: 200px;
  max-width: 70%;
  font-size: 12px;
}
.param-group-body .param-row:last-child {
  border-bottom: none;
}
.param-row.editing {
  background: rgba(22, 119, 255, 0.04);
}
.param-key {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
  white-space: nowrap;
}
.param-value {
  min-width: 0;
  display: flex;
  justify-content: flex-end;
}
/* 高亮值样式：默认文本 */
.param-chip {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
  font-size: 12px;
  line-height: 20px;
  padding: 0 10px;
  border-radius: 6px;
  background: #fffbe6;
  border: 1px solid #ffe58f;
  color: #ad6800;
  white-space: nowrap;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* 数字 */
.chip-num {
  background: #e6f4ff;
  border-color: #91caff;
  color: #0958d9;
  font-weight: 500;
}
/* 文本（带引号字符串等） */
.chip-str {
  background: #f9f0ff;
  border-color: #d3adf7;
  color: #531dab;
}
/* 版本行：绿色高亮 */
.version-row {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 8px;
  padding: 7px 12px;
  cursor: text;
}
.chip-version {
  background: #f6ffed;
  border-color: #95de64;
  color: #237804;
  font-weight: 600;
}
.param-switch {
  margin: 2px 0;
}
.edit-input {
  width: 180px;
  max-width: 60%;
  font-size: 12px;
}
</style>

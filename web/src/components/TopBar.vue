<template>
  <a-layout-header class="topbar">
    <div class="brand" @click="$router.push('/vllm')">
      <thunderbolt-filled class="brand-icon" />
      <span class="brand-name">benchscope</span>
      <a-tag color="blue" style="margin-left: 8px">v1.0.4</a-tag>
    </div>

    <a-menu
      class="nav-menu"
      mode="horizontal"
      :selectedKeys="[activeKey]"
      :items="menuItems"
      @click="onMenuClick"
    />

    <div class="topbar-right">
      <StatusBadge label="服务" :ready="serviceReady" :extra="serviceExtra" />
      <a-divider type="vertical" />
      <StatusBadge label="环境" :ready="inferenceReady" :extra="inferenceExtra" />
      <a-button type="primary" ghost size="small" style="margin-left: 12px" @click="$router.push('/settings')">
        <template #icon><setting-outlined /></template>
        设置
      </a-button>
    </div>
  </a-layout-header>
</template>

<script setup>
import { computed, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  FileSearchOutlined,
  RocketOutlined,
  SettingOutlined,
  ThunderboltFilled,
  ThunderboltOutlined,
} from '@ant-design/icons-vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useConfigStore } from '@/store/config'

const route = useRoute()
const router = useRouter()
const config = useConfigStore()

const activeKey = computed(() => {
  if (route.path.startsWith('/vllm')) return 'vllm'
  if (route.path.startsWith('/sglang')) return 'sglang'
  if (route.path.startsWith('/logs')) return 'logs'
  return 'vllm'
})

const menuItems = [
  { key: 'vllm', icon: () => h(ThunderboltOutlined), label: 'vLLM' },
  { key: 'sglang', icon: () => h(RocketOutlined), label: 'SGLang' },
  { key: 'logs', icon: () => h(FileSearchOutlined), label: '日志管理' },
]

const inferenceReady = computed(() => config.status?.inference === 'ready')
// 服务 = benchscope 应用自身（在线即就绪）；环境 = 推理服务环境（在线/离线）
const serviceReady = computed(() => true)
const serviceExtra = 'benchscope 应用服务'
const inferenceExtra = computed(() =>
  inferenceReady.value
    ? `${config.status?.models?.length || 0} 个模型`
    : config.status?.error || '推理环境离线',
)

function onMenuClick({ key }) {
  if (key === 'vllm') router.push('/vllm')
  else if (key === 'sglang') router.push('/sglang')
  else if (key === 'logs') router.push('/logs')
}
</script>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  background: #fff;
  padding: 0 20px;
  height: 56px;
  line-height: 56px;
  border-bottom: 1px solid #f0f0f0;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.06);
}
.brand {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  margin-right: 24px;
  user-select: none;
}
.brand-icon {
  color: #1677ff;
  font-size: 22px;
}
.brand-name {
  font-size: 17px;
  font-weight: 700;
  color: rgba(0, 0, 0, 0.88);
}
.nav-menu {
  flex: 1;
  min-width: 0;
  border-bottom: none;
}
.topbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}
</style>

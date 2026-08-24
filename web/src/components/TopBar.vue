<template>
  <a-layout-header class="topbar">
    <div class="brand" @click="$router.push('/dashboard')">
      <img src="/bs-logo.png" class="brand-logo" alt="BS" />
      <span class="brand-name">BenchScope</span>
      <a-tag color="blue" style="margin-left: 8px">v1.0.5</a-tag>
    </div>

    <a-menu
      class="nav-menu"
      mode="horizontal"
      :selectedKeys="[activeKey]"
      :items="menuItems"
      @click="onMenuClick"
    />

    <div class="topbar-right">
      <StatusBadge :label="t('service')" :ready="serviceReady" :extra="serviceExtra" />
      <a-divider type="vertical" />
      <StatusBadge :label="t('environment')" :ready="inferenceReady" :extra="inferenceExtra" />
    </div>
  </a-layout-header>
</template>

<script setup>
import { computed, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DashboardOutlined,
  ExperimentOutlined,
  MessageOutlined,
  SettingOutlined,
  FundOutlined,
} from '@ant-design/icons-vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useConfigStore } from '@/store/config'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()
const config = useConfigStore()

const activeKey = computed(() => {
  const path = route.path
  if (path.startsWith('/dashboard')) return 'dashboard'
  if (path.startsWith('/performance')) return 'performance'
  if (path.startsWith('/accuracy')) return 'accuracy'
  if (path.startsWith('/sessions')) return 'sessions'
  if (path.startsWith('/settings')) return 'settings'
  return 'dashboard'
})

const menuItems = [
  { key: 'dashboard', icon: () => h(DashboardOutlined), label: t('dashboard') },
  { key: 'performance', icon: () => h(ExperimentOutlined), label: t('performance') },
  { key: 'accuracy', icon: () => h(FundOutlined), label: t('accuracy') },
  { key: 'sessions', icon: () => h(MessageOutlined), label: t('sessions') },
  { key: 'settings', icon: () => h(SettingOutlined), label: t('settings') },
]

const inferenceReady = computed(() => config.status?.inference === 'ready')
const serviceReady = computed(() => true)
const serviceExtra = 'benchscope'
const inferenceExtra = computed(() =>
  inferenceReady.value
    ? `${config.status?.models?.length || 0} ${t('models')}`
    : config.status?.error || t('offline'),
)

function onMenuClick({ key }) {
  router.push(`/${key}`)
}
</script>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  background: var(--ant-color-bg-container, #fff);
  padding: 0 20px;
  height: 56px;
  line-height: 56px;
  border-bottom: 1px solid var(--ant-color-border, #f0f0f0);
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
.brand-logo {
  width: 28px;
  height: 28px;
  border-radius: 6px;
}
.brand-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
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

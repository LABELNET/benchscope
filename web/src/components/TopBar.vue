<template>
  <a-layout-header class="topbar">
    <div class="brand" @click="$router.push('/dashboard')">
      <img src="/blue_logo.png" class="brand-logo" alt="BS" />
      <span class="brand-name">BenchScope</span>
      <a-tag v-if="versionTag" color="blue" style="margin-left: 8px">{{ versionTag }}</a-tag>
    </div>

    <a-menu
      class="nav-menu"
      mode="horizontal"
      :selectedKeys="[activeKey]"
      :items="menuItems"
      @click="onMenuClick"
    />

    <div class="topbar-right">
      <!-- Service 状态：仅状态颜色（图标），无文字 -->
      <StatusBadge :label="t('service')" :ready="serviceReady" :extra="serviceExtra" no-label />
    </div>
  </a-layout-header>
</template>

<script setup>
import { computed, h, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DashboardOutlined,
  ExperimentOutlined,
  MessageOutlined,
  SettingOutlined,
  FundOutlined,
  DatabaseOutlined,
} from '@ant-design/icons-vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/api'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()

const versionTag = ref('')
onMounted(async () => {
  try {
    const res = await api.getVersion()
    versionTag.value = res.display || ''
  } catch {
    versionTag.value = ''
  }
})

const activeKey = computed(() => {
  const path = route.path
  if (path.startsWith('/dashboard')) return 'dashboard'
  if (path.startsWith('/performance')) return 'performance'
  if (path.startsWith('/accuracy')) return 'accuracy'
  if (path.startsWith('/sessions')) return 'sessions'
  if (path.startsWith('/datas')) return 'datas'
  if (path.startsWith('/settings')) return 'settings'
  return 'dashboard'
})

const menuItems = computed(() => [
  { key: 'dashboard', icon: () => h(DashboardOutlined), label: t('dashboard') },
  { key: 'performance', icon: () => h(ExperimentOutlined), label: t('performance') },
  { key: 'accuracy', icon: () => h(FundOutlined), label: t('accuracy') },
  { key: 'sessions', icon: () => h(MessageOutlined), label: t('sessions') },
  { key: 'datas', icon: () => h(DatabaseOutlined), label: t('datas') },
  { key: 'settings', icon: () => h(SettingOutlined), label: t('settings') },
])

const serviceReady = computed(() => true)
const serviceExtra = 'benchscope'

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
  width: 48px;
  height: 48px;
  border-radius: 12px;
  object-fit: contain;
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

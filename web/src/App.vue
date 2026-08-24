<template>
  <a-config-provider :locale="antdLocale" :theme="themeConfig">
    <a-layout class="app-layout">
      <TopBar />
      <a-layout class="app-content-layout">
        <router-view />
      </a-layout>
    </a-layout>
  </a-config-provider>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { theme as antTheme } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import enUS from 'ant-design-vue/es/locale/en_US'
import TopBar from '@/components/TopBar.vue'
import { useConfigStore } from '@/store/config'
import { useTestStore } from '@/store/test'
import { i18nState, initI18n } from '@/i18n'

const config = useConfigStore()
const test = useTestStore()

const antdLocale = computed(() => (i18nState.locale === 'zh' ? zhCN : enUS))

const themeConfig = computed(() => {
  const isDark = resolvedTheme.value === 'dark'
  return {
    token: {
      colorPrimary: '#1677ff',
      borderRadius: 6,
      fontSize: 14,
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
      ...(isDark
        ? {
            colorBgContainer: '#141414',
            colorBgElevated: '#1f1f1f',
            colorBgLayout: '#000',
            colorText: 'rgba(255,255,255,0.85)',
            colorTextSecondary: 'rgba(255,255,255,0.65)',
            colorBorder: '#303030',
          }
        : {}),
    },
    algorithm: isDark ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
  }
})

const resolvedTheme = computed(() => {
  const pref = config.config?.theme || 'light'
  if (pref === 'system') {
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return pref
})

watch(resolvedTheme, (val) => {
  document.documentElement.setAttribute('data-theme', val)
  document.body.className = val === 'dark' ? 'theme-dark' : 'theme-light'
})

onMounted(async () => {
  await config.load()
  initI18n(config.config?.locale)
  test.loadTasks()
  test.connect()
  document.documentElement.setAttribute('data-theme', resolvedTheme.value)
})
</script>

<style>
body {
  margin: 0;
  background: var(--ant-color-bg-layout, #f5f5f5);
  transition: background 0.3s;
}
.app-layout {
  height: 100vh;
}
.app-content-layout {
  flex: 1;
  overflow: hidden;
}
.theme-dark body,
body.theme-dark {
  background: #000;
}
</style>

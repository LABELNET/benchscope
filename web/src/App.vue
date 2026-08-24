<template>
  <a-config-provider :locale="zhCN" :theme="theme">
    <a-layout style="height: 100vh">
      <TopBar />
      <a-layout style="flex: 1; overflow: hidden">
        <router-view />
      </a-layout>
    </a-layout>
  </a-config-provider>
</template>

<script setup>
import { onMounted } from 'vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import TopBar from '@/components/TopBar.vue'
import { useConfigStore } from '@/store/config'
import { useTestStore } from '@/store/test'

const config = useConfigStore()
const test = useTestStore()

const theme = {
  token: {
    colorPrimary: '#1677ff',
    borderRadius: 6,
    fontSize: 14,
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
  },
}

onMounted(() => {
  config.load()
  test.refresh()
  test.connect()
})
</script>

<style>
body {
  margin: 0;
  background: #f5f5f5;
}
</style>

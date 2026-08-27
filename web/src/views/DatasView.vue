<template>
  <div class="datas-page">
    <!-- 副导航：白底黑色，紧贴主导航下方，宽度收窄 -->
    <div class="datas-subnav">
      <div
        v-for="item in subnavItems"
        :key="item.key"
        class="subnav-item"
        :class="{ active: activeTab === item.key }"
        @click="go(item.key)"
      >
        {{ item.label }}
      </div>
    </div>

    <!-- 子路由内容 -->
    <div class="datas-content">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()

const subnavItems = computed(() => [
  { key: 'perfs', label: t('perfsTab') },
  { key: 'evals', label: t('evalsTab') },
  { key: 'analysis', label: t('analysis') },
])

const activeTab = computed(() => {
  const seg = route.path.split('/').filter(Boolean)
  const last = seg[seg.length - 1]
  return ['perfs', 'evals', 'analysis'].includes(last) ? last : 'perfs'
})

function go(key) {
  if (activeTab.value === key) return
  router.push(`/datas/${key}`)
}
</script>

<style scoped>
.datas-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* 副导航：白底黑色，紧贴主导航下方，与页面内容区等宽 */
.datas-subnav {
  display: flex;
  align-items: center;
  background: var(--ant-color-bg-container, #fff);
  border-bottom: 1px solid var(--ant-color-border, #f0f0f0);
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.05);
  padding: 0 20px;
  flex-shrink: 0;
  width: 100%;
  gap: 4px;
}
.subnav-item {
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 500;
  color: var(--ant-color-text-secondary, #666);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  user-select: none;
  white-space: nowrap;
}
.subnav-item:hover {
  color: var(--ant-color-text, rgba(0, 0, 0, 0.88));
}
.subnav-item.active {
  color: #1677ff;
  border-bottom-color: #1677ff;
  font-weight: 600;
}

.datas-content {
  flex: 1;
  min-height: 0;
}
</style>

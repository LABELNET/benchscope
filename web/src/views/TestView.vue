<template>
  <a-layout class="page-layout">
    <!-- 左侧固定导航：测试流程 -->
    <a-layout-sider width="200" theme="light" class="workflow-sider">
      <div class="sider-title">测试流程</div>
      <a
        v-for="s in sections"
        :key="s.id"
        class="side-item"
        :class="{ active: activeSection === s.id }"
        @click="goTo(s.id)"
      >
        <component :is="s.icon" /> <span>{{ s.label }}</span>
      </a>
    </a-layout-sider>

    <!-- 内容区（内部滚动） -->
    <a-layout-content ref="contentEl" class="page-content">
      <!-- 副导航（固定在内容顶部） -->
      <SubTabBar v-model="activeTab" class="subnav" />

      <div class="blocks-wrap">
        <!-- 测试环境 -->
        <section id="env" class="block">
          <a-card size="small" class="panel" title="测试环境">
            <template #extra>
              <a-tag :color="inferenceReady ? 'green' : 'red'">
                <span class="dot" :class="inferenceReady ? 'ok' : 'bad'"></span>
                {{ inferenceReady ? '在线' : '离线' }}
              </a-tag>
            </template>
            <EnvPanel />
          </a-card>
        </section>

        <!-- 测试配置 -->
        <section id="config" class="block">
          <a-card size="small" class="panel" title="测试配置">
            <TestConfigPanel
              ref="configPanel"
              :framework="framework"
              :dataset-type="activeTab"
              @pick-model="goTo('env')"
            />
          </a-card>
        </section>

        <!-- 测试进度 -->
        <section id="progress" class="block">
          <a-card size="small" class="panel" title="测试进度">
            <TestProgressPanel :starting="starting" @start="start" @stop="stop" />
          </a-card>
        </section>

        <!-- 测试结果 -->
        <section id="result" class="block">
          <a-card size="small" class="panel" title="测试结果">
            <RealtimeResultPanel :rows="test.rows" :threshold="threshold" :running="test.running" />
          </a-card>
        </section>
      </div>
    </a-layout-content>
  </a-layout>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { BarChartOutlined, CloudServerOutlined, FormOutlined, SyncOutlined } from '@ant-design/icons-vue'
import SubTabBar from '@/components/SubTabBar.vue'
import EnvPanel from '@/components/EnvPanel.vue'
import TestConfigPanel from '@/components/TestConfigPanel.vue'
import TestProgressPanel from '@/components/TestProgressPanel.vue'
import RealtimeResultPanel from '@/components/RealtimeResultPanel.vue'
import { useTestStore } from '@/store/test'
import { useConfigStore } from '@/store/config'

const props = defineProps({ framework: { type: String, default: 'vllm' } })
const test = useTestStore()
const config = useConfigStore()

const activeTab = ref('random')
const configPanel = ref(null)
const starting = ref(false)
const contentEl = ref(null)

const threshold = computed(() => config.config?.tpot_threshold_ms ?? null)
const inferenceReady = computed(() => config.status?.inference === 'ready')

const sections = [
  { id: 'env', label: '测试环境', icon: CloudServerOutlined },
  { id: 'config', label: '测试配置', icon: FormOutlined },
  { id: 'progress', label: '测试进度', icon: SyncOutlined },
  { id: 'result', label: '测试结果', icon: BarChartOutlined },
]
const activeSection = ref('env')
let observer = null

// scrollspy：以内容区为滚动容器，高亮左侧导航
function setupObserver() {
  const rootEl = contentEl.value?.$el || contentEl.value
  if (!rootEl || typeof rootEl.getBoundingClientRect !== 'function') return
  observer = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) activeSection.value = e.target.id
      }
    },
    { root: rootEl, rootMargin: '0px 0px -70% 0px', threshold: 0 },
  )
  for (const s of sections) {
    const el = document.getElementById(s.id)
    if (el) observer.observe(el)
  }
}
function goTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  activeSection.value = id
}

onMounted(() => {
  setTimeout(setupObserver, 100)
})
onBeforeUnmount(() => {
  if (observer) observer.disconnect()
})

async function start() {
  const payload = await configPanel.value?.buildPayload()
  if (!payload) return
  starting.value = true
  try {
    const resp = await test.start({ ...payload, framework: props.framework })
    message.success(`测试已启动：${resp.run_id}`)
  } catch (e) {
    message.error(`启动失败：${e.message}`)
  } finally {
    starting.value = false
  }
}

async function stop() {
  try {
    await test.stop()
    message.info('已发送取消请求')
  } catch (e) {
    message.error(e.message)
  }
}
</script>

<style scoped>
.page-layout {
  height: 100%;
}
.workflow-sider {
  border-right: 1px solid #f0f0f0;
  height: 100%;
  overflow: auto;
  padding: 12px 0;
}
.sider-title {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  padding: 0 16px 8px;
}
.side-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 16px;
  cursor: pointer;
  color: rgba(0, 0, 0, 0.65);
  font-size: 14px;
  border-left: 3px solid transparent;
  transition: all 0.2s;
}
.side-item:hover {
  color: #1677ff;
  background: #fafafa;
}
.side-item.active {
  color: #1677ff;
  background: #e6f4ff;
  border-left-color: #1677ff;
  font-weight: 600;
}
.page-content {
  height: 100%;
  background: #f5f5f5;
  overflow: auto;
  display: flex;
  flex-direction: column;
}
.subnav {
  position: sticky;
  top: 0;
  z-index: 20;
  flex-shrink: 0;
}
.blocks-wrap {
  padding: 16px 20px;
  max-width: 1500px;
  width: 100%;
}
.block {
  scroll-margin-top: 56px;
  margin-bottom: 16px;
}
.panel {
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}
.dot.ok {
  background: #52c41a;
}
.dot.bad {
  background: #ff4d4f;
}
</style>

import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/vllm' },
  { path: '/vllm', name: 'vllm', component: () => import('@/views/TestView.vue'), props: { framework: 'vllm' } },
  { path: '/sglang', name: 'sglang', component: () => import('@/views/TestView.vue'), props: { framework: 'sglang' } },
  { path: '/logs', name: 'logs', component: () => import('@/views/LogView.vue') },
  { path: '/settings', name: 'settings', component: () => import('@/views/SettingsView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})

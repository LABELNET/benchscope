import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
  { path: '/performance', name: 'performance', component: () => import('@/views/PerformanceView.vue') },
  { path: '/performance/:taskId', name: 'taskDetail', component: () => import('@/views/TaskDetailView.vue'), props: true },
  { path: '/accuracy', name: 'accuracy', component: () => import('@/views/AccuracyView.vue') },
  { path: '/sessions', name: 'sessions', component: () => import('@/views/SessionsView.vue') },
  { path: '/settings', name: 'settings', component: () => import('@/views/SettingsView.vue') },
  // 兼容旧路由
  { path: '/vllm', redirect: '/performance' },
  { path: '/sglang', redirect: '/performance' },
  { path: '/logs', redirect: '/dashboard' },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})

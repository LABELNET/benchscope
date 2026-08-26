import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
  { path: '/performance', name: 'performance', component: () => import('@/views/PerformanceView.vue') },
  // 创建 Perf 任务：并发模式 / 阈值模式 三步表单（?mode=concurrency|threshold）
  { path: '/performance/create', name: 'perf-create', component: () => import('@/views/PerfCreateView.vue') },
  // 单任务重设计：创建与详情都内联进 /performance，旧路由重定向回主页
  { path: '/performance/:taskId', redirect: '/performance' },
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

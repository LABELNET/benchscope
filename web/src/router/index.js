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
  // 创建精度任务三步表单（数据集 / 模式与引擎 / 预览与 Token 强提醒确认）
  { path: '/accuracy/create', name: 'accuracy-create', component: () => import('@/views/AccuracyCreateView.vue') },
  { path: '/sessions', name: 'sessions', component: () => import('@/views/SessionsView.vue') },
  {
    path: '/datas',
    name: 'datas',
    component: () => import('@/views/DatasView.vue'),
    redirect: '/datas/perfs',
    children: [
      { path: 'perfs', name: 'datas-perfs', component: () => import('@/views/DatasPerfsView.vue') },
      { path: 'evals', redirect: '/datas/perfs' },
      { path: 'analysis', name: 'datas-analysis', component: () => import('@/views/DatasAnalysisView.vue') },
    ],
  },
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

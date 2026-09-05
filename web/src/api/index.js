import axios from 'axios'

const http = axios.create({ baseURL: '', timeout: 60000 })

http.interceptors.response.use(
  (resp) => resp.data,
  (err) => {
    const detail = err?.response?.data?.detail || err.message || '请求失败'
    return Promise.reject(new Error(detail))
  },
)

export default http

export const api = {
  // 系统
  getVersion: () => http.get('/api/version'),

  // 配置
  getConfig: () => http.get('/api/config'),
  getModelCatalog: () => http.get('/api/config/model-catalog'),
  updateConfig: (patch) => http.post('/api/config', patch),
  getStatus: () => http.get('/api/config/status'),
  getModels: () => http.get('/api/config/models'),
  testConnection: (data) => http.post('/api/config/test-connection', data),
  getGpu: () => http.get('/api/config/gpu'),
  getParams: (framework) => http.get(`/api/config/params/${framework}`),
  getParamsYaml: (framework) => http.get(`/api/config/params-yaml/${framework}`),
  saveParamsYaml: (framework, content) => http.put(`/api/config/params-yaml/${framework}`, { content }),
  getDatasets: () => http.get('/api/config/datasets'),
  downloadDataset: (id) => http.post('/api/config/datasets/download', { id }),

  // 内置 bench 引擎
  getBenchEngines: () => http.get('/api/benchs'),
  getBenchEngine: (engineId) => http.get(`/api/benchs/${engineId}`),
  getBenchParams: (engineId) => http.get(`/api/benchs/${engineId}/params`),
  checkBenchEnv: (engineId) => http.get(`/api/benchs/${engineId}/env-check`),
  setEngineMock: (engineId, enabled) => http.post(`/api/benchs/${engineId}/mock`, { enabled }),
  getBenchsYaml: () => http.get('/api/benchs/config/yaml'),
  saveBenchsYaml: (content, mockOutput) => http.put('/api/benchs/config/yaml', { content, mock_output: mockOutput }),
  importBenchs: (content, mockOutput, apply) => http.post('/api/benchs/import', {
    content, mock_output: mockOutput, dry_run: !apply, apply: !!apply,
  }),
  getBenchAuthoring: () => http.get('/api/benchs/authoring'),
  // 内置技能清单（Settings → Skills）
  getSkills: () => http.get('/api/skills'),
  downloadSkill: (id) => http.get(`/api/skills/${id}/download`, { responseType: 'blob' }),
  // Providers（推理服务提供方）：多 Provider 管理，激活项同步到 api
  listProviders: () => http.get('/api/config/providers'),
  addProvider: (data) => http.post('/api/config/providers', data),
  updateProvider: (id, data) => http.put(`/api/config/providers/${id}`, data),
  deleteProvider: (id) => http.delete(`/api/config/providers/${id}`),
  activateProvider: (id) => http.post(`/api/config/providers/${id}/activate`),
  // 引擎参数清单（随引擎切换，每个引擎一套）
  getBenchParamsYaml: (engineId) => http.get(`/api/benchs/${engineId}/params-yaml`),
  saveBenchParamsYaml: (engineId, content) =>
    http.put(`/api/benchs/${engineId}/params-yaml`, { content }),
  // 上传引擎包（yaml 定义 / tar.gz 技能包）
  uploadBenchEngine: (file, onProgress) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/api/benchs/upload', form, { timeout: 120000, onUploadProgress: onProgress })
  },

  // 缓存目录管理
  getDirs: () => http.get('/api/config/dirs'),
  updateDirs: (patch) => http.post('/api/config/dirs', patch),
  restartService: (migrate) => http.post('/api/config/restart', { migrate }),

  // 任务
  listTasks: () => http.get('/api/tasks'),
  getTask: (taskId) => http.get(`/api/tasks/${taskId}`),
  getTaskLogs: (taskId) => http.get(`/api/tasks/${taskId}/logs`),
  createTask: (payload) => http.post('/api/tasks', payload),
  startTask: (taskId) => http.post(`/api/tasks/${taskId}/start`),
  stopTask: (taskId) => http.post(`/api/tasks/${taskId}/stop`),
  deleteTask: (taskId) => http.delete(`/api/tasks/${taskId}`),
  updateTaskThreshold: (taskId, thresholdMs) => http.patch(`/api/tasks/${taskId}/threshold`, { tpot_threshold_ms: thresholdMs }),
  previewTask: (payload) => http.post('/api/tasks/preview', payload),
  exportTaskExcel: (taskId, payload) => http.post(`/api/tasks/${taskId}/export`, payload, { responseType: 'blob' }),

  // Dashboard
  getDashboardStats: () => http.get('/api/dashboard/stats'),
  getDashboardEnv: () => http.get('/api/dashboard/env'),

  // 日志
  listRuns: () => http.get('/api/logs/runs'),
  getRun: (runId) => http.get(`/api/logs/runs/${runId}`),
  getRunLive: (runId) => http.get(`/api/logs/runs/${runId}/live`),
  deleteRun: (runId) => http.delete(`/api/logs/runs/${runId}`),
  previewFile: (runId, name) =>
    http.get(`/api/logs/runs/${runId}/preview`, { params: { name } }),
  downloadUrl: (runId, name) => `/api/logs/runs/${runId}/download?name=${encodeURIComponent(name)}`,
  backupRun: (runId) => http.get(`/api/logs/runs/${runId}/backup`, { responseType: 'blob' }),
  importRun: (formData, onProgress) =>
    http.post('/api/logs/runs/import', formData, { timeout: 120000, onUploadProgress: onProgress }),
  runSummary: (runId, threshold) =>
    http.get(`/api/logs/runs/${runId}/summary`, { params: { threshold } }),
  listDatasets: () => http.get('/api/logs/datasets'),
  uploadDataset: (file) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/api/logs/datasets/upload', form, { timeout: 120000 })
  },
  deleteDataset: (name) => http.delete(`/api/logs/datasets/${encodeURIComponent(name)}`),
  sharegptStatus: () => http.get('/api/logs/datasets/sharegpt'),
  sharegptDownload: () => http.post('/api/logs/datasets/sharegpt/download'),

  // 会话
  listSessions: () => http.get('/api/sessions'),
  createSession: (data) => http.post('/api/sessions', data),
  getSession: (id) => http.get(`/api/sessions/${id}`),
  deleteSession: (id) => http.delete(`/api/sessions/${id}`),
  renameSession: (id, title) => http.patch(`/api/sessions/${id}/title`, { title }),
  updateSessionPerf: (id, perf) => http.patch(`/api/sessions/${id}/perf`, { perf }),
  clearSessions: () => http.delete('/api/sessions'),
  chatUrl: (sessionId) => `/api/sessions/${sessionId}/chat`,

  // 精度测试（Accuracy，独立模块）
  listAccTasks: () => http.get('/api/accuracy/tasks'),
  createAccTask: (payload) => http.post('/api/accuracy/tasks', payload),
  getAccTask: (taskId) => http.get(`/api/accuracy/tasks/${taskId}`),
  stopAccTask: (taskId) => http.post(`/api/accuracy/tasks/${taskId}/stop`),
  deleteAccTask: (taskId) => http.delete(`/api/accuracy/tasks/${taskId}`),
  listAccSamples: (taskId, params) => http.get(`/api/accuracy/tasks/${taskId}/samples`, { params }),
  exportAccSamplesUrl: (taskId, filter) => `/api/accuracy/tasks/${taskId}/export-samples?filter=${filter}`,
  getAccBenchmark: (taskId) => http.get(`/api/accuracy/tasks/${taskId}/benchmark`),
  listAccEngines: () => http.get('/api/accuracy/engines'),
  checkAccEngineEnv: (engineId) => http.get(`/api/accuracy/engines/${engineId}/env-check`),
  listAccDatasets: () => http.get('/api/accuracy/datasets'),
  importAccDataset: (file, name) => {
    const form = new FormData()
    form.append('file', file)
    return http.post(`/api/accuracy/datasets/import?name=${encodeURIComponent(name || '')}`, form, { timeout: 120000 })
  },
  deleteAccDataset: (id) => http.delete(`/api/accuracy/datasets/${encodeURIComponent(id)}`),
  previewAccDataset: (ref) => http.post('/api/accuracy/datasets/preview', ref),
  statsAccDataset: (ref) => http.post('/api/accuracy/datasets/stats', ref, { timeout: 120000 }),
  estimateAcc: (params) => http.get('/api/accuracy/estimate', { params }),
  getBaselines: () => http.get('/api/accuracy/baselines'),
  saveBaselines: (content) => http.put('/api/accuracy/baselines', { content }),
  compareAccTasks: (taskIds) => http.post('/api/accuracy/compare', { task_ids: taskIds }),
}

export function wsUrl() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/ws`
}

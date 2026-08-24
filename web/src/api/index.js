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
  // 配置
  getConfig: () => http.get('/api/config'),
  updateConfig: (patch) => http.post('/api/config', patch),
  getStatus: () => http.get('/api/config/status'),
  getModels: () => http.get('/api/config/models'),
  testConnection: (data) => http.post('/api/config/test-connection', data),
  getGpu: () => http.get('/api/config/gpu'),
  getParams: (framework) => http.get(`/api/config/params/${framework}`),

  // 测试
  startTest: (payload) => http.post('/api/test/start', payload),
  stopTest: () => http.post('/api/test/stop'),
  testStatus: () => http.get('/api/test/status'),
  previewTest: (payload) => http.post('/api/test/preview', payload),

  // 日志
  listRuns: () => http.get('/api/logs/runs'),
  getRun: (runId) => http.get(`/api/logs/runs/${runId}`),
  previewFile: (runId, name) =>
    http.get(`/api/logs/runs/${runId}/preview`, { params: { name } }),
  downloadUrl: (runId, name) => `/api/logs/runs/${runId}/download?name=${encodeURIComponent(name)}`,
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
}

export function wsUrl() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/ws`
}

import { defineStore } from 'pinia'
import { api } from '@/api'

export const useConfigStore = defineStore('config', {
  state: () => ({
    config: null,
    status: { web: 'offline', inference: 'offline', models: [], last_check: null, error: null },
    gpu: { auto_detected: null, config: { auto: true, name: '', count: 8 } },
    params: { vllm: [], sglang: [] },
    loading: false,
  }),
  getters: {
    apiBase: (s) => s.config?.api?.base_url || '',
    frameworkName: () => ({ vllm: 'vLLM', sglang: 'SGLang' }),
  },
  actions: {
    async load() {
      this.loading = true
      try {
        const [config, status, gpu] = await Promise.all([
          api.getConfig(),
          api.getStatus().catch(() => null),
          api.getGpu().catch(() => null),
        ])
        this.config = config
        if (status) this.status = status
        if (gpu) this.gpu = gpu
      } finally {
        this.loading = false
      }
    },
    async loadParams(framework) {
      if (!this.params[framework]?.length) {
        try {
          const resp = await api.getParams(framework)
          this.params[framework] = resp.params || []
        } catch {
          this.params[framework] = []
        }
      }
      return this.params[framework]
    },
    async save(patch) {
      this.config = await api.updateConfig(patch)
      return this.config
    },
    async refreshStatus() {
      try {
        this.status = await api.getStatus()
      } catch {
        /* 忽略 */
      }
    },
    applyStatus(payload) {
      if (payload?.status) this.status = payload.status
    },
  },
})

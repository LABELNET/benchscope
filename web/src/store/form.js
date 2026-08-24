import { defineStore } from 'pinia'

/**
 * 测试表单共享状态：跨「推理服务面板 / 测试配置面板 / 测试进度面板」共享。
 * 模型选择在推理服务面板，其余配置在测试配置面板，开始测试时由 DatasetTab 汇总。
 */
export const useTestForm = defineStore('testForm', {
  state: () => ({
    model: '',
    tokenizer: '',
    precision: '',
    tpot_threshold_ms: 100,
    concurrency_list: [1, 4, 8, 16, 32, 40, 64, 128],
    request_rate: 'inf',
    gpu: { auto: true, name: '', count: 8 },
    force: false,
    extra_args: [],
    curated: {},
    _initialized: false,
  }),
  actions: {
    initFromConfig(config, gpu) {
      if (this._initialized) return
      if (config?.tpot_threshold_ms) this.tpot_threshold_ms = config.tpot_threshold_ms
      if (config?.request_rate) this.request_rate = config.request_rate
      if (gpu?.config) {
        this.gpu.name = gpu.config.name || ''
        this.gpu.count = gpu.config.count || 8
        this.gpu.auto = gpu.config.auto ?? true
      }
      this._initialized = true
    },
    initCurated(schema) {
      if (Object.keys(this.curated).length) return
      for (const p of schema || []) {
        if (p.default !== undefined && p.default !== null) this.curated[p.key] = p.default
      }
    },
  },
})

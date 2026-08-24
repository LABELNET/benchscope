import { defineStore } from 'pinia'
import { api, wsUrl } from '@/api'

let socket = null
let reconnectTimer = null

export const useTestStore = defineStore('test', {
  state: () => ({
    connected: false,
    running: false,
    run: null,          // 当前 run 快照（含 rows）
    rows: [],           // 结果行（实时）
    logLines: [],       // 当前 run 实时日志行（上限 8000）
    currentCase: '',    // 实时日志所属用例
    currentConc: null,
    error: null,
    lastRunId: null,
  }),
  getters: {
    resultsByCase: (s) => {
      const map = {}
      for (const r of s.rows) {
        const label = r.label || r.case || 'unknown'
        if (r.metrics) {
          if (!map[label]) map[label] = []
          map[label].push(r)
        }
      }
      return map
    },
  },
  actions: {
    connect() {
      if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return
      try {
        socket = new WebSocket(wsUrl())
      } catch {
        return
      }
      socket.onopen = () => {
        this.connected = true
      }
      socket.onclose = () => {
        this.connected = false
        clearTimeout(reconnectTimer)
        reconnectTimer = setTimeout(() => this.connect(), 3000)
      }
      socket.onerror = () => {
        this.connected = false
      }
      socket.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          this.handleMessage(msg)
        } catch {
          /* 忽略 */
        }
      }
    },
    handleMessage(msg) {
      switch (msg.type) {
        case 'status':
          useConfigStore().applyStatus(msg)
          break
        case 'run_started':
        case 'run_snapshot':
          this.run = msg.run
          this.lastRunId = msg.run?.run_id
          this.rows = msg.run?.rows || []
          this.running = msg.run?.status === 'running'
          this.logLines = []
          this.error = null
          break
        case 'log_line':
          if (msg.run_id !== this.lastRunId && this.lastRunId) return
          this.currentCase = msg.case
          this.currentConc = msg.concurrency
          this.logLines.push(msg.line)
          if (this.logLines.length > 8000) this.logLines.splice(0, this.logLines.length - 8000)
          break
        case 'result': {
          if (msg.run_id !== this.lastRunId && this.lastRunId) return
          const row = msg.row
          const idx = this.rows.findIndex(
            (r) => r.label === row.label && r.concurrency === row.concurrency,
          )
          if (idx >= 0) this.rows.splice(idx, 1, row)
          else this.rows.push(row)
          break
        }
        case 'run_done':
          if (msg.run) {
            this.run = msg.run
            this.rows = msg.run.rows || this.rows
          }
          this.running = false
          break
        case 'run_error':
          this.running = false
          this.error = msg.error
          if (msg.run) this.run = msg.run
          break
      }
    },
    async start(payload) {
      this.error = null
      const resp = await api.startTest(payload)
      return resp
    },
    async stop() {
      await api.stopTest()
    },
    async refresh() {
      try {
        const resp = await api.testStatus()
        this.running = resp.running
        if (resp.run) {
          this.run = resp.run
          this.lastRunId = resp.run.run_id
          if (resp.run.rows) this.rows = resp.run.rows
        }
      } catch {
        /* 忽略 */
      }
    },
    clear() {
      this.rows = []
      this.logLines = []
      this.run = null
      this.error = null
    },
  },
})

// 便捷引用，避免循环依赖
import { useConfigStore } from './config'

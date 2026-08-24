import { defineStore } from 'pinia'
import { api, wsUrl } from '@/api'
import { useConfigStore } from './config'

let socket = null
let reconnectTimer = null

export const useTestStore = defineStore('test', {
  state: () => ({
    connected: false,
    tasks: {},           // task_id -> task snapshot
    activeTaskId: null,  // 当前查看的任务
    logLines: {},        // task_id -> log lines
    currentCase: '',
    currentConc: null,
  }),
  getters: {
    taskList: (s) => Object.values(s.tasks).sort((a, b) => (b.created_at || '').localeCompare(a.created_at || '')),
    activeTask: (s) => s.tasks[s.activeTaskId] || null,
    activeLogs: (s) => s.logLines[s.activeTaskId] || [],
    runningTasks: (s) => Object.values(s.tasks).filter((t) => t.status === 'running'),
  },
  actions: {
    connect() {
      if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return
      try {
        socket = new WebSocket(wsUrl())
      } catch { return }
      socket.onopen = () => { this.connected = true }
      socket.onclose = () => {
        this.connected = false
        clearTimeout(reconnectTimer)
        reconnectTimer = setTimeout(() => this.connect(), 3000)
      }
      socket.onerror = () => { this.connected = false }
      socket.onmessage = (ev) => {
        try { this.handleMessage(JSON.parse(ev.data)) } catch { /* ignore */ }
      }
    },
    handleMessage(msg) {
      switch (msg.type) {
        case 'status':
          useConfigStore().applyStatus(msg)
          break
        case 'task_snapshot':
        case 'task_started':
          if (msg.task) this.tasks[msg.task_id] = msg.task
          break
        case 'task_result': {
          const task = this.tasks[msg.task_id]
          if (!task) break
          const row = msg.row
          if (!task.rows) task.rows = []
          const idx = task.rows.findIndex((r) => r.label === row.label && r.concurrency === row.concurrency)
          if (idx >= 0) task.rows.splice(idx, 1, row)
          else task.rows.push(row)
          break
        }
        case 'task_log':
          if (!this.logLines[msg.task_id]) this.logLines[msg.task_id] = []
          this.currentCase = msg.case
          this.currentConc = msg.concurrency
          const lines = this.logLines[msg.task_id]
          lines.push(msg.line)
          if (lines.length > 8000) lines.splice(0, lines.length - 8000)
          break
        case 'task_done':
          if (msg.task) this.tasks[msg.task_id] = msg.task
          break
        case 'task_error':
          if (msg.task) this.tasks[msg.task_id] = msg.task
          break
      }
    },
    setActiveTask(taskId) {
      this.activeTaskId = taskId
    },
    async loadTasks() {
      try {
        const resp = await api.listTasks()
        for (const t of resp.tasks || []) {
          this.tasks[t.task_id] = t
        }
      } catch { /* ignore */ }
    },
    async createTask(payload) {
      const resp = await api.createTask(payload)
      if (resp.task) this.tasks[resp.task_id] = resp.task
      return resp
    },
    async startTask(taskId) {
      const resp = await api.startTask(taskId)
      if (resp.task) this.tasks[resp.task_id] = resp.task
      return resp
    },
    async stopTask(taskId) {
      await api.stopTask(taskId)
    },
    async deleteTask(taskId) {
      await api.deleteTask(taskId)
      delete this.tasks[taskId]
      delete this.logLines[taskId]
    },
  },
})

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
    currentPos: {},      // task_id -> { case, concurrency } 当前正在执行的位置(仅 running 时有效)
  }),
  getters: {
    taskList: (s) => Object.values(s.tasks).sort((a, b) => (b.created_at || '').localeCompare(a.created_at || '')),
    activeTask: (s) => s.tasks[s.activeTaskId] || null,
    activeLogs: (s) => s.logLines[s.activeTaskId] || [],
    runningTasks: (s) => Object.values(s.tasks).filter((t) => t.status === 'running'),
    // 单任务语义：返回最新一个任务（无任务返回 null）
    theTask: (s) => {
      const list = Object.values(s.tasks).sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
      return list[0] || null
    },
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
          // 该并发已完成:若当前位置匹配则清出,以便推进到下一个并发
          const pos = this.currentPos[msg.task_id]
          if (pos && pos.case === row.label && pos.concurrency === row.concurrency) {
            this.currentPos[msg.task_id] = null
          }
          break
        }
        case 'task_log':
          if (!this.logLines[msg.task_id]) this.logLines[msg.task_id] = []
          this.currentPos[msg.task_id] = { case: msg.case, concurrency: msg.concurrency }
          const lines = this.logLines[msg.task_id]
          lines.push(msg.line)
          if (lines.length > 8000) lines.splice(0, lines.length - 8000)
          break
        case 'task_done':
        case 'task_error': {
          // 停止的任务:用户已点"停止",停止后恢复默认界面 → 后台清理并移除
          if (msg.task && msg.task.status === 'stopped') {
            delete this.tasks[msg.task_id]
            delete this.logLines[msg.task_id]
            delete this.currentPos[msg.task_id]
            api.deleteTask(msg.task_id).catch(() => {})
          } else if (msg.task) {
            this.tasks[msg.task_id] = msg.task
          }
          // 任务结束:清出当前位置,避免残留高亮
          this.currentPos[msg.task_id] = null
          break
        }
        case 'task_updated':
          // 阈值等字段更新
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
    async loadTask(taskId) {
      // 拉取完整快照(含 rows),list_tasks 不带 rows,刷新后需补全实时数据
      try {
        const snap = await api.getTask(taskId)
        if (snap) this.tasks[taskId] = snap
      } catch { /* ignore */ }
    },
    async loadTaskLogs(taskId) {
      // 拉取整条测试日志(full.log)，用于详情页 Terminal 历史回放
      // 后端写文件先于广播 WS，故历史响应是当前 logLines 的超集；
      // 仅 fetch 期间到达的 WS 行不在历史响应内，需保留这些末尾额外行
      try {
        const resp = await api.getTaskLogs(taskId)
        const historical = resp.lines || []
        const cur = this.logLines[taskId] || []
        if (!historical.length) return
        if (!cur.length) {
          this.logLines[taskId] = historical
          return
        }
        // 定位 historical 末行在 cur 中的位置：其后即为 fetch 期间到达的 WS 行
        const lastHist = historical[historical.length - 1]
        let alignIdx = -1
        for (let i = cur.length - 1; i >= 0; i--) {
          if (cur[i] === lastHist) { alignIdx = i; break }
        }
        if (alignIdx >= 0 && alignIdx < cur.length - 1) {
          this.logLines[taskId] = historical.concat(cur.slice(alignIdx + 1))
        } else {
          this.logLines[taskId] = historical
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
      delete this.currentPos[taskId]
    },
    async updateThreshold(taskId, thresholdMs) {
      const snap = await api.updateTaskThreshold(taskId, thresholdMs)
      if (snap) this.tasks[taskId] = snap
      return snap
    },
  },
})

import { defineStore } from 'pinia'
import { api } from '@/api'

// 独立精度测试模块 store：复用 useTestStore 的 WebSocket 连接（eval_task_* 消息族）
export const useAccuracyStore = defineStore('accuracy', {
  state: () => ({
    tasks: {},          // task_id -> task snapshot（含 result）
    activeTaskId: null, // 当前查看的任务
    logLines: {},       // task_id -> 终端日志行
    samples: {},        // task_id -> 实时逐题结果（running 时累加，done 后以 API 分页为准）
    selectedIds: [],    // Datas/evals 对比选择
  }),
  getters: {
    taskList: (s) => Object.values(s.tasks).sort((a, b) => (b.created_at || '').localeCompare(a.created_at || '')),
    activeTask: (s) => s.tasks[s.activeTaskId] || null,
    activeLogs: (s) => s.logLines[s.activeTaskId] || [],
    runningTasks: (s) => Object.values(s.tasks).filter((t) => t.status === 'running'),
  },
  actions: {
    handleEvalMessage(msg) {
      switch (msg.type) {
        case 'eval_task_snapshot':
        case 'eval_task_started':
          if (msg.task) {
            // WS 回放的列表快照不带 result：本地已有完整详情（含 result）时保留，避免覆盖
            const id = msg.task.task_id || msg.task_id
            const cur = this.tasks[id]
            if (cur && cur.result != null && msg.task.result == null) {
              msg.task.result = cur.result
            }
            this.tasks[id] = msg.task
          }
          break
        case 'eval_task_log': {
          const id = msg.task_id
          if (!this.logLines[id]) this.logLines[id] = []
          this.logLines[id].push(msg.line)
          const lines = this.logLines[id]
          if (lines.length > 8000) lines.splice(0, lines.length - 8000)
          break
        }
        case 'eval_task_progress': {
          const task = this.tasks[msg.task_id]
          if (task && msg.progress) task.progress = msg.progress
          break
        }
        case 'eval_task_result': {
          const task = this.tasks[msg.task_id]
          if (task) {
            task.progress = { done: (task.progress?.done || 0) + 1, total: Math.max(task.progress?.total || 0, (task.progress?.done || 0) + 1) }
          }
          if (!this.samples[msg.task_id]) this.samples[msg.task_id] = []
          const arr = this.samples[msg.task_id]
          arr.push(msg.sample)
          if (arr.length > 500) arr.splice(0, arr.length - 500)
          break
        }
        case 'eval_task_done':
        case 'eval_task_error':
          if (msg.task) this.tasks[msg.task.task_id || msg.task_id] = msg.task
          break
      }
    },
    setActive(taskId) {
      this.activeTaskId = taskId
    },
    async loadTasks() {
      try {
        const resp = await api.listAccTasks()
        for (const t of resp.tasks || []) this.tasks[t.task_id] = t
      } catch { /* ignore */ }
    },
    async loadTask(taskId) {
      try {
        const resp = await api.getAccTask(taskId)
        if (resp?.task) this.tasks[taskId] = resp.task
      } catch { /* ignore */ }
    },
    async createTask(payload) {
      const resp = await api.createAccTask(payload)
      if (resp.task) {
        this.tasks[resp.task.task_id] = resp.task
        this.activeTaskId = resp.task.task_id
      }
      return resp
    },
    async deleteTask(taskId) {
      await api.deleteAccTask(taskId)
      delete this.tasks[taskId]
      delete this.logLines[taskId]
      delete this.samples[taskId]
      if (this.activeTaskId === taskId) this.activeTaskId = null
      this.selectedIds = this.selectedIds.filter((id) => id !== taskId)
    },
  },
})

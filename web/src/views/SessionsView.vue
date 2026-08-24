<template>
  <div class="sessions-page">
    <!-- 左侧栏 -->
    <div class="sidebar">
      <div class="sidebar-top">
        <a-button block class="new-session-btn" @click="createSession">
          <template #icon><smile-outlined /></template>
          {{ t('newSession') }}
        </a-button>
      </div>

      <div class="workspaces-section">
        <div class="workspaces-header">
          <span class="workspaces-label">{{ t('chats') }}</span>
        </div>
        <div class="session-list">
          <div
            v-for="s in sessions"
            :key="s.session_id"
            class="session-item"
            :class="{ active: activeId === s.session_id }"
            @click="selectSession(s.session_id)"
          >
            <message-outlined class="session-icon" />
            <span class="session-name">{{ s.title }}</span>
            <a-popconfirm :title="t('clearConfirm')" @confirm="deleteSession(s.session_id)" ok-text="OK" cancel-text="Cancel">
              <close-outlined class="session-close" @click.stop />
            </a-popconfirm>
          </div>
          <a-empty v-if="!sessions.length" :description="t('noData')" :image-style="{ height: '40px' }" style="padding: 20px 0" />
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-area">
      <template v-if="activeSession">
        <!-- 消息列表 -->
        <div class="chat-messages" ref="msgBox">
          <div v-for="(msg, i) in displayMessages" :key="i" class="msg-row" :class="msg.role">
            <div class="msg-avatar">
              <div v-if="msg.role === 'user'" class="avatar user-avatar">U</div>
              <div v-else class="avatar ai-avatar">
                <img src="/bs-logo.png" alt="AI" class="avatar-img" />
              </div>
            </div>
            <div class="msg-content-wrap">
              <!-- 思考过程 -->
              <div v-if="msg.thinking" class="thinking-block">
                <div class="thinking-header" @click="msg._thinkingOpen = !msg._thinkingOpen">
                  <down-outlined :rotate="msg._thinkingOpen ? 0 : -90" class="thinking-arrow" />
                  <span class="thinking-label">{{ t('thinking') }}</span>
                </div>
                <div v-show="msg._thinkingOpen !== false" class="thinking-content">
                  <div class="thinking-text">{{ msg.thinking }}</div>
                </div>
              </div>
              <!-- 回复内容 -->
              <div v-if="msg.content" class="reply-content" v-html="renderMarkdown(msg.content)"></div>
            </div>
          </div>
          <!-- 流式输出中 -->
          <div v-if="streaming" class="msg-row assistant">
            <div class="msg-avatar">
              <div class="avatar ai-avatar">
                <img src="/bs-logo.png" alt="AI" class="avatar-img" />
              </div>
            </div>
            <div class="msg-content-wrap">
              <div v-if="streamThinking" class="thinking-block">
                <div class="thinking-header">
                  <span class="thinking-label">{{ t('thinking') }}</span>
                  <span class="thinking-dots"><span></span><span></span><span></span></span>
                </div>
                <div class="thinking-content">
                  <div class="thinking-text">{{ streamThinking }}<span class="cursor-blink">|</span></div>
                </div>
              </div>
              <div v-if="streamBuffer" class="reply-content" v-html="renderMarkdown(streamBuffer)"></div>
              <div v-if="!streamBuffer && !streamThinking" class="reply-content">
                <span class="cursor-blink">|</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部输入栏 -->
        <div class="input-bar">
          <div class="input-container">
            <div class="input-box">
              <a-textarea
                v-model:value="inputText"
                :placeholder="t('messagePlaceholder')"
                :auto-size="{ minRows: 1, maxRows: 6 }"
                @pressEnter="onInputEnter"
                :disabled="streaming"
                bordered
                class="chat-textarea"
              />
              <div class="input-bottom-row">
                <div class="input-left">
                  <a-tooltip title="Upload file">
                    <paper-clip-outlined class="attach-icon" />
                  </a-tooltip>
                  <a-tooltip title="Web search">
                    <global-outlined class="attach-icon" />
                  </a-tooltip>
                </div>
                <div class="input-right">
                  <span class="model-name">{{ selectedModel || 'No model' }}</span>
                  <a-select v-model:value="qualityLevel" size="small" :bordered="false" style="width: 70px" class="quality-select">
                    <a-select-option value="high">High</a-select-option>
                    <a-select-option value="medium">Medium</a-select-option>
                    <a-select-option value="low">Low</a-select-option>
                  </a-select>
                  <div v-if="streaming" class="loading-spinner"></div>
                  <a-button
                    type="primary"
                    shape="circle"
                    size="large"
                    @click="sendMessage"
                    :disabled="!inputText.trim()"
                    class="send-btn"
                  >
                    <template #icon><arrow-up-outlined /></template>
                  </a-button>
                </div>
              </div>
            </div>
            <!-- 性能提示栏 -->
            <div v-if="perfStats.turns > 0" class="perf-bar">
              <span class="perf-item">{{ perfStats.turns }} turns · {{ perfStats.steps }} steps</span>
              <span class="perf-sep">|</span>
              <span class="perf-item">LLM {{ perfStats.llmTime }}</span>
              <span class="perf-sep">|</span>
              <span class="perf-item">TTFT avg {{ perfStats.ttft }} · {{ perfStats.tokPerSec }} tok/s</span>
              <span class="perf-sep">|</span>
              <span class="perf-item">Cache hit {{ perfStats.cacheHit }}</span>
              <span class="perf-sep">|</span>
              <span class="perf-item">Input {{ perfStats.inputTokens }} tok</span>
            </div>
          </div>
        </div>
      </template>

      <div v-else class="empty-state">
        <a-empty :description="t('noSession')" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { SmileOutlined, MessageOutlined, CloseOutlined, DownOutlined, ArrowUpOutlined, PaperClipOutlined, GlobalOutlined } from '@ant-design/icons-vue'
import { api } from '@/api'
import { useConfigStore } from '@/store/config'
import { t } from '@/i18n'

const config = useConfigStore()
const sessions = ref([])
const activeId = ref(null)
const activeSession = ref(null)
const inputText = ref('')
const streaming = ref(false)
const streamBuffer = ref('')
const streamThinking = ref('')
const msgBox = ref(null)
const qualityLevel = ref('high')

// 性能统计
const perfStats = ref({
  turns: 0,
  steps: 0,
  llmTime: '0s',
  ttft: '0s',
  tokPerSec: '0',
  cacheHit: '0%',
  inputTokens: '0',
})

const modelOptions = computed(() => (config.status?.models || []).map((m) => ({ value: m, label: m })))

// 本地记住的模型选择（与 TopBar 共享 localStorage）
const localModelKey = 'benchscope_chat_model'
const selectedModel = ref(localStorage.getItem(localModelKey) || '')

// 当模型列表加载后，默认选第一个
watch(modelOptions, (opts) => {
  if (opts.length && !opts.find(o => o.value === selectedModel.value)) {
    selectedModel.value = opts[0].value
    localStorage.setItem(localModelKey, selectedModel.value)
  }
}, { immediate: true })

const displayMessages = computed(() => {
  if (!activeSession.value?.messages) return []
  return activeSession.value.messages
    .filter(m => m.role !== 'system')
    .map(m => ({
      ...m,
      _thinkingOpen: m._thinkingOpen !== undefined ? m._thinkingOpen : true,
    }))
})

// ===== Markdown 渲染 =====
function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function renderMarkdown(text) {
  if (!text) return ''
  const lines = text.split('\n')
  let html = ''
  let inCodeBlock = false
  let codeLines = []
  let codeLang = ''

  const flushCode = () => {
    if (codeLines.length) {
      const codeText = escapeHtml(codeLines.join('\n'))
      html += `<div class="code-block"><div class="code-header"><span class="code-lang">${codeLang || 'code'}</span><button class="copy-btn" onclick="navigator.clipboard.writeText(this.parentElement.nextElementSibling.textContent).then(()=>this.textContent='Copied!')">Copy</button></div><pre><code>${codeText}</code></pre></div>`
    }
    codeLines = []
    codeLang = ''
  }

  for (const line of lines) {
    if (line.startsWith('```')) {
      if (inCodeBlock) { flushCode(); inCodeBlock = false }
      else { inCodeBlock = true; codeLang = line.slice(3).trim() }
      continue
    }
    if (inCodeBlock) { codeLines.push(line); continue }

    if (line.trim() === '') { html += '<br/>'; continue }

    let processed = escapeHtml(line)
    // inline code
    processed = processed.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    // bold
    processed = processed.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // italic
    processed = processed.replace(/\*(.+?)\*/g, '<em>$1</em>')

    if (line.startsWith('- ') || line.startsWith('* ')) {
      html += `<div class="bullet-line"><span class="bullet-dot">•</span><span>${processed.slice(2)}</span></div>`
    } else if (/^\d+\.\s/.test(line)) {
      const num = line.match(/^(\d+)\./)[1]
      html += `<div class="bullet-line"><span class="bullet-num">${num}.</span><span>${processed.replace(/^\d+\.\s/, '')}</span></div>`
    } else {
      html += `<div class="text-line">${processed}</div>`
    }
  }
  if (inCodeBlock) flushCode()
  return html
}

async function loadSessions() {
  try {
    const resp = await api.listSessions()
    sessions.value = resp.sessions || []
  } catch { /* ignore */ }
}

async function selectSession(id) {
  activeId.value = id
  try {
    const resp = await api.getSession(id)
    activeSession.value = resp
    await nextTick()
    scrollToBottom()
  } catch (e) { message.error(e.message) }
}

async function createSession() {
  try {
    const resp = await api.createSession({ model: selectedModel.value || '' })
    await loadSessions()
    if (resp.session) {
      await selectSession(resp.session.session_id)
    }
  } catch (e) { message.error(e.message) }
}

async function deleteSession(id) {
  try {
    await api.deleteSession(id)
    if (activeId.value === id) {
      activeId.value = null
      activeSession.value = null
    }
    await loadSessions()
  } catch (e) { message.error(e.message) }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || !activeId.value || streaming.value) return

  const userMsg = {
    role: 'user',
    content: text,
    timestamp: new Date().toISOString().slice(0, 19).replace('T', ' '),
    model: selectedModel.value || '',
    _thinkingOpen: true,
  }
  if (!activeSession.value.messages) activeSession.value.messages = []
  activeSession.value.messages.push(userMsg)
  inputText.value = ''
  await nextTick()
  scrollToBottom()

  streaming.value = true
  streamBuffer.value = ''
  streamThinking.value = ''
  let assistantContent = ''
  let assistantThinking = ''
  const startTime = Date.now()
  let firstTokenTime = 0
  let tokenCount = 0

  try {
    const resp = await fetch(api.chatUrl(activeId.value), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, model: selectedModel.value || undefined }),
    })

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const dataStr = line.slice(6).trim()
        if (!dataStr) continue
        try {
          const data = JSON.parse(dataStr)
          if (data.token) {
            tokenCount++
            if (!firstTokenTime) firstTokenTime = Date.now()
            assistantContent += data.token
            streamBuffer.value = assistantContent
            scrollToBottom()
          }
          if (data.thinking) {
            assistantThinking += data.thinking
            streamThinking.value = assistantThinking
            scrollToBottom()
          }
          if (data.error) message.error(data.error)
        } catch { /* ignore */ }
      }
    }

    // 完成后将 assistant 消息加入列表
    if (assistantContent || assistantThinking) {
      activeSession.value.messages.push({
        role: 'assistant',
        content: assistantContent,
        thinking: assistantThinking || '',
        timestamp: new Date().toISOString().slice(0, 19).replace('T', ' '),
        model: selectedModel.value || '',
        _thinkingOpen: true,
      })
    }

    // 计算性能统计
    const elapsed = Date.now() - startTime
    const ttftSec = firstTokenTime ? ((firstTokenTime - startTime) / 1000).toFixed(1) : '0'
    const tokPerSec = elapsed > 0 ? Math.round(tokenCount / (elapsed / 1000)) : 0
    const userMsgs = activeSession.value.messages.filter(m => m.role === 'user').length
    const asstMsgs = activeSession.value.messages.filter(m => m.role === 'assistant').length
    perfStats.value = {
      turns: userMsgs,
      steps: userMsgs + asstMsgs,
      llmTime: formatDuration(elapsed),
      ttft: `${ttftSec}s`,
      tokPerSec: String(tokPerSec),
      cacheHit: '—',
      inputTokens: String(tokenCount),
    }

    await loadSessions()
  } catch (e) {
    message.error(e.message)
  } finally {
    streaming.value = false
    streamBuffer.value = ''
    streamThinking.value = ''
  }
}

function onInputEnter(e) {
  if (e.shiftKey) return
  e.preventDefault()
  sendMessage()
}

function scrollToBottom() {
  if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
}

function formatDuration(ms) {
  const totalSec = Math.floor(ms / 1000)
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  if (m > 0) return `${m}m${String(s).padStart(2, '0')}s`
  return `${totalSec}s`
}

onMounted(() => {
  loadSessions()
  config.refreshStatus()
  // 如果没有本地记住的模型，默认选第一个
  if (!selectedModel.value && modelOptions.value.length) {
    selectedModel.value = modelOptions.value[0].value
    localStorage.setItem(localModelKey, selectedModel.value)
  }
})
</script>

<style scoped>
.sessions-page {
  display: flex;
  height: 100%;
  overflow: hidden;
  background: #fff;
}

/* ===== 左侧栏 ===== */
.sidebar {
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}

.sidebar-top {
  padding: 12px;
}

.new-session-btn {
  border-radius: 20px;
  height: 40px;
  font-size: 14px;
  border: 1px solid #d9d9d9;
  background: #fff;
  color: #333;
}
.new-session-btn:hover {
  border-color: #1677ff;
  color: #1677ff;
}

.workspaces-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.workspaces-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px 8px;
}

.workspaces-label {
  font-size: 12px;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 2px;
  transition: background 0.2s;
  position: relative;
}
.session-item:hover {
  background: #e6f4ff;
}
.session-item.active {
  background: #bae0ff;
}

.session-icon {
  font-size: 16px;
  color: #1677ff;
  flex-shrink: 0;
}

.session-name {
  flex: 1;
  font-size: 13px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-close {
  font-size: 14px;
  color: #bbb;
  opacity: 0;
  transition: opacity 0.2s;
  flex-shrink: 0;
}
.session-item:hover .session-close {
  opacity: 1;
}
.session-close:hover {
  color: #ff4d4f;
}

/* ===== 主内容区 ===== */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #fff;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

/* ===== 消息行 ===== */
.msg-row {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  align-items: flex-start;
}

.msg-row.user {
  flex-direction: row-reverse;
}

.msg-avatar {
  flex-shrink: 0;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
}

.user-avatar {
  background: #1677ff;
  color: #fff;
}

.ai-avatar {
  background: #f0f5ff;
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.msg-content-wrap {
  max-width: 70%;
  min-width: 120px;
}

.msg-row.user .msg-content-wrap {
  align-items: flex-end;
}

/* ===== 思考块 ===== */
.thinking-block {
  margin-bottom: 8px;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  background: #fafafa;
  overflow: hidden;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  cursor: pointer;
  user-select: none;
}

.thinking-arrow {
  font-size: 12px;
  color: #999;
  transition: transform 0.2s;
}

.thinking-label {
  font-size: 12px;
  color: #999;
  font-weight: 500;
}

.thinking-dots {
  display: flex;
  gap: 3px;
  margin-left: auto;
}

.thinking-dots span {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #999;
  animation: dotPulse 1.4s infinite ease-in-out;
}

.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dotPulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.thinking-content {
  padding: 0 12px 10px;
}

.thinking-text {
  font-size: 13px;
  color: #888;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ===== 回复内容 ===== */
.reply-content {
  font-size: 14px;
  line-height: 1.7;
  color: #333;
  word-break: break-word;
}

.msg-row.user .reply-content {
  background: #1677ff;
  color: #fff;
  padding: 10px 14px;
  border-radius: 12px;
  border-top-right-radius: 4px;
}

.msg-row.assistant .reply-content {
  padding: 2px 0;
}

/* ===== 代码块 ===== */
.code-block {
  margin: 8px 0;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
  background: #fafafa;
}

.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: #f5f5f5;
  border-bottom: 1px solid #e8e8e8;
}

.code-lang {
  font-size: 12px;
  color: #999;
  font-family: monospace;
}

.copy-btn {
  font-size: 12px;
  color: #666;
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 4px;
}
.copy-btn:hover {
  background: #e6f4ff;
  color: #1677ff;
}

.code-block pre {
  margin: 0;
  padding: 12px 16px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
}

.code-block code {
  font-family: 'SF Mono', Monaco, 'Cascadia Code', Consolas, monospace;
}

.inline-code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', Consolas, monospace;
  color: #d4380d;
}

.bullet-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 4px 0;
}

.bullet-dot, .bullet-num {
  color: #999;
  flex-shrink: 0;
  margin-top: 2px;
}

.text-line {
  margin: 4px 0;
}

.cursor-blink {
  animation: blink 1s step-end infinite;
  color: #1677ff;
  font-weight: bold;
}
@keyframes blink {
  50% { opacity: 0; }
}

/* ===== 底部输入栏 ===== */
.input-bar {
  padding: 0 32px 20px;
}

.input-container {
  max-width: 800px;
  margin: 0 auto;
}

.input-box {
  border: 1px solid #e8e8e8;
  border-radius: 20px;
  padding: 12px 16px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input-box:focus-within {
  border-color: #1677ff;
  box-shadow: 0 2px 16px rgba(22, 119, 255, 0.12);
}

.chat-textarea {
  border: none !important;
  box-shadow: none !important;
  resize: none;
  font-size: 15px;
  line-height: 1.6;
  padding: 4px 0 !important;
}
.chat-textarea:focus {
  box-shadow: none !important;
}

.input-bottom-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f5f5f5;
}

.input-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.attach-icon {
  font-size: 16px;
  color: #bbb;
  cursor: pointer;
  transition: color 0.2s;
}
.attach-icon:hover {
  color: #1677ff;
}

.input-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-name {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quality-select {
  font-size: 13px;
}
.quality-select :deep(.ant-select-selector) {
  background: transparent !important;
  color: #1677ff;
  font-weight: 500;
  font-size: 13px;
}

.loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid #e8e8e8;
  border-top-color: #1677ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.send-btn {
  width: 36px !important;
  height: 36px !important;
  min-width: 36px !important;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ===== 性能提示栏 ===== */
.perf-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px 16px;
  margin-top: 8px;
}

.perf-item {
  font-size: 12px;
  color: #999;
  white-space: nowrap;
}

.perf-sep {
  font-size: 12px;
  color: #ddd;
  margin: 0 2px;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>

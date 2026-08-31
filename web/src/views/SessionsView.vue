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
          <a-popconfirm :title="t('clearConfirm')" @confirm="clearAllSessions" ok-text="OK" cancel-text="Cancel">
            <a-button size="small" type="ghost" class="clear-all-btn">{{ t('clearSessions') }}</a-button>
          </a-popconfirm>
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
        <!-- 会话标题栏:推理性能数据（颜色标记所选模型状态：默认红/未选或离线，在线绿） -->
        <div class="chat-header" :class="providerOnline ? 'chat-ok' : 'chat-bad'">
          <div class="perf-bar">
            <span class="perf-item">{{ displayPerf.turns }} turns · {{ displayPerf.steps }} steps</span>
            <span class="perf-sep">|</span>
            <span class="perf-item">LLM {{ displayPerf.llmTime }}</span>
            <span class="perf-sep">|</span>
            <span class="perf-item">TTFT {{ displayPerf.ttft }} · {{ displayPerf.tokPerSec }} tok/s</span>
            <span class="perf-sep">|</span>
            <span class="perf-item">Output {{ displayPerf.tokPerSec }} tok/s</span>
            <span class="perf-sep">|</span>
            <span class="perf-item">TPOT {{ displayPerf.tpot }}</span>
            <span class="perf-sep">|</span>
            <span class="perf-item">ITL {{ displayPerf.itl }}</span>
          </div>
        </div>
        <!-- 消息列表 -->
        <div class="chat-messages" ref="msgBox">
          <div v-for="(msg, i) in displayMessages" :key="i" class="msg-row" :class="msg.role">
            <div class="msg-avatar">
              <div v-if="msg.role === 'user'" class="avatar user-avatar">U</div>
              <div v-else class="avatar ai-avatar">
                <img src="/blue_logo.png" alt="AI" class="avatar-img" />
              </div>
            </div>
            <div class="msg-content-wrap">
              <!-- 思考过程 -->
              <div v-if="msg.thinking" class="thinking-block">
                <div class="thinking-header" @click="msg._thinkingOpen = !msg._thinkingOpen">
                  <down-outlined :rotate="msg._thinkingOpen ? 0 : -90" class="thinking-arrow" />
                  <span class="thinking-label">{{ t('thinkingInProgress') }}</span>
                </div>
                <div v-show="msg._thinkingOpen === true" class="thinking-content">
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
                <img src="/blue_logo.png" alt="AI" class="avatar-img" />
              </div>
            </div>
            <div class="msg-content-wrap">
              <div v-if="streamThinking" class="thinking-block">
                <div class="thinking-header" @click="streamThinkingOpen = !streamThinkingOpen">
                  <down-outlined :rotate="streamThinkingOpen ? 0 : -90" class="thinking-arrow" />
                  <span class="thinking-label">{{ t('thinkingInProgress') }}</span>
                  <span class="thinking-dots"><span></span><span></span><span></span></span>
                </div>
                <div v-show="streamThinkingOpen" class="thinking-content">
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

        <!-- 底部输入栏:输入内容框 + 底部操作(模型/发送靠右) -->
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
                :class="{ 'has-content': inputText.trim() }"
              />
              <div class="input-bottom-row">
                <div class="input-right">
                  <a-select
                    v-model:value="selectedProviderId"
                    :options="providerOptions"
                    size="small"
                    :bordered="false"
                    style="width: 150px"
                    :placeholder="t('selectInferenceProvider')"
                    :loading="providerProbing"
                    @change="onProviderChange"
                  />
                  <a-select
                    v-model:value="selectedModel"
                    :options="modelOptions"
                    size="small"
                    :bordered="false"
                    style="width: 200px"
                    :placeholder="t('selectModelForChat')"
                  />
                  <a-select
                    v-model:value="selectedQuality"
                    :options="qualityOptions"
                    size="small"
                    :bordered="false"
                    style="width: 86px"
                  />
                  <span class="thinking-toggle">
                    <span class="thinking-toggle-label">{{ t('thinking') }}</span>
                    <a-switch v-model:checked="enableThinking" size="small" />
                  </span>
                  <div v-if="streaming" class="loading-spinner"></div>
                  <span
                    class="send-text"
                    :class="{ 'send-active': streaming || (inputText.trim() && !streaming), 'send-stop': streaming }"
                    @click="onSendClick"
                  >{{ streaming ? t('stop') : t('send') }}</span>
                </div>
              </div>
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
import { SmileOutlined, MessageOutlined, CloseOutlined, DownOutlined } from '@ant-design/icons-vue'
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
const streamAbort = ref(null)
const streamThinkingOpen = ref(false)
const msgBox = ref(null)

// 性能统计
const defaultPerf = { turns: 0, steps: 0, llmTime: '0s', ttft: '0s', tokPerSec: '0', inputTokens: '0', tpot: '0ms', itl: '0ms' }
const perfStats = ref({ ...defaultPerf })
const livePerf = ref(null)
const displayPerf = computed(() => (streaming.value && livePerf.value) ? livePerf.value : (activeSession.value?.perf || defaultPerf))

// Provider 选择：联动模型列表；header 颜色标记所选 Provider 状态（默认红，在线绿）
const localProviderKey = 'benchscope_chat_provider'
const providers = ref([])
const selectedProviderId = ref(localStorage.getItem(localProviderKey) || '')
const providerProbing = ref(false)
const providerOnline = ref(false)
const providerModels = ref([])
const providerOptions = computed(() => providers.value.map((p) => ({ value: p.id, label: p.name })))
const modelOptions = computed(() => providerModels.value.map((m) => ({ value: m, label: m })))

// 对话质量 high/medium/low
const qualityOptions = computed(() => [
  { value: 'high', label: t('qualityHigh') },
  { value: 'medium', label: t('qualityMedium') },
  { value: 'low', label: t('qualityLow') },
])
const localQualityKey = 'benchscope_chat_quality'
const selectedQuality = ref(localStorage.getItem(localQualityKey) || 'medium')
watch(selectedQuality, (v) => localStorage.setItem(localQualityKey, v))

// 思考开关
const localThinkingKey = 'benchscope_chat_thinking'
const enableThinking = ref(localStorage.getItem(localThinkingKey) !== 'false')
watch(enableThinking, (v) => localStorage.setItem(localThinkingKey, String(v)))

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
  return activeSession.value.messages.filter(m => m.role !== 'system')
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
    // 恢复该会话的配置与性能数据
    if (resp.quality) selectedQuality.value = resp.quality
    if (resp.enable_thinking !== undefined) enableThinking.value = resp.enable_thinking
    if (resp.model) selectedModel.value = resp.model
    // 思考块默认折叠
    if (resp.messages) {
      resp.messages.forEach(m => { if (m._thinkingOpen === undefined) m._thinkingOpen = false })
    }
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

async function clearAllSessions() {
  try {
    await api.clearSessions()
    sessions.value = []
    activeId.value = null
    activeSession.value = null
    message.success(t('clearSessions'))
  } catch (e) { message.error(e.message) }
}

// 发送/停止按钮(文字):流式中显示"停止"，点击中止数据流；否则有内容才可发送
function onSendClick() {
  if (streaming.value) {
    stopStream()
    return
  }
  if (inputText.value.trim() && !streaming.value) sendMessage()
}

// 停止当前流式：中止请求，数据流立即停止，文字改回"发送"
function stopStream() {
  streamAbort.value?.abort()
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
  streamThinkingOpen.value = false
  streamAbort.value = new AbortController()
  let assistantContent = ''
  let assistantThinking = ''
  const startTime = Date.now()
  let firstTokenTime = 0
  let tokenCount = 0
  let lastTokenTime = 0
  let itlSum = 0
  let itlCount = 0

  // 实时更新顶部性能数据
  const updateLivePerf = () => {
    const now = Date.now()
    const elapsed = now - startTime
    const ttftSec = firstTokenTime ? ((firstTokenTime - startTime) / 1000).toFixed(1) : '0'
    const decodeElapsed = firstTokenTime ? (now - firstTokenTime) : 0
    const tokPerSec = decodeElapsed > 0 ? Math.round(tokenCount / (decodeElapsed / 1000)) : 0
    const tpotMs = tokenCount > 0 ? (decodeElapsed / tokenCount).toFixed(0) : '0'
    const itlMs = itlCount > 0 ? (itlSum / itlCount).toFixed(0) : '0'
    const userMsgs = activeSession.value.messages.filter(m => m.role === 'user').length
    livePerf.value = {
      turns: userMsgs,
      steps: userMsgs + 1,
      llmTime: formatDuration(elapsed),
      ttft: `${ttftSec}s`,
      tokPerSec: String(tokPerSec),
      inputTokens: String(tokenCount),
      tpot: `${tpotMs}ms`,
      itl: `${itlMs}ms`,
    }
  }
  updateLivePerf()

  try {
    const resp = await fetch(api.chatUrl(activeId.value), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, model: selectedModel.value || undefined, quality: selectedQuality.value, enable_thinking: enableThinking.value, provider_id: selectedProviderId.value }),
      signal: streamAbort.value?.signal,
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
            const now = Date.now()
            if (!firstTokenTime) firstTokenTime = now
            if (lastTokenTime) {
              itlSum += now - lastTokenTime
              itlCount++
            }
            lastTokenTime = now
            assistantContent += data.token
            streamBuffer.value = assistantContent
            updateLivePerf()
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

    // 完成后将 assistant 消息加入列表(思考默认收起)
    if (assistantContent || assistantThinking) {
      activeSession.value.messages.push({
        role: 'assistant',
        content: assistantContent,
        thinking: assistantThinking || '',
        timestamp: new Date().toISOString().slice(0, 19).replace('T', ' '),
        model: selectedModel.value || '',
        _thinkingOpen: false,
      })
    }

    // 计算性能统计并记录到当前会话
    const elapsed = Date.now() - startTime
    const ttftSec = firstTokenTime ? ((firstTokenTime - startTime) / 1000).toFixed(1) : '0'
    const decodeElapsed = firstTokenTime ? (Date.now() - firstTokenTime) : 0
    const tokPerSec = decodeElapsed > 0 ? Math.round(tokenCount / (decodeElapsed / 1000)) : 0
    const tpotMs = tokenCount > 0 ? (decodeElapsed / tokenCount).toFixed(0) : '0'
    const itlMs = itlCount > 0 ? (itlSum / itlCount).toFixed(0) : '0'
    const userMsgs = activeSession.value.messages.filter(m => m.role === 'user').length
    const asstMsgs = activeSession.value.messages.filter(m => m.role === 'assistant').length
    perfStats.value = {
      turns: userMsgs,
      steps: userMsgs + asstMsgs,
      llmTime: formatDuration(elapsed),
      ttft: `${ttftSec}s`,
      tokPerSec: String(tokPerSec),
      inputTokens: String(tokenCount),
      tpot: `${tpotMs}ms`,
      itl: `${itlMs}ms`,
    }
    activeSession.value.perf = { ...perfStats.value }
    api.updateSessionPerf(activeId.value, perfStats.value).catch(() => {})
    livePerf.value = null

    await loadSessions()
  } catch (e) {
    if (e.name === 'AbortError') {
      // 手动停止：保存已流式生成的部分内容（若有），不报错
      if ((assistantContent || assistantThinking) && activeSession.value) {
        activeSession.value.messages.push({
          role: 'assistant',
          content: assistantContent,
          thinking: assistantThinking || '',
          timestamp: new Date().toISOString().slice(0, 19).replace('T', ' '),
          model: selectedModel.value || '',
          _thinkingOpen: false,
        })
      }
    } else {
      message.error(e.message)
    }
  } finally {
    streaming.value = false
    livePerf.value = null
    streamBuffer.value = ''
    streamThinking.value = ''
    streamThinkingOpen.value = false
    streamAbort.value = null
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

async function loadProviders() {
  try {
    const resp = await api.listProviders()
    providers.value = resp.providers || []
    // 默认选择第一个 Provider
    if (!providers.value.some((p) => p.id === selectedProviderId.value)) {
      selectedProviderId.value = providers.value[0]?.id || ''
      localStorage.setItem(localProviderKey, selectedProviderId.value)
    }
    await probeProvider()
  } catch {
    providers.value = []
    providerOnline.value = false
    providerModels.value = []
  }
}

// 探测所选 Provider：模型列表 + 在线状态（header 颜色）
async function probeProvider() {
  const p = providers.value.find((x) => x.id === selectedProviderId.value)
  if (!p) {
    providerOnline.value = false
    providerModels.value = []
    return
  }
  providerProbing.value = true
  try {
    const result = await api.testConnection({
      base_url: p.base_url,
      endpoint: p.endpoint || '/v1/chat/completions',
      api_key: p.api_key || '',
      extra_headers: p.extra_headers || {},
    })
    providerOnline.value = !!result.ok
    providerModels.value = result.models || []
  } catch {
    providerOnline.value = false
    providerModels.value = []
  } finally {
    providerProbing.value = false
  }
}

function onProviderChange() {
  localStorage.setItem(localProviderKey, selectedProviderId.value)
  selectedModel.value = ''
  probeProvider()
}

onMounted(() => {
  loadSessions()
  loadProviders()
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
  background: var(--ant-color-bg-container, #fff);
}

/* ===== 左侧栏 ===== */
.sidebar {
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid var(--ant-color-border, #f0f0f0);
  display: flex;
  flex-direction: column;
  background: var(--ant-color-bg-layout, #fafafa);
}

.sidebar-top {
  padding: 12px;
}

.new-session-btn {
  border-radius: 20px;
  height: 40px;
  font-size: 14px;
  border: 1px solid var(--ant-color-border, #d9d9d9);
  background: var(--ant-color-bg-container, #fff);
  color: var(--ant-color-text, #333);
}
.new-session-btn:hover {
  border-color: var(--ant-color-primary, #1677ff);
  color: var(--ant-color-primary, #1677ff);
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
  color: var(--ant-color-text-tertiary, #999);
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
  background: var(--ant-color-primary-bg, #e6f4ff);
}
.session-item.active {
  background: var(--ant-color-primary-bg-hover, #bae0ff);
}

.session-icon {
  font-size: 16px;
  color: var(--ant-color-primary, #1677ff);
  flex-shrink: 0;
}

.session-name {
  flex: 1;
  font-size: 12px;
  color: var(--ant-color-text, #333);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-close {
  font-size: 14px;
  color: var(--ant-color-text-quaternary, #bbb);
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
  background: var(--ant-color-bg-container, #fff);
}

.chat-header {
  flex-shrink: 0;
  border-bottom: 1px solid #f0f0f0;
  background: var(--ant-color-bg-container, #fff);
  transition: border-color 0.3s;
}
/* 所选 Provider 在线 → 绿色；默认/离线 → 红色 */
.chat-header.chat-ok {
  border-bottom: 2px solid #52c41a;
}
.chat-header.chat-bad {
  border-bottom: 2px solid #ff4d4f;
}
.chat-header .perf-bar {
  margin-top: 0;
  padding: 6px 16px;
  justify-content: flex-start;
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
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
}

.user-avatar {
  background: var(--ant-color-primary, #1677ff);
  color: #fff;
}

.ai-avatar {
  background: var(--ant-color-primary-bg, #f0f5ff);
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
  font-size: 12px;
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
  background: #ffffff;
  border-left: 3px solid #1677ff;
  padding: 10px 14px;
  border-radius: 0 8px 8px 0;
  margin-top: 4px;
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
.chat-textarea.has-content {
  color: #1677ff;
}

.input-bottom-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f5f5f5;
}

.input-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.send-text {
  font-size: 14px;
  font-weight: 600;
  color: #ccc;
  cursor: not-allowed;
  user-select: none;
  padding: 4px 10px;
  transition: color 0.2s;
}
.send-active {
  color: #1677ff;
  cursor: pointer;
}
.send-active:hover {
  color: #4096ff;
}
.send-stop {
  color: #fa541c;
  cursor: pointer;
}
.send-stop:hover {
  color: #ff7a45;
}

.thinking-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
}
.thinking-toggle-label {
  font-size: 13px;
  color: #666;
  white-space: nowrap;
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

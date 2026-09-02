<template>
  <div class="sessions-page">
    <!-- 左侧栏 -->
    <div class="sidebar">
      <div class="sidebar-top">
        <a-button block class="new-session-btn" @click="createSession">
          <template #icon><plus-outlined /></template>
          {{ t('newSession') }}
        </a-button>
      </div>

      <div class="workspaces-section">
        <div class="workspaces-header">
          <span class="workspaces-label">{{ t('chats') }}</span>
          <a-button size="small" type="ghost" class="clear-all-btn" @click="clearOpen = true">{{ t('clearSessions') }}</a-button>
        </div>
        <div class="session-list">
          <div
            v-for="s in sessions"
            :key="s.session_id"
            class="session-item"
            :class="{ active: activeId === s.session_id }"
            @click="selectSession(s.session_id)"
          >
            <!-- 前置小图标：通讯中显示“三个点滚动”，否则静态消息图标 -->
            <div class="session-icon-wrap">
              <span v-if="streamingId === s.session_id" class="session-typing"><span></span><span></span><span></span></span>
              <message-outlined v-else class="session-icon" />
            </div>
            <div class="session-main">
              <span class="session-name">{{ s.title }}</span>
              <span class="session-time">{{ formatModTime(s.updated_at) }}</span>
            </div>
            <!-- 三点菜单：重命名 / 删除 -->
            <a-dropdown :trigger="['click']">
              <more-outlined class="session-more" @click.stop />
              <template #overlay>
                <a-menu @click="onSessionMenu(s.session_id, $event.key)">
                  <a-menu-item key="rename">
                    <edit-outlined class="menu-icon" />{{ t('sessionRename') }}
                  </a-menu-item>
                  <a-menu-item key="delete" class="menu-danger">
                    <delete-outlined class="menu-icon" />{{ t('delete') }}
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </div>
          <a-empty v-if="!sessions.length" :description="t('noData')" :image-style="{ height: '40px' }" style="padding: 20px 0" />
        </div>
      </div>

      <!-- 重命名弹出框 -->
      <a-modal
        v-model:open="renameOpen"
        :title="t('sessionRename')"
        :ok-text="t('save')"
        :cancel-text="t('cancel')"
        @ok="confirmRename"
        @cancel="renameOpen = false"
        :confirm-loading="renaming"
        :width="380"
      >
        <a-input v-model:value="renameValue" :placeholder="t('sessionRenamePlaceholder')" @pressEnter="confirmRename" maxlength="60" show-count />
      </a-modal>

      <!-- 清空会话：居中确认弹窗 -->
      <a-modal
        v-model:open="clearOpen"
        :title="t('clearSessions')"
        :ok-text="t('clear')"
        :ok-danger="true"
        :cancel-text="t('cancel')"
        :width="400"
        :centered="true"
        @ok="clearAllSessions"
        @cancel="clearOpen = false"
      >
        <div class="clear-modal-content">
          <warning-outlined class="clear-warn-icon" />
          <span>{{ t('clearConfirm') }}</span>
        </div>
      </a-modal>
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
          <!-- 对话采样参数配置 -->
          <div class="chat-params">
            <span class="chat-param">
              <span class="param-label">top_k</span>
              <a-input-number v-model:value="chatTopK" size="small" :min="1" :max="200" :precision="0" class="param-input" />
            </span>
            <span class="chat-param">
              <span class="param-label">temp</span>
              <a-input-number v-model:value="chatTemperature" size="small" :min="0" :max="2" :step="0.1" class="param-input" />
            </span>
            <span class="chat-param">
              <span class="param-label">top_p</span>
              <a-input-number v-model:value="chatTopP" size="small" :min="0" :max="1" :step="0.05" class="param-input" />
            </span>
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
                    class="chat-select"
                    :placeholder="t('selectInferenceProvider')"
                    :loading="providerProbing"
                    @change="onProviderChange"
                  />
                  <a-select
                    v-model:value="selectedModel"
                    :options="modelOptions"
                    size="small"
                    :bordered="false"
                    class="chat-select model-select"
                    :placeholder="t('selectModelForChat')"
                  />
                  <a-select
                    v-model:value="selectedQuality"
                    :options="qualityOptions"
                    size="small"
                    :bordered="false"
                    class="chat-select quality-select"
                  />
                  <span class="thinking-toggle">
                    <span class="thinking-toggle-label">{{ t('thinking') }}</span>
                    <a-switch v-model:checked="enableThinking" size="small" />
                  </span>
                  <div v-if="streaming" class="loading-spinner"></div>
                  <span
                    class="send-btn"
                    :class="{ 'send-active': streaming || (inputText.trim() && !streaming), 'send-stop': streaming }"
                    @click="onSendClick"
                  >
                    <arrow-right-outlined v-if="!streaming" class="send-icon" />
                    <span v-else class="stop-square"></span>
                  </span>
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { MessageOutlined, DownOutlined, ArrowRightOutlined, PlusOutlined, MoreOutlined, EditOutlined, DeleteOutlined, WarningOutlined } from '@ant-design/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import python from 'highlight.js/lib/languages/python'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import xml from 'highlight.js/lib/languages/xml'
import css from 'highlight.js/lib/languages/css'
import sql from 'highlight.js/lib/languages/sql'
import java from 'highlight.js/lib/languages/java'
import c from 'highlight.js/lib/languages/c'
import cpp from 'highlight.js/lib/languages/cpp'
import go from 'highlight.js/lib/languages/go'
import rust from 'highlight.js/lib/languages/rust'
import yaml from 'highlight.js/lib/languages/yaml'
import markdown from 'highlight.js/lib/languages/markdown'
import plaintext from 'highlight.js/lib/languages/plaintext'
import 'highlight.js/styles/atom-one-dark.css'
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

// 正在通讯的会话 id：对应左侧列表图标显示“三个点滚动”动画
const streamingId = ref(null)

// 重命名会话
const renameOpen = ref(false)
const renameValue = ref('')
const renaming = ref(false)
const renameTargetId = ref(null)

// 清空会话（居中确认弹窗）
const clearOpen = ref(false)

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

// 对话采样参数（顶部性能栏配置，持久化本地）
const localTopKKey = 'benchscope_chat_top_k'
const chatTopK = ref(localStorage.getItem(localTopKKey) !== null ? Number(localStorage.getItem(localTopKKey)) : 10)
watch(chatTopK, (v) => localStorage.setItem(localTopKKey, String(v)))
const localTempKey = 'benchscope_chat_temperature'
const chatTemperature = ref(localStorage.getItem(localTempKey) !== null ? Number(localStorage.getItem(localTempKey)) : 0.5)
watch(chatTemperature, (v) => localStorage.setItem(localTempKey, String(v)))
const localTopPKey = 'benchscope_chat_top_p'
const chatTopP = ref(localStorage.getItem(localTopPKey) !== null ? Number(localStorage.getItem(localTopPKey)) : 1)
watch(chatTopP, (v) => localStorage.setItem(localTopPKey, String(v)))

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

// ===== Markdown 渲染（marked + highlight.js + DOMPurify，含代码块语法高亮） =====
marked.setOptions({ gfm: true, breaks: true })

// 注册常用的 highlight.js 语言（core 按需注册，控制包体积）
const HLJS_LANGS = {
  javascript, typescript, python, json, bash, xml, css, sql, java, c, cpp, go, rust, yaml, markdown, plaintext,
}
Object.entries(HLJS_LANGS).forEach(([name, lang]) => { hljs.registerLanguage(name, lang) })

function escapePlain(text) {
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

// 代码行内转义（供 hljs.highlight 的 syntax highlight），失败回退转义
function highlightCode(code, lang) {
  try {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang, ignoreIllegals: true }).value
    }
    return hljs.highlightAuto(code).value
  } catch {
    return escapePlain(code)
  }
}

// 把 hljs 高亮后的 HTML 按行拆分，处理跨行 span（在换行处闭合/重开 span，保证每行标签闭合）
// 自定义 marked 代码块 renderer：语法高亮后输出简洁 <pre><code>（无行号）
// （marked v18：Renderer.code 接收单个 token 对象 { text, lang, escaped }）
const mdRenderer = new marked.Renderer()
mdRenderer.code = function (token) {
  const rawCode = (token && token.text != null ? String(token.text) : '').replace(/\n$/, '')
  const lang = ((token && token.lang || '').trim().split(/\s+/)[0] || '').toLowerCase()
  const highlighted = highlightCode(rawCode, lang)
  const l = escapePlain(lang || 'code')
  return `<div class="code-block"><div class="code-header"><span class="code-lang">${l}</span><span class="copy-btn">Copy</span></div><pre><code>${highlighted}</code></pre></div>`
}
marked.use({ renderer: mdRenderer })

function renderMarkdown(text) {
  if (!text) return ''
  let html = ''
  try {
    html = marked.parse(text)
  } catch {
    return ''
  }
  // 代码块已在 renderer.code 中生成完整结构，此处仅做 XSS 净化
  if (DOMPurify && typeof DOMPurify.sanitize === 'function') {
    return DOMPurify.sanitize(html, { ADD_ATTR: ['target'] })
  }
  return html
}

// 代码块 Copy 按钮：轻量事件委托（v-html 动态插入，避免内联 onclick 被 DOMPurify 清理）
function onDocClick(e) {
  const btn = e.target && e.target.closest ? e.target.closest('.copy-btn') : null
  if (!btn) return
  const block = btn.closest('.code-block')
  const pre = block && block.querySelector('pre')
  if (!pre) return
  // 复制 <pre> 内纯代码文本（不含行号）
  const raw = pre.textContent
  const orig = btn.textContent
  navigator.clipboard
    .writeText(raw)
    .then(() => { btn.textContent = 'Copied!'; setTimeout(() => { btn.textContent = orig }, 1200) })
    .catch(() => {})
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

// 三点菜单：重命名 / 删除
function onSessionMenu(id, key) {
  if (key === 'rename') {
    const s = sessions.value.find(x => x.session_id === id)
    renameTargetId.value = id
    renameValue.value = (s && s.title) || ''
    renameOpen.value = true
  } else if (key === 'delete') {
    deleteSession(id)
  }
}

async function confirmRename() {
  const title = renameValue.value.trim()
  if (!title) return
  if (!renameTargetId.value) return
  renaming.value = true
  try {
    const resp = await api.renameSession(renameTargetId.value, title)
    // 同步标题（活动会话对象与侧栏列表）
    if (activeId.value === renameTargetId.value && activeSession.value) {
      const renamed = resp && resp.session
      activeSession.value.title = (renamed && renamed.title) || title
    }
    await loadSessions()
    renameOpen.value = false
  } catch (e) { message.error(e.message) }
  finally { renaming.value = false }
}

// 修改时间展示：去掉秒，显示 MM-DD HH:mm；跨年补年份
function formatModTime(ts) {
  if (!ts) return ''
  const d = new Date(String(ts).replace(' ', 'T'))
  if (isNaN(d.getTime())) return String(ts)
  const pad = (n) => String(n).padStart(2, '0')
  const mm = pad(d.getMonth() + 1)
  const dd = pad(d.getDate())
  const hh = pad(d.getHours())
  const mi = pad(d.getMinutes())
  const year = d.getFullYear()
  if (year !== new Date().getFullYear()) return `${year}-${mm}-${dd}`
  return `${mm}-${dd} ${hh}:${mi}`
}

async function clearAllSessions() {
  try {
    await api.clearSessions()
    sessions.value = []
    activeId.value = null
    activeSession.value = null
    clearOpen.value = false
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
  streamingId.value = activeId.value
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
      body: JSON.stringify({ message: text, model: selectedModel.value || undefined, quality: selectedQuality.value, enable_thinking: enableThinking.value, provider_id: selectedProviderId.value, top_k: chatTopK.value, temperature: chatTemperature.value, top_p: chatTopP.value }),
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
    streamingId.value = null
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
  // 代码块 Copy 按钮事件委托
  document.addEventListener('click', onDocClick)
  // 如果没有本地记住的模型，默认选第一个
  if (!selectedModel.value && modelOptions.value.length) {
    selectedModel.value = modelOptions.value[0].value
    localStorage.setItem(localModelKey, selectedModel.value)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
})
</script>

<style scoped>
.sessions-page {
  display: flex;
  height: 100%;
  overflow: hidden;
  background: var(--ant-color-bg-container, #fff);
}

/* ===== 左侧栏：浅色会话侧栏 ===== */
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
  font-weight: 500;
  border: 1px solid var(--ant-color-primary, #1677ff) !important;
  background: var(--ant-color-primary, #1677ff) !important;
  color: #fff !important;
}
.new-session-btn:hover {
  border-color: var(--ant-color-primary-hover, #4096ff) !important;
  background: var(--ant-color-primary-hover, #4096ff) !important;
  color: #fff !important;
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

.clear-all-btn {
  font-size: 12px;
  color: var(--ant-color-text-secondary, #666);
  border-color: var(--ant-color-border, #d9d9d9);
  background: transparent;
}
.clear-all-btn:hover {
  color: var(--ant-color-primary, #1677ff);
  border-color: var(--ant-color-primary, #1677ff);
}

/* 清空会话居中确认弹窗内容（modal teleport 到 body，需 global） */
:global(.clear-modal-content) {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--ant-color-text, #333);
}
:global(.clear-warn-icon) {
  font-size: 20px;
  color: #faad14;
  flex-shrink: 0;
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
  padding: 7px 10px;
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
.session-item.active .session-icon,
.session-item.active .session-name {
  color: var(--ant-color-primary, #1677ff);
}

/* 前置小图标容器：固定宽度，通讯时切换为滚动三点 */
.session-icon-wrap {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.session-icon {
  font-size: 16px;
  color: var(--ant-color-primary, #1677ff);
}

/* 会话主区：标题 + 修改时间 */
.session-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.session-name {
  font-size: 12px;
  color: var(--ant-color-text, #333);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-time {
  font-size: 11px;
  color: var(--ant-color-text-quaternary, #bbb);
  line-height: 1.2;
}

/* 三点菜单 */
.session-more {
  font-size: 14px;
  color: var(--ant-color-text-quaternary, #bbb);
  opacity: 0;
  transition: opacity 0.2s;
  flex-shrink: 0;
  padding: 2px;
  border-radius: 4px;
}
.session-item:hover .session-more,
.session-item.active .session-more {
  opacity: 1;
}
.session-more:hover {
  color: var(--ant-color-primary, #1677ff);
  background: rgba(0, 0, 0, 0.04);
}

/* 三点滚动动画（会话通讯中） */
.session-typing {
  display: inline-flex;
  gap: 2px;
}
.session-typing span {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--ant-color-primary, #1677ff);
  animation: sessionDotRoll 1.2s infinite ease-in-out;
}
.session-typing span:nth-child(2) { animation-delay: 0.18s; }
.session-typing span:nth-child(3) { animation-delay: 0.36s; }
@keyframes sessionDotRoll {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
  30% { transform: translateY(-3px); opacity: 1; }
}

/* 菜单项图标间距（下拉菜单 teleport 到 body，需 global） */
:global(.menu-icon) {
  margin-right: 6px;
}
:global(.menu-danger) {
  color: #ff4d4f !important;
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
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  border-bottom: 1px solid #eef1f6;
  background: #f6f8fb;
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
  flex: 1 1 auto;
  min-width: 0;
}

/* 顶部对话采样参数配置：宽度足够时右对齐，宽度不足时换行 */
.chat-params {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 2px 16px 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
  margin-left: auto;
  margin-right: 4px;
}
.chat-param {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.param-label {
  font-size: 11px;
  color: var(--ant-color-text-tertiary, #999);
  font-weight: 500;
}
.param-input {
  width: 72px;
  font-size: 12px;
}
.param-input :deep(.ant-input-number-input) {
  font-size: 12px;
  color: #999;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
  background:
    radial-gradient(circle at 0% 0%, rgba(22, 119, 255, 0.05), transparent 42%),
    radial-gradient(circle at 100% 100%, rgba(22, 119, 255, 0.03), transparent 40%),
    #f6f8fb;
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
  background: linear-gradient(135deg, #1677ff, #3f8cff);
  color: #fff;
  box-shadow: 0 2px 6px rgba(22, 119, 255, 0.35);
}

.ai-avatar {
  background: var(--ant-color-primary-bg, #f0f5ff);
  overflow: hidden;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  border: 1px solid #e8eefb;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.msg-content-wrap {
  max-width: 70%;
  min-width: 120px;
  display: flex;
  flex-direction: column;
}

.msg-row.assistant .msg-content-wrap {
  align-items: flex-start;
}

.msg-row.user .msg-content-wrap {
  align-items: flex-end;
}

/* ===== 思考块 ===== */
.thinking-block {
  margin-bottom: 8px;
  border: 1px solid rgba(22, 119, 255, 0.18);
  border-radius: 10px;
  background: #f5f8ff;
  overflow: hidden;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  cursor: pointer;
  user-select: none;
}

.thinking-arrow {
  font-size: 12px;
  color: #1677ff;
  transition: transform 0.2s;
}

.thinking-label {
  font-size: 12px;
  color: #1677ff;
  font-weight: 600;
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
  background: #1677ff;
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

/* ===== 回复内容（气泡） ===== */
.reply-content {
  font-size: 14px;
  line-height: 1.75;
  color: #262626;
  word-break: break-word;
}

.msg-row.user .reply-content {
  background: linear-gradient(135deg, #1677ff, #3f8cff);
  color: #fff;
  padding: 10px 14px;
  border-radius: 14px;
  border-top-right-radius: 4px;
  box-shadow: 0 2px 8px rgba(22, 119, 255, 0.28);
}

.msg-row.assistant .reply-content {
  background: #fff;
  padding: 12px 16px;
  border-radius: 4px 14px 14px 14px;
  margin-top: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  border: 1px solid #eef1f6;
}

/* ===== 代码块（纯黑底 + 无行号 + 紧凑小号代码字体，含语法高亮） ===== */
.code-block {
  margin: 10px 0;
  border: 1px solid #262626;
  border-radius: 8px;
  overflow: hidden;
  background: #0a0a0a;
}

/* 极简头部：弱化语言标签与 Copy，悬停时 Copy 显示 */
.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 14px;
  background: #0e0e0e;
  border-bottom: 1px solid #1e1e1e;
}

.code-lang {
  font-size: 11px;
  letter-spacing: 0.3px;
  color: #6b6b6b;
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  font-weight: 400;
}

.copy-btn {
  font-size: 11px;
  letter-spacing: 0.3px;
  color: #8a8a8a;
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 4px;
  opacity: 0;
  transition: opacity 0.2s, color 0.2s, background 0.2s;
}
.code-block:hover .copy-btn,
.copy-btn:hover {
  opacity: 1;
}
.copy-btn:hover {
  color: #cfcfcf;
  background: rgba(255, 255, 255, 0.06);
}

/* 代码主体：比正文（14px/1.75）更小的紧凑等宽字体 */
.code-block pre {
  margin: 0;
  padding: 8px 14px;
  overflow-x: auto;
  font-size: 12.5px;
  line-height: 1.4;
  color: #e6edf3;
}

.code-block code {
  font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', 'SFMono-Regular', 'Cascadia Code', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 12.5px;
  line-height: 1.4;
  color: #e6edf3;
  background: transparent;
  font-variant-ligatures: none;
  tab-size: 4;
}

.code-block pre code.hljs {
  background: transparent;
  padding: 0;
  display: block;
  overflow-x: auto;
  font-size: 12.5px;
  line-height: 1.4;
}

.inline-code {
  background: #0d0d0d;
  border: 1px solid #2a2a2a;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12.5px;
  font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', 'SFMono-Regular', 'Cascadia Code', Consolas, monospace;
  color: #3fb950;
}

/* ===== markdown 元素（marked 输出）统一排版 ===== */
.reply-content > *:first-child {
  margin-top: 0;
}
.reply-content > *:last-child {
  margin-bottom: 0;
}
.reply-content h1,
.reply-content h2,
.reply-content h3,
.reply-content h4 {
  margin: 14px 0 8px;
  font-weight: 600;
  line-height: 1.4;
  color: #1f2329;
}
.reply-content h1 {
  font-size: 20px;
  border-bottom: 1px solid #eee;
  padding-bottom: 6px;
}
.reply-content h2 {
  font-size: 18px;
  border-bottom: 1px solid #eee;
  padding-bottom: 4px;
}
.reply-content h3 {
  font-size: 16px;
}
.reply-content h4 {
  font-size: 15px;
}
.reply-content p {
  margin: 6px 0;
}
.reply-content ul,
.reply-content ol {
  margin: 6px 0;
  padding-left: 22px;
}
.reply-content li {
  margin: 3px 0;
}
.reply-content blockquote {
  margin: 8px 0;
  padding: 4px 12px;
  border-left: 3px solid #1677ff;
  background: #f6f8fb;
  border-radius: 0 6px 6px 0;
  color: #555;
}
.reply-content a {
  color: #1677ff;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.reply-content hr {
  margin: 12px 0;
  border: none;
  border-top: 1px solid #eee;
}
.reply-content table {
  border-collapse: collapse;
  margin: 8px 0;
  width: 100%;
  font-size: 13px;
}
.reply-content th,
.reply-content td {
  border: 1px solid #e8e8e8;
  padding: 6px 10px;
  text-align: left;
}
.reply-content th {
  background: #f5f7fa;
  font-weight: 600;
}
.reply-content img {
  max-width: 100%;
  border-radius: 6px;
}
/* 用户气泡内：链接/行内代码用白色系 */
.msg-row.user .reply-content a {
  color: #fff;
  text-decoration: underline;
}
.msg-row.user .reply-content .inline-code {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
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
  padding: 10px 32px 20px;
  background: #f6f8fb; /* 与对话区背景一致，融为一体 */
}

.input-container {
  max-width: 800px;
  margin: 0 auto;
}

.input-box {
  border: 1px solid #eef1f6;
  border-radius: 18px;
  padding: 12px 16px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
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

/* 输入栏下拉（Provider/Model/Quality）：统一宽度、灰色小字 */
.chat-select {
  width: 128px;
  font-size: 12px;
}
.chat-select.model-select {
  width: 150px;
}
.chat-select :deep(.ant-select-selection-item) {
  font-size: 12px;
  color: #999;
}
.chat-select :deep(.ant-select-selector) {
  background: transparent !important;
}
.chat-select:deep(.ant-select-arrow) {
  color: #bbb;
  font-size: 10px;
}

/* 发送 / 停止小图标按钮：蓝色圆圈 + 白色箭头 / 白色方块 */
.send-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #ccc;
  color: #fff;
  cursor: not-allowed;
  transition: background 0.2s;
}
.send-btn.send-active,
.send-btn.send-stop {
  background: #1677ff;
  cursor: pointer;
}
.send-btn.send-active:hover,
.send-btn.send-stop:hover {
  background: #4096ff;
}
.send-icon {
  font-size: 14px;
  color: #fff;
}
.stop-square {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: #fff;
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
  font-size: 12px;
}
.quality-select :deep(.ant-select-selector) {
  background: transparent !important;
  color: #999;
  font-weight: 400;
  font-size: 12px;
}
.quality-select :deep(.ant-select-selection-item) {
  color: #999;
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

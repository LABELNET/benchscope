<template>
  <div class="sessions-page">
    <!-- 左侧：会话列表 -->
    <div class="session-sidebar">
      <div class="sidebar-header">
        <a-button type="primary" block @click="createSession">
          <template #icon><plus-outlined /></template>
          {{ t('newSession') }}
        </a-button>
        <a-popconfirm :title="t('clearConfirm')" @confirm="clearAll" ok-text="OK" cancel-text="Cancel">
          <a-button size="small" danger ghost style="margin-top: 8px" block>{{ t('clearSessions') }}</a-button>
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
          <div class="session-title">{{ s.title }}</div>
          <div class="session-meta">
            <span>{{ s.model || '-' }}</span>
            <span>{{ s.updated_at?.slice(5, 16) || '' }}</span>
          </div>
          <a-button type="text" size="small" class="session-del" @click.stop="deleteSession(s.session_id)">
            <delete-outlined />
          </a-button>
        </div>
        <a-empty v-if="!sessions.length" :description="t('noData')" :image-style="{ height: '40px' }" style="padding: 20px 0" />
      </div>
    </div>

    <!-- 右侧：对话区 -->
    <div class="chat-area">
      <template v-if="activeSession">
        <!-- 顶部：模型选择 -->
        <div class="chat-header">
          <a-space>
            <span style="font-weight: 600">{{ activeSession.title }}</span>
            <a-select v-model:value="chatModel" size="small" style="width: 200px" :placeholder="t('selectModelForChat')" :options="modelOptions" allow-clear />
          </a-space>
        </div>

        <!-- 消息列表 -->
        <div class="chat-messages" ref="msgBox">
          <div v-for="(msg, i) in activeSession.messages" :key="i" class="msg-row" :class="msg.role">
            <div class="msg-avatar">
              <a-avatar :style="{ backgroundColor: msg.role === 'user' ? '#1677ff' : '#52c41a' }" size="small">
                {{ msg.role === 'user' ? 'U' : 'A' }}
              </a-avatar>
            </div>
            <div class="msg-bubble">
              <div class="msg-content">{{ msg.content }}</div>
              <div class="msg-time">{{ msg.timestamp }}</div>
            </div>
          </div>
          <!-- 流式输出中 -->
          <div v-if="streaming" class="msg-row assistant">
            <div class="msg-avatar">
              <a-avatar :style="{ backgroundColor: '#52c41a' }" size="small">A</a-avatar>
            </div>
            <div class="msg-bubble">
              <div class="msg-content streaming">{{ streamBuffer }}<span class="cursor-blink">|</span></div>
            </div>
          </div>
        </div>

        <!-- 底部：输入框 -->
        <div class="chat-input">
          <a-textarea
            v-model:value="inputText"
            :placeholder="t('inputPlaceholder')"
            :auto-size="{ minRows: 1, maxRows: 4 }"
            @pressEnter="onInputEnter"
            :disabled="streaming"
          />
          <a-button type="primary" @click="sendMessage" :loading="streaming" :disabled="!inputText.trim()">
            {{ t('send') }}
          </a-button>
        </div>
      </template>

      <div v-else class="no-session">
        <a-empty :description="t('noSession')" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { api } from '@/api'
import { useConfigStore } from '@/store/config'
import { t } from '@/i18n'

const config = useConfigStore()
const sessions = ref([])
const activeId = ref(null)
const activeSession = ref(null)
const chatModel = ref('')
const inputText = ref('')
const streaming = ref(false)
const streamBuffer = ref('')
const msgBox = ref(null)

const modelOptions = computed(() => (config.status?.models || []).map((m) => ({ value: m, label: m })))

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
    chatModel.value = resp.model || ''
    await nextTick()
    scrollToBottom()
  } catch (e) { message.error(e.message) }
}

async function createSession() {
  try {
    const resp = await api.createSession({ model: chatModel.value || '' })
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

async function clearAll() {
  try {
    await api.clearSessions()
    activeId.value = null
    activeSession.value = null
    sessions.value = []
  } catch (e) { message.error(e.message) }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || !activeId.value || streaming.value) return

  // 乐观更新
  const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString().slice(0, 19).replace('T', ' '), model: '' }
  if (!activeSession.value.messages) activeSession.value.messages = []
  activeSession.value.messages.push(userMsg)
  inputText.value = ''
  await nextTick()
  scrollToBottom()

  // SSE 流式请求
  streaming.value = true
  streamBuffer.value = ''
  let assistantContent = ''

  try {
    const resp = await fetch(api.chatUrl(activeId.value), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
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
            assistantContent += data.token
            streamBuffer.value = assistantContent
            scrollToBottom()
          }
          if (data.error) {
            message.error(data.error)
          }
        } catch { /* ignore parse error */ }
      }
    }

    // 完成后刷新会话数据
    await selectSession(activeId.value)
    await loadSessions()
  } catch (e) {
    message.error(e.message)
  } finally {
    streaming.value = false
    streamBuffer.value = ''
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

watch(chatModel, (v) => {
  if (activeSession.value) activeSession.value.model = v
})

onMounted(() => {
  loadSessions()
  config.refreshStatus()
})
</script>

<style scoped>
.sessions-page {
  display: flex;
  height: 100%;
  overflow: hidden;
}
.session-sidebar {
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}
.sidebar-header {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.session-item {
  position: relative;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.2s;
}
.session-item:hover {
  background: #e6f4ff;
}
.session-item.active {
  background: #bae0ff;
}
.session-title {
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-right: 24px;
}
.session-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}
.session-del {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
  transition: opacity 0.2s;
}
.session-item:hover .session-del {
  opacity: 1;
}
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-header {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  align-items: flex-start;
}
.msg-row.user {
  flex-direction: row-reverse;
}
.msg-bubble {
  max-width: 70%;
}
.msg-content {
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-row.user .msg-content {
  background: #1677ff;
  color: #fff;
}
.msg-row.assistant .msg-content {
  background: #f5f5f5;
  color: #333;
}
.msg-time {
  font-size: 11px;
  color: #bbb;
  margin-top: 4px;
}
.msg-row.user .msg-time {
  text-align: right;
}
.streaming .cursor-blink {
  animation: blink 1s step-end infinite;
}
@keyframes blink {
  50% { opacity: 0; }
}
.chat-input {
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  gap: 8px;
  align-items: flex-end;
}
.chat-input textarea {
  flex: 1;
}
.no-session {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>

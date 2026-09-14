<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import AssistantMessage from './components/AssistantMessage.vue'
import ChatInput from './components/ChatInput.vue'
import UserMessage from './components/UserMessage.vue'
import { useChatStream } from './composables/useChatStream'

const scrollArea = ref<HTMLElement | null>(null)
const { messages, isStreaming, error, sendMessage, reset, stopStreaming } = useChatStream()

watch(messages, async () => {
  await nextTick()
  const el = scrollArea.value
  if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
}, { deep: true })

async function handleSend(text: string, attachments = []) {
  await sendMessage(text, attachments)
}

function newChat() {
  if (isStreaming.value) return
  reset()
}

function stopChat() {
  stopStreaming()
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">✦</div>
        <div>
          <div class="brand-title">Semantic Agent</div>
          <div class="brand-subtitle">OpenAI Compatible Agent</div>
        </div>
      </div>
      <div class="topbar-actions">
        <button v-if="isStreaming" class="stop-chat" @click="stopChat">■ 终止对话</button>
        <button class="new-chat" :disabled="isStreaming" @click="newChat">＋ 新对话</button>
      </div>
    </header>

    <main ref="scrollArea" class="chat-scroll">
      <div v-if="messages.length === 0" class="welcome">
        <div class="welcome-icon">✦</div>
        <h1>有什么可以帮你的？</h1>
        <p>支持思考、Tool Call、Tool 执行和流式回答。</p>
        <div class="suggestions">
          <button @click="handleSend('北京今天的天气怎么样？')">查询北京天气</button>
          <button @click="handleSend('请解释一下 ReAct Agent 是如何工作的。')">解释 ReAct Agent</button>
          <button @click="handleSend('帮我设计一个简单的 Agent 架构。')">设计 Agent 架构</button>
        </div>
      </div>

      <div v-else class="conversation">
        <template v-for="message in messages" :key="message.id">
          <UserMessage v-if="message.role === 'user'" :content="message.content || ''" :attachments="message.attachments || []" />
          <AssistantMessage v-else-if="message.turn" :turn="message.turn" />
          <div v-else class="assistant-error">{{ message.content }}</div>
        </template>
        <div v-if="error" class="error-banner">{{ error }}</div>
      </div>
    </main>

    <footer class="composer-wrap">
      <ChatInput :disabled="isStreaming" @send="handleSend" />
    </footer>
  </div>
</template>

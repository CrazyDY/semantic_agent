<script setup lang="ts">
import { nextTick, ref } from 'vue'

const props = defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ send: [text: string] }>()
const text = ref('')
const input = ref<HTMLTextAreaElement | null>(null)

function resize() {
  const el = input.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 180)}px`
}

function send() {
  const value = text.value.trim()
  if (!value || props.disabled) return
  emit('send', value)
  text.value = ''
  nextTick(resize)
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}
</script>

<template>
  <div class="composer-shell">
    <div class="composer">
      <textarea
        ref="input"
        v-model="text"
        :disabled="disabled"
        rows="1"
        placeholder="给 AI 发送消息..."
        @input="resize"
        @keydown="onKeydown"
      />
      <button class="send-button" :disabled="disabled || !text.trim()" @click="send" aria-label="发送">
        ↑
      </button>
    </div>
    <div class="composer-tip">Enter 发送 · Shift + Enter 换行</div>
  </div>
</template>

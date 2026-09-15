<script setup lang="ts">
import ThinkingBlock from './ThinkingBlock.vue'
import ToolCallBlock from './ToolCallBlock.vue'
import type { AssistantTurn } from '../types/chat'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps<{ turn: AssistantTurn }>()
const emit = defineEmits<{ 'tool-approval': [value: { callId: string; approved: boolean }] }>()

marked.setOptions({
  gfm: true,
  breaks: true,
})

function renderMarkdown(text: string) {
  const html = marked.parse(text, {
    async: false,
  }) as string

  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
  })
}
</script>

<template>
  <div class="message-row assistant-row">
    <div class="assistant-avatar">A</div>
    <div class="assistant-content">
      <ThinkingBlock
        :content="turn.thinking"
        :done="turn.thinkingDone"
        :expanded="turn.thinkingExpanded"
      />

      <ToolCallBlock v-for="tool in turn.tools" :key="tool.callId" :tool="tool" @approve="emit('tool-approval', { callId: $event.callId, approved: $event.approved })" />

      <div v-if="turn.content" class="markdown-content" v-html="renderMarkdown(turn.content)" />
      <span v-if="turn.streaming" class="streaming-cursor" />
    </div>
  </div>
</template>

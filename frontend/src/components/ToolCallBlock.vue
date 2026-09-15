<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ToolCallState } from '../types/chat'

const props = defineProps<{ tool: ToolCallState }>()
const emit = defineEmits<{ approve: [value: { callId: string; approved: boolean }] }>()
const expanded = ref(false)
const submittingApproval = ref(false)

const statusText = computed(() => ({
  calling: '准备调用',
  awaiting_approval: '等待确认',
  running: '执行中',
  success: '已完成',
  error: '失败',
}[props.tool.status]))

const argumentsText = computed(() => {
  if (props.tool.parsedArguments !== null) {
    try { return JSON.stringify(props.tool.parsedArguments, null, 2) } catch { /* fall through */ }
  }
  return props.tool.arguments || '{}'
})

const resultText = computed(() => {
  if (props.tool.result === null) return ''
  try { return JSON.stringify(props.tool.result, null, 2) } catch { return String(props.tool.result) }
})

function approve(approved: boolean) {
  if (submittingApproval.value) return
  submittingApproval.value = true
  emit('approve', { callId: props.tool.callId, approved })
}
</script>

<template>
  <div class="tool-card" :class="`tool-${tool.status}`">
    <button class="tool-header" @click="expanded = !expanded">
      <span class="tool-symbol">⚙</span>
      <span class="tool-name">{{ tool.name }}</span>
      <span class="tool-status">{{ statusText }}</span>
      <span class="chevron" :class="{ open: expanded }">⌄</span>
    </button>
    <div v-if="expanded" class="tool-body">
      <div class="tool-section-title">参数</div>
      <pre>{{ argumentsText }}</pre>
      <template v-if="resultText">
        <div class="tool-section-title result-title">结果</div>
        <pre>{{ resultText }}</pre>
      </template>
      <div v-if="tool.error" class="tool-error">{{ tool.error }}</div>
    </div>
    <div v-if="tool.status === 'awaiting_approval'" class="tool-approval">
      <span>是否允许执行此工具？</span>
      <div>
        <button class="tool-deny" :disabled="submittingApproval" @click="approve(false)">拒绝</button>
        <button class="tool-allow" :disabled="submittingApproval" @click="approve(true)">允许执行</button>
      </div>
    </div>
  </div>
</template>

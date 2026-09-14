<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  content: string
  done: boolean
  expanded: boolean
}>()

const open = ref(props.expanded)
watch(() => props.expanded, (value) => { open.value = value })
</script>

<template>
  <div v-if="content" class="thinking-block">
    <button class="thinking-header" @click="open = !open">
      <span class="thinking-icon">✦</span>
      <span>{{ done ? '已完成思考' : '正在思考' }}</span>
      <span class="chevron" :class="{ open }">⌄</span>
    </button>
    <div v-show="open" class="thinking-body">{{ content }}</div>
  </div>
</template>

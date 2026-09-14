<script setup lang="ts">
defineProps<{ content: string }>()
</script>

<template>
  <div class="message-row user-row">
    <div class="user-bubble">{{ content }}</div>
  </div>
</template>

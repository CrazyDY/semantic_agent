<script setup lang="ts">
import type { ImageAttachment } from '../types/chat'

defineProps<{ content: string; attachments?: ImageAttachment[] }>()
</script>

<template>
  <div class="message-row user-row">
    <div class="user-bubble">
      <div v-if="content">{{ content }}</div>
      <div v-if="attachments?.length" class="user-images">
        <img v-for="attachment in attachments" :key="attachment.id" :src="attachment.url" :alt="attachment.name" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref } from 'vue'
import type { ImageAttachment } from '../types/chat'

const props = defineProps<{ disabled?: boolean }>()
const emit = defineEmits<{ send: [text: string, attachments: ImageAttachment[]] }>()
const text = ref('')
const input = ref<HTMLTextAreaElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const attachments = ref<ImageAttachment[]>([])
const isDragging = ref(false)
const uploadError = ref('')
const MAX_IMAGES = 4
const MAX_FILE_SIZE = 10 * 1024 * 1024

function resize() {
  const el = input.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 180)}px`
}

function send() {
  const value = text.value.trim()
  if ((!value && !attachments.value.length) || props.disabled) return
  emit('send', value, attachments.value)
  text.value = ''
  attachments.value = []
  uploadError.value = ''
  nextTick(resize)
}

function openFilePicker() {
  if (!props.disabled) fileInput.value?.click()
}

function addFiles(files: FileList | File[]) {
  uploadError.value = ''
  const candidates = Array.from(files).filter((file) => file.type.startsWith('image/'))
  if (!candidates.length) {
    uploadError.value = '请选择图片文件。'
    return
  }
  const available = MAX_IMAGES - attachments.value.length
  if (available <= 0) {
    uploadError.value = `最多可添加 ${MAX_IMAGES} 张图片。`
    return
  }
  const accepted = candidates.slice(0, available)
  if (candidates.length > available) uploadError.value = `最多可添加 ${MAX_IMAGES} 张图片。`
  for (const file of accepted) {
    if (file.size > MAX_FILE_SIZE) {
      uploadError.value = '单张图片不能超过 10 MB。'
      continue
    }
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result !== 'string') return
      attachments.value.push({ id: crypto.randomUUID(), name: file.name, url: reader.result })
    }
    reader.readAsDataURL(file)
  }
}

function onFilesSelected(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files) addFiles(target.files)
  target.value = ''
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  if (!props.disabled && event.dataTransfer?.files) addFiles(event.dataTransfer.files)
}

function onPaste(event: ClipboardEvent) {
  const files = Array.from(event.clipboardData?.files ?? [])
  if (files.some((file) => file.type.startsWith('image/'))) {
    event.preventDefault()
    addFiles(files)
  }
}

function removeAttachment(id: string) {
  attachments.value = attachments.value.filter((attachment) => attachment.id !== id)
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}

onBeforeUnmount(() => { attachments.value = [] })
</script>

<template>
  <div class="composer-shell">
    <div class="composer" :class="{ 'is-dragging': isDragging }" @dragenter.prevent="isDragging = true" @dragover.prevent @dragleave.prevent="isDragging = false" @drop.prevent="onDrop">
      <input ref="fileInput" class="file-input" type="file" accept="image/*" multiple @change="onFilesSelected" />
      <div v-if="attachments.length" class="attachment-list">
        <div v-for="attachment in attachments" :key="attachment.id" class="attachment-preview">
          <img :src="attachment.url" :alt="attachment.name" />
          <button type="button" aria-label="移除图片" @click="removeAttachment(attachment.id)">×</button>
        </div>
      </div>
      <textarea
        ref="input"
        v-model="text"
        :disabled="disabled"
        rows="1"
        placeholder="给 AI 发送消息..."
        @input="resize"
        @keydown="onKeydown"
        @paste="onPaste"
      />
      <button type="button" class="attach-button" :disabled="disabled" @click="openFilePicker" aria-label="添加图片" title="添加图片">＋</button>
      <button class="send-button" :disabled="disabled || (!text.trim() && !attachments.length)" @click="send" aria-label="发送">
        ↑
      </button>
    </div>
    <div class="composer-tip">可上传、拖入或粘贴图片（最多 4 张，每张 10 MB）· Enter 发送 · Shift + Enter 换行</div>
    <div v-if="uploadError" class="upload-error">{{ uploadError }}</div>
  </div>
</template>

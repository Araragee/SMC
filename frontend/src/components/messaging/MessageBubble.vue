<script setup lang="ts">
import type { ChatMessage } from '@types'

const props = defineProps<{
  message:    ChatMessage
  isMine:     boolean
  showSender: boolean  // true for group chats
}>()

const formatTime = function(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
}
</script>

<template>
  <!-- Own message -->
  <div v-if="isMine" class="flex justify-end mb-1.5">
    <div class="relative group max-w-[75%]">
      <div class="bg-primary text-on-surface rounded-3xl rounded-br-sm px-4 py-2.5 text-sm">
        <p class="break-words leading-relaxed">{{ message.isDeleted ? '[deleted]' : message.body }}</p>
      </div>
      <span class="absolute bottom-full right-2 mb-1 text-[10px] text-on-surface-variant opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
        {{ formatTime(message.createdAt) }}
      </span>
    </div>
  </div>

  <!-- Other's message -->
  <div v-else class="flex justify-start mb-1.5 gap-2">
    <div
      v-if="showSender && message.senderName"
      class="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center text-[10px] font-black text-primary shrink-0 mt-auto"
    >
      {{ message.senderName.charAt(0).toUpperCase() }}
    </div>
    <div class="relative group max-w-[75%]">
      <p v-if="showSender && message.senderName" class="text-[10px] font-bold text-on-surface-variant mb-0.5 ml-1">
        {{ message.senderName }}
      </p>
      <div class="bg-on-surface/[0.06] dark:bg-on-surface/10 text-on-surface rounded-3xl rounded-bl-sm px-4 py-2.5 text-sm">
        <p class="break-words leading-relaxed">{{ message.isDeleted ? '[deleted]' : message.body }}</p>
      </div>
      <span class="absolute bottom-full left-2 mb-1 text-[10px] text-on-surface-variant opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
        {{ formatTime(message.createdAt) }}
      </span>
    </div>
  </div>
</template>

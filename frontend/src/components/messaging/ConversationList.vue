<script setup lang="ts">
import { ref } from 'vue'
import { useMessagingStore } from '@stores/messaging'
import { useAuthStore } from '@stores/auth'
import type { Conversation } from '@types'
import NewConversationModal from './NewConversationModal.vue'

const emit = defineEmits<{ select: [id: number] }>()

const store = useMessagingStore()
const auth = useAuthStore()
const showNew = ref(false)

const getDisplayName = function (conv: Conversation): string {
  if (conv.type === 'session_thread') return conv.name ?? 'Session Thread'
  if (conv.type === 'group') return conv.name ?? 'Group Chat'
  // DM: show the other participant's name
  const other = conv.participants.find((p) => p.userId !== auth.currentUser?.id)
  return other?.name ?? 'Direct Message'
}

const getIcon = function (conv: Conversation): string {
  if (conv.type === 'session_thread') return 'event_note'
  if (conv.type === 'group') return 'group'
  return 'chat_bubble'
}

const formatTime = function (iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
  }
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const onCreated = function (id: number) {
  showNew.value = false
  emit('select', id)
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Search / New -->
    <div class="px-4 py-3 border-b border-on-surface/[0.04] dark:border-on-surface/5">
      <button
        class="w-full flex items-center justify-center gap-2 py-2 bg-primary/10 hover:bg-primary/20 border border-primary/20 rounded-2xl text-primary text-xs font-semibold uppercase transition-colors"
        @click="showNew = true"
      >
        <span class="material-symbols-outlined text-base">edit_square</span>
        New Conversation
      </button>
    </div>

    <!-- List -->
    <div class="flex-1 overflow-y-auto">
      <div
        v-if="store.sortedConversations.length === 0"
        class="flex flex-col items-center justify-center h-full text-center px-6"
      >
        <span class="material-symbols-outlined text-4xl text-on-surface-variant mb-3">chat</span>
        <p class="text-sm font-bold text-on-surface-variant">No conversations yet</p>
        <p class="text-xs text-on-surface-variant/60 mt-1">Start a new chat above</p>
      </div>

      <button
        v-for="conv in store.sortedConversations"
        :key="conv.id"
        class="w-full flex items-center gap-3 px-4 py-3 hover:bg-on-surface/[0.04] dark:hover:bg-on-surface/5 transition-colors border-b border-on-surface/[0.03] dark:border-on-surface/[0.03] text-left"
        :class="conv.id === store.activeConversationId ? 'bg-primary/5' : ''"
        @click="emit('select', conv.id)"
      >
        <!-- Avatar -->
        <div
          class="size-10 rounded-2xl flex items-center justify-center shrink-0 text-sm font-semibold"
          :class="
            conv.type === 'session_thread'
              ? 'bg-tertiary/10 text-tertiary'
              : conv.type === 'group'
                ? 'bg-success/10 text-success'
                : 'bg-primary/10 text-primary'
          "
        >
          <span
            class="material-symbols-outlined text-lg"
            style="font-variation-settings: 'FILL' 1"
            >{{ getIcon(conv) }}</span
          >
        </div>

        <!-- Content -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between gap-2">
            <p class="text-sm font-bold text-on-surface truncate">{{ getDisplayName(conv) }}</p>
            <span class="text-xs text-on-surface-variant shrink-0">{{
              formatTime(conv.lastMessage?.createdAt)
            }}</span>
          </div>
          <p class="text-xs text-on-surface-variant truncate mt-0.5">
            {{ conv.lastMessage?.body ?? 'No messages yet' }}
          </p>
        </div>

        <!-- Unread badge -->
        <span
          v-if="(store.unreadCounts[conv.id] ?? conv.unreadCount) > 0"
          class="min-w-[18px] h-[18px] bg-primary rounded-full text-xs font-semibold text-on-primary flex items-center justify-center px-1 shrink-0"
        >
          {{
            (store.unreadCounts[conv.id] ?? conv.unreadCount) > 99
              ? '99+'
              : (store.unreadCounts[conv.id] ?? conv.unreadCount)
          }}
        </span>
      </button>
    </div>
  </div>

  <NewConversationModal v-if="showNew" @close="showNew = false" @created="onCreated" />
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useMessagingStore } from '@stores/messaging'
import { useAuthStore } from '@stores/auth'
import MessageBubble from './MessageBubble.vue'

const props = defineProps<{ conversationId: number }>()

const store   = useMessagingStore()
const auth    = useAuthStore()
const listRef = ref<HTMLDivElement | null>(null)
const input   = ref('')
const isLoadingMore = ref(false)
const nextCursor    = ref<string | null>(null)

const conv = computed(() => store.conversations.find(c => c.id === props.conversationId) ?? null)
const msgs = computed(() => store.messages[props.conversationId] ?? [])
const isGroup = computed(() => conv.value?.type === 'group')
const typingList = computed(() => store.typingUsers[props.conversationId] ?? [])

const scrollToBottom = function(smooth = false) {
  nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTo({ top: listRef.value.scrollHeight, behavior: smooth ? 'smooth' : 'instant' })
    }
  })
}

const isAtBottom = function(): boolean  {
  if (!listRef.value) return true
  const el = listRef.value
  return el.scrollTop + el.clientHeight >= el.scrollHeight - 16
}

onMounted(async () => {
  if (!store.messages[props.conversationId]) {
    nextCursor.value = await store.fetchMessages(props.conversationId)
  }
  store.markRead(props.conversationId)
  scrollToBottom()
})

onUnmounted(() => {
  // Clear typing state for this conversation
  if (store.typingUsers[props.conversationId]) {
    store.typingUsers[props.conversationId] = []
  }
})

watch(msgs, (newMsgs, oldMsgs) => {
  if (newMsgs.length > (oldMsgs?.length ?? 0)) {
    if (isAtBottom()) scrollToBottom(true)
    store.markRead(props.conversationId)
  }
}, { deep: false })

const loadMore = async function() {
  if (!nextCursor.value || isLoadingMore.value) return
  isLoadingMore.value = true
  const el = listRef.value
  const prevScrollHeight = el?.scrollHeight ?? 0
  nextCursor.value = await store.fetchMessages(props.conversationId, nextCursor.value)
  isLoadingMore.value = false
  nextTick(() => {
    if (el) el.scrollTop = el.scrollHeight - prevScrollHeight
  })
}

let typingTimer: ReturnType<typeof setTimeout> | null = null
const onInput = function() {
  if (typingTimer) return
  store.sendTyping(props.conversationId)
  typingTimer = setTimeout(() => { typingTimer = null }, 1000)
}

const send = function() {
  const trimmed = input.value.trim()
  if (!trimmed) return
  store.sendMessage(props.conversationId, trimmed)
  input.value = ''
  scrollToBottom(true)
}

const onKeydown = function(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

const getConvLabel = function(): string  {
  if (!conv.value) return 'Chat'
  if (conv.value.type === 'session_thread') return conv.value.name ?? 'Session Thread'
  if (conv.value.type === 'group') return conv.value.name ?? 'Group Chat'
  const other = conv.value.participants.find(p => p.userId !== auth.currentUser?.id)
  return other?.name ?? 'Direct Message'
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Session thread header -->
    <div
      v-if="conv?.type === 'session_thread'"
      class="px-4 py-2 bg-blue-500/5 border-b border-blue-500/10"
    >
      <p class="text-xs font-semibold text-blue-400 uppercase mb-0.5">Session Thread</p>
      <p class="text-xs font-bold text-on-surface truncate">{{ conv.name }}</p>
    </div>

    <!-- Message list -->
    <div
      ref="listRef"
      class="flex-1 overflow-y-auto px-4 py-3 space-y-0.5 scroll-smooth"
    >
      <!-- Load more -->
      <div class="flex justify-center mb-2">
        <button
          v-if="nextCursor"
          class="text-xs font-bold text-on-surface-variant hover:text-orange-500 transition-colors px-3 py-1.5 rounded-xl bg-black/[0.04] dark:bg-white/5"
          :disabled="isLoadingMore"
          @click="loadMore"
        >
          {{ isLoadingMore ? 'Loading…' : 'Load older messages' }}
        </button>
      </div>

      <MessageBubble
        v-for="msg in msgs"
        :key="msg.id"
        :message="msg"
        :is-mine="msg.senderId === auth.currentUser?.id"
        :show-sender="isGroup"
      />

      <!-- Typing indicator -->
      <div v-if="typingList.length > 0" class="flex justify-start mb-1.5">
        <div class="bg-black/[0.06] dark:bg-white/10 rounded-3xl rounded-bl-sm px-4 py-3 flex gap-1 items-center">
          <span class="size-1.5 rounded-full bg-on-surface-variant animate-bounce [animation-delay:0ms]" />
          <span class="size-1.5 rounded-full bg-on-surface-variant animate-bounce [animation-delay:150ms]" />
          <span class="size-1.5 rounded-full bg-on-surface-variant animate-bounce [animation-delay:300ms]" />
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="msgs.length === 0 && !isLoadingMore" class="flex flex-col items-center justify-center py-12 text-center">
        <span class="material-symbols-outlined text-3xl text-on-surface-variant mb-2">chat_bubble_outline</span>
        <p class="text-xs font-bold text-on-surface-variant">No messages yet</p>
        <p class="text-xs text-on-surface-variant/60 mt-1">Say hello!</p>
      </div>
    </div>

    <!-- Input bar -->
    <div class="px-4 py-3 border-t border-black/[0.04] dark:border-white/5">
      <div class="flex items-end gap-2">
        <textarea
          v-model="input"
          rows="1"
          class="flex-1 bg-black/[0.04] dark:bg-white/5 border border-black/[0.06] dark:border-white/5 rounded-2xl px-4 py-2 text-sm text-on-surface placeholder:text-on-surface-variant resize-none focus:outline-none focus:ring-2 focus:ring-orange-500/40 transition-all max-h-24 overflow-y-auto"
          :placeholder="`Message ${getConvLabel()}…`"
          @input="onInput"
          @keydown="onKeydown"
        />
        <button
          class="icon-btn"
          :class="input.trim() ? 'bg-orange-500 text-white hover:bg-orange-600 active:scale-95' : 'bg-black/[0.04] dark:bg-white/5 text-on-surface-variant cursor-not-allowed'"
          :disabled="!input.trim()"
          @click="send"
        >
          <span class="material-symbols-outlined text-lg" style="font-variation-settings: 'FILL' 1">send</span>
        </button>
      </div>
    </div>
  </div>
</template>

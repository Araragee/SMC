<script setup lang="ts">
import { useMessagingStore } from '@stores/messaging'
import ConversationList from './ConversationList.vue'
import ChatWindow from './ChatWindow.vue'

const store = useMessagingStore()

const selectConversation = function(id: string) {
  store.activeConversationId = id
}

const back = function() {
  store.activeConversationId = null
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]"
      enter-from-class="translate-x-full"
      enter-to-class="translate-x-0"
      leave-active-class="transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)]"
      leave-from-class="translate-x-0"
      leave-to-class="translate-x-full"
    >
      <div v-if="store.isOpen" class="fixed inset-0 z-[300] flex justify-end pointer-events-none">
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/20 backdrop-blur-sm pointer-events-auto"
          @click="store.closePanel()"
        />

        <!-- Drawer -->
        <div class="relative w-full max-w-sm h-full glass-heavy flex flex-col pointer-events-auto shadow-2xl">
          <!-- Header -->
          <div class="flex items-center gap-3 px-5 py-4 border-b border-black/[0.04] dark:border-white/5 shrink-0">
            <button
              v-if="store.activeConversationId"
              class="w-9 h-9 rounded-xl bg-black/[0.04] dark:bg-white/5 flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-colors"
              @click="back"
            >
              <span class="material-symbols-outlined">arrow_back</span>
            </button>
            <h2 class="flex-1 text-lg font-black text-on-surface">
              {{ store.activeConversationId ? (store.activeConversation?.name ?? 'Chat') : 'Messages' }}
            </h2>
            <button
              class="w-9 h-9 rounded-xl bg-black/[0.04] dark:bg-white/5 flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-colors"
              @click="store.closePanel()"
            >
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <!-- Body -->
          <div class="flex-1 min-h-0">
            <ConversationList
              v-if="!store.activeConversationId"
              @select="selectConversation"
            />
            <ChatWindow
              v-else
              :conversation-id="store.activeConversationId"
            />
          </div>

          <!-- WS status indicator -->
          <div
            v-if="store.wsStatus !== 'connected'"
            class="px-4 py-2 text-center text-[10px] font-bold"
            :class="store.wsStatus === 'connecting' ? 'bg-amber-500/10 text-amber-500' : 'bg-red-500/10 text-red-400'"
          >
            {{ store.wsStatus === 'connecting' ? 'Connecting…' : 'Disconnected — reconnecting…' }}
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

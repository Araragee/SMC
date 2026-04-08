<script setup lang="ts">
import { useMessagingStore } from '../../stores/messaging'
import { useAuthStore } from '../../stores/auth'
import ConversationList from './ConversationList.vue'
import ChatWindow from './ChatWindow.vue'

// Directive for clicking outside
const vClickOutside = {
  mounted(el: any, binding: any) {
    el.clickOutsideEvent = (event: Event) => {
      // Check if the click was outside the element AND not on the trigger button
      const trigger = document.getElementById('messaging-trigger')
      if (
        !(el === event.target || el.contains(event.target)) &&
        !(trigger === event.target || trigger?.contains(event.target))
      ) {
        binding.value(event)
      }
    }
    document.addEventListener('click', el.clickOutsideEvent)
  },
  unmounted(el: any) {
    document.removeEventListener('click', el.clickOutsideEvent)
  },
}

const store = useMessagingStore()
const authStore = useAuthStore()

const selectConversation = function(id: string) {
  store.activeConversationId = id
}

const back = function() {
  store.activeConversationId = null
}

const togglePanel = function() {
  if (store.isOpen) {
    store.closePanel()
  } else {
    store.isOpen = true
  }
}
</script>

<template>
  <Teleport to="body">
    <!-- Floating Trigger Icon -->
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 translate-y-4 scale-95"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 translate-y-4 scale-95"
    >
      <div
        v-if="authStore.isAuthenticated"
        class="fixed bottom-6 right-6 z-[250]"
      >
        <button
          id="messaging-trigger"
          class="w-16 h-16 rounded-[2rem] bg-gradient-to-br from-orange-500 to-orange-700 text-white shadow-2xl shadow-orange-950/40 flex items-center justify-center transition-all hover:scale-110 active:scale-95 group relative"
          :class="{ 'rotate-90': store.isOpen }"
          @click="togglePanel"
        >
          <span class="material-symbols-outlined text-3xl font-variation-fill">
            {{ store.isOpen ? 'close' : 'chat' }}
          </span>

          <!-- Unread Badge -->
          <span
            v-if="!store.isOpen && store.totalUnread > 0"
            class="absolute -top-1 -right-1 min-w-[24px] h-6 bg-white text-orange-600 rounded-full text-[11px] font-black flex items-center justify-center px-1.5 shadow-lg border-2 border-orange-500"
          >
            {{ store.totalUnread > 99 ? '99+' : store.totalUnread }}
          </span>
        </button>
      </div>
    </Transition>

    <!-- Floating Chat Card -->
    <Transition
      enter-active-class="transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)]"
      enter-from-class="opacity-0 scale-75 translate-y-10 translate-x-10 blur-lg"
      enter-to-class="opacity-100 scale-100 translate-y-0 translate-x-0 blur-0"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100 scale-100 translate-y-0 translate-x-0 blur-0"
      leave-to-class="opacity-0 scale-75 translate-y-10 translate-x-10 blur-lg"
    >
      <div
        v-if="store.isOpen"
        v-click-outside="() => store.closePanel()"
        class="fixed bottom-28 right-6 z-[300] w-[calc(100vw-3rem)] sm:w-96 max-h-[600px] h-[calc(100vh-140px)] glass-heavy rounded-[2.5rem] flex flex-col shadow-2xl border border-white/10 overflow-hidden"
      >
        <!-- Header -->
        <div class="flex items-center gap-3 px-6 py-5 border-b border-black/[0.04] dark:border-white/5 shrink-0 bg-white/5">
          <button
            v-if="store.activeConversationId"
            class="w-10 h-10 rounded-2xl bg-black/[0.04] dark:bg-white/5 flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-colors"
            @click="back"
          >
            <span class="material-symbols-outlined">arrow_back</span>
          </button>
          <div class="flex-1 min-w-0">
            <h2 class="text-xl font-black text-on-surface truncate">
              {{ store.activeConversationId ? (store.activeConversation?.name ?? 'Chat') : 'Messages' }}
            </h2>
            <p v-if="!store.activeConversationId" class="text-[10px] font-bold text-orange-500 uppercase tracking-widest">
              Direct Support
            </p>
          </div>
          <button
            class="w-10 h-10 rounded-2xl bg-black/[0.04] dark:bg-white/5 flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-colors"
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
          class="px-4 py-2 text-center text-[10px] font-bold shrink-0"
          :class="store.wsStatus === 'connecting' ? 'bg-amber-500/10 text-amber-500' : 'bg-red-500/10 text-red-400'"
        >
          {{ store.wsStatus === 'connecting' ? 'Connecting…' : 'Disconnected — reconnecting…' }}
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.font-variation-fill {
  font-variation-settings: 'FILL' 1;
}
</style>

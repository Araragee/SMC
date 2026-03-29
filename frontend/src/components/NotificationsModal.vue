<script setup lang="ts">
import { computed } from 'vue'
import type { Notification } from '../types'
import { useNotificationStore } from '../stores/notification'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const props = defineProps<{
  isOpen: boolean
  notifications: Notification[]
}>()

const emit = defineEmits<{
  close: []
  select: [notification: Notification]
}>()

const notifStore = useNotificationStore()
const authStore = useAuthStore()
const router = useRouter()

const sortedNotifications = computed(() => {
  return [...props.notifications].sort((a, b) => {
    // Unread first, then by date desc
    if (a.isRead !== b.isRead) return a.isRead ? 1 : -1
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  })
})

const unreadCount = computed(() => props.notifications.filter(n => !n.isRead).length)

function typeClasses(type: string) {
  const map: Record<string, string> = {
    info: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
    success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
    warning: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
    error: 'bg-red-500/10 border-red-500/20 text-red-400',
  }
  return map[type] || map.info
}

function typeIcon(type: string) {
  const map: Record<string, string> = {
    info: 'info',
    success: 'check_circle',
    warning: 'warning',
    error: 'error',
  }
  return map[type] || 'notifications'
}

function formatTime(iso: string) {
  const date = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return 'Just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function handleNotifClick(notif: Notification) {
  if (!notif.isRead) {
    notifStore.markAsRead(notif.id)
  }
  if (notif.link) {
    emit('close')
    router.push(notif.link)
  } else {
    emit('select', notif)
  }
}

function markAllAsRead() {
  if (authStore.currentUser?.id) {
    notifStore.markAllAsRead(authStore.currentUser.id)
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition enter-active-class="transition-all duration-200 ease-out" enter-from-class="opacity-0 scale-95 translate-y-4 blur-[4px]" enter-to-class="opacity-100 scale-100 translate-y-0 blur-0" leave-active-class="transition-all duration-200 ease-in" leave-from-class="opacity-100 scale-100 translate-y-0 blur-0" leave-to-class="opacity-0 scale-95 translate-y-4 blur-[4px]">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        @click.self="$emit('close')"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/30 dark:bg-black/60 backdrop-blur-sm" @click="$emit('close')" />

        <!-- Modal -->
        <div class="relative w-full max-w-md glass-heavy rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]">
          <!-- Header -->
          <div class="flex items-center justify-between p-6 border-b border-black/5 dark:border-white/5 shrink-0">
            <div>
              <p class="text-[10px] font-black text-orange-500 uppercase tracking-widest mb-1">Stay Updated</p>
              <h3 class="text-xl font-black text-on-surface dark:text-on-surface">Notifications</h3>
            </div>
            <div class="flex items-center gap-2">
              <button
                v-if="unreadCount > 0"
                class="text-[10px] font-bold text-on-surface-variant dark:text-on-surface-variant hover:text-primary transition-colors uppercase tracking-wider px-2 py-1"
                @click="markAllAsRead"
              >
                Mark all as read
              </button>
              <button
                class="w-10 h-10 rounded-2xl bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 border border-black/8 dark:border-white/10 flex items-center justify-center text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-all"
                @click="$emit('close')"
              >
                <span class="material-symbols-outlined text-lg">close</span>
              </button>
            </div>
          </div>

          <!-- Notification List -->
          <div class="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
            <div v-if="notifications.length === 0" class="text-center py-12">
              <div class="w-16 h-16 bg-black/[0.04] dark:bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4 border border-white/40 dark:border-white/5">
                <span class="material-symbols-outlined text-3xl text-on-surface-variant/60 dark:text-on-surface-variant/40">notifications_off</span>
              </div>
              <p class="text-on-surface-variant dark:text-on-surface-variant font-medium">All caught up!</p>
              <p class="text-on-surface-variant dark:text-on-surface-variant text-sm mt-1">No new notifications at the moment.</p>
            </div>

            <div
              v-for="notif in sortedNotifications"
              :key="notif.id"
              class="group relative rounded-2xl p-4 border transition-all cursor-pointer"
              :class="[
                notif.isRead 
                  ? 'bg-black/[0.02] dark:bg-white/[0.02] border-black/[0.05] dark:border-white/5 opacity-60' 
                  : 'bg-orange-500/5 border-orange-500/20 hover:bg-orange-500/10'
              ]"
              @click="handleNotifClick(notif)"
            >
              <div class="flex gap-4">
                <!-- Icon/Indicator -->
                <div 
                  class="w-10 h-10 rounded-xl shrink-0 flex items-center justify-center border"
                  :class="typeClasses(notif.type)"
                >
                  <span class="material-symbols-outlined text-xl">{{ typeIcon(notif.type) }}</span>
                </div>

                <!-- Content -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-start justify-between gap-2 mb-1">
                    <h4 class="text-sm font-bold text-on-surface dark:text-on-surface truncate group-hover:text-orange-400 transition-colors">
                      {{ notif.title || 'Notification' }}
                    </h4>
                    <span class="text-[10px] text-on-surface-variant dark:text-on-surface-variant whitespace-nowrap font-medium">
                      {{ formatTime(notif.createdAt) }}
                    </span>
                  </div>
                  <p class="text-xs text-on-surface-variant dark:text-on-surface-variant leading-relaxed line-clamp-2 group-hover:text-on-surface">
                    {{ notif.message }}
                  </p>
                </div>
              </div>

              <!-- Unread Dot -->
              <div 
                v-if="!notif.isRead"
                class="absolute top-4 right-4 w-2 h-2 bg-orange-500 rounded-full shadow-[0_0_10px_rgba(249,115,22,0.5)]"
              ></div>
            </div>
          </div>

          <!-- Footer -->
          <div class="p-4 border-t border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-white/[0.02] shrink-0 text-center">
            <p class="text-[10px] text-on-surface-variant dark:text-on-surface-variant font-bold uppercase tracking-tighter">
              Showing last {{ notifications.length }} notifications
            </p>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>


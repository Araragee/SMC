<script setup lang="ts">
import { computed } from 'vue'
import type { Notification } from '@types'
import { useNotificationStore } from '@stores/notification'
import { useAuthStore } from '@stores/auth'
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

import { ref } from 'vue'

const activeFilter = ref<'all' | 'unread' | 'sessions' | 'shop' | 'payments' | 'auth'>('all')

const sortedNotifications = computed(() => {
  let list = props.notifications

  if (activeFilter.value === 'unread') {
    list = list.filter((n) => !n.isRead)
  } else if (activeFilter.value === 'sessions') {
    list = list.filter(
      (n) =>
        n.message?.toLowerCase().includes('session') ||
        n.title?.toLowerCase().includes('session') ||
        n.link?.includes('/schedule')
    )
  } else if (activeFilter.value === 'shop') {
    list = list.filter(
      (n) =>
        n.message?.toLowerCase().includes('order') ||
        n.message?.toLowerCase().includes('shop') ||
        n.message?.toLowerCase().includes('product') ||
        n.link?.includes('/shop')
    )
  } else if (activeFilter.value === 'payments') {
    list = list.filter(
      (n) =>
        n.message?.toLowerCase().includes('payment') ||
        n.message?.toLowerCase().includes('receipt') ||
        n.link?.includes('/payments')
    )
  } else if (activeFilter.value === 'auth') {
    list = list.filter(
      (n) =>
        n.message?.toLowerCase().includes('password') ||
        n.message?.toLowerCase().includes('login') ||
        n.message?.toLowerCase().includes('security')
    )
  }

  return [...list].sort((a: any, b: any) => {
    if (a.isRead !== b.isRead) return a.isRead ? 1 : -1
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  })
})

const unreadCount = computed(() => props.notifications.filter((n) => !n.isRead).length)

const typeClasses = function (type: string) {
  const map: Record<string, string> = {
    info: 'bg-tertiary/10 border-tertiary/20 text-tertiary',
    success: 'bg-success/10 border-success/20 text-success',
    warning: 'bg-warning/10 border-warning/20 text-warning',
    error: 'bg-error/10 border-error/20 text-error',
  }
  return map[type] || map.info
}

const typeIcon = function (type: string) {
  const map: Record<string, string> = {
    info: 'info',
    success: 'check_circle',
    warning: 'warning',
    error: 'error',
  }
  return map[type] || 'notifications'
}

const formatTime = function (iso: string) {
  const date = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return 'Just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const handleNotifClick = function (notif: Notification) {
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

const markAllAsRead = function () {
  if (authStore.currentUser?.id) {
    notifStore.markAllAsRead(authStore.currentUser.id)
  }
}

const closeModal = () => {
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 scale-95 translate-y-4 blur-[4px]"
      enter-to-class="opacity-100 scale-100 translate-y-0 blur-0"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100 scale-100 translate-y-0 blur-0"
      leave-to-class="opacity-0 scale-95 translate-y-4 blur-[4px]"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        @click.self="closeModal"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/40 dark:bg-black/70" @click="closeModal" />

        <!-- Modal -->
        <div
          class="modal-shell relative w-full max-w-md glass-heavy rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between gap-3 p-5 sm:p-6 border-b border-on-surface/5 shrink-0"
          >
            <div class="min-w-0">
              <p class="text-xs font-semibold text-primary uppercase mb-1">Stay Updated</p>
              <h3 class="text-xl font-semibold text-on-surface">Notifications</h3>
            </div>
            <div class="flex items-center gap-1 sm:gap-2 shrink-0">
              <button
                v-if="unreadCount > 0"
                class="text-xs font-bold text-on-surface-variant hover:text-primary transition-colors uppercase px-2 py-1 text-right leading-tight"
                @click="markAllAsRead"
              >
                Mark all<br class="sm:hidden" />
                as read
              </button>
              <button class="icon-btn" @click="closeModal">
                <span class="material-symbols-outlined text-lg">close</span>
              </button>
            </div>
          </div>

          <!-- Filter Pills -->
          <div
            class="px-5 sm:px-6 py-2 flex gap-1.5 overflow-x-auto custom-scrollbar shrink-0 border-b border-on-surface/5 bg-on-surface/[0.01] dark:bg-on-surface/[0.01]"
          >
            <button
              v-for="filter in ['all', 'unread', 'sessions', 'shop', 'payments', 'auth'] as const"
              :key="filter"
              class="shrink-0 px-3.5 py-1.5 rounded-full text-xs font-semibold uppercase transition-all whitespace-nowrap"
              :class="
                activeFilter === filter
                  ? 'bg-primary text-on-primary shadow-sm'
                  : 'bg-on-surface/[0.04] dark:bg-on-surface/5 text-on-surface-variant hover:text-on-surface'
              "
              @click="activeFilter = filter"
            >
              {{ filter }}
            </button>
          </div>

          <!-- Notification List -->
          <div class="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
            <div v-if="notifications.length === 0" class="text-center py-12">
              <div
                class="size-16 bg-on-surface/[0.04] dark:bg-on-surface/5 rounded-full flex items-center justify-center mx-auto mb-4 border border-on-surface/40 dark:border-on-surface/5"
              >
                <span
                  class="material-symbols-outlined text-3xl text-on-surface-variant/60 dark:text-on-surface-variant/40"
                  >notifications_off</span
                >
              </div>
              <p class="text-on-surface-variant font-medium">All caught up!</p>
              <p class="text-on-surface-variant text-sm mt-1">
                No new notifications at the moment.
              </p>
            </div>

            <div
              v-for="notif in sortedNotifications"
              :key="notif.id"
              class="group relative rounded-2xl p-4 border transition-all cursor-pointer"
              :class="[
                notif.isRead
                  ? 'bg-on-surface/[0.02] dark:bg-on-surface/[0.02] border-on-surface/[0.05] dark:border-on-surface/5 opacity-60'
                  : 'bg-primary/5 border-primary/20 hover:bg-primary/10',
              ]"
              @click="handleNotifClick(notif)"
            >
              <div class="flex gap-4">
                <!-- Icon/Indicator -->
                <div
                  class="size-10 rounded-xl shrink-0 flex items-center justify-center border"
                  :class="typeClasses(notif.type)"
                >
                  <span class="material-symbols-outlined text-xl">{{ typeIcon(notif.type) }}</span>
                </div>

                <!-- Content -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-start justify-between gap-2 mb-1">
                    <h4
                      class="text-sm font-bold text-on-surface truncate group-hover:text-primary transition-colors"
                    >
                      {{ notif.title || 'Notification' }}
                    </h4>
                    <span class="text-xs text-on-surface-variant whitespace-nowrap font-medium">
                      {{ formatTime(notif.createdAt) }}
                    </span>
                  </div>
                  <p
                    class="text-xs text-on-surface-variant leading-relaxed line-clamp-2 group-hover:text-on-surface"
                  >
                    {{ notif.message }}
                  </p>
                </div>
              </div>

              <!-- Unread Dot -->
              <div
                v-if="!notif.isRead"
                class="absolute top-4 right-4 size-2 bg-primary rounded-full shadow-[0_0_10px_rgba(249,115,22,0.5)]"
              ></div>
            </div>
          </div>

          <!-- Footer -->
          <div
            class="p-4 border-t border-on-surface/5 bg-on-surface/[0.02] dark:bg-on-surface/[0.02] shrink-0 text-center"
          >
            <p class="text-xs text-on-surface-variant font-bold uppercase tracking-tighter">
              Showing last {{ notifications.length }} notifications
            </p>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

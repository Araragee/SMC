<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notification'
import type { Notification } from '../types'
import NotificationsModal from './NotificationsModal.vue'
import NotificationDetailModal from './NotificationDetailModal.vue'
import UserSettingsModal from './UserSettingsModal.vue'

// Directive for clicking outside
const vClickOutside = {
  mounted(el: any, binding: any) {
    el.clickOutsideEvent = (event: Event) => {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value(event)
      }
    }
    document.addEventListener('click', el.clickOutsideEvent)
  },
  unmounted(el: any) {
    document.removeEventListener('click', el.clickOutsideEvent)
  },
}

const router = useRouter()
const authStore = useAuthStore()
const notifStore = useNotificationStore()

const isNotificationsOpen = ref(false)
const isSettingsOpen = ref(false)
const isUserDropdownOpen = ref(false)
const selectedNotification = ref<Notification | null>(null)

function openNotificationDetail(notification: Notification) {
  selectedNotification.value = notification
}

const roleLabel = computed(() => {
  const labels: Record<string, string> = {
    admin: 'Admin',
    teacher: 'Teacher',
    student: 'Student',
  }
  return labels[authStore.userRole || ''] || authStore.userRole || ''
})

const unreadCount = computed(() => notifStore.unreadCount)

const logout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <header
    class="fixed top-8 right-4 sm:right-8 z-[100] w-[calc(100%-2rem)] sm:w-max px-4 sm:px-6 h-16 bg-white/80 dark:bg-surface-container-low/40 backdrop-blur-3xl rounded-full shadow-lg dark:shadow-[inset_1px_1px_0px_0px_rgba(255,255,255,0.1)] flex items-center gap-3 sm:gap-6 border border-zinc-200 dark:border-white/5 transition-colors duration-300"
  >
    <!-- Logo Section -->
    <div class="flex items-center gap-3 px-2">
      <div class="w-10 h-10 rounded-2xl bg-gradient-to-br from-orange-500 to-orange-700 flex items-center justify-center shadow-lg shadow-orange-900/40 shrink-0">
        <span class="material-symbols-outlined text-zinc-900 dark:text-white text-xl" style="font-variation-settings: 'FILL' 1">music_note</span>
      </div>
      <div class="hidden sm:block leading-none">
        <h2 class="text-zinc-900 dark:text-white font-black tracking-tight text-sm">Sernan's</h2>
        <p class="text-orange-500 text-[10px] font-bold uppercase tracking-wider">Music Clinic</p>
      </div>
    </div>

    <!-- Spacer Dot -->
    <div class="w-1.5 h-1.5 rounded-full bg-white/20 shrink-0"></div>

    <!-- Notifications -->
    <button
      class="relative w-11 h-11 rounded-full flex items-center justify-center text-zinc-600 dark:text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-white/5 transition-all group"
      title="Notifications"
      @click="isNotificationsOpen = true"
    >
      <span class="material-symbols-outlined text-2xl group-hover:scale-110 transition-transform">notifications</span>
      <span
        v-if="unreadCount > 0"
        class="absolute top-1.5 right-1.5 w-5 h-5 bg-orange-500 rounded-full text-[10px] font-black text-zinc-900 dark:text-white flex items-center justify-center border-2 border-white dark:border-[#121212]"
      >{{ unreadCount > 9 ? '9+' : unreadCount }}</span>
    </button>

    <!-- Spacer Dot -->
    <div class="w-1.5 h-1.5 rounded-full bg-zinc-300 dark:bg-white/20 shrink-0"></div>

    <!-- User Profile Dropdown -->
    <div class="relative">
      <button
        class="flex items-center gap-3 px-4 py-2 rounded-full hover:bg-zinc-100 dark:hover:bg-white/5 transition-all group border border-transparent"
        :class="{ 'bg-zinc-100 dark:bg-white/10 border-zinc-200 dark:border-white/10 shadow-lg': isUserDropdownOpen }"
        @click.stop="isUserDropdownOpen = !isUserDropdownOpen"
      >
        <div class="w-10 h-10 rounded-full bg-orange-500/20 border border-orange-500/30 flex items-center justify-center text-orange-500 font-black text-sm shrink-0 group-hover:border-orange-500/50 transition-colors overflow-hidden">
          <img v-if="authStore.currentUser?.avatarUrl" :src="authStore.currentUser.avatarUrl" class="w-full h-full object-cover" />
          <span v-else>{{ authStore.currentUser?.name?.charAt(0)?.toUpperCase() || '?' }}</span>
        </div>
        <div class="hidden lg:block text-left">
          <p class="text-sm font-bold text-zinc-900 dark:text-white leading-tight truncate max-w-[120px]">{{ authStore.currentUser?.name || 'User' }}</p>
          <p class="text-[10px] text-zinc-600 dark:text-zinc-500 font-bold uppercase tracking-widest">{{ roleLabel }}</p>
        </div>
        <span 
          class="material-symbols-outlined text-zinc-500 dark:text-zinc-400 dark:text-zinc-500 text-xl transition-transform duration-300"
          :class="{ 'rotate-180': isUserDropdownOpen }"
        >expand_more</span>
      </button>

      <!-- Dropdown Content -->
      <Transition enter-active-class="transition-all duration-200 ease-out" enter-from-class="opacity-0 translate-y-2 scale-95 blur-[4px]" enter-to-class="opacity-100 translate-y-0 scale-100 blur-0" leave-active-class="transition-all duration-200 ease-in" leave-from-class="opacity-100 translate-y-0 scale-100 blur-0" leave-to-class="opacity-0 translate-y-2 scale-95 blur-[4px]">
        <div 
          v-if="isUserDropdownOpen"
          v-click-outside="() => isUserDropdownOpen = false"
          class="absolute top-full right-0 mt-3 w-56 bg-white dark:bg-zinc-900/90 backdrop-blur-2xl rounded-[1.5rem] border border-zinc-200 dark:border-white/10 shadow-xl dark:shadow-2xl overflow-hidden z-[110]"
        >
          <div class="p-4 border-b border-zinc-100 dark:border-white/5 bg-zinc-50/50 dark:bg-white/[0.02]">
            <p class="text-[10px] font-black text-zinc-500 dark:text-zinc-400 dark:text-zinc-500 uppercase tracking-widest mb-1">Signed in as</p>
            <p class="text-sm font-bold text-zinc-900 dark:text-white truncate">{{ authStore.currentUser?.email }}</p>
          </div>
          
          <div class="p-2">
            <button
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-zinc-600 dark:text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-white/5 transition-all text-xs font-bold"
              @click="isSettingsOpen = true; isUserDropdownOpen = false"
            >
              <span class="material-symbols-outlined text-lg">person_edit</span>
              Profile Settings
            </button>
            <button class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-zinc-600 dark:text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-white/5 transition-all text-xs font-bold">
              <span class="material-symbols-outlined text-lg">settings</span>
              Preferences
            </button>
            <div class="h-px bg-zinc-100 dark:bg-white/5 my-1 mx-2"></div>
            <button
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-zinc-500 dark:text-zinc-400 dark:text-zinc-500 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition-all text-xs font-black"
              @click="logout"
            >
              <span class="material-symbols-outlined text-lg">logout</span>
              Sign Out
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </header>

  <!-- Notifications Modal -->
  <NotificationsModal
    :is-open="isNotificationsOpen"
    :notifications="notifStore.notifications"
    @close="isNotificationsOpen = false"
    @select="openNotificationDetail"
  />

  <!-- Notification Detail Modal -->
  <NotificationDetailModal
    :notification="selectedNotification"
    @close="selectedNotification = null"
  />

  <!-- User Settings Modal -->
  <UserSettingsModal
    :is-open="isSettingsOpen"
    @close="isSettingsOpen = false"
  />
</template>


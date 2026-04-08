<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notification'
import { useModalStore } from '../stores/modal'
import type { Notification } from '../types'
import NotificationsModal from './NotificationsModal.vue'
import NotificationDetailModal from './NotificationDetailModal.vue'
import UserSettingsModal from './UserSettingsModal.vue'
import PreferencesModal from './PreferencesModal.vue'

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
const modalStore = useModalStore()

const isUserDropdownOpen = ref(false)
const selectedNotification = ref<Notification | null>(null)

const openNotificationDetail = function(notification: Notification) {
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
  router.push('/')
}

const openNotifications = () => {
  modalStore.openNotifications()
}

const openSettings = () => {
  modalStore.openSettings()
  isUserDropdownOpen.value = false
}

const openPreferences = () => {
  modalStore.openPreferences()
  isUserDropdownOpen.value = false
}

const toggleUserDropdown = () => {
  isUserDropdownOpen.value = !isUserDropdownOpen.value
}

const closeUserDropdown = () => {
  isUserDropdownOpen.value = false
}
</script>

<template>
  <header
    class="fixed top-8 right-4 sm:right-8 z-[100] w-[calc(100%-2rem)] sm:w-max px-4 sm:px-6 h-16 glass-thin rounded-full flex items-center gap-3 sm:gap-6 transition-colors duration-300"
  >
    <!-- Logo Section -->
    <div class="flex items-center gap-3 px-2">
      <div class="w-10 h-10 rounded-2xl bg-gradient-to-br from-orange-500 to-orange-700 flex items-center justify-center shadow-lg shadow-orange-900/40 shrink-0 overflow-hidden">
        <img src="/logo.png" alt="Logo" class="w-full h-full object-cover" />
      </div>
      <div class="hidden sm:block leading-none">
        <h2 class="text-on-surface dark:text-on-surface font-black tracking-tight text-sm">Sernan's</h2>
        <p class="text-orange-500 text-[10px] font-bold uppercase tracking-wider">Music Clinic</p>
      </div>
    </div>

    <!-- Spacer Dot -->
    <div class="w-1.5 h-1.5 rounded-full bg-black/10 dark:bg-white/20 shrink-0"></div>

    <!-- Notifications -->
    <button
      class="relative w-11 h-11 rounded-full flex items-center justify-center text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-black/5 dark:hover:bg-white/5 transition-all group"
      title="Notifications"
      @click="openNotifications"
    >
      <span class="material-symbols-outlined text-2xl group-hover:scale-110 transition-transform">notifications</span>
      <span
        v-if="unreadCount > 0"
        class="absolute top-1.5 right-1.5 w-5 h-5 bg-error rounded-full text-[10px] font-black text-white flex items-center justify-center border-2 border-surface dark:border-surface"
      >{{ unreadCount > 9 ? '9+' : unreadCount }}</span>
    </button>

    <!-- Spacer Dot -->
    <div class="w-1.5 h-1.5 rounded-full bg-outline-variant dark:bg-outline-variant shrink-0"></div>

    <!-- User Profile Dropdown -->
    <div class="relative">
      <button
        class="flex items-center gap-3 px-4 py-2 rounded-full hover:bg-black/5 dark:hover:bg-white/5 transition-all group border border-transparent"
        :class="{ 'bg-black/5 dark:bg-white/10 border-outline-variant shadow-lg': isUserDropdownOpen }"
        @click.stop="toggleUserDropdown"
      >
        <div class="w-10 h-10 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center text-primary font-black text-sm shrink-0 group-hover:border-primary/50 transition-colors overflow-hidden">
          <img v-if="authStore.currentUser?.avatarUrl" :src="authStore.currentUser.avatarUrl" class="w-full h-full object-cover" />
          <span v-else>{{ authStore.currentUser?.name?.charAt(0)?.toUpperCase() || '?' }}</span>
        </div>
        <div class="hidden lg:block text-left">
          <p class="text-sm font-bold text-on-surface dark:text-on-surface leading-tight truncate max-w-[120px]">{{ authStore.currentUser?.name || 'User' }}</p>
          <p class="text-[10px] text-on-surface-variant dark:text-on-surface-variant font-bold uppercase tracking-widest">{{ roleLabel }}</p>
        </div>
        <span 
          class="material-symbols-outlined text-on-surface-variant dark:text-on-surface-variant text-xl transition-transform duration-300"
          :class="{ 'rotate-180': isUserDropdownOpen }"
        >expand_more</span>
      </button>

      <!-- Dropdown Content -->
      <Transition enter-active-class="transition-all duration-200 ease-out" enter-from-class="opacity-0 translate-y-2 scale-95 blur-[4px]" enter-to-class="opacity-100 translate-y-0 scale-100 blur-0" leave-active-class="transition-all duration-200 ease-in" leave-from-class="opacity-100 translate-y-0 scale-100 blur-0" leave-to-class="opacity-0 translate-y-2 scale-95 blur-[4px]">
        <div 
          v-if="isUserDropdownOpen"
          v-click-outside="closeUserDropdown"
          class="absolute top-full right-0 mt-3 w-56 glass-heavy rounded-[1.5rem] overflow-hidden z-[110]"
        >
          <div class="p-4 border-b border-outline-variant dark:border-outline-variant bg-black/2 dark:bg-white/2">
            <p class="text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest mb-1">Signed in as</p>
            <p class="text-sm font-bold text-on-surface dark:text-on-surface truncate">{{ authStore.currentUser?.email }}</p>
          </div>
          
          <div class="p-2">
            <button
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-black/5 dark:hover:bg-white/5 transition-all text-xs font-bold"
              @click="openSettings"
            >
              <span class="material-symbols-outlined text-lg">person_edit</span>
              Profile Settings
            </button>
            <button
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-black/5 dark:hover:bg-white/5 transition-all text-xs font-bold"
              @click="openPreferences"
            >
              <span class="material-symbols-outlined text-lg">settings</span>
              Preferences
            </button>
            <div class="h-px bg-outline-variant dark:bg-outline-variant my-1 mx-2"></div>
            <button
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-error dark:text-error hover:text-white hover:bg-error/90 dark:hover:bg-error/90 transition-all text-xs font-black"
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
    :is-open="modalStore.isNotificationsOpen"
    :notifications="notifStore.notifications"
    @close="modalStore.closeNotifications()"
    @select="openNotificationDetail"
  />
  <NotificationDetailModal
    :notification="selectedNotification"
    @close="selectedNotification = null"
  />
  <UserSettingsModal
    :is-open="modalStore.isSettingsOpen"
    @close="modalStore.closeSettings()"
  />
  <PreferencesModal
    :is-open="modalStore.isPreferencesOpen"
    @close="modalStore.closePreferences()"
  />
</template>

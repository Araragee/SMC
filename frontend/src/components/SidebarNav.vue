<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notification'
import { useMessagingStore } from '../stores/messaging'
import { useModalStore } from '../stores/modal'
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
const route = useRoute()
const authStore = useAuthStore()
const notifStore = useNotificationStore()
const messagingStore = useMessagingStore()
const modalStore = useModalStore()

const isSidebarOpen = ref(false)
const isUserDropdownOpen = ref(false)
const selectedNotification = ref<Notification | null>(null)

type NavItem = { path: string; icon: string; label: string }

const navsByRole: Record<string, NavItem[]> = {
  admin: [
    { path: '/admin', icon: 'dashboard', label: 'Dashboard' },
    { path: '/admin/schedule', icon: 'calendar_month', label: 'Schedule' },
    { path: '/admin/students', icon: 'school', label: 'Students' },
    { path: '/admin/teachers', icon: 'person_book', label: 'Teachers' },
    { path: '/admin/users', icon: 'manage_accounts', label: 'All Users' },
  ],
  teacher: [
    { path: '/teacher', icon: 'dashboard', label: 'Dashboard' },
    { path: '/teacher/schedule', icon: 'calendar_month', label: 'Schedule' },
    { path: '/teacher/students', icon: 'group', label: 'Students' },
    { path: '/teacher/instruments', icon: 'piano', label: 'Instruments' },
    { path: '/teacher/payments', icon: 'payments', label: 'Payments' },
  ],
  student: [
    { path: '/student', icon: 'dashboard', label: 'Dashboard' },
    { path: '/student/schedule', icon: 'calendar_today', label: 'Schedule' },
    { path: '/student/homework', icon: 'school', label: 'Homework' },
  ],
}

const navItems = computed<NavItem[]>(() => navsByRole[authStore.userRole || ''] ?? [])

const isActive = (path: string) => route.path === path

const openNotificationDetail = function (notification: Notification) {
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

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}

const closeSidebar = () => {
  isSidebarOpen.value = false
}

const openNotifications = () => {
  modalStore.openNotifications()
}

const openMessaging = () => {
  messagingStore.isOpen = true
}

const toggleUserDropdown = () => {
  isUserDropdownOpen.value = !isUserDropdownOpen.value
}

const openSettings = () => {
  modalStore.openSettings()
  isUserDropdownOpen.value = false
}
</script>

<template>
  <!-- Mobile Hamburger Overlay Toggle -->
  <button
    class="fixed top-4 left-4 z-[105] lg:hidden w-12 h-12 bg-surface-container-low/80 backdrop-blur-lg rounded-full border border-black/[0.08] dark:border-white/10 flex items-center justify-center shadow-lg"
    @click="toggleSidebar"
  >
    <span class="material-symbols-outlined text-on-surface dark:text-on-surface">menu</span>
  </button>

  <Transition
    enter-active-class="transition-opacity duration-300"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-300"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="isSidebarOpen"
      class="fixed inset-0 bg-black/50 z-[90] lg:hidden backdrop-blur-sm"
      @click="closeSidebar"
    />
  </Transition>

  <aside
    class="fixed top-0 left-0 h-screen w-full glass-thin border-r border-black/5 dark:border-white/5 p-4 flex flex-col z-[100] transition-transform duration-300 lg:w-full lg:sticky lg:top-6 lg:h-auto lg:rounded-[2rem] lg:shadow-2xl lg:translate-x-0"
    :class="isSidebarOpen ? 'translate-x-0' : '-translate-x-full'"
  >
    <!-- Logo Section -->
    <div class="flex flex-col items-center py-4 mb-2">
      <div
        class="w-12 h-12 rounded-2xl bg-gradient-to-br from-orange-500 to-orange-700 flex items-center justify-center shadow-lg shadow-orange-900/40 shrink-0 mb-3 overflow-hidden"
      >
        <img src="/logo.png" alt="Logo" class="w-full h-full object-cover" />
      </div>
      <div class="text-center leading-none">
        <h2 class="text-on-surface dark:text-on-surface font-black tracking-tight text-lg">
          Sernan's
        </h2>
        <p class="text-orange-500 text-[11px] font-bold uppercase tracking-wider">Music Clinic</p>
      </div>
    </div>

    <div class="h-px bg-black/[0.04] dark:bg-white/5 my-4"></div>

    <!-- Nav Links -->
    <nav
      class="flex flex-col flex-1 lg:flex-none lg:max-h-[50vh] overflow-y-auto overflow-x-hidden pt-2 scrollbar-hide"
    >
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="flex items-center gap-3 px-4 py-3 border rounded-2xl text-sm font-bold transition-all border-opacity-20 py-1.5"
        :class="
          isActive(item.path)
            ? 'bg-orange-500/10 text-orange-500 border-orange-500 shadow-sm shadow-orange-500/20'
            : 'text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-black/5 dark:hover:bg-white/5 border-transparent'
        "
        @click="closeSidebar"
      >
        <span
          class="material-symbols-outlined text-xl"
          :style="isActive(item.path) ? 'font-variation-settings: \'FILL\' 1' : ''"
          >{{ item.icon }}</span
        >
        <span>{{ item.label }}</span>
      </router-link>
    </nav>

    <!-- Bottom Section -->
    <div class="py-3 border-black/[0.04] dark:border-white/5 flex flex-col gap-3 relative">
      <div class="flex flex-col items-center gap-2 w-full">
        <!-- Notifications -->
        <button
          class="w-full relative flex-1 flex items-center justify-start gap-2 p-3 bg-black/[0.04] dark:bg-white/5 hover:bg-black/5 dark:hover:bg-white/10 rounded-2xl text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-all group border border-black/[0.04] dark:border-white/5"
          @click="openNotifications"
        >
          <span class="material-symbols-outlined text-xl group-hover:scale-110 transition-transform"
            >notifications</span
          >
          <span class="text-xs font-bold uppercase tracking-wider">Notifs</span>
          <span
            v-if="unreadCount > 0"
            class="absolute top-1.5 right-2 w-4 h-4 bg-orange-500 rounded-full text-[9px] font-black text-white flex items-center justify-center"
            >{{ unreadCount > 9 ? '9+' : unreadCount }}</span
          >
        </button>
        <!-- Messages -->
        <button
          class="w-full relative flex-1 flex items-center justify-start gap-2 p-3 bg-black/[0.04] dark:bg-white/5 hover:bg-black/5 dark:hover:bg-white/10 rounded-2xl text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-all group border border-black/[0.04] dark:border-white/5"
          @click="openMessaging"
        >
          <span
            class="material-symbols-outlined text-xl group-hover:scale-110 transition-transform"
            style="font-variation-settings: 'FILL' 1"
            >chat</span
          >
          <span class="text-xs font-bold uppercase tracking-wider">Chat</span>
          <span
            v-if="messagingStore.totalUnread > 0"
            class="absolute top-1.5 right-2 min-w-[16px] h-4 bg-orange-500 rounded-full text-[9px] font-black text-white flex items-center justify-center px-0.5"
            >{{ messagingStore.totalUnread > 99 ? '99+' : messagingStore.totalUnread }}</span
          >
        </button>
      </div>

      <!-- User Profile Dropdown -->
      <div class="relative w-full">
        <button
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl hover:bg-black/5 dark:hover:bg-white/5 transition-all group border border-transparent"
          :class="{
            'bg-white/10 border-black/[0.08] dark:border-white/10 shadow-lg': isUserDropdownOpen,
          }"
          @click.stop="toggleUserDropdown"
        >
          <div
            class="w-10 h-10 rounded-full bg-orange-500/20 border border-orange-500/30 flex items-center justify-center text-orange-400 font-black text-sm shrink-0 group-hover:border-orange-500/50 transition-colors overflow-hidden"
          >
            <img
              v-if="authStore.currentUser?.avatarUrl"
              :src="authStore.currentUser.avatarUrl"
              class="w-full h-full object-cover"
            />
            <span v-else>{{ authStore.currentUser?.name?.charAt(0)?.toUpperCase() || '?' }}</span>
          </div>
          <div class="flex-1 text-left min-w-0">
            <p
              class="text-sm font-bold text-on-surface dark:text-on-surface leading-tight truncate"
            >
              {{ authStore.currentUser?.name || 'User' }}
            </p>
            <p
              class="text-[10px] text-on-surface-variant dark:text-on-surface-variant font-bold uppercase tracking-widest truncate"
            >
              {{ roleLabel }}
            </p>
          </div>
          <span
            class="material-symbols-outlined text-on-surface-variant dark:text-on-surface-variant text-xl transition-transform duration-300"
            :class="{ 'rotate-180 text-on-surface dark:text-on-surface': isUserDropdownOpen }"
            >expand_less</span
          >
        </button>

        <!-- Dropdown Content -->
        <Transition
          enter-active-class="transition-all duration-200 ease-out"
          enter-from-class="opacity-0 translate-y-2 scale-95 blur-[4px]"
          enter-to-class="opacity-100 translate-y-0 scale-100 blur-0"
          leave-active-class="transition-all duration-200 ease-in"
          leave-from-class="opacity-100 translate-y-0 scale-100 blur-0"
          leave-to-class="opacity-0 translate-y-2 scale-95 blur-[4px]"
        >
          <div
            v-if="isUserDropdownOpen"
            v-click-outside="() => (isUserDropdownOpen = false)"
            class="absolute bottom-full left-0 mb-3 w-56 glass-heavy rounded-[1.5rem] shadow-2xl overflow-hidden z-[110]"
          >
            <div
              class="p-4 border-b border-black/[0.04] dark:border-white/5 bg-black/[0.02] dark:bg-white/[0.02]"
            >
              <p
                class="text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest mb-1"
              >
                Signed in as
              </p>
              <p class="text-sm font-bold text-on-surface dark:text-on-surface truncate">
                {{ authStore.currentUser?.email }}
              </p>
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
              >
                <span class="material-symbols-outlined text-lg">settings</span>
                Preferences
              </button>
              <div class="h-px bg-black/[0.04] dark:bg-white/5 my-1 mx-2"></div>
              <button
                class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-on-surface-variant dark:text-on-surface-variant hover:text-red-500 dark:hover:text-red-400 hover:bg-red-500/10 transition-all text-xs font-black"
                @click="logout"
              >
                <span class="material-symbols-outlined text-lg">logout</span>
                Sign Out
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </aside>

  <!-- Notifications Modal -->
  <NotificationsModal
    :is-open="modalStore.isNotificationsOpen"
    :notifications="notifStore.notifications"
    @close="modalStore.closeNotifications()"
    @select="openNotificationDetail"
  />

  <!-- Notification Detail Modal -->
  <NotificationDetailModal
    :notification="selectedNotification"
    @close="selectedNotification = null"
  />

  <!-- User Settings Modal -->
  <UserSettingsModal :is-open="modalStore.isSettingsOpen" @close="modalStore.closeSettings()" />
</template>

<style scoped>
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>

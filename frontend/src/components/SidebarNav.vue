<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@stores/auth'
import { useNotificationStore } from '@stores/notification'
import { useMessagingStore } from '@stores/messaging'
import { useModalStore } from '@stores/modal'
import NotificationsModal from '@components/NotificationsModal.vue'
import NotificationDetailModal from '@components/NotificationDetailModal.vue'
import UserSettingsModal from '@components/UserSettingsModal.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const notifStore = useNotificationStore()
const messagingStore = useMessagingStore()
const modalStore = useModalStore()

const isSidebarOpen = ref(false)
const isUserDropdownOpen = ref(false)
const selectedNotification = ref<any>(null)

const roleLabel = computed(() => {
  const role = authStore.currentUser?.role || 'student'
  return role.charAt(0).toUpperCase() + role.slice(1)
})

const navItems = computed(() => {
  const role = authStore.currentUser?.role || 'student'
  const items = [
    { label: 'Dashboard', icon: 'dashboard', path: `/${role}` },
    { label: 'Schedule', icon: 'calendar_month', path: `/${role}/schedule` },
  ]

  if (role === 'admin') {
    items.push(
      { label: 'Students', icon: 'group', path: '/admin/students' },
      { label: 'Teachers', icon: 'person', path: '/admin/teachers' },
      { label: 'Ledger', icon: 'payments', path: '/admin/payments' },
      { label: 'Shop', icon: 'storefront', path: '/admin/instruments' }
    )
  } else if (role === 'teacher') {
    items.push(
      { label: 'Students', icon: 'group', path: '/teacher/students' },
      { label: 'Payments', icon: 'payments', path: '/teacher/payments' },
      { label: 'Instruments', icon: 'piano', path: '/teacher/instruments' },
      { label: 'Shop', icon: 'storefront', path: '/teacher/shop' }
    )
  } else if (role === 'student') {
    items.push(
      { label: 'Homework', icon: 'menu_book', path: '/student/homework' },
      { label: 'Payments', icon: 'payments', path: '/student/payments' },
      { label: 'Shop', icon: 'storefront', path: '/student/shop' }
    )
  }

  return items
})

const unreadCount = computed(() => notifStore.unreadCount)

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}

const closeSidebar = () => {
  isSidebarOpen.value = false
}

const toggleUserDropdown = () => {
  isUserDropdownOpen.value = !isUserDropdownOpen.value
}

const logout = async () => {
  await authStore.logout()
  router.push('/login')
}

const openNotifications = () => {
  modalStore.openNotifications()
  closeSidebar()
}

const openMessaging = () => {
  messagingStore.isOpen = true
  closeSidebar()
}

const openSettings = () => {
  modalStore.openSettings()
  isUserDropdownOpen.value = false
  closeSidebar()
}

const openNotificationDetail = (notif: any) => {
  selectedNotification.value = notif
}

const isActive = (path: string) => {
  if (path === '/admin' || path === '/teacher' || path === '/student') {
    return route.path === path
  }
  return route.path.startsWith(path)
}

onMounted(() => {
  if (authStore.currentUser?.id) {
    notifStore.fetchNotifications(authStore.currentUser.id)
  }
  messagingStore.fetchConversations()
})
</script>

<template>
  <button
    class="fixed top-4 left-4 z-[105] lg:hidden w-12 h-12 bg-surface-container-low/80 backdrop-blur-lg rounded-full border border-black/[0.08] dark:border-white/10 flex items-center justify-center shadow-lg"
    @click="toggleSidebar"
  >
    <span class="material-symbols-outlined text-on-surface dark:text-on-surface">menu</span>
  </button>

  <div
    v-if="isSidebarOpen"
    class="fixed inset-0 bg-black/50 z-[90] lg:hidden backdrop-blur-sm"
    @click="closeSidebar"
  ></div>

  <aside
    class="fixed top-0 left-0 h-screen w-full glass-thin border-r border-black/5 dark:border-white/5 p-4 flex flex-col z-[100] lg:w-full lg:sticky lg:top-6 lg:h-auto lg:rounded-[2rem] lg:shadow-2xl lg:translate-x-0"
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
        class="flex items-center gap-3 px-4 py-3 border rounded-2xl text-sm font-bold border-opacity-20 py-1.5"
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
          >{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </router-link>
    </nav>

    <!-- Bottom Section -->
    <div class="py-3 border-black/[0.04] dark:border-white/5 flex flex-col gap-3 relative">
      <div class="flex flex-col items-center gap-2 w-full">
        <!-- Notifications -->
        <button
          class="w-full relative flex-1 flex items-center justify-start gap-2 p-3 bg-black/[0.04] dark:bg-white/5 hover:bg-black/5 dark:hover:bg-white/10 rounded-2xl text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface group border border-black/[0.04] dark:border-white/5"
          @click="openNotifications"
        >
          <span class="material-symbols-outlined text-xl group-hover:scale-110">notifications</span>
          <span class="text-xs font-bold uppercase tracking-wider">Notifs</span>
          <span
            v-if="unreadCount > 0"
            class="absolute top-1.5 right-2 w-4 h-4 bg-orange-500 rounded-full text-[9px] font-black text-white flex items-center justify-center"
            >{{ unreadCount > 9 ? '9+' : unreadCount }}</span>
        </button>
        <!-- Messages -->
        <button
          class="w-full relative flex-1 flex items-center justify-start gap-2 p-3 bg-black/[0.04] dark:bg-white/5 hover:bg-black/5 dark:hover:bg-white/10 rounded-2xl text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface group border border-black/[0.04] dark:border-white/5"
          @click="openMessaging"
        >
          <span
            class="material-symbols-outlined text-xl group-hover:scale-110"
            style="font-variation-settings: 'FILL' 1"
            >chat</span>
          <span class="text-xs font-bold uppercase tracking-wider">Chat</span>
          <span
            v-if="messagingStore.totalUnread > 0"
            class="absolute top-1.5 right-2 min-w-[16px] h-4 bg-orange-500 rounded-full text-[9px] font-black text-white flex items-center justify-center px-0.5"
            >{{ messagingStore.totalUnread > 99 ? '99+' : messagingStore.totalUnread }}</span>
        </button>
      </div>

      <!-- User Profile Dropdown -->
      <div class="relative w-full">
        <button
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl hover:bg-black/5 dark:hover:bg-white/5 group border border-transparent"
          :class="{
            'bg-white/10 border-black/[0.08] dark:border-white/10 shadow-lg': isUserDropdownOpen,
          }"
          @click.stop="toggleUserDropdown"
        >
          <div
            class="w-10 h-10 rounded-full bg-orange-500/20 border border-orange-500/30 flex items-center justify-center text-orange-400 font-black text-sm shrink-0 group-hover:border-orange-500/50 overflow-hidden"
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
            class="material-symbols-outlined text-on-surface-variant dark:text-on-surface-variant text-xl"
            :class="{ 'rotate-180 text-on-surface dark:text-on-surface': isUserDropdownOpen }"
            >expand_less</span>
        </button>

        <!-- Dropdown Content -->
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
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-black/5 dark:hover:bg-white/5 text-xs font-bold"
              @click="openSettings"
            >
              <span class="material-symbols-outlined text-lg">person_edit</span>
              Profile Settings
            </button>
            <button
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-black/5 dark:hover:bg-white/5 text-xs font-bold"
              @click="openSettings"
            >
              <span class="material-symbols-outlined text-lg">settings</span>
              Preferences
            </button>
            <div class="h-px bg-black/[0.04] dark:bg-white/5 my-1 mx-2"></div>
            <button
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-on-surface-variant dark:text-on-surface-variant hover:text-red-500 dark:hover:text-red-400 hover:bg-red-500/10 text-xs font-black"
              @click="logout"
            >
              <span class="material-symbols-outlined text-lg">logout</span>
              Sign Out
            </button>
          </div>
        </div>
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

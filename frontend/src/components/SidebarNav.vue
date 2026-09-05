<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@stores/auth'
import { SHOP_ENABLED } from '@typescript/constants'
import { useNotificationStore } from '@stores/notification'
import { useMessagingStore } from '@stores/messaging'
import { useModalStore } from '@stores/modal'
import NotificationsModal from '@components/NotificationsModal.vue'
import NotificationDetailModal from '@components/NotificationDetailModal.vue'
import UserSettingsModal from '@components/UserSettingsModal.vue'

// ── click-outside directive ───────────────────────────────────────────────────
const vClickOutside = {
  mounted(el: any, binding: any) {
    el._co = (e: Event) => {
      if (!el.contains(e.target)) binding.value(e)
    }
    document.addEventListener('click', el._co)
  },
  unmounted(el: any) {
    document.removeEventListener('click', el._co)
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
      { label: 'Users', icon: 'manage_accounts', path: '/admin/users' },
      { label: 'Students', icon: 'group', path: '/admin/students' },
      { label: 'Roster', icon: 'checklist', path: '/admin/roster' },
      { label: 'Teachers', icon: 'person', path: '/admin/teachers' },
      { label: 'Ledger', icon: 'payments', path: '/admin/payments' },
      ...(SHOP_ENABLED ? [{ label: 'Shop', icon: 'storefront', path: '/admin/instruments' }] : []),
      { label: 'Activity', icon: 'history', path: '/admin/activity-log' }
    )
  } else if (role === 'teacher') {
    items.push(
      { label: 'Students', icon: 'group', path: '/teacher/students' },
      { label: 'Instruments', icon: 'piano', path: '/teacher/instruments' },
      { label: 'Payments', icon: 'payments', path: '/teacher/payments' },
      ...(SHOP_ENABLED ? [{ label: 'Shop', icon: 'storefront', path: '/teacher/shop' }] : [])
    )
  } else if (role === 'student') {
    items.push(
      { label: 'Homework', icon: 'menu_book', path: '/student/homework' },
      { label: 'Payments', icon: 'payments', path: '/student/payments' },
      ...(SHOP_ENABLED ? [{ label: 'Shop', icon: 'storefront', path: '/student/shop' }] : [])
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

// Below 640px style.css pins the body and scrolls #app, so the usual
// body-overflow lock does nothing; lock whichever element actually scrolls.
watch(isSidebarOpen, (open) => {
  const app = document.getElementById('app')
  if (app) app.style.overflow = open ? 'hidden' : ''
  document.body.style.overflow = open ? 'hidden' : ''
})

const onKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') closeSidebar()
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

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  const app = document.getElementById('app')
  if (app) app.style.overflow = ''
  document.body.style.overflow = ''
})

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  if (authStore.currentUser?.id) {
    notifStore.fetchNotifications(authStore.currentUser.id)
  }
  messagingStore.fetchConversations()
})
</script>

<template>
  <button
    class="fixed top-4 left-4 z-[105] lg:hidden size-12 bg-surface-container-low/80 rounded-full border border-on-surface/[0.08] dark:border-on-surface/10 flex items-center justify-center shadow-lg"
    :aria-expanded="isSidebarOpen"
    aria-controls="app-sidebar"
    :aria-label="isSidebarOpen ? 'Close menu' : 'Open menu'"
    @click="toggleSidebar"
  >
    <span class="material-symbols-outlined text-on-surface">
      {{ isSidebarOpen ? 'close' : 'menu' }}
    </span>
    <!-- The dock used to surface these counts on every screen; behind a drawer
  they are invisible, so the trigger carries a dot when either is unread. -->
    <span
      v-if="!isSidebarOpen && (unreadCount > 0 || messagingStore.totalUnread > 0)"
      class="absolute top-1 right-1 size-3 rounded-full bg-primary border-2 border-surface-container-low"
      aria-hidden="true"
    ></span>
  </button>

  <Transition
    enter-active-class="transition-opacity duration-300"
    enter-from-class="opacity-0"
    leave-active-class="transition-opacity duration-300"
    leave-to-class="opacity-0"
  >
    <div
      v-if="isSidebarOpen"
      class="fixed inset-0 bg-black/40 dark:bg-black/70 z-[90] lg:hidden"
      @click="closeSidebar"
    ></div>
  </Transition>

  <aside
    id="app-sidebar"
    class="fixed top-0 left-0 h-screen w-[280px] max-w-[85vw] glass-thin border-r border-on-surface/5 p-4 flex flex-col z-[100] transition-transform duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] lg:w-full lg:max-w-none lg:sticky lg:top-6 lg:h-auto lg:rounded-3xl lg:border-r-0 lg:shadow-2xl lg:translate-x-0 lg:transition-none"
    :class="isSidebarOpen ? 'translate-x-0' : '-translate-x-full'"
  >
    <!-- Logo Section -->
    <div class="flex flex-col items-center py-4 mb-2">
      <div
        class="size-12 rounded-2xl bg-primary flex items-center justify-center shadow-lg shrink-0 mb-3 overflow-hidden"
      >
        <img src="/logo.png" alt="Logo" class="w-full h-full object-cover" />
      </div>
      <div class="text-center leading-none">
        <h2 class="text-on-surface font-semibold tracking-tight text-lg">Sernan's</h2>
        <p class="text-primary text-xs font-bold uppercase">Music Clinic</p>
      </div>
    </div>

    <div class="h-px bg-on-surface/[0.04] dark:bg-on-surface/5 my-4"></div>

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
            ? 'bg-primary/10 text-primary border-primary shadow-sm'
            : 'text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-on-surface/5 dark:hover:bg-on-surface/5 border-transparent'
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
    <div
      class="py-3 border-on-surface/[0.04] dark:border-on-surface/5 flex flex-col gap-3 relative"
    >
      <div class="flex flex-col items-center gap-2 w-full">
        <!-- Notifications -->
        <button
          class="w-full relative flex-1 flex items-center justify-start gap-2 p-3 bg-on-surface/[0.04] dark:bg-on-surface/5 hover:bg-on-surface/5 dark:hover:bg-on-surface/10 rounded-2xl text-on-surface-variant hover:text-on-surface group border border-on-surface/[0.04] dark:border-on-surface/5"
          @click="openNotifications"
        >
          <span class="material-symbols-outlined text-xl group-hover:scale-110">notifications</span>
          <span class="text-xs font-bold uppercase">Notifs</span>
          <span
            v-if="unreadCount > 0"
            class="absolute top-1.5 right-2 size-4 bg-primary rounded-full text-xs font-semibold text-on-primary flex items-center justify-center"
            >{{ unreadCount > 9 ? '9+' : unreadCount }}</span
          >
        </button>
        <!-- Messages -->
        <button
          class="w-full relative flex-1 flex items-center justify-start gap-2 p-3 bg-on-surface/[0.04] dark:bg-on-surface/5 hover:bg-on-surface/5 dark:hover:bg-on-surface/10 rounded-2xl text-on-surface-variant hover:text-on-surface group border border-on-surface/[0.04] dark:border-on-surface/5"
          @click="openMessaging"
        >
          <span
            class="material-symbols-outlined text-xl group-hover:scale-110"
            style="font-variation-settings: 'FILL' 1"
            >chat</span
          >
          <span class="text-xs font-bold uppercase">Chat</span>
          <span
            v-if="messagingStore.totalUnread > 0"
            class="absolute top-1.5 right-2 min-w-[16px] h-4 bg-primary rounded-full text-xs font-semibold text-on-primary flex items-center justify-center px-0.5"
            >{{ messagingStore.totalUnread > 99 ? '99+' : messagingStore.totalUnread }}</span
          >
        </button>
      </div>

      <!-- User Profile Dropdown -->
      <div class="relative w-full">
        <button
          class="w-full flex items-center gap-3 px-3 py-2 rounded-2xl hover:bg-on-surface/5 dark:hover:bg-on-surface/5 group border border-transparent"
          :class="{
            'bg-on-surface/10 border-on-surface/[0.08] dark:border-on-surface/10 shadow-lg':
              isUserDropdownOpen,
          }"
          @click.stop="toggleUserDropdown"
        >
          <div
            class="size-10 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center text-primary font-semibold text-sm shrink-0 group-hover:border-primary/50 overflow-hidden"
          >
            <img
              v-if="authStore.currentUser?.avatarUrl"
              :src="authStore.currentUser.avatarUrl"
              class="w-full h-full object-cover"
            />
            <span v-else>{{ authStore.currentUser?.name?.charAt(0)?.toUpperCase() || '?' }}</span>
          </div>
          <div class="flex-1 text-left min-w-0">
            <p class="text-sm font-bold text-on-surface leading-tight truncate">
              {{ authStore.currentUser?.name || 'User' }}
            </p>
            <p class="text-xs text-on-surface-variant font-bold uppercase truncate">
              {{ roleLabel }}
            </p>
          </div>
          <span
            class="material-symbols-outlined text-on-surface-variant text-xl"
            :class="{ 'rotate-180 text-on-surface': isUserDropdownOpen }"
            >expand_less</span
          >
        </button>

        <!-- Dropdown Content -->
        <div
          v-if="isUserDropdownOpen"
          v-click-outside="() => (isUserDropdownOpen = false)"
          class="absolute bottom-full left-0 mb-3 w-56 glass-heavy rounded-[1.5rem] shadow-2xl overflow-hidden z-[110]"
        >
          <div
            class="p-4 border-b border-on-surface/[0.04] dark:border-on-surface/5 bg-on-surface/[0.02] dark:bg-on-surface/[0.02]"
          >
            <p class="text-xs font-semibold text-on-surface-variant uppercase mb-1">Signed in as</p>
            <p class="text-sm font-bold text-on-surface truncate">
              {{ authStore.currentUser?.email }}
            </p>
          </div>

          <div class="p-2">
            <button
              class="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-on-surface/5 dark:hover:bg-on-surface/5 text-xs font-bold"
              @click="openSettings"
            >
              <span class="material-symbols-outlined text-lg">person_edit</span>
              Profile Settings
            </button>
            <button
              class="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-on-surface/5 dark:hover:bg-on-surface/5 text-xs font-bold"
              @click="openSettings"
            >
              <span class="material-symbols-outlined text-lg">settings</span>
              Preferences
            </button>
            <div class="h-px bg-on-surface/[0.04] dark:bg-on-surface/5 my-1 mx-2"></div>
            <button
              class="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-on-surface-variant hover:text-error dark:hover:text-error hover:bg-error/10 text-xs font-semibold"
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

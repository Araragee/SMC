<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notification'
import { useMessagingStore } from '../stores/messaging'
import { useModalStore } from '../stores/modal'

const route = useRoute()
const authStore = useAuthStore()
const notifStore = useNotificationStore()
const messagingStore = useMessagingStore()
const modalStore = useModalStore()

const isVisible = ref(true)
let lastScrollY = 0

type NavItem = { path: string; icon: string; label: string }

const navsByRole: Record<string, NavItem[]> = {
  admin: [
    { path: '/admin', icon: 'dashboard', label: 'Dashboard' },
    { path: '/admin/users', icon: 'person', label: 'Users' },
    { path: '/admin/schedule', icon: 'calendar_month', label: 'Schedule' },
  ],
  teacher: [
    { path: '/teacher', icon: 'dashboard', label: 'Dashboard' },
    { path: '/teacher/schedule', icon: 'calendar_month', label: 'Schedule' },
    { path: '/teacher/students', icon: 'group', label: 'Students' },
  ],
  student: [
    { path: '/student', icon: 'dashboard', label: 'Dashboard' },
    { path: '/student/schedule', icon: 'calendar_today', label: 'Schedule' },
    { path: '/student/homework', icon: 'school', label: 'Homework' },
  ],
}

const navItems = computed<NavItem[]>(() => {
  const role = authStore.currentUser?.role || ''
  return navsByRole[role] ?? []
})

const isActive = (path: string) => route.path === path

const handleScroll = function() {
  const currentScrollY = window.scrollY
  if (currentScrollY > lastScrollY && currentScrollY > 100) {
    isVisible.value = false
  } else {
    isVisible.value = true
  }
  lastScrollY = currentScrollY
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<template>
  <div 
    class="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100]"
    :class="isVisible ? 'translate-y-0 opacity-100 scale-100' : 'translate-y-24 opacity-0 scale-90'"
  >
    <nav class="flex items-center gap-1 p-2 bg-surface-container-low/80 backdrop-blur-2xl rounded-full border border-white/10 shadow-2xl shadow-black/40">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="relative p-3 rounded-full group"
        :class="isActive(item.path) ? 'bg-orange-500 scale-110 shadow-lg shadow-orange-500/40' : 'hover:bg-white/5'"
      >
        <span 
          class="material-symbols-outlined"
          :class="isActive(item.path) ? 'text-white' : 'text-on-surface-variant group-hover:text-on-surface'"
          :style="isActive(item.path) ? 'font-variation-settings: \'FILL\' 1' : ''"
        >
          {{ item.icon }}
        </span>
        
        <!-- Subtle Active Indicator Dot -->
        <div 
          v-if="isActive(item.path)"
          class="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 bg-white rounded-full"
        ></div>
      </router-link>

      <div class="w-px h-6 bg-white/10 mx-1"></div>

      <!-- Notifications -->
      <button 
        class="relative p-3 rounded-full hover:bg-white/5 group"
        @click="modalStore.openNotifications()"
      >
        <span class="material-symbols-outlined text-on-surface-variant group-hover:text-on-surface">notifications</span>
        <span 
          v-if="notifStore.unreadCount > 0"
          class="absolute top-2 right-2 w-4 h-4 bg-orange-500 rounded-full border-2 border-surface-container-low text-[8px] font-black text-white flex items-center justify-center"
        >
          {{ notifStore.unreadCount > 9 ? '9+' : notifStore.unreadCount }}
        </span>
      </button>

      <!-- Messaging -->
      <button 
        class="relative p-3 rounded-full hover:bg-white/5 group"
        @click="messagingStore.isOpen = true"
      >
        <span class="material-symbols-outlined text-on-surface-variant group-hover:text-on-surface">chat</span>
        <span 
          v-if="messagingStore.totalUnread > 0"
          class="absolute top-2 right-2 w-4 h-4 bg-orange-500 rounded-full border-2 border-surface-container-low text-[8px] font-black text-white flex items-center justify-center"
        >
          {{ messagingStore.totalUnread > 9 ? '9+' : messagingStore.totalUnread }}
        </span>
      </button>

      <!-- Profile/Logout -->
      <button 
        class="w-10 h-10 rounded-full border border-orange-500/30 overflow-hidden ml-1 hover:border-orange-500/60"
        @click="modalStore.openSettings()"
      >
        <img 
          v-if="authStore.currentUser?.avatarUrl" 
          :src="authStore.currentUser.avatarUrl" 
          class="w-full h-full object-cover" 
        />
        <div v-else class="w-full h-full bg-orange-500/20 flex items-center justify-center text-orange-400 text-xs font-black uppercase">
          {{ authStore.currentUser?.name?.charAt(0) || '?' }}
        </div>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.material-symbols-outlined {
  font-size: 24px;
}
</style>

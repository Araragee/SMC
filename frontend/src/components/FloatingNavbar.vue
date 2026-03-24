<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const authStore = useAuthStore()

type NavItem = { path: string; icon: string; label: string }

const navsByRole: Record<string, NavItem[]> = {
  admin: [
    { path: '/admin', icon: 'dashboard', label: 'Dashboard' },
    { path: '/admin/users', icon: 'group', label: 'Users' },
    { path: '/admin/schedule', icon: 'calendar_month', label: 'Schedule' },
  ],
  teacher: [
    { path: '/teacher', icon: 'dashboard', label: 'Dashboard' },
    { path: '/teacher/schedule', icon: 'calendar_month', label: 'Schedule' },
    { path: '/teacher/students', icon: 'group', label: 'Students' },
    { path: '/teacher/instruments', icon: 'piano', label: 'Instruments' },
    { path: '/teacher/payments', icon: 'payments', label: 'Payments' },
    { path: '/teacher/messages', icon: 'chat', label: 'Messages' },
  ],
  student: [
    { path: '/student', icon: 'dashboard', label: 'Dashboard' },
    { path: '/student/schedule', icon: 'calendar_today', label: 'Schedule' },
    { path: '/student/homework', icon: 'school', label: 'Homework' },
  ],
}

const navItems = computed<NavItem[]>(() => navsByRole[authStore.userRole || ''] ?? [])

const isActive = (path: string) => route.path === path
</script>

<template>
  <header
    class="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] w-max px-5 h-14 bg-surface-container-low/40 backdrop-blur-3xl rounded-full inner-glow-white-10 shadow-2xl flex items-center gap-2 border border-white/5"
  >
    <nav class="flex items-center gap-1">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="flex items-center gap-1.5 px-3.5 py-2 rounded-full text-sm font-medium transition-all"
        :class="
          isActive(item.path)
            ? 'bg-orange-500/20 text-orange-500 font-bold'
            : 'text-zinc-400 hover:text-white hover:bg-white/5'
        "
      >
        <span
          class="material-symbols-outlined text-[18px]"
          :style="isActive(item.path) ? 'font-variation-settings: \'FILL\' 1' : ''"
          >{{ item.icon }}</span
        >
        <span class="hidden sm:inline">{{ item.label }}</span>
      </router-link>
    </nav>

    <div class="h-5 w-px bg-white/10 mx-1"></div>

    <div class="relative flex items-center">
      <span class="material-symbols-outlined absolute left-3 text-zinc-500 text-sm">search</span>
      <input
        type="text"
        placeholder="Quick find..."
        class="bg-white/5 border border-white/10 rounded-full pl-9 pr-4 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-orange-500/50 w-36 placeholder-zinc-500"
      />
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@stores/auth'

const route = useRoute()
const authStore = useAuthStore()

type NavItem = { path: string; icon: string; label: string }

const navsByRole: Record<string, NavItem[]> = {
  admin: [
    { path: '/admin', icon: 'dashboard', label: 'Dashboard' },
    { path: '/admin/users', icon: 'manage_accounts', label: 'Users' },
    { path: '/admin/schedule', icon: 'calendar_month', label: 'Schedule' },
    { path: '/admin/students', icon: 'group', label: 'Students' },
  ],
  teacher: [
    { path: '/teacher', icon: 'dashboard', label: 'Dashboard' },
    { path: '/teacher/schedule', icon: 'calendar_month', label: 'Schedule' },
    { path: '/teacher/students', icon: 'group', label: 'Students' },
    { path: '/teacher/payments', icon: 'payments', label: 'Payments' },
  ],
  student: [
    { path: '/student', icon: 'dashboard', label: 'Dashboard' },
    { path: '/student/schedule', icon: 'calendar_today', label: 'Schedule' },
    { path: '/student/homework', icon: 'school', label: 'Homework' },
    { path: '/student/payments', icon: 'payments', label: 'Payments' },
  ],
}

const navItems = computed<NavItem[]>(() => navsByRole[authStore.userRole || ''] ?? [])

const isActive = (path: string) => route.path === path
</script>

<template>
  <header
    class="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] w-max px-5 h-14 glass-thin rounded-full flex items-center gap-2 transition-colors duration-300"
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
            : 'text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-black/5 dark:hover:bg-white/5'
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

    <div class="h-5 w-px bg-outline-variant dark:bg-outline-variant mx-1"></div>
  </header>
</template>

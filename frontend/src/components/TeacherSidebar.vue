<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const logout = () => {
  authStore.logout()
  router.push('/')
}
</script>

<template>
  <aside class="w-64 flex flex-col pt-8 pb-8 px-0 border-r border-black/[0.04] dark:border-white/5 glass-thin shrink-0 sticky top-0 h-screen text-on-surface dark:text-on-surface">
    <div class="px-8 mb-12 flex items-center gap-3">
      <div class="w-10 h-10 rounded-full bg-gradient-to-br from-orange-500 to-orange-700 flex items-center justify-center shadow-lg shadow-orange-900/40">
        <span class="material-symbols-outlined text-white dark:text-white" aria-hidden="true" style="font-variation-settings:'FILL' 1">music_note</span>
      </div>
      <div>
        <h1 class="text-sm font-bold leading-tight">Sernan's Music<br/>Clinic</h1>
        <p class="text-[8px] uppercase tracking-[0.2em] text-on-surface-variant dark:text-on-surface-variant font-bold mt-1">Premium Education</p>
      </div>
    </div>
    
    <nav class="flex-1 space-y-2 px-4">
      <router-link to="/teacher" class="flex items-center gap-3 rounded-full px-5 py-3 transition-colors" active-class="bg-black/[0.04] dark:bg-white/5 text-tertiary shadow-inner" exact-active-class="bg-black/[0.04] dark:bg-white/5 text-tertiary shadow-inner" :class="{ 'text-on-surface-variant dark:text-on-surface-variant hover:bg-black/[0.04] dark:hover:bg-white/5 hover:text-on-surface': $route.path !== '/teacher' }">
        <span class="material-symbols-outlined text-xl" :style="$route.path === '/teacher' ? 'font-variation-settings:\'FILL\' 1' : ''">dashboard</span>
        <span class="text-sm font-bold">Dashboard</span>
      </router-link>
      <router-link to="/teacher/students" class="flex items-center gap-3 hover:bg-black/[0.04] dark:hover:bg-white/5 rounded-full px-5 py-3 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-colors" active-class="bg-black/[0.04] dark:bg-white/5 text-tertiary shadow-inner">
        <span class="material-symbols-outlined text-xl">group</span>
        <span class="text-sm font-medium">Students</span>
      </router-link>
      <router-link to="/teacher/instruments" class="flex items-center gap-3 hover:bg-black/[0.04] dark:hover:bg-white/5 rounded-full px-5 py-3 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-colors" active-class="bg-black/[0.04] dark:bg-white/5 text-tertiary shadow-inner">
        <span class="material-symbols-outlined text-xl">piano</span>
        <span class="text-sm font-medium">Instruments</span>
      </router-link>
      <router-link to="/teacher/payments" class="flex items-center gap-3 hover:bg-black/[0.04] dark:hover:bg-white/5 rounded-full px-5 py-3 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-colors" active-class="bg-black/[0.04] dark:bg-white/5 text-tertiary shadow-inner">
        <span class="material-symbols-outlined text-xl">payments</span>
        <span class="text-sm font-medium">Payments</span>
      </router-link>
      <router-link to="/teacher/messages" class="flex items-center gap-3 hover:bg-black/[0.04] dark:hover:bg-white/5 rounded-full px-5 py-3 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-colors" active-class="bg-black/[0.04] dark:bg-white/5 text-tertiary shadow-inner">
        <span class="material-symbols-outlined text-xl">chat</span>
        <span class="text-sm font-medium">Messages</span>
      </router-link>
    </nav>
    
    <div class="px-6 mt-auto space-y-6">
      <button class="w-full bg-gradient-to-r from-[#ff6b35] to-[#f94d00] text-white dark:text-white rounded-full py-3.5 px-4 font-bold text-sm shadow-[0_4px_24px_rgba(255,107,53,0.4)] flex items-center justify-center gap-2 hover:scale-[1.02] active:scale-95 transition-all">
        <span class="material-symbols-outlined text-[20px]">add</span>
        New Enrollment
      </button>
      <div class="space-y-4 pt-6 border-t border-black/8 dark:border-white/5">
        <router-link to="#" class="flex items-center gap-3 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface text-sm transition-colors">
          <span class="material-symbols-outlined text-xl">help</span>
          Help Center
        </router-link>
        <button class="flex items-center gap-3 text-on-surface-variant dark:text-on-surface-variant hover:text-red-500 dark:hover:text-red-400 text-sm transition-colors w-full text-left" @click="logout">
          <span class="material-symbols-outlined text-xl">logout</span>
          Sign Out
        </button>
      </div>
    </div>
  </aside>
</template>

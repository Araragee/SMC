<template>
  <aside class="fixed left-0 top-0 w-64 flex flex-col p-4 gap-8 bg-surface-container-low/40 backdrop-blur-3xl rounded-3xl m-4 h-[calc(100vh-2rem)] z-50 inner-glow-white-10 shadow-2xl transition-all duration-300">
    <div class="flex items-center gap-3 px-2">
      <div class="w-10 h-10 rounded-2xl bg-gradient-to-br from-orange-500 to-orange-700 flex items-center justify-center shadow-lg shadow-orange-900/40">
        <span class="material-symbols-outlined text-white" style="font-variation-settings: 'FILL' 1;">music_note</span>
      </div>
      <div>
        <h2 class="text-orange-500 font-black tracking-tight leading-none text-lg">Student Portal</h2>
        <p class="text-[10px] text-on-surface-variant uppercase tracking-[0.2em] mt-1 font-bold">Sernan's Music</p>
      </div>
    </div>
    
    <nav class="flex flex-col gap-2">
      <router-link
        to="/student"
        class="group flex items-center gap-3 px-4 py-3 bg-gradient-to-br from-orange-500 to-orange-700 text-white rounded-2xl shadow-lg shadow-orange-900/20 font-plus-jakarta-sans text-sm font-medium tracking-wide cubic-bezier(0.2,0.8,0.2,1) hover:translate-x-1"
        aria-current="page"
      >
        <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">dashboard</span>
        <span>Dashboard</span>
      </router-link>
      <a href="#" class="group flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-white hover:bg-surface-container-highest/50 transition-colors rounded-2xl font-plus-jakarta-sans text-sm font-medium tracking-wide cubic-bezier(0.2,0.8,0.2,1) hover:translate-x-1">
        <span class="material-symbols-outlined">calendar_today</span>
        <span>My Schedule</span>
      </a>
      <a href="#" class="group flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-white hover:bg-surface-container-highest/50 transition-colors rounded-2xl font-plus-jakarta-sans text-sm font-medium tracking-wide cubic-bezier(0.2,0.8,0.2,1) hover:translate-x-1">
        <span class="material-symbols-outlined">school</span>
        <span>Homework</span>
      </a>
    </nav>
    
    <div class="mt-auto space-y-4">
      <button
        class="group flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-red-400 hover:bg-red-500/10 transition-colors rounded-2xl font-plus-jakarta-sans text-sm font-medium tracking-wide cubic-bezier(0.2,0.8,0.2,1) hover:translate-x-1 w-full text-left"
        aria-label="Sign out of your account"
        @click="logout"
      >
        <span class="material-symbols-outlined">logout</span>
        <span>Sign Out</span>
      </button>

      <div class="p-4 bg-surface-container-highest/30 rounded-2xl flex items-center gap-3 border border-white/5">
        <div class="w-10 h-10 rounded-full border-2 border-orange-500/30 bg-surface-container-highest flex items-center justify-center text-white font-bold text-sm shrink-0">
          {{ authStore.currentUser?.name?.charAt(0) || 'S' }}
        </div>
        <div class="overflow-hidden">
          <p class="text-xs font-bold text-on-surface truncate">{{ authStore.currentUser?.name || 'Student' }}</p>
          <p class="text-[10px] text-on-surface-variant truncate">Student</p>
        </div>
      </div>
    </div>
  </aside>
</template>

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

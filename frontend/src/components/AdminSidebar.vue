<template>
  <aside
    class="fixed left-0 top-0 flex flex-col h-full p-4 z-[60] w-64 bg-zinc-900/80 backdrop-blur-2xl rounded-r-[24px] shadow-2xl shadow-orange-900/10 font-['Plus_Jakarta_Sans'] font-medium text-sm"
    role="navigation"
    aria-label="Admin navigation"
  >
    <div class="px-4 mb-10 mt-2">
      <div class="flex items-center gap-3">
        <div
          class="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center text-white shadow-lg shadow-orange-500/30"
          aria-hidden="true"
        >
          <span class="material-symbols-outlined" aria-hidden="true">school</span>
        </div>
        <div>
          <h1 class="text-xl font-bold text-white leading-tight">Sernan's Music</h1>
          <p class="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">Admin Panel</p>
        </div>
      </div>
    </div>

    <nav class="flex-1 space-y-2" aria-label="Main menu">
      <router-link
        to="/admin"
        class="flex items-center gap-3 bg-gradient-to-r from-orange-500/20 to-orange-600/10 text-orange-500 rounded-[24px] px-4 py-3 border-l-4 border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/50"
        aria-current="page"
      >
        <span class="material-symbols-outlined" aria-hidden="true">dashboard</span>
        <span>Dashboard</span>
      </router-link>
      <a
        href="#"
        class="flex items-center gap-3 text-zinc-400 px-4 py-3 hover:translate-x-1 hover:bg-zinc-800/50 rounded-[24px] transition-all focus:outline-none focus:ring-2 focus:ring-zinc-500/50"
        aria-label="Manage users"
      >
        <span class="material-symbols-outlined" aria-hidden="true">group</span>
        <span>Users</span>
      </a>
      <a
        href="#"
        class="flex items-center gap-3 text-zinc-400 px-4 py-3 hover:translate-x-1 hover:bg-zinc-800/50 rounded-[24px] transition-all focus:outline-none focus:ring-2 focus:ring-zinc-500/50"
        aria-label="View global schedule"
      >
        <span class="material-symbols-outlined" aria-hidden="true">calendar_month</span>
        <span>Global Schedule</span>
      </a>
    </nav>

    <div class="mt-auto pt-6 border-t border-white/5 space-y-2">
      <button
        @click="logout"
        class="flex items-center gap-3 text-zinc-400 px-4 py-3 hover:translate-x-1 hover:bg-red-500/10 hover:text-red-400 rounded-[24px] transition-all w-full text-left focus:outline-none focus:ring-2 focus:ring-red-500/30"
        aria-label="Sign out of your account"
      >
        <span class="material-symbols-outlined" aria-hidden="true">logout</span>
        <span>Sign Out</span>
      </button>
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

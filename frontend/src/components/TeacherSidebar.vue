<template>
  <aside class="fixed left-0 top-0 flex flex-col h-full p-4 z-40 w-64 bg-zinc-900/80 backdrop-blur-2xl rounded-r-[24px] shadow-2xl shadow-orange-900/10 font-['Plus_Jakarta_Sans'] font-medium text-sm">
    <div class="px-4 mb-10 mt-2">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-2xl bg-primary flex items-center justify-center text-white shadow-[0_0_20px_rgba(255,69,0,0.4)]">
          <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">music_note</span>
        </div>
        <div>
          <h1 class="text-xl font-bold text-white leading-tight tracking-tight">Teacher Hub</h1>
          <p class="text-[10px] uppercase tracking-widest text-zinc-400 font-bold">Faculty</p>
        </div>
      </div>
    </div>
    <nav class="flex-1 space-y-2">
      <router-link to="/teacher" class="flex items-center gap-3 bg-gradient-to-r from-orange-500/20 to-orange-600/10 text-orange-500 rounded-[24px] px-4 py-3 border-l-4 border-orange-500">
        <span class="material-symbols-outlined">dashboard</span>
        <span>Dashboard</span>
      </router-link>
      <a href="#" class="flex items-center gap-3 text-zinc-400 px-4 py-3 hover:translate-x-1 hover:bg-zinc-800/50 rounded-[24px] transition-all">
        <span class="material-symbols-outlined">group</span>
        <span>My Roster</span>
      </a>
    </nav>
    <div class="mt-auto space-y-4">
      <button class="w-full py-3.5 px-4 bg-primary text-white rounded-[24px] font-bold shadow-[0_8px_20px_rgba(255,69,0,0.3)] hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-2">
        <span class="material-symbols-outlined">add</span>
        <span>New Schedule</span>
      </button>
      <div class="pt-4 border-t border-white/5 space-y-1">
        <button @click="logout" class="flex items-center gap-3 text-zinc-400 px-4 py-2 hover:bg-red-500/10 hover:text-red-400 rounded-[24px] transition-all w-full text-left">
          <span class="material-symbols-outlined text-lg">logout</span>
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const logout = () => {
    router.push('/')
}
</script>

<template>
  <aside class="fixed left-0 top-0 flex flex-col h-full p-4 z-40 w-64 bg-zinc-900/60 backdrop-blur-2xl rounded-r-3xl border-r border-white/5 font-['Plus_Jakarta_Sans'] font-medium text-sm">
    <div class="px-4 mb-10 mt-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-primary flex items-center justify-center text-white shadow-lg shadow-primary/20">
          <span class="material-symbols-outlined">piano</span>
        </div>
        <div>
          <h1 class="text-lg font-black text-white tracking-tighter leading-none">Student Portal</h1>
          <p class="text-[10px] uppercase tracking-widest text-zinc-500 mt-1">Sernan's Music</p>
        </div>
      </div>
    </div>
    <nav class="flex-1 space-y-2">
      <router-link to="/student" class="flex items-center gap-3 bg-gradient-to-r from-primary/20 to-primary/5 text-primary rounded-3xl px-4 py-3 border-l-4 border-primary transition-all duration-300">
        <span class="material-symbols-outlined">dashboard</span>
        <span>Dashboard</span>
      </router-link>
      <a href="#" class="flex items-center gap-3 text-zinc-400 px-4 py-3 hover:bg-white/5 hover:translate-x-1 rounded-3xl transition-all duration-300">
        <span class="material-symbols-outlined">calendar_today</span>
        <span>My Schedule</span>
      </a>
      <a href="#" class="flex items-center gap-3 text-zinc-400 px-4 py-3 hover:bg-white/5 hover:translate-x-1 rounded-3xl transition-all duration-300">
        <span class="material-symbols-outlined">school</span>
        <span>Homework</span>
      </a>
    </nav>
    <div class="px-2 mt-auto">
      <button class="w-full py-3 px-4 bg-gradient-to-br from-[#FF4500] to-[#FF6A00] text-white rounded-3xl font-bold shadow-lg shadow-primary/20 flex items-center justify-center gap-2 active:scale-95 transition-all hover:-translate-y-0.5">
        <span class="material-symbols-outlined text-sm">add</span>
        <span>Request Session</span>
      </button>
    </div>
    <div class="pt-6 border-t border-white/5 mt-6 mb-2">
      <button @click="logout" class="flex items-center gap-3 text-zinc-400 px-4 py-3 hover:bg-white/5 rounded-3xl transition-all duration-300 w-full text-left">
        <span class="material-symbols-outlined">logout</span>
        <span>Sign Out</span>
      </button>
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

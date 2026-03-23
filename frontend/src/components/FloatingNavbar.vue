<template>
  <header class="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] mx-auto w-max px-6 h-16 bg-surface-container-low/40 backdrop-blur-3xl rounded-full inner-glow-white-10 shadow-2xl flex items-center gap-8 border border-white/5">
    <div class="flex items-center gap-2">
      <h1 class="text-lg font-black bg-gradient-to-br from-orange-400 to-orange-600 bg-clip-text text-transparent">Sernan's Music Clinic</h1>
    </div>
    
    <nav class="flex items-center gap-6">
      <router-link to="/" class="text-sm font-bold text-orange-500 pb-1 border-b-2 border-orange-500">Dashboard</router-link>
      <a href="#" class="text-sm font-medium text-zinc-400 hover:text-white transition-colors pb-1 border-b-2 border-transparent hover:border-white/20">Schedules</a>
      <a href="#" class="text-sm font-medium text-zinc-400 hover:text-white transition-colors pb-1 border-b-2 border-transparent hover:border-white/20">Curriculum</a>
      <a href="#" class="text-sm font-medium text-zinc-400 hover:text-white transition-colors pb-1 border-b-2 border-transparent hover:border-white/20">Recitals</a>
    </nav>
    
    <div class="relative flex items-center ml-4">
      <span class="material-symbols-outlined absolute left-3 text-zinc-500 text-sm">search</span>
      <input type="text" placeholder="Quick find..." class="bg-white/5 border border-white/10 rounded-full pl-9 pr-4 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-orange-500/50 w-48 placeholder-zinc-500" />
    </div>
  </header>
</template>

<script setup lang="ts">
// Common floating navbar component
</script>

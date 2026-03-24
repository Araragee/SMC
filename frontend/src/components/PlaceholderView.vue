<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => {
  const parts = route.path.split('/')
  return parts[parts.length - 1] || 'Module'
})
const role = computed(() => {
  const parts = route.path.split('/')
  return parts[1] || 'student'
})
</script>

<template>
  <div class="flex h-screen items-center justify-center text-center p-8">
    <div class="max-w-md w-full">
      <div class="w-16 h-16 rounded-full bg-surface-container-low border border-black/[0.04] dark:border-white/5 flex items-center justify-center mx-auto mb-4">
        <span class="material-symbols-outlined text-orange-500 text-3xl" style="font-variation-settings:'FILL' 1">construction</span>
      </div>
      <h2 class="text-3xl font-black text-zinc-900 dark:text-white capitalize mb-4 tracking-tight">{{ title }}</h2>
      <p class="text-zinc-600 dark:text-zinc-500 text-base leading-relaxed mb-8">
        This module is part of the Sernan's Music Cosmic Liquid expansion and is currently under construction.
      </p>
      
      <div class="flex items-center justify-center">
        <router-link :to="`/${role}`" class="inline-flex items-center gap-2 px-8 py-3 rounded-full bg-gradient-to-r from-[#ff6b35] to-[#f94d00] text-zinc-900 dark:text-white font-bold text-sm shadow-[0_4px_24px_rgba(255,107,53,0.4)] hover:scale-[1.02] active:scale-95 transition-all">
          <span class="material-symbols-outlined text-sm">arrow_back</span>
          Return to Dashboard
        </router-link>
      </div>
    </div>
  </div>
</template>

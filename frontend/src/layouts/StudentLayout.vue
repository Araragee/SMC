<script setup lang="ts">
import SidebarNav from '../components/SidebarNav.vue'
</script>

<template>
  <div class="cosmic-void antialiased min-h-screen selection:bg-primary/30 bg-zinc-50 dark:bg-[#0e0e0e] font-sans text-zinc-900 dark:text-white transition-colors duration-300">
    <div class="fixed top-1/4 -left-20 w-96 h-96 bg-primary/10 blur-[128px] rounded-full -z-10 pointer-events-none" />
    <div class="fixed bottom-1/4 -right-20 w-96 h-96 bg-tertiary/10 blur-[128px] rounded-full -z-10 pointer-events-none" />

    <div class="flex min-h-screen">
      <SidebarNav />
      <main class="flex-1 lg:ml-64 p-6 min-h-screen">
        <RouterView />
      </main>
    </div>
  </div>
</template>

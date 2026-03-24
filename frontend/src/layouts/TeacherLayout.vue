<script setup lang="ts">
import SidebarNav from '../components/SidebarNav.vue'
</script>

<template>
  <div
    class="cosmic-void antialiased min-h-screen selection:bg-primary/30 bg-zinc-50 dark:bg-[#0e0e0e] font-sans text-zinc-900 dark:text-white transition-colors duration-300"
  >
    <div
      class="fixed top-1/4 -left-20 w-96 h-96 bg-primary/10 blur-[128px] rounded-full -z-10 pointer-events-none"
    />
    <div
      class="fixed bottom-1/4 -right-20 w-96 h-96 bg-tertiary/10 blur-[128px] rounded-full -z-10 pointer-events-none"
    />

    <div class="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-6 gap-6 min-h-screen p-6">
      <div class="hidden lg:block lg:col-span-1">
        <SidebarNav />
      </div>
      <div class="lg:hidden">
        <SidebarNav />
      </div>
      <main class="lg:col-span-5 min-h-screen w-full">
        <RouterView />
      </main>
    </div>
  </div>
</template>

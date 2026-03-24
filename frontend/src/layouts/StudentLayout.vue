<script setup lang="ts">
import FloatingNavbar from '../components/FloatingNavbar.vue'
import TopNavbar from '../components/TopNavbar.vue'
</script>

<template>
  <div class="cosmic-void antialiased min-h-screen selection:bg-primary/30 bg-[#0e0e0e] font-sans text-white">
    <div class="fixed top-1/4 -left-20 w-96 h-96 bg-primary/10 blur-[128px] rounded-full -z-10 pointer-events-none" />
    <div class="fixed bottom-1/4 -right-20 w-96 h-96 bg-tertiary/10 blur-[128px] rounded-full -z-10 pointer-events-none" />

    <TopNavbar />
    <FloatingNavbar />

    <div class="p-6 pt-20 pb-28 min-h-screen">
      <RouterView />
    </div>
  </div>
</template>

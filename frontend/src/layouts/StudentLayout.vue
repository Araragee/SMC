<script setup lang="ts">
import SidebarNav from '../components/SidebarNav.vue'
import BlobBackground from '../components/BlobBackground.vue'
</script>

<template>
  <BlobBackground>
    <div class="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-6 gap-6 min-h-screen p-6 antialiased font-sans text-on-surface selection:bg-primary/30">
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
  </BlobBackground>
</template>

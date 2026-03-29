<script setup lang="ts">
import SidebarNav from '../components/SidebarNav.vue'
import MobileDock from '../components/MobileDock.vue'
import BlobBackground from '../components/BlobBackground.vue'
</script>

<template>
  <BlobBackground>
    <div class="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-6 gap-6 min-h-screen p-6 antialiased font-sans text-on-surface selection:bg-primary/30">
      <!-- Sidebar for Desktop -->
      <div class="hidden lg:block lg:col-span-1">
        <SidebarNav />
      </div>

      <!-- Main Content -->
      <main class="lg:col-span-5 min-h-screen w-full pb-28 lg:pb-0">
        <RouterView />
      </main>

      <!-- Floating Dock for Mobile -->
      <div class="lg:hidden">
        <MobileDock />
      </div>
    </div>
  </BlobBackground>
</template>

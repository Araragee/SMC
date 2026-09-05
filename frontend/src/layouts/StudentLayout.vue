<script setup lang="ts">
import SidebarNav from '@components/SidebarNav.vue'
import BlobBackground from '@components/BlobBackground.vue'
</script>

<template>
  <BlobBackground>
    <div
      class="max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-6 gap-6 min-h-screen px-4 py-6 lg:p-6 antialiased font-sans text-on-surface selection:bg-primary/30"
    >
      <!-- Sidebar: drawer below lg, static column from lg up -->
      <div class="lg:col-span-1">
        <SidebarNav />
      </div>

      <!-- Main Content -->
      <main class="lg:col-span-5 min-h-screen w-full pt-16 lg:pt-0">
        <RouterView />
      </main>
    </div>
  </BlobBackground>
</template>

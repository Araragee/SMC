<script setup lang="ts">
import BlobBackground from '../components/BlobBackground.vue'
</script>

<template>
  <BlobBackground>
    <div class="min-h-screen flex items-center justify-center antialiased font-sans text-on-surface selection:bg-primary/30">
      <RouterView />
    </div>
  </BlobBackground>
</template>

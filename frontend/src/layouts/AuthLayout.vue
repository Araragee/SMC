<template>
  <div class="cosmic-void text-on-surface antialiased min-h-screen selection:bg-primary/30 flex items-center justify-center">
    <!-- Background Decorative Elements -->
    <div class="fixed top-1/4 -left-20 w-96 h-96 bg-primary/10 blur-[128px] rounded-full -z-10 pointer-events-none"></div>
    <div class="fixed bottom-1/4 -right-20 w-96 h-96 bg-tertiary/10 blur-[128px] rounded-full -z-10 pointer-events-none"></div>
    <RouterView />
  </div>
</template>

<script setup lang="ts">
</script>

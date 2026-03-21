<template>
  <div class="bg-surface text-white selection:bg-primary/30 antialiased min-h-screen admin-layout-bg">
    <slot />
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.admin-layout-bg {
  background: radial-gradient(circle at top left, #2a1100, #09090b);
}
</style>

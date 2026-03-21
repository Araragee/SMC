<template>
  <div class="text-on-surface min-h-screen antialiased student-layout-bg">
    <slot />
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.student-layout-bg {
  background: radial-gradient(circle at 0% 0%, #18181b 0%, #09090b 100%);
  background-attachment: fixed;
}
</style>

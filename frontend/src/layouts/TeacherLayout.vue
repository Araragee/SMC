<template>
  <div class="text-on-surface min-h-screen teacher-layout-bg">
    <slot />
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.teacher-layout-bg {
  background: radial-gradient(circle at top left, #1a1a1a 0%, #09090b 100%);
}
</style>

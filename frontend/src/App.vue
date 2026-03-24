<script setup lang="ts">
import ToastContainer from './components/ToastContainer.vue'
</script>

<template>
  <div class="selection:bg-primary/30 antialiased font-sans min-h-screen text-zinc-900 bg-zinc-50 dark:text-white dark:bg-[#0e0e0e] transition-colors duration-300">
    <RouterView v-slot="{ Component, route: currentRoute }">
      <Transition :name="currentRoute.meta.transition as string || 'fade'" mode="out-in">
        <component :is="Component" :key="currentRoute.fullPath" />
      </Transition>
    </RouterView>
    <ToastContainer />
  </div>
</template>

<style>
/* Global styles and transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>

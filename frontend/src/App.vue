<script setup lang="ts">
import ToastContainer from './components/ToastContainer.vue'
</script>

<template>
  <div class="antialiased font-sans selection:bg-primary/30">
    <RouterView v-slot="{ Component, route: currentRoute }">
      <Transition :name="currentRoute.meta.transition as string || 'fade'" mode="out-in">
        <component :is="Component" :key="currentRoute.fullPath" />
      </Transition>
    </RouterView>
    <ToastContainer />
  </div>
</template>

<style>
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

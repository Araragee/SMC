<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AuthLayout from './layouts/AuthLayout.vue'
import ToastContainer from './components/ToastContainer.vue'

const route = useRoute()
const layout = computed(() => route.meta.layout || AuthLayout)
</script>

<template>
  <component :is="layout">
    <RouterView v-slot="{ Component, route: currentRoute }">
      <Transition :name="currentRoute.meta.transition as string || 'fade'" mode="out-in">
        <component :is="Component" :key="currentRoute.fullPath" />
      </Transition>
    </RouterView>
  </component>
  <ToastContainer />
</template>

<style>
/* Route fade transition */
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

/* Slide-up transition (for dashboards) */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: opacity 0.25s ease, transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.slide-up-enter-from {
  opacity: 0;
  transform: translateY(16px);
}
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>

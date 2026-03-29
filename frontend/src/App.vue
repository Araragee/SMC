<script setup lang="ts">
import { onMounted, watch } from 'vue'
import ToastContainer from './components/ToastContainer.vue'
import MessagingPanel from './components/messaging/MessagingPanel.vue'
import { useAuthStore } from './stores/auth'
import { useMessagingStore } from './stores/messaging'

const auth      = useAuthStore()
const messaging = useMessagingStore()

onMounted(() => {
  if (auth.isAuthenticated) messaging.connectWS()
})

watch(() => auth.isAuthenticated, (v) => {
  if (v) messaging.connectWS()
  else   messaging.disconnectWS()
})
</script>

<template>
  <div class="antialiased font-sans selection:bg-primary/30">
    <RouterView v-slot="{ Component, route: currentRoute }">
      <Transition :name="currentRoute.meta.transition as string || 'fade'" mode="out-in">
        <component :is="Component" :key="currentRoute.fullPath" />
      </Transition>
    </RouterView>
    <ToastContainer />
    <MessagingPanel />
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

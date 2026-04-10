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
    <RouterView />
    <ToastContainer />
    <MessagingPanel />
  </div>
</template>

<style>
/* Global resets or simple styles only */
</style>

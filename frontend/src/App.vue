<script setup lang="ts">
import { onMounted, watch } from 'vue'
import ToastContainer from '@components/ToastContainer.vue'
import MessagingPanel from '@components/messaging/MessagingPanel.vue'
import AppDialogHost from '@components/AppDialogHost.vue'
import { useAuthStore } from '@stores/auth'
import { useMessagingStore } from '@stores/messaging'
import { useMaintenanceStore } from '@stores/maintenance'

const auth      = useAuthStore()
const messaging = useMessagingStore()
const maintenance = useMaintenanceStore()

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
    <div v-if="maintenance.isMaintenance" class="fixed inset-0 bg-black/75 backdrop-blur-md flex items-center justify-center z-[9999] p-4">
      <div class="glass-heavy glass-specular max-w-md w-full p-8 rounded-3xl shadow-2xl text-center space-y-6">
        <div class="inline-flex p-4 bg-primary/10 rounded-full text-primary">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-12">
            <path stroke-linecap="round" stroke-linejoin="round" d="M11.42 15.17L17.25 21A2.653 2.653 0 1113.5 17.25l-5.83-5.83m.002 0a3.9 3.9 0 01-5.17-5.17m5.17 5.17l-1.02-1.02m0 0L7.1 5.6m-1.6 1.6L4 5.6" />
          </svg>
        </div>
        <div class="space-y-2">
          <h2 class="text-2xl font-bold tracking-tight text-glow">Maintenance Mode</h2>
          <p class="text-on-surface-variant text-sm leading-relaxed">
            The portal is currently undergoing scheduled updates. Please try again shortly.
          </p>
        </div>
        <div class="pt-4 border-t border-outline-variant/30">
          <button @click="maintenance.clearMaintenance()" class="px-6 py-2 bg-primary hover:bg-primary-dim text-on-primary rounded-xl font-semibold shadow-lg shadow-primary/20 transition duration-200 text-sm">
            Retry Connection
          </button>
        </div>
      </div>
    </div>
    <RouterView />
    <ToastContainer />
    <MessagingPanel />
    <AppDialogHost />
  </div>
</template>

<style>
/* Global resets or simple styles only */
</style>

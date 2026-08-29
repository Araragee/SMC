<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@stores/auth'

const router = useRouter()
const auth = useAuthStore()

const homeRoute = computed(() => `/${auth.userRole ?? 'login'}`)

function goHome() {
  router.push(homeRoute.value)
}
</script>

<template>
  <div class="flex h-screen items-center justify-center text-center p-8">
    <div class="max-w-md w-full">
      <div class="size-16 rounded-full bg-surface-container-low border border-on-surface/[0.04] dark:border-on-surface/5 flex items-center justify-center mx-auto mb-4">
        <span class="material-symbols-outlined text-rose-500 text-3xl" style="font-variation-settings:'FILL' 1">search_off</span>
      </div>
      <h1 class="text-2xl font-bold text-on-surface mb-2">Page Not Found</h1>
      <p class="text-sm text-on-surface-variant mb-6">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <button
        @click="goHome"
        class="inline-flex items-center gap-2 px-4 py-2 rounded-2xl bg-primary text-on-primary text-sm font-semibold hover:opacity-90 transition-opacity"
      >
        <span class="material-symbols-outlined text-base">home</span>
        Go to Dashboard
      </button>
    </div>
  </div>
</template>

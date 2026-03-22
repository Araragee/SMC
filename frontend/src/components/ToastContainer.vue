<template>
  <Teleport to="body">
    <div
      class="fixed top-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none"
      role="region"
      aria-label="Notifications"
      aria-live="polite"
      aria-atomic="false"
    >
      <TransitionGroup name="toast">
        <div
          v-for="toast in toastStore.toasts"
          :key="toast.id"
          class="pointer-events-auto flex items-start gap-3 min-w-[300px] max-w-[400px] px-4 py-3 rounded-xl border backdrop-blur-xl shadow-xl"
          :class="toastClasses(toast.type)"
          role="alert"
          :aria-label="`${toast.type}: ${toast.title}`"
        >
          <span class="material-symbols-outlined text-lg mt-0.5 shrink-0" :class="iconClasses(toast.type)" aria-hidden="true">
            {{ toastIcon(toast.type) }}
          </span>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-white leading-tight">{{ toast.title }}</p>
            <p v-if="toast.message" class="text-xs text-white/70 mt-0.5 leading-snug">{{ toast.message }}</p>
          </div>
          <button
            @click="toastStore.remove(toast.id)"
            class="text-white/40 hover:text-white/80 transition-colors shrink-0 ml-1 focus:outline-none focus:ring-2 focus:ring-white/30 rounded"
            :aria-label="`Dismiss notification: ${toast.title}`"
          >
            <span class="material-symbols-outlined text-sm" aria-hidden="true">close</span>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useToastStore } from '../stores/toast'

const toastStore = useToastStore()

type ToastType = 'success' | 'error' | 'warning' | 'info'

const toastClasses = (type: ToastType) => ({
  'bg-emerald-900/80 border-emerald-500/30': type === 'success',
  'bg-red-900/80 border-red-500/30': type === 'error',
  'bg-amber-900/80 border-amber-500/30': type === 'warning',
  'bg-indigo-900/80 border-indigo-500/30': type === 'info',
})

const iconClasses = (type: ToastType) => ({
  'text-emerald-400': type === 'success',
  'text-red-400': type === 'error',
  'text-amber-400': type === 'warning',
  'text-indigo-400': type === 'info',
})

const toastIcon = (type: ToastType) => ({
  success: 'check_circle',
  error: 'error',
  warning: 'warning',
  info: 'info',
}[type])
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(60px) scale(0.9);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(60px) scale(0.9);
}
.toast-move {
  transition: transform 0.3s ease;
}
</style>

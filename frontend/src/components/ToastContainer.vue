<script setup lang="ts">
import { useToastStore } from '@stores/toast'

const toastStore = useToastStore()

type ToastType = 'success' | 'error' | 'warning' | 'info'

const toastClasses = (type: ToastType) => ({
  'bg-success/20 dark:bg-success-container/40 border border-success/50 dark:border-success/30':
    type === 'success',
  'bg-error/20 dark:bg-error-container/40 border border-error/50 dark:border-error/30':
    type === 'error',
  'bg-warning/20 dark:bg-warning-container/40 border border-warning/50 dark:border-warning/30':
    type === 'warning',
  'bg-tertiary/20 dark:bg-tertiary-container/40 border border-tertiary/50 dark:border-tertiary/30':
    type === 'info',
})

const textClasses = (type: ToastType) => ({
  'text-on-success-container': type === 'success',
  'text-on-error-container': type === 'error',
  'text-on-warning-container': type === 'warning',
  'text-on-tertiary-container': type === 'info',
})

const iconClasses = (type: ToastType) => ({
  'text-success': type === 'success',
  'text-error': type === 'error',
  'text-warning': type === 'warning',
  'text-tertiary': type === 'info',
})

const toastIcon = (type: ToastType) =>
  ({
    success: 'check_circle',
    error: 'error',
    warning: 'warning',
    info: 'info',
  })[type]
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed top-4 inset-x-4 z-[9999] flex flex-col items-center gap-3 pointer-events-none lg:top-6 lg:right-6 lg:left-auto lg:inset-x-auto lg:items-end"
      role="region"
      aria-label="Notifications"
      aria-live="polite"
      aria-atomic="false"
    >
      <TransitionGroup
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="opacity-0 -translate-y-4 scale-90 lg:translate-y-0 lg:translate-x-[60px]"
        enter-to-class="opacity-100 translate-y-0 translate-x-0 scale-100"
        leave-active-class="transition-all duration-300 ease-in"
        leave-from-class="opacity-100 translate-y-0 translate-x-0 scale-100"
        leave-to-class="opacity-0 -translate-y-4 scale-90 lg:translate-y-0 lg:translate-x-[60px]"
        move-class="transition-transform duration-300 ease-in-out"
      >
        <div
          v-for="toast in toastStore.toasts"
          :key="toast.id"
          class="pointer-events-auto flex items-start gap-3 w-full max-w-[400px] lg:min-w-[300px] px-4 py-3 rounded-xl shadow-xl transition-colors duration-300"
          :class="[toastClasses(toast.type), textClasses(toast.type)]"
          role="alert"
          :aria-label="`${toast.type}: ${toast.title}`"
        >
          <span
            class="material-symbols-outlined text-lg mt-0.5 shrink-0"
            :class="iconClasses(toast.type)"
            aria-hidden="true"
          >
            {{ toastIcon(toast.type) }}
          </span>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold leading-tight">{{ toast.title }}</p>
            <p v-if="toast.message" class="text-xs opacity-80 mt-0.5 leading-snug">
              {{ toast.message }}
            </p>
          </div>
          <button
            class="opacity-60 hover:opacity-100 transition-opacity shrink-0 ml-1 focus:outline-none focus:ring-2 focus:ring-on-surface/20 dark:focus:ring-on-surface/30 rounded"
            :aria-label="`Dismiss notification: ${toast.title}`"
            @click="toastStore.remove(toast.id)"
          >
            <span class="material-symbols-outlined text-sm" aria-hidden="true">close</span>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

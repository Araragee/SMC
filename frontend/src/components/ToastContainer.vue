<script setup lang="ts">
import { useToastStore } from '@stores/toast'

const toastStore = useToastStore()

type ToastType = 'success' | 'error' | 'warning' | 'info'

const toastClasses = (type: ToastType) => ({
  'bg-emerald-500/20 dark:bg-emerald-900/40 border border-emerald-500/50 dark:border-emerald-500/30': type === 'success',
  'bg-red-500/20 dark:bg-red-900/40 border border-red-500/50 dark:border-red-500/30': type === 'error',
  'bg-amber-500/20 dark:bg-amber-900/40 border border-amber-500/50 dark:border-amber-500/30': type === 'warning',
  'bg-blue-500/20 dark:bg-blue-900/40 border border-blue-500/50 dark:border-blue-500/30': type === 'info',
})

const textClasses = (type: ToastType) => ({
  'text-emerald-900 dark:text-emerald-100': type === 'success',
  'text-red-900 dark:text-red-100': type === 'error',
  'text-amber-900 dark:text-amber-100': type === 'warning',
  'text-blue-900 dark:text-blue-100': type === 'info',
})

const iconClasses = (type: ToastType) => ({
  'text-emerald-600 dark:text-emerald-400': type === 'success',
  'text-red-600 dark:text-red-400': type === 'error',
  'text-amber-600 dark:text-amber-400': type === 'warning',
  'text-blue-600 dark:text-blue-400': type === 'info',
})

const toastIcon = (type: ToastType) => ({
  success: 'check_circle',
  error: 'error',
  warning: 'warning',
  info: 'info',
}[type])
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed top-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none"
      role="region"
      aria-label="Notifications"
      aria-live="polite"
      aria-atomic="false"
    >
      <TransitionGroup enter-active-class="transition-all duration-300 ease-out" enter-from-class="opacity-0 translate-x-[60px] scale-90" enter-to-class="opacity-100 translate-x-0 scale-100" leave-active-class="transition-all duration-300 ease-in" leave-from-class="opacity-100 translate-x-0 scale-100" leave-to-class="opacity-0 translate-x-[60px] scale-90" move-class="transition-transform duration-300 ease-in-out">
        <div
          v-for="toast in toastStore.toasts"
          :key="toast.id"
          class="pointer-events-auto flex items-start gap-3 min-w-[300px] max-w-[400px] px-4 py-3 rounded-xl shadow-xl transition-colors duration-300"
          :class="[toastClasses(toast.type), textClasses(toast.type)]"
          role="alert"
          :aria-label="`${toast.type}: ${toast.title}`"
        >
          <span class="material-symbols-outlined text-lg mt-0.5 shrink-0" :class="iconClasses(toast.type)" aria-hidden="true">
            {{ toastIcon(toast.type) }}
          </span>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold leading-tight">{{ toast.title }}</p>
            <p v-if="toast.message" class="text-xs opacity-80 mt-0.5 leading-snug">{{ toast.message }}</p>
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

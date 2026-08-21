<script setup lang="ts">
import type { Notification } from '@types'

defineProps<{
  notification: Notification | null
}>()

defineEmits<{
  close: []
}>()

const typeClasses = function (type: string) {
  const map: Record<string, string> = {
    info: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
    success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
    warning: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
    error: 'bg-red-500/10 border-red-500/20 text-red-400',
  }
  return map[type] || map.info
}



const typeIcon = function (type: string) {
  const map: Record<string, string> = {
    info: 'info',
    success: 'check_circle',
    warning: 'warning',
    error: 'error',
  }
  return map[type] || 'notifications'
}

const typeLabel = function (type: string) {
  const map: Record<string, string> = {
    info: 'Information',
    success: 'Success',
    warning: 'Attention Needed',
    error: 'Alert',
  }
  return map[type] || 'Notification'
}

const formatFullDate = function (iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

const formatTime = function (iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  })
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 scale-95 translate-y-4 blur-[4px]"
      enter-to-class="opacity-100 scale-100 translate-y-0 blur-0"
      leave-active-class="transition-all duration-300 ease-in"
      leave-from-class="opacity-100 scale-100 translate-y-0 blur-0"
      leave-to-class="opacity-0 scale-95 translate-y-4 blur-[4px]"
    >
      <div
        v-if="notification"
        class="fixed inset-0 z-[210] flex items-center justify-center p-4"
        @click.self="$emit('close')"
      >
        <!-- Backdrop (slightly darker to focus on the detail) -->
        <div
          class="absolute inset-0 bg-on-surface/30 dark:bg-on-surface/50"
          @click="$emit('close')"
        />

        <!-- Modal -->
        <div
          class="relative w-full max-w-lg glass-heavy rounded-3xl shadow-2xl overflow-hidden flex flex-col"
        >
          <!-- Header Section -->
          <div class="p-8 pb-4">
            <div class="flex items-start justify-between gap-6 mb-6">
              <div class="flex items-center gap-3">
                <div
                  class="size-12 rounded-2xl flex items-center justify-center border shadow-inner"
                  :class="typeClasses(notification.type)"
                >
                  <span class="material-symbols-outlined text-2xl">{{
                    typeIcon(notification.type)
                  }}</span>
                </div>
                <div>
                  <span
                    class="text-xs font-semibold uppercase text-on-surface-variant dark:text-on-surface-variant mb-1 block"
                  >
                    {{ typeLabel(notification.type) }}
                  </span>
                  <div class="flex items-center gap-2">
                    <span
                      class="text-xs font-medium text-on-surface-variant dark:text-on-surface-variant"
                      >{{ formatFullDate(notification.createdAt) }}</span
                    >
                    <span class="size-1 rounded-full bg-outline-variant"></span>
                    <span
                      class="text-xs font-medium text-on-surface-variant dark:text-on-surface-variant"
                      >{{ formatTime(notification.createdAt) }}</span
                    >
                  </div>
                </div>
              </div>
              <button
                class="icon-btn"
                @click="$emit('close')"
              >
                <span
                  class="material-symbols-outlined text-lg group-hover:rotate-90 transition-transform duration-300"
                  >close</span
                >
              </button>
            </div>

            <h2
              class="text-2xl font-semibold text-on-surface dark:text-on-surface leading-tight tracking-tight"
            >
              {{ notification.title || 'Notification Update' }}
            </h2>
          </div>

          <!-- Content Section -->
          <div class="px-8 py-6">
            <div
              class="h-px bg-outline-variant mb-8"
            ></div>

            <div class="prose max-w-none">
              <p
                class="text-lg text-on-surface-variant dark:text-on-surface-variant leading-[1.8] font-medium selection:bg-primary/30"
              >
                {{ notification.message }}
              </p>
            </div>

            <div
              class="h-px bg-outline-variant mt-8"
            ></div>
          </div>

          <!-- Footer/Actions -->
          <div class="p-8 pt-4 flex items-center justify-between gap-4">
            <div class="flex flex-col gap-2">
              <div
                v-if="!notification.isRead"
                class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 w-max"
              >
                <span class="size-1.5 rounded-full bg-primary animate-pulse"></span>
                <span class="text-xs font-semibold text-primary uppercase"
                  >New</span
                >
              </div>
              <div
                v-else
                class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-outline-variant/20 border border-outline-variant/40 w-max"
              >
                <span
                  class="material-symbols-outlined text-[12px] text-on-surface-variant dark:text-on-surface-variant"
                  >done_all</span
                >
                <span
                  class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase"
                  >Read</span
                >
              </div>
            </div>

            <div class="flex gap-3">
              <router-link
                v-if="notification.link"
                :to="notification.link"
                class="px-6 py-3 bg-primary text-on-primary font-bold rounded-2xl shadow-lg transition-all hover:scale-[1.02] active:scale-95 text-sm flex items-center gap-2"
                @click="$emit('close')"
              >
                <span class="material-symbols-outlined text-sm">open_in_new</span>
                View Details
              </router-link>
              <button
                class="px-6 py-3 bg-on-surface/5 dark:bg-on-surface/5 hover:bg-on-surface/10 dark:hover:bg-on-surface/10 border border-on-surface/8 dark:border-on-surface/10 text-on-surface dark:text-on-surface font-bold rounded-2xl transition-all hover:scale-[1.02] active:scale-95 text-sm"
                @click="$emit('close')"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

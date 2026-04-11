<script setup lang="ts">
import type { Notification } from '@types'

defineProps<{
  notification: Notification | null
}>()

defineEmits<{
  close: []
}>()

const typeClasses = function(type: string) {
  const map: Record<string, string> = {
    info: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
    success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
    warning: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
    error: 'bg-red-500/10 border-red-500/20 text-red-400',
  }
  return map[type] || map.info
}

const typeGradient = function(type: string) {
  const map: Record<string, string> = {
    info: 'bg-gradient-to-r from-blue-600 to-indigo-600',
    success: 'bg-gradient-to-r from-emerald-600 to-teal-600',
    warning: 'bg-gradient-to-r from-amber-600 to-orange-600',
    error: 'bg-gradient-to-r from-red-600 to-rose-600',
  }
  return map[type] || map.info
}

const typeIcon = function(type: string) {
  const map: Record<string, string> = {
    info: 'info',
    success: 'check_circle',
    warning: 'warning',
    error: 'error',
  }
  return map[type] || 'notifications'
}

const typeLabel = function(type: string) {
  const map: Record<string, string> = {
    info: 'Information',
    success: 'Success',
    warning: 'Attention Needed',
    error: 'Alert',
  }
  return map[type] || 'Notification'
}

const formatFullDate = function(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const formatTime = function(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit'
  })
}
</script>

<template>
  <Teleport to="body">
    <Transition enter-active-class="transition-all duration-300 ease-out" enter-from-class="opacity-0 scale-95 translate-y-4 blur-[4px]" enter-to-class="opacity-100 scale-100 translate-y-0 blur-0" leave-active-class="transition-all duration-300 ease-in" leave-from-class="opacity-100 scale-100 translate-y-0 blur-0" leave-to-class="opacity-0 scale-95 translate-y-4 blur-[4px]">
      <div
        v-if="notification"
        class="fixed inset-0 z-[210] flex items-center justify-center p-4"
        @click.self="$emit('close')"
      >
        <!-- Backdrop (slightly darker to focus on the detail) -->
        <div class="absolute inset-0 bg-black/30 dark:bg-black/80 backdrop-blur-md" @click="$emit('close')" />

        <!-- Modal -->
        <div class="relative w-full max-w-lg glass-heavy rounded-[2rem] shadow-2xl overflow-hidden flex flex-col">
          <!-- Decorative Top Bar -->
          <div :class="['h-1.5 w-full', typeGradient(notification.type)]"></div>

          <!-- Header Section -->
          <div class="p-8 pb-4">
            <div class="flex items-start justify-between gap-6 mb-6">
              <div class="flex items-center gap-3">
                <div 
                  class="w-12 h-12 rounded-2xl flex items-center justify-center border shadow-inner"
                  :class="typeClasses(notification.type)"
                >
                  <span class="material-symbols-outlined text-2xl">{{ typeIcon(notification.type) }}</span>
                </div>
                <div>
                  <span class="text-[10px] font-black uppercase tracking-[0.2em] text-on-surface-variant dark:text-on-surface-variant mb-1 block">
                    {{ typeLabel(notification.type) }}
                  </span>
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-medium text-on-surface-variant dark:text-on-surface-variant">{{ formatFullDate(notification.createdAt) }}</span>
                    <span class="w-1 h-1 rounded-full bg-outline-variant"></span>
                    <span class="text-xs font-medium text-on-surface-variant dark:text-on-surface-variant">{{ formatTime(notification.createdAt) }}</span>
                  </div>
                </div>
              </div>
              <button
                class="w-10 h-10 rounded-2xl bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 border border-black/8 dark:border-white/10 flex items-center justify-center text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface transition-all group"
                @click="$emit('close')"
              >
                <span class="material-symbols-outlined text-lg group-hover:rotate-90 transition-transform duration-300">close</span>
              </button>
            </div>

            <h2 class="text-2xl font-black text-on-surface dark:text-on-surface leading-tight tracking-tight">
              {{ notification.title || 'Notification Update' }}
            </h2>
          </div>

          <!-- Content Section -->
          <div class="px-8 py-6">
            <div class="h-px bg-gradient-to-r from-outline-variant/40 via-outline-variant/20 to-transparent mb-8"></div>
            
            <div class="prose max-w-none">
              <p class="text-lg text-on-surface-variant dark:text-on-surface-variant leading-[1.8] font-medium selection:bg-orange-500/30">
                {{ notification.message }}
              </p>
            </div>
            
            <div class="h-px bg-gradient-to-r from-transparent via-outline-variant/20 to-outline-variant/40 mt-8"></div>
          </div>

          <!-- Footer/Actions -->
          <div class="p-8 pt-4 flex items-center justify-between gap-4">
            <div class="flex flex-col gap-2">
              <div v-if="!notification.isRead" class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-orange-500/10 border border-orange-500/20 w-max">
                <span class="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse"></span>
                <span class="text-[10px] font-black text-orange-500 uppercase tracking-widest">New</span>
              </div>
              <div v-else class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-outline-variant/20 border border-outline-variant/40 w-max">
                <span class="material-symbols-outlined text-[12px] text-on-surface-variant dark:text-on-surface-variant">done_all</span>
                <span class="text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest">Read</span>
              </div>
            </div>

            <div class="flex gap-3">
              <router-link
                v-if="notification.link"
                :to="notification.link"
                class="px-6 py-3 bg-gradient-to-br from-orange-500 to-orange-700 hover:from-orange-400 hover:to-orange-600 text-white font-bold rounded-2xl shadow-lg shadow-orange-900/20 transition-all hover:scale-[1.02] active:scale-95 text-sm flex items-center gap-2"
                @click="$emit('close')"
              >
                <span class="material-symbols-outlined text-sm">open_in_new</span>
                View Details
              </router-link>
              <button
                class="px-6 py-3 bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 border border-black/8 dark:border-white/10 text-on-surface dark:text-on-surface font-bold rounded-2xl transition-all hover:scale-[1.02] active:scale-95 text-sm"
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


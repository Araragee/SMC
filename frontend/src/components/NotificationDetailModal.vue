<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="notification"
        class="fixed inset-0 z-[210] flex items-center justify-center p-4"
        @click.self="$emit('close')"
      >
        <!-- Backdrop (slightly darker to focus on the detail) -->
        <div class="absolute inset-0 bg-black/80 backdrop-blur-md" @click="$emit('close')" />

        <!-- Modal -->
        <div class="relative w-full max-w-lg liquid-glass rounded-[2rem] border border-white/10 shadow-2xl overflow-hidden flex flex-col">
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
                  <span class="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500 mb-1 block">
                    {{ typeLabel(notification.type) }}
                  </span>
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-medium text-zinc-400">{{ formatFullDate(notification.createdAt) }}</span>
                    <span class="w-1 h-1 rounded-full bg-zinc-700"></span>
                    <span class="text-xs font-medium text-zinc-500">{{ formatTime(notification.createdAt) }}</span>
                  </div>
                </div>
              </div>
              <button
                @click="$emit('close')"
                class="w-10 h-10 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center text-zinc-400 hover:text-white transition-all group"
              >
                <span class="material-symbols-outlined text-lg group-hover:rotate-90 transition-transform duration-300">close</span>
              </button>
            </div>

            <h2 class="text-2xl font-black text-white leading-tight tracking-tight">
              {{ notification.title || 'Notification Update' }}
            </h2>
          </div>

          <!-- Content Section -->
          <div class="px-8 py-6">
            <div class="h-px bg-gradient-to-r from-white/10 via-white/5 to-transparent mb-8"></div>
            
            <div class="prose prose-invert max-w-none">
              <p class="text-lg text-zinc-300 leading-[1.8] font-medium selection:bg-orange-500/30">
                {{ notification.message }}
              </p>
            </div>
            
            <div class="h-px bg-gradient-to-r from-transparent via-white/5 to-white/10 mt-8"></div>
          </div>

          <!-- Footer/Actions -->
          <div class="p-8 pt-4 flex items-center justify-between gap-4">
            <div class="flex flex-col gap-2">
              <div v-if="!notification.isRead" class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-orange-500/10 border border-orange-500/20 w-max">
                <span class="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse"></span>
                <span class="text-[10px] font-black text-orange-500 uppercase tracking-widest">New</span>
              </div>
              <div v-else class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-zinc-500/10 border border-zinc-500/20 w-max">
                <span class="material-symbols-outlined text-[12px] text-zinc-500">done_all</span>
                <span class="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Read</span>
              </div>
            </div>

            <div class="flex gap-3">
              <router-link
                v-if="notification.link"
                :to="notification.link"
                @click="$emit('close')"
                class="px-6 py-3 bg-gradient-to-br from-orange-500 to-orange-700 hover:from-orange-400 hover:to-orange-600 text-white font-bold rounded-2xl shadow-lg shadow-orange-900/20 transition-all hover:scale-[1.02] active:scale-95 text-sm flex items-center gap-2"
              >
                <span class="material-symbols-outlined text-sm">open_in_new</span>
                View Details
              </router-link>
              <button
                @click="$emit('close')"
                class="px-6 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold rounded-2xl transition-all hover:scale-[1.02] active:scale-95 text-sm"
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

<script setup lang="ts">
import type { Notification } from '../types'

defineProps<{
  notification: Notification | null
}>()

defineEmits<{
  close: []
}>()

function typeClasses(type: string) {
  const map: Record<string, string> = {
    info: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
    success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
    warning: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
    error: 'bg-red-500/10 border-red-500/20 text-red-400',
  }
  return map[type] || map.info
}

function typeGradient(type: string) {
  const map: Record<string, string> = {
    info: 'bg-gradient-to-r from-blue-600 to-indigo-600',
    success: 'bg-gradient-to-r from-emerald-600 to-teal-600',
    warning: 'bg-gradient-to-r from-amber-600 to-orange-600',
    error: 'bg-gradient-to-r from-red-600 to-rose-600',
  }
  return map[type] || map.info
}

function typeIcon(type: string) {
  const map: Record<string, string> = {
    info: 'info',
    success: 'check_circle',
    warning: 'warning',
    error: 'error',
  }
  return map[type] || 'notifications'
}

function typeLabel(type: string) {
  const map: Record<string, string> = {
    info: 'Information',
    success: 'Success',
    warning: 'Attention Needed',
    error: 'Alert',
  }
  return map[type] || 'Notification'
}

function formatFullDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  })
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit' 
  })
}
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-active .relative,
.modal-leave-active .relative {
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.modal-enter-from .relative {
  transform: scale(0.9) translateY(30px);
  filter: blur(10px);
}
</style>

<script setup lang="ts">
import { useThemeStore } from '../stores/theme'

defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const themeStore = useThemeStore()

const handleSave = function() {
  // Theme changes are reactive and persist automatically via themeStore watchers
  emit('close')
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
        v-if="isOpen"
        class="fixed inset-0 z-[220] flex items-center justify-center p-4"
        @click.self="$emit('close')"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/30 dark:bg-black/80 backdrop-blur-md" @click="$emit('close')" />

        <!-- Modal Card -->
        <div
          class="relative w-full max-w-xl glass-heavy rounded-[2.5rem] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        >
          <!-- Decorative Header -->
          <div
            class="h-2 w-full bg-gradient-to-r from-orange-600 via-orange-400 to-orange-600"
          ></div>

          <!-- Header Section -->
          <div class="p-8 pb-0 flex items-start justify-between">
            <div>
              <p class="text-[10px] font-black text-orange-500 uppercase tracking-[0.3em] mb-2">
                User Preferences
              </p>
              <h2 class="text-3xl font-black text-on-surface dark:text-on-surface tracking-tight">Preferences</h2>
            </div>
            <button
              class="w-12 h-12 rounded-2xl bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 border border-black/8 dark:border-white/10 flex items-center justify-center text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-all group"
              @click="$emit('close')"
            >
              <span
                class="material-symbols-outlined text-xl group-hover:rotate-90 transition-transform duration-300"
                >close</span
              >
            </button>
          </div>

          <div class="flex-1 overflow-y-auto p-8 pt-6 space-y-10 custom-scrollbar">
            <!-- Appearance Section -->
            <section class="space-y-6">
              <div class="flex items-center gap-3 px-1">
                <span class="material-symbols-outlined text-orange-500 text-lg">palette</span>
                <h3
                  class="text-sm font-black text-on-surface dark:text-on-surface uppercase tracking-widest"
                >
                  Appearance
                </h3>
              </div>

              <div
                class="bg-surface-container-low dark:bg-surface-container-low border border-outline-variant dark:border-outline-variant rounded-3xl p-6 space-y-4"
              >
                <div>
                  <h4 class="text-on-surface font-bold text-sm">Color Theme</h4>
                  <p class="text-on-surface-variant text-xs mt-1">
                    Choose how Sernan's Music Clinic appears on your device.
                  </p>
                </div>
                <!-- 3-Way Theme Picker -->
                <div class="flex rounded-2xl bg-black/[0.04] dark:bg-white/5 border border-black/[0.06] dark:border-white/8 p-1 gap-1">
                  <button
                    v-for="opt in ([
                      { value: 'system', icon: 'desktop_windows', label: 'System' },
                      { value: 'light', icon: 'light_mode', label: 'Light' },
                      { value: 'dark', icon: 'dark_mode', label: 'Dark' },
                    ] as const)"
                    :key="opt.value"
                    class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-xs font-bold transition-all duration-300"
                    :class="themeStore.preference === opt.value
                      ? 'bg-white dark:bg-white/15 text-orange-600 dark:text-orange-400 shadow-sm border border-black/[0.06] dark:border-white/10'
                      : 'text-on-surface-variant hover:text-on-surface hover:bg-black/[0.04] dark:hover:bg-white/5'"
                    :aria-label="`Switch to ${opt.label} mode`"
                    :aria-pressed="themeStore.preference === opt.value"
                    @click="themeStore.setPreference(opt.value)"
                  >
                    <span class="material-symbols-outlined text-base" :style="themeStore.preference === opt.value ? 'font-variation-settings: \'FILL\' 1' : ''">{{ opt.icon }}</span>
                    {{ opt.label }}
                  </button>
                </div>
              </div>
            </section>
          </div>

          <!-- Sticky Footer -->
          <div
            class="p-8 border-t border-black/5 dark:border-white/5 bg-black/[0.02] dark:bg-white/[0.02] flex items-center justify-end gap-4 shrink-0"
          >
            <button
              class="px-6 py-3 text-sm font-bold text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-colors"
              @click="$emit('close')"
            >
              Cancel
            </button>
            <button
              class="px-10 py-3 bg-gradient-to-br from-orange-500 to-orange-700 hover:from-orange-400 hover:to-orange-600 text-white dark:text-white font-black rounded-2xl shadow-lg shadow-orange-950/20 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:scale-100 flex items-center gap-2"
              @click="handleSave"
            >
              DONE
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { useThemeStore } from '@stores/theme'
import type { ThemePreference } from '@stores/theme'

interface ThemeOption {
  value: ThemePreference
  icon: string
  label: string
}

defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const themeStore = useThemeStore()

// 'system' leads because deferring to the OS is the setting most people want
// and the one they get before they ever open this modal.
const themeOptions: ThemeOption[] = [
  { value: 'system', icon: 'desktop_windows', label: 'System' },
  { value: 'light', icon: 'light_mode', label: 'Light' },
  { value: 'dark', icon: 'dark_mode', label: 'Dark' },
]

// The theme store persists to localStorage and repaints on its own watchers,
// so the choice has already taken effect by the time this runs. There is
// nothing to submit — the button only dismisses.
const handleDone = () => {
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
        <div class="absolute inset-0 bg-black/40 dark:bg-black/70" @click="$emit('close')" />

        <!-- Modal Card -->
        <div
          class="modal-shell relative w-full max-w-md glass-heavy rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        >
          <!-- Header -->
          <div class="flex items-start justify-between gap-4 px-5 pt-5 sm:px-8 sm:pt-7">
            <div class="min-w-0">
              <p class="text-xs font-semibold text-primary uppercase mb-1">Display</p>
              <h2 class="text-2xl sm:text-3xl font-semibold text-on-surface tracking-tight">
                Preferences
              </h2>
            </div>
            <button
              class="icon-btn shrink-0 bg-on-surface/5 hover:bg-on-surface/10"
              aria-label="Close preferences"
              @click="$emit('close')"
            >
              <span class="material-symbols-outlined text-xl">close</span>
            </button>
          </div>

          <div class="flex-1 overflow-y-auto px-5 py-6 sm:px-8 custom-scrollbar">
            <!-- Appearance -->
            <h3
              class="mb-4 pb-2 border-b border-outline-variant/20 text-xs font-semibold uppercase text-on-surface-variant"
            >
              Appearance
            </h3>

            <h4 class="text-sm font-bold text-on-surface">Color Theme</h4>
            <p class="mt-0.5 mb-4 text-xs text-on-surface-variant leading-relaxed">
              Choose how Sernan's Music Clinic appears on this device. System follows your
              operating system setting.
            </p>

            <div
              class="flex rounded-2xl bg-on-surface/[0.04] dark:bg-on-surface/5 p-1 gap-1"
              role="group"
              aria-label="Color theme"
            >
              <button
                v-for="opt in themeOptions"
                :key="opt.value"
                class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-xs font-bold transition-colors"
                :class="
                  themeStore.preference === opt.value
                    ? 'bg-surface-container-lowest dark:bg-on-surface/15 text-primary shadow-sm'
                    : 'text-on-surface-variant hover:text-on-surface'
                "
                :aria-label="`Switch to ${opt.label} mode`"
                :aria-pressed="themeStore.preference === opt.value"
                @click="themeStore.setPreference(opt.value)"
              >
                <span
                  class="material-symbols-outlined text-base"
                  :class="
                    themeStore.preference === opt.value ? `[font-variation-settings:'FILL'_1]` : ''
                  "
                  >{{ opt.icon }}</span
                >
                {{ opt.label }}
              </button>
            </div>
          </div>

          <!-- Sticky Footer -->
          <div
            class="shrink-0 flex items-center justify-end gap-3 px-5 py-4 sm:px-8 border-t border-on-surface/5 bg-on-surface/[0.02]"
          >
            <button class="btn-primary" @click="handleDone">Done</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

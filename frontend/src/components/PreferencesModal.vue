<script setup lang="ts">
import BaseModal from '@components/BaseModal.vue'
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

// The theme store persists and repaints on its own watchers, so the choice has
// already taken effect. There is nothing to submit; the button only dismisses.
const handleDone = () => {
  emit('close')
}
</script>

<template>
  <BaseModal
    :is-open="isOpen"
    eyebrow="Display"
    title="Preferences"
    close-label="Close preferences"
    @close="$emit('close')"
  >
    <h3
      class="mb-4 pb-2 border-b border-outline-variant/20 text-xs font-semibold uppercase text-on-surface-variant"
    >
      Appearance
    </h3>

    <h4 class="text-sm font-bold text-on-surface">Color Theme</h4>
    <p class="mt-0.5 mb-4 text-xs text-on-surface-variant leading-relaxed">
      Choose how Sernan's Music Clinic appears on this device. System follows your operating
      system setting.
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

    <template #footer>
      <button class="btn-primary" @click="handleDone">Done</button>
    </template>
  </BaseModal>
</template>

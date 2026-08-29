<script setup lang="ts">
import { dialogState } from '@composables/useDialog'

function handleConfirm() {
  dialogState.open = false
  dialogState.resolve?.(dialogState.type === 'prompt' ? dialogState.inputValue || null : true)
  dialogState.resolve = null
}

function handleCancel() {
  dialogState.open = false
  dialogState.resolve?.(dialogState.type === 'prompt' ? null : false)
  dialogState.resolve = null
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') handleCancel()
  if (e.key === 'Enter' && dialogState.type === 'confirm') handleConfirm()
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 scale-95 blur-[4px]"
      enter-to-class="opacity-100 scale-100 blur-0"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100 scale-100 blur-0"
      leave-to-class="opacity-0 scale-95 blur-[4px]"
    >
      <div
        v-if="dialogState.open"
        class="fixed inset-0 z-[9999] flex items-center justify-center p-4"
        @keydown="handleKeydown"
      >
        <div class="absolute inset-0 bg-black/40 dark:bg-black/70" @click="handleCancel" />

        <div class="relative w-full max-w-sm glass-heavy border border-outline-variant/30 rounded-3xl p-6 shadow-2xl overflow-hidden">
          <!-- Accent glow -->
          <div
            class="absolute top-0 right-0 size-28 blur-[64px] rounded-full -z-10 pointer-events-none"
            :class="dialogState.destructive ? 'bg-error/20' : 'bg-primary/15'"
          />

          <!-- Header -->
          <div class="flex items-center gap-3 mb-4">
            <span
              class="material-symbols-outlined text-2xl"
              :class="dialogState.destructive ? 'text-error' : 'text-primary'"
            >
              {{ dialogState.type === 'prompt' ? 'edit_note' : (dialogState.destructive ? 'warning' : 'help') }}
            </span>
            <h3 class="text-lg font-semibold text-on-surface">{{ dialogState.title }}</h3>
          </div>

          <!-- Message -->
          <p class="text-sm text-on-surface-variant mb-4 leading-relaxed">{{ dialogState.message }}</p>

          <!-- Input for prompt mode -->
          <div v-if="dialogState.type === 'prompt'" class="mb-4">
            <input
              v-model="dialogState.inputValue"
              :placeholder="dialogState.placeholder || 'Enter text…'"
              class="input"
              autofocus
              @keydown.enter="handleConfirm"
            />
          </div>

          <!-- Actions -->
          <div class="flex gap-3 justify-end">
            <button
              class="px-4 py-2 rounded-2xl text-sm font-bold text-on-surface-variant bg-surface-container-highest/40 hover:bg-surface-container-highest/70 border border-outline-variant/20 transition-all"
              @click="handleCancel"
            >
              Cancel
            </button>
            <button
              class="px-4 py-2 rounded-2xl text-sm font-bold transition-all"
              :class="dialogState.destructive ? 'bg-error/90 hover:bg-error text-on-error shadow-[0_0_20px_-4px_rgba(186,26,26,0.4)]' : 'bg-primary/90 hover:bg-primary text-on-primary shadow-[0_0_20px_-4px_rgba(255,144,109,0.3)]'"
              @click="handleConfirm"
            >
              {{ dialogState.type === 'prompt' ? 'Submit' : 'Confirm' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

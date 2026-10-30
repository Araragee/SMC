<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'

type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '4xl'
/** Stacking tier. A modal opened from another modal needs 'raised'; the
 *  messaging panel and anything that must sit over everything take 'top'. */
type ModalLayer = 'default' | 'raised' | 'top'

const props = withDefaults(
  defineProps<{
    isOpen: boolean
    title?: string
    eyebrow?: string
    size?: ModalSize
    layer?: ModalLayer
    closeLabel?: string
    /** false for a modal the user must answer rather than dismiss. */
    dismissible?: boolean
    /** Sit against the bottom edge below sm, centred from sm up. Reaching a
     *  centred dialog's controls one-handed on a phone is awkward; a sheet
     *  puts them under the thumb. */
    sheet?: boolean
  }>(),
  {
    title: '',
    eyebrow: '',
    size: 'md',
    layer: 'default',
    closeLabel: 'Close',
    dismissible: true,
    sheet: false,
  }
)

const emit = defineEmits<{
  close: []
}>()

const sizeClass = computed(
  () =>
    ({
      sm: 'max-w-sm',
      md: 'max-w-md',
      lg: 'max-w-lg',
      xl: 'max-w-xl',
      '2xl': 'max-w-2xl',
      '4xl': 'max-w-4xl',
    })[props.size]
)

const layerClass = computed(
  () =>
    ({
      default: 'z-[200]',
      raised: 'z-[250]',
      top: 'z-[300]',
    })[props.layer]
)

const close = () => {
  if (props.dismissible) emit('close')
}

// Escape closed exactly one of the twenty-three hand-rolled modals this
// replaces. Bound on window rather than the panel so it works before anything
// inside has been focused.
const onKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.isOpen) close()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
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
        class="fixed inset-0 flex justify-center p-4"
        :class="[layerClass, sheet ? 'items-end sm:items-center' : 'items-center']"
        role="dialog"
        aria-modal="true"
        :aria-label="title || undefined"
        @click.self="close"
      >
        <div class="absolute inset-0 bg-black/40 dark:bg-black/70" @click="close" />

        <div
          class="modal-shell relative w-full glass-heavy rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
          :class="sizeClass"
        >
          <slot name="header">
            <div
              v-if="title || eyebrow"
              class="flex items-start justify-between gap-4 px-5 pt-5 sm:px-8 sm:pt-7"
            >
              <div class="min-w-0">
                <p v-if="eyebrow" class="text-xs font-semibold text-primary uppercase mb-1">
                  {{ eyebrow }}
                </p>
                <h2 class="text-2xl sm:text-3xl font-semibold text-on-surface tracking-tight">
                  {{ title }}
                </h2>
              </div>
              <button
                v-if="dismissible"
                class="icon-btn shrink-0 bg-on-surface/5 hover:bg-on-surface/10"
                :aria-label="closeLabel"
                @click="close"
              >
                <span class="material-symbols-outlined text-xl">close</span>
              </button>
            </div>
          </slot>

          <div class="flex-1 overflow-y-auto px-5 py-6 sm:px-8 custom-scrollbar">
            <slot />
          </div>

          <div
            v-if="$slots.footer"
            class="shrink-0 flex items-center justify-end gap-3 px-5 py-4 sm:px-8 border-t border-on-surface/5 bg-on-surface/[0.02]"
          >
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

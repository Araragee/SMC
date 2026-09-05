<script setup lang="ts">
import { computed } from 'vue'

/**
 * BaseCard — iOS 26 Liquid Glass card system
 *
 * Variants:
 *  'base'        — solid surface (default)
 *  'interactive' — base + lift on hover
 *  'overlay'     — thin glass overlay
 *  'glass'       — iOS 26 standard glass (blur 40px, 68% white / 70% dark)
 *  'glass-thin'  — lightweight glass for navbars, pills, floating elements
 *  'glass-heavy' — opaque glass for modals and sheets
 *  'glass-tinted'— brand-tinted glass for accent cards
 *
 * Props:
 *  specular  — adds the iOS diagonal shimmer highlight layer
 *  padding   — controls inner padding ('none' | 'sm' | 'md' | 'lg')
 *  radius    — border-radius override ('sm' | 'md' | 'lg' | 'xl' | '2xl')
 */

type CardVariant =
  | 'base'
  | 'interactive'
  | 'overlay'
  | 'glass'
  | 'glass-thin'
  | 'glass-heavy'
  | 'glass-tinted'
type PaddingSize = 'none' | 'sm' | 'md' | 'lg'
type RadiusSize = 'sm' | 'md' | 'lg' | 'xl' | '2xl'

interface Props {
  variant?: CardVariant
  elevation?: 'low' | 'highest'
  specular?: boolean
  padding?: PaddingSize
  radius?: RadiusSize
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'base',
  elevation: 'highest',
  specular: false,
  padding: 'lg',
  radius: 'lg',
})

const radiusClass: Record<RadiusSize, string> = {
  sm: 'rounded-xl',
  md: 'rounded-2xl',
  lg: 'rounded-[24px]',
  xl: 'rounded-3xl',
  '2xl': 'rounded-3xl',
}

const paddingClass: Record<PaddingSize, string> = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
}

const isGlass = computed(() =>
  ['glass', 'glass-thin', 'glass-heavy', 'glass-tinted', 'overlay'].includes(props.variant)
)

const surfaceClass = computed(() => {
  switch (props.variant) {
    case 'glass':
      return 'glass'
    case 'glass-thin':
      return 'glass-thin'
    case 'glass-heavy':
      return 'glass-heavy'
    case 'glass-tinted':
      return 'glass-tinted'
    case 'overlay':
      return 'glass-thin'
    default:
      return props.elevation === 'highest'
        ? 'bg-surface-container-highest dark:bg-surface-container-highest border border-outline-variant/30 dark:border-outline-variant/20'
        : 'bg-surface-container-low dark:bg-surface-container-low border border-outline-variant/30 dark:border-outline-variant/20'
  }
})

const interactiveClass = computed(() =>
  props.variant === 'interactive'
    ? 'hover:-translate-y-1 hover:shadow-[0_0_64px_rgba(70,15,0,0.1)] dark:hover:shadow-[0_0_64px_rgba(255,144,109,0.08)] cursor-pointer'
    : ''
)

const computedClasses = computed(() => [
  'relative overflow-hidden transition-all duration-300',
  radiusClass[props.radius],
  surfaceClass.value,
  interactiveClass.value,
  props.specular ? 'glass-specular' : '',
])
</script>

<template>
  <div :class="computedClasses">
    <!-- Inner specular glow ring (non-glass variants only) -->
    <div
      v-if="!isGlass"
      class="absolute inset-0 pointer-events-none z-0"
      :class="radiusClass[radius]"
      style="
        box-shadow:
          inset 1px 1px 0px rgba(255, 255, 255, 0.07),
          inset 0px -1px 0px rgba(0, 0, 0, 0.12);
      "
    ></div>

    <div class="relative z-10 w-full h-full flex flex-col gap-6" :class="paddingClass[padding]">
      <slot></slot>
    </div>
  </div>
</template>

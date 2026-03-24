<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  variant?: 'base' | 'interactive' | 'overlay';
  elevation?: 'low' | 'highest';
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'base',
  elevation: 'highest'
});

const computedClasses = computed(() => {
  const baseClass = 'relative rounded-[24px] overflow-hidden transition-all duration-300';

  const surfaceClass = props.variant === 'overlay'
    ? 'bg-surface-variant/40 backdrop-blur-[24px]'
    : (props.elevation === 'highest' ? 'bg-surface-container-highest' : 'bg-surface-container-low');

  // "Liquid Glows: For floating elements, use a primary tinted shadow. Instead of #000000, use on_primary_container (#460f00) at 10% opacity with a 64px blur."
  const interactiveClass = props.variant === 'interactive'
    ? 'hover:-translate-y-1 hover:shadow-[0_0_64px_rgba(70,15,0,0.1)] cursor-pointer'
    : '';

  return [baseClass, surfaceClass, interactiveClass].join(' ');
});
</script>

<template>
  <div :class="computedClasses">
    <!-- Liquid Glass Inner Glow -->
    <div class="absolute inset-0 rounded-[24px] pointer-events-none border border-white/5 shadow-[inset_1px_1px_0px_0px_rgba(255,255,255,0.15)] z-0"></div>

    <div class="relative z-10 w-full h-full p-8 flex flex-col gap-8">
      <!-- "Spacing-6 (2rem) of vertical white space to separate list items" -->
      <!-- We achieve this by defaulting the internal layout to flex-col gap-8 -->
      <slot></slot>
    </div>
  </div>
</template>


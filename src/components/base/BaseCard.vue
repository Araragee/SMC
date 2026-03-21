<template>
  <div :class="computedClasses">
    <!-- Liquid Glass Inner Glow -->
    <div class="absolute inset-0 rounded-[24px] pointer-events-none border border-white/5 inner-glow-top-left z-0"></div>

    <div class="relative z-10 w-full h-full p-8 flex flex-col gap-8">
      <!-- "Spacing-6 (2rem) of vertical white space to separate list items" -->
      <!-- We achieve this by defaulting the internal layout to flex-col gap-8 -->
      <slot></slot>
    </div>
  </div>
</template>

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

  let surfaceClass = '';

  // "Use surface-variant with backdrop-filter: blur(24px). Elements behind the card should be visible but diffused"
  if (props.variant === 'overlay') {
    surfaceClass = 'bg-surface-variant/40 backdrop-blur-[24px]';
  } else {
    // "Place a surface_container_highest card inside a surface_container_low parent."
    if (props.elevation === 'highest') {
        surfaceClass = 'bg-surface-container-highest';
    } else {
        surfaceClass = 'bg-surface-container-low';
    }
  }

  // "Liquid Glows: For floating elements, use a primary tinted shadow. Instead of #000000, use on_primary_container (#460f00) at 10% opacity with a 64px blur."
  const interactiveClass = props.variant === 'interactive'
    ? 'hover:-translate-y-1 hover:shadow-[0_0_64px_rgba(70,15,0,0.1)] cursor-pointer'
    : '';

  return [baseClass, surfaceClass, interactiveClass].join(' ');
});
</script>

<style scoped>
/* Inner Glow: To achieve the "Liquid Glass" look, apply a 1px inner-shadow (inset) using on_surface at 15% opacity to the top and left edges of glass containers. This mimics the light-catching edge of a glass pane. */
.inner-glow-top-left {
  box-shadow: inset 1px 1px 0px 0px rgba(255, 255, 255, 0.15);
}

/* Glass Cards & Lists
   Constraint: No dividers. Use Spacing-6 (2rem) of vertical white space to separate list items.
   Visual Interest: Use surface-variant with backdrop-filter: blur(24px). Elements behind the card should be visible but diffused, creating an "iOS 26" depth effect. */
</style>

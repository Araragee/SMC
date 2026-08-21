<script setup lang="ts">
import { computed } from 'vue';

type ButtonVariant = 'primary' | 'secondary' | 'tertiary';
type ButtonSize = 'sm' | 'md' | 'lg';
type ButtonType = 'button' | 'submit' | 'reset';

interface Props {
  variant?: ButtonVariant;
  size?: ButtonSize;
  type?: ButtonType;
  fullWidth?: boolean;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md',
  type: 'button',
  fullWidth: false,
  disabled: false
});

const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void;
}>();

const onClick = (event: MouseEvent) => {
  if (!props.disabled) {
    emit('click', event);
  }
};

const computedClasses = computed(() => {
  const baseClasses = 'group relative font-bold font-headline uppercase overflow-hidden active:scale-[0.98] transition-all duration-300 rounded-xl';

  const variantClasses = {
    // Solid fill: the old glow hardcoded an rgba() of the previous brand
    // colour and did not follow the theme.
    primary: 'bg-primary text-on-primary hover:bg-primary-dim border-none shadow-e1',
    secondary: 'bg-surface-container-highest text-primary border border-outline-variant/20', // Ghost border
    tertiary: 'bg-transparent text-primary hover:bg-on-surface/5 border-none relative after:content-[""] after:absolute after:bottom-2 after:left-1/2 after:-translate-x-1/2 after:w-0 after:h-0.5 after:bg-primary hover:after:w-1/2 after:transition-all after:duration-300' // tertiary spec
  };

  const sizeClasses = {
    sm: 'h-10 px-4 text-xs',
    md: 'h-14 px-6 text-sm',
    lg: 'h-16 px-8 text-base'
  };

  return [
    baseClasses,
    variantClasses[props.variant],
    sizeClasses[props.size],
    props.fullWidth ? 'w-full' : '',
    props.disabled ? 'opacity-50 cursor-not-allowed active:scale-100' : ''
  ];
});
</script>

<template>
  <button
    :class="computedClasses"
    :type="type"
    @click="onClick"
  >
    <span class="relative z-10 flex items-center justify-center gap-2">
      <slot name="icon-left"></slot>
      <slot></slot>
      <slot name="icon-right"></slot>
    </span>
  </button>
</template>


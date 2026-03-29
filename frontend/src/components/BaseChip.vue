<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  modelValue?: boolean;
  label?: string;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  label: '',
  disabled: false
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'change', value: boolean): void;
}>();

const toggleSelection = () => {
  if (!props.disabled) {
    const newValue = !props.modelValue;
    emit('update:modelValue', newValue);
    emit('change', newValue);
  }
};

const computedClasses = computed(() => {
  const baseClasses = 'relative inline-flex items-center justify-center px-4 py-2 rounded-[24px] overflow-hidden transition-all duration-400 ease-[cubic-bezier(0.2,0.8,0.2,1)] duration-[400ms] ease-[cubic-bezier(0.2,0.8,0.2,1)]';

  // Selection Chips
  // "Unselected: surface_container_highest with on_surface_variant text."
  // "Selected: primary background with on_primary (#5b1600) text. The transition must be a "liquid" morph effect."

  const unselectedClasses = 'bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-highest/80';
  const selectedClasses = 'bg-primary text-on-primary font-bold shadow-[0_0_20px_rgba(255,144,109,0.3)] scale-105';

  const stateClasses = props.modelValue ? selectedClasses : unselectedClasses;
  const disabledClasses = props.disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer';

  return [baseClasses, stateClasses, disabledClasses].join(' ');
});
</script>

<template>
  <button
    type="button"
    :class="computedClasses"
    @click="toggleSelection"
  >
    <div class="relative z-10 flex items-center gap-2">
      <slot name="icon-left"></slot>
      <span class="text-[10px] uppercase tracking-widest font-bold font-label"><slot>{{ label }}</slot></span>
      <slot name="icon-right"></slot>
    </div>
  </button>
</template>

<script setup lang="ts">
import { computed, ref, useId } from 'vue';

interface Props {
  modelValue?: string | number;
  label?: string;
  type?: string;
  placeholder?: string;
  iconLeft?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  type: 'text',
  placeholder: '',
  required: false,
  disabled: false
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
  (e: 'blur', event: FocusEvent): void;
  (e: 'focus', event: FocusEvent): void;
}>();

const id = useId();
const showPassword = ref(false);

const inputType = computed(() => {
  if (props.type === 'password') {
    return showPassword.value ? 'text' : 'password';
  }
  return props.type;
});

const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value;
};

const updateValue = (event: Event) => {
  const target = event.target as HTMLInputElement;
  emit('update:modelValue', target.value);
};

const computedClasses = computed(() => {
  const baseClasses = 'w-full min-h-[4rem] border-none rounded-[24px] pr-6 text-on-surface placeholder:text-on-surface-variant transition-all duration-300 focus:ring-1 focus:ring-primary/50 focus:bg-surface-container-high py-[1.4rem]';

  // Padding left adjustments based on left icon
  const paddingClasses = props.iconLeft ? 'pl-14' : 'pl-6';

  // Error state
  const stateClasses = props.error
    ? 'bg-error/10 text-error-dim focus:ring-error-dim border border-error/30'
    : 'bg-on-surface/5 dark:bg-on-surface/5 border border-on-surface/8 dark:border-on-surface/10';

  const disabledClasses = props.disabled ? 'opacity-50 cursor-not-allowed' : '';

  return [baseClasses, paddingClasses, stateClasses, disabledClasses].join(' ');
});
</script>

<template>
  <div class="space-y-2 w-full">
    <div v-if="label" class="flex justify-between items-center px-1">
      <label :for="id" class="text-xs uppercase text-on-surface-variant font-bold">
        {{ label }}
      </label>
      <slot name="label-right"></slot>
    </div>
    <div class="relative group">
      <span
        v-if="iconLeft"
        class="material-symbols-outlined absolute left-5 top-1/2 -translate-y-1/2 text-on-surface-variant text-xl transition-colors group-focus-within:text-primary"
      >
        {{ iconLeft }}
      </span>
      <input
        :id="id"
        :type="inputType"
        :value="modelValue"
        :placeholder="placeholder"
        :required="required"
        :disabled="disabled"
        :class="computedClasses"
        @input="updateValue"
        @blur="$emit('blur', $event)"
        @focus="$emit('focus', $event)"
      />

      <!-- Right slot for things like password visibility toggle -->
      <slot name="icon-right">
        <button
            v-if="type === 'password'"
            type="button"
            class="absolute right-5 top-1/2 -translate-y-1/2 text-on-surface-variant cursor-pointer hover:text-on-surface dark:hover:text-on-surface transition-colors"
            @click="togglePasswordVisibility"
        >
            <span class="material-symbols-outlined">{{ showPassword ? 'visibility_off' : 'visibility' }}</span>
        </button>
      </slot>

      <!-- Subtle cosmic orange glow at base on focus -->
      <div
        class="absolute bottom-0 left-4 right-4 h-px bg-primary opacity-0 transition-opacity duration-300 group-focus-within:opacity-50 blur-sm"
      ></div>
    </div>
    <p v-if="error" class="text-error-dim text-xs mt-1 ml-1">{{ error }}</p>
  </div>
</template>


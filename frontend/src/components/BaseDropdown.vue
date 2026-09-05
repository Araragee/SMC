<script setup lang="ts">
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from '@headlessui/vue'
import { computed } from 'vue'

export interface DropdownOption {
  value: string | number | null
  label: string
  disabled?: boolean
}

interface Props {
  modelValue?: string | number | null
  options?: DropdownOption[]
  label?: string
  placeholder?: string
  iconLeft?: string
  error?: string
  disabled?: boolean
  size?: 'sm' | 'md'
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  options: () => [],
  label: '',
  placeholder: 'Select…',
  iconLeft: '',
  error: '',
  disabled: false,
  size: 'md',
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | number | null): void
  (e: 'change', value: string | number | null): void
}>()

const selected = computed({
  get: () => props.modelValue,
  set: (value: string | number | null) => {
    emit('update:modelValue', value)
    emit('change', value)
  },
})

const selectedLabel = computed(
  () => props.options.find((o) => o.value === props.modelValue)?.label ?? ''
)

const sizeClasses = computed(
  () =>
    ({
      sm: 'py-2 text-xs',
      md: 'py-3 text-sm',
    })[props.size]
)

const stateClasses = computed(() =>
  props.error
    ? 'bg-error-container text-on-error-container border-error'
    : 'bg-surface-container-highest/20 text-on-surface border-outline-variant/40'
)

const buttonClasses = computed(() =>
  [
    'relative w-full cursor-pointer rounded-xl border pr-10 text-left transition-colors',
    'focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/30',
    'disabled:cursor-not-allowed disabled:opacity-50',
    props.iconLeft ? 'pl-11' : 'pl-4',
    sizeClasses.value,
    stateClasses.value,
  ].join(' ')
)

const optionClasses = (active: boolean, isSelected: boolean) =>
  [
    'relative cursor-pointer select-none rounded-lg px-3 py-2 text-sm transition-colors',
    active ? 'bg-primary-container text-on-primary-container' : 'text-on-surface',
    isSelected ? 'font-semibold' : '',
  ].join(' ')
</script>

<template>
  <div class="w-full space-y-2">
    <Listbox v-model="selected" :disabled="disabled" as="div" class="w-full space-y-2">
      <label v-if="label" class="block px-1 text-xs font-bold uppercase text-on-surface-variant">
        {{ label }}
      </label>

      <div class="relative">
        <span
          v-if="iconLeft"
          class="material-symbols-outlined pointer-events-none absolute left-3 top-1/2 z-10 -translate-y-1/2 text-lg text-on-surface-variant"
        >
          {{ iconLeft }}
        </span>

        <ListboxButton :class="buttonClasses">
          <span :class="selectedLabel ? '' : 'text-on-surface-variant'">
            {{ selectedLabel || placeholder }}
          </span>
          <span
            class="material-symbols-outlined pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-lg text-on-surface-variant"
          >
            expand_more
          </span>
        </ListboxButton>

        <transition
          leave-active-class="transition duration-100 ease-in"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0"
        >
          <ListboxOptions
            class="absolute z-50 mt-2 max-h-60 w-full overflow-auto rounded-xl border border-outline-variant/40 bg-surface-container p-1 shadow-lg focus:outline-none"
          >
            <ListboxOption
              v-for="option in options"
              v-slot="{ active, selected: isSelected }"
              :key="String(option.value)"
              :value="option.value"
              :disabled="option.disabled"
              as="template"
            >
              <li :class="optionClasses(active, isSelected)">{{ option.label }}</li>
            </ListboxOption>
          </ListboxOptions>
        </transition>
      </div>
    </Listbox>

    <p v-if="error" class="ml-1 text-xs text-error">{{ error }}</p>
  </div>
</template>

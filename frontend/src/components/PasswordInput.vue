<script setup lang="ts">
import { ref } from 'vue'

// A bare `.input` styled password field with a show/hide toggle. The raw
// <input type="password"> elements it replaces had no way to reveal what was
// typed, which is where most failed logins on a temp password came from.
//
// BaseInput already does this, but it carries the tall pill styling used by
// modals; the auth screens use the flatter `.input` class, so this keeps them
// looking the same while gaining the toggle.

withDefaults(
  defineProps<{
    placeholder?: string
    autocomplete?: string
    required?: boolean
    id?: string
  }>(),
  { placeholder: '', autocomplete: 'current-password', required: false, id: undefined }
)

const model = defineModel<string>({ default: '' })
const visible = ref(false)
</script>

<template>
  <div class="relative">
    <input
      :id="id"
      v-model="model"
      :type="visible ? 'text' : 'password'"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      :required="required"
      class="input pr-12"
    />
    <button
      type="button"
      tabindex="-1"
      class="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-on-surface-variant transition-colors hover:text-on-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
      :aria-label="visible ? 'Hide password' : 'Show password'"
      :aria-pressed="visible"
      @click="visible = !visible"
    >
      <span class="material-symbols-outlined text-xl">
        {{ visible ? 'visibility_off' : 'visibility' }}
      </span>
    </button>
  </div>
</template>

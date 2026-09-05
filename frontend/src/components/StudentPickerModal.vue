<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { User } from '@types'

const props = withDefaults(
  defineProps<{
    isOpen: boolean
    students: User[]
    teacherName?: string
    /** 'assign' puts students on a roster; 'enroll' also grants session credits. */
    isSubmitting?: boolean
  }>(),
  {
    teacherName: '',
    isSubmitting: false,
  },
)

const emit = defineEmits<{
  close: []
  confirm: [studentIds: number[], sessions: number]
}>()

const search = ref('')
const selected = ref<number[]>([])
const sessions = ref(8)

const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return props.students
  return props.students.filter(
    (s) => s.name.toLowerCase().includes(term) || (s.email ?? '').toLowerCase().includes(term),
  )
})

const allFilteredSelected = computed(
  () => filtered.value.length > 0 && filtered.value.every((s) => selected.value.includes(s.id)),
)

const toggle = (id: number) => {
  selected.value = selected.value.includes(id)
    ? selected.value.filter((s) => s !== id)
    : [...selected.value, id]
}

const toggleAllFiltered = () => {
  const ids = filtered.value.map((s) => s.id)
  selected.value = allFilteredSelected.value
    ? selected.value.filter((id) => !ids.includes(id))
    : [...new Set([...selected.value, ...ids])]
}

const submit = () => {
  if (!selected.value.length) return
  emit('confirm', [...selected.value], sessions.value)
}

// Reset between openings so a previous selection never leaks into the next batch.
watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      search.value = ''
      selected.value = []
    }
  },
)
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="student-picker-title"
    >
      <div class="absolute inset-0 bg-black/40 dark:bg-black/70" @click="emit('close')" />

      <div class="card modal-shell relative flex w-full max-w-lg flex-col bg-surface-container shadow-xl">
        <header class="card-header">
          <div class="space-y-1">
            <h2 id="student-picker-title" class="section-title">
              Bulk enroll students
            </h2>
            <p class="section-caption">
              {{ teacherName ? `Teacher: ${teacherName}` : 'Select existing student accounts.' }}
            </p>
          </div>
          <button class="icon-btn" aria-label="Close" @click="emit('close')">
            <span class="material-symbols-outlined text-lg" aria-hidden="true">close</span>
          </button>
        </header>

        <div class="space-y-4 px-6 py-4">
          <div class="field">
            <label for="picker-search" class="field-label">Search students</label>
            <input
              id="picker-search"
              v-model="search"
              type="search"
              class="input"
              placeholder="Name or email"
            />
          </div>

          <div class="field">
            <label for="picker-sessions" class="field-label">Sessions per student</label>
            <input
              id="picker-sessions"
              v-model.number="sessions"
              type="number"
              min="1"
              class="input num"
            />
          </div>

          <div class="flex items-center justify-between">
            <p class="field-hint num">{{ selected.length }} selected</p>
            <button
              type="button"
              class="btn-ghost btn-sm"
              :disabled="!filtered.length"
              @click="toggleAllFiltered"
            >
              {{ allFilteredSelected ? 'Clear all' : 'Select all' }}
            </button>
          </div>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto border-t border-outline-variant/20">
          <p v-if="!filtered.length" class="empty-state section-caption">
            No matching students.
          </p>
          <ul v-else class="divide-y divide-outline-variant/15">
            <li v-for="student in filtered" :key="student.id">
              <label
                class="flex cursor-pointer items-center gap-4 px-6 py-3 transition-colors hover:bg-on-surface/5"
              >
                <input
                  type="checkbox"
                  class="size-4 shrink-0 accent-primary"
                  :checked="selected.includes(student.id)"
                  @change="toggle(student.id)"
                />
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-sm font-medium text-on-surface">{{ student.name }}</span>
                  <span class="block truncate text-xs text-on-surface-variant">{{ student.email }}</span>
                </span>
                <span class="num shrink-0 text-xs text-on-surface-variant">
                  {{ student.sessionsLeft ?? 0 }} credits
                </span>
              </label>
            </li>
          </ul>
        </div>

        <footer class="flex justify-end gap-3 border-t border-outline-variant/20 px-6 py-4">
          <button type="button" class="btn-ghost" @click="emit('close')">Cancel</button>
          <button
            type="button"
            class="btn-primary"
            :disabled="!selected.length || isSubmitting"
            @click="submit"
          >
            {{ isSubmitting ? 'Working…' : 'Enroll selected' }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

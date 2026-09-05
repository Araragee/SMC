<script setup lang="ts">
import BaseDropdown from '@/components/BaseDropdown.vue';
import { ref, computed } from 'vue'
import axios from 'axios'
import { API_URL } from '@typescript/constants'
import { useAuthStore } from '@stores/auth'
import { useToastStore } from '@stores/toast'
import type { User } from '@types'

const props = defineProps<{
  isOpen: boolean
  teachers: User[]
  students: User[]
}>()

const emit = defineEmits<{ close: []; created: [] }>()

const auth = useAuthStore()
const toast = useToastStore()

const today = new Date().toISOString().split('T')[0]
const form = ref({
  teacherId: null as number | null,
  studentId: null as number | null,
  date: today,
  time: '10:00',
  durationHours: '1',
  cadence: 'weekly' as 'weekly' | 'biweekly' | 'monthly',
  occurrences: 4,
  notes: '',
})

const submitting = ref(false)

const isValid = computed(() =>
  !!form.value.teacherId &&
  !!form.value.studentId &&
  !!form.value.date &&
  !!form.value.time &&
  form.value.occurrences >= 2 &&
  form.value.occurrences <= 52
)

const submit = async function () {
  if (!isValid.value || submitting.value) return
  submitting.value = true
  try {
    const [y, m, d] = form.value.date.split('-').map(Number)
    const [hr, min] = form.value.time.split(':').map(Number)
    const start = new Date(y, m - 1, d, hr, min)
    const end = new Date(start.getTime() + parseFloat(form.value.durationHours) * 3600000)
    const res = await axios.post(`${API_URL}/sessions/recurring`, {
      teacher_id: form.value.teacherId,
      student_id: form.value.studentId,
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      cadence: form.value.cadence,
      occurrences: form.value.occurrences,
      notes: form.value.notes || null,
    }, { headers: { Authorization: `Bearer ${auth.token}` } })
    toast.success(`Created ${res.data.created_count} sessions`)
    emit('created')
    emit('close')
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed'
    toast.error(msg)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 dark:bg-black/70 p-4" @click.self="emit('close')">
    <div class="modal-shell w-full max-w-lg bg-surface-container-lowest dark:bg-zinc-900 rounded-3xl p-6 shadow-2xl space-y-4">
      <h2 class="text-2xl font-semibold text-on-surface dark:text-on-surface">Recurring Lessons</h2>
      <p class="text-sm text-on-surface-variant dark:text-on-surface-variant">Create a series of scheduled sessions.</p>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label class="space-y-1">
          <span class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant">Teacher</span>
          <BaseDropdown v-model="form.teacherId" :options="[{ value: null, label: 'Select…' }, ...teachers.map(t => ({ value: t.id, label: t.name }))]" />
        </label>
        <label class="space-y-1">
          <span class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant">Student</span>
          <BaseDropdown v-model="form.studentId" :options="[{ value: null, label: 'Select…' }, ...students.map(s => ({ value: s.id, label: s.name }))]" />
        </label>
        <label class="space-y-1">
          <span class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant">First date</span>
          <input v-model="form.date" type="date" class="w-full px-3 py-2 rounded-2xl bg-zinc-100 dark:bg-zinc-800 text-on-surface dark:text-on-surface" />
        </label>
        <label class="space-y-1">
          <span class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant">Time</span>
          <input v-model="form.time" type="time" class="w-full px-3 py-2 rounded-2xl bg-zinc-100 dark:bg-zinc-800 text-on-surface dark:text-on-surface" />
        </label>
        <label class="space-y-1">
          <span class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant">Duration (hours)</span>
          <input v-model="form.durationHours" type="number" min="0.25" step="0.25" class="w-full px-3 py-2 rounded-2xl bg-zinc-100 dark:bg-zinc-800 text-on-surface dark:text-on-surface" />
        </label>
        <label class="space-y-1">
          <span class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant">Cadence</span>
          <BaseDropdown v-model="form.cadence" :options="[{ value: 'weekly', label: 'Weekly' }, { value: 'biweekly', label: 'Biweekly' }, { value: 'monthly', label: 'Monthly' }]" />
        </label>
        <label class="col-span-2 space-y-1">
          <span class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant">Occurrences (2–52)</span>
          <input v-model.number="form.occurrences" type="number" min="2" max="52" class="w-full px-3 py-2 rounded-2xl bg-zinc-100 dark:bg-zinc-800 text-on-surface dark:text-on-surface" />
        </label>
        <label class="col-span-2 space-y-1">
          <span class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant">Notes</span>
          <textarea v-model="form.notes" rows="2" class="w-full px-3 py-2 rounded-2xl bg-zinc-100 dark:bg-zinc-800 text-on-surface dark:text-on-surface"></textarea>
        </label>
      </div>

      <div class="flex gap-2 justify-end pt-2">
        <button class="px-4 py-2 rounded-2xl bg-zinc-200 dark:bg-zinc-800 text-on-surface dark:text-on-surface font-semibold" @click="emit('close')">Cancel</button>
        <button
          class="px-4 py-2 rounded-2xl bg-primary text-on-primary font-bold disabled:opacity-50"
          :disabled="!isValid || submitting"
          @click="submit"
        >
          {{ submitting ? 'Creating…' : 'Create Series' }}
        </button>
      </div>
    </div>
  </div>
</template>

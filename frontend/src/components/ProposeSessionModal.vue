<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import type { User, Session, InstrumentRecord } from '@types'
import { useScheduleStore } from '@stores/schedule'

const props = defineProps<{
  isOpen: boolean
  userRole: 'admin' | 'teacher' | 'student'
  currentUserId: number
  teachers: User[]
  students: User[]
  instruments?: InstrumentRecord[]
  initialDate?: Date
}>()

const emit = defineEmits<{
  close: []
  submitted: [session: Session]
}>()

const scheduleStore = useScheduleStore()

const todayStr = new Date().toISOString().split('T')[0]

const form = ref({
  teacherId: props.userRole === 'teacher' ? (props.currentUserId as number | null) : null as number | null,
  studentId: props.userRole === 'student' ? (props.currentUserId as number | null) : null as number | null,
  date: props.initialDate ? props.initialDate.toISOString().split('T')[0] : todayStr,
  time: '10:00',
  durationHours: '1',
  notes: '',
  instrumentId: null as number | null,
})

const isSubmitting = ref(false)

watch(() => props.initialDate, (d) => {
  if (d) form.value.date = d.toISOString().split('T')[0]
})

watch(() => form.value.teacherId, (newId) => {
  if (newId) {
    scheduleStore.fetchTeacherPublicSessions(Number(newId))
  }
}, { immediate: true })

onMounted(() => {
  if (form.value.teacherId) {
    scheduleStore.fetchTeacherPublicSessions(Number(form.value.teacherId))
  }
})

const busySlotsOnSelectedDate = computed(() => {
  if (!form.value.teacherId || !form.value.date) return []
  return scheduleStore.teacherBusySlots.filter((slot: any) => {
    const slotDateStr = slot.startTime.split('T')[0]
    return slotDateStr === form.value.date
  })
})

const formatSlotTime = (iso: string) => {
  return new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })
}

const overlapsWithBusySlot = computed(() => {
  if (!form.value.teacherId || !form.value.date || !form.value.time) return false
  const [y, m, d] = form.value.date.split('-').map(Number)
  const [hr, min] = form.value.time.split(':').map(Number)
  const startDt = new Date(y, m - 1, d, hr, min)
  const endDt = new Date(startDt.getTime() + parseFloat(form.value.durationHours) * 3600000)

  return scheduleStore.teacherBusySlots.some((slot: any) => {
    const slotStart = new Date(slot.startTime)
    const slotEnd = new Date(slot.endTime)
    return startDt < slotEnd && endDt > slotStart
  })
})

const isValid = computed(() => {
  const needsTeacher = props.userRole === 'student' || props.userRole === 'admin'
  const needsStudent = props.userRole === 'teacher' || props.userRole === 'admin'
  return (
    form.value.date &&
    form.value.time &&
    (!needsTeacher || form.value.teacherId) &&
    (!needsStudent || form.value.studentId) &&
    !overlapsWithBusySlot.value
  )
})

const submitLabel = computed(() => {
  if (isSubmitting.value) return 'Submitting...'
  if (props.userRole === 'admin') return 'Schedule Session'
  return 'Send Proposal'
})

const submit = async function() {
  if (!isValid.value || isSubmitting.value) return
  isSubmitting.value = true
  try {
    const [y, m, d] = form.value.date.split('-').map(Number)
    const [hr, min] = form.value.time.split(':').map(Number)
    const startDt = new Date(y, m - 1, d, hr, min)
    const endDt = new Date(startDt.getTime() + parseFloat(form.value.durationHours) * 3600000)

    emit('submitted', {
      id: 0,
      teacherId: Number(form.value.teacherId),
      studentId: Number(form.value.studentId),
      startTime: startDt.toISOString(),
      endTime: endDt.toISOString(),
      status: 'scheduled',
      notes: form.value.notes || undefined,
      instrumentId: form.value.instrumentId ?? undefined,
      homeworkCompleted: false,
    })
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition enter-active-class="transition-all duration-200 ease-out" enter-from-class="opacity-0 scale-95 translate-y-4 blur-[4px]" enter-to-class="opacity-100 scale-100 translate-y-0 blur-0" leave-active-class="transition-all duration-200 ease-in" leave-from-class="opacity-100 scale-100 translate-y-0 blur-0" leave-to-class="opacity-0 scale-95 translate-y-4 blur-[4px]">
      <div
        v-if="true"
        class="fixed inset-0 z-[300] flex items-center justify-center p-4"
        @click.self="$emit('close')"
      >
        <div class="absolute inset-0 bg-black/40 dark:bg-black/70" @click="$emit('close')" />

        <div class="relative w-full max-w-md glass-heavy rounded-3xl shadow-2xl">
          <!-- Header -->
          <div class="flex items-center justify-between p-6 border-b border-on-surface/5 dark:border-on-surface/5">
            <div>
              <p class="text-xs font-semibold text-primary uppercase mb-1">
                {{ userRole === 'admin' ? 'Direct Schedule' : 'Propose Session' }}
              </p>
              <h3 class="text-xl font-semibold text-on-surface dark:text-on-surface">New Session Request</h3>
            </div>
            <button
              class="icon-btn"
              @click="$emit('close')"
            >
              <span class="material-symbols-outlined text-lg">close</span>
            </button>
          </div>

          <!-- Form -->
          <div class="p-6 space-y-4">
            <!-- Teacher select (for student / admin) -->
            <div v-if="userRole === 'student' || userRole === 'admin'">
              <label class="block text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase mb-2">Teacher</label>
              <select
                v-model="form.teacherId"
                class="input"
              >
                <option :value="null" disabled class="bg-surface-container">Select a teacher</option>
                <option v-for="t in teachers" :key="t.id" :value="t.id" class="bg-surface-container">{{ t.name }}</option>
              </select>
            </div>

            <!-- Student select (for teacher / admin) -->
            <div v-if="userRole === 'teacher' || userRole === 'admin'">
              <label class="block text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase mb-2">Student</label>
              <select
                v-model="form.studentId"
                class="input"
              >
                <option :value="null" disabled class="bg-surface-container">Select a student</option>
                <option v-for="s in students" :key="s.id" :value="s.id" class="bg-surface-container">{{ s.name }}</option>
              </select>
            </div>

            <!-- Date & Time -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase mb-2">Date</label>
                <input
                  v-model="form.date"
                  type="date"
                  :min="todayStr"
                  class="input"
                />
              </div>
              <div>
                <label class="block text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase mb-2">Time</label>
                <input
                  v-model="form.time"
                  type="time"
                  class="input"
                />
              </div>
            </div>

            <!-- Duration -->
            <div>
              <label class="block text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase mb-2">Duration</label>
              <select
                v-model="form.durationHours"
                class="input"
              >
                <option value="0.5" class="bg-surface-container">30 minutes</option>
                <option value="1" class="bg-surface-container">1 hour</option>
                <option value="1.5" class="bg-surface-container">1.5 hours</option>
                <option value="2" class="bg-surface-container">2 hours</option>
              </select>
            </div>

            <!-- Busy slots helper & overlap warning -->
            <div v-if="busySlotsOnSelectedDate.length > 0" class="alert-error">
              <p class="text-xs font-semibold text-red-500 dark:text-red-400 uppercase mb-1 flex items-center gap-1">
                <span class="material-symbols-outlined text-xs">warning</span>
                Teacher Busy Slots on this Date:
              </p>
              <div class="flex flex-wrap gap-1.5 mt-1">
                <span v-for="slot in busySlotsOnSelectedDate" class="text-xs font-bold bg-red-500/10 border border-red-500/20 text-red-700 dark:text-red-300 px-2 py-0.5 rounded-lg">
                  {{ formatSlotTime(slot.startTime) }} - {{ formatSlotTime(slot.endTime) }}
                </span>
              </div>
              <p v-if="overlapsWithBusySlot" class="text-xs font-semibold text-red-600 dark:text-red-400 mt-2">
                ⚠️ Overlap conflict detected. Please select another time.
              </p>
            </div>

            <!-- Instrument (optional, shown if instruments list is provided) -->
            <div v-if="instruments && instruments.length > 0">
              <label class="block text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase mb-2">
                Instrument <span class="normal-case font-medium">(optional)</span>
              </label>
              <select
                v-model="form.instrumentId"
                class="input"
              >
                <option :value="null" class="bg-surface-container">No specific instrument</option>
                <option v-for="inst in instruments" :key="inst.id" :value="inst.id" class="bg-surface-container">{{ inst.name }}</option>
              </select>
            </div>

            <!-- Notes -->
            <div>
              <label class="block text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase mb-2">Notes <span class="text-on-surface-variant dark:text-on-surface-variant normal-case font-medium">(optional)</span></label>
              <textarea
                v-model="form.notes"
                rows="3"
                placeholder="Add context, instrument focus, or any special requests..."
                class="input resize-none"
              />
            </div>

            <!-- Approval notice for non-admin -->
            <div v-if="userRole !== 'admin'" class="alert-info">
              <span class="material-symbols-outlined text-blue-400 text-base mt-0.5">info</span>
              <p class="text-blue-700 dark:text-blue-300 text-xs leading-relaxed">
                <template v-if="userRole === 'student'">Your request will be sent to your teacher for review, then forwarded to admin for final approval.</template>
                <template v-else>Your proposal will be sent to admin for final approval before being confirmed.</template>
              </p>
            </div>
          </div>

          <!-- Footer -->
          <div class="p-4 border-t border-on-surface/5 dark:border-on-surface/5 flex gap-3">
            <button
              :disabled="!isValid || isSubmitting"
              class="flex-1 py-3 bg-primary text-on-primary font-bold rounded-2xl shadow-lg hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-2 text-sm disabled:opacity-40 disabled:cursor-not-allowed disabled:scale-100"
              @click="submit"
            >
              <span v-if="isSubmitting" class="material-symbols-outlined text-base animate-spin">refresh</span>
              <span v-else class="material-symbols-outlined text-base">send</span>
              {{ submitLabel }}
            </button>
            <button
              class="px-4 py-3 bg-on-surface/5 dark:bg-on-surface/5 hover:bg-on-surface/10 dark:hover:bg-on-surface/10 border border-on-surface/8 dark:border-on-surface/10 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface font-bold rounded-2xl transition-all text-sm"
              @click="$emit('close')"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>


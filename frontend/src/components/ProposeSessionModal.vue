<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { User, Session } from '../types'

const props = defineProps<{
  userRole: 'admin' | 'teacher' | 'student'
  currentUserId: string
  teachers: User[]
  students: User[]
  initialDate?: Date
}>()

const emit = defineEmits<{
  close: []
  submitted: [session: Session]
}>()

const todayStr = new Date().toISOString().split('T')[0]

const form = ref({
  teacherId: props.userRole === 'teacher' ? props.currentUserId : '',
  studentId: props.userRole === 'student' ? props.currentUserId : '',
  date: props.initialDate ? props.initialDate.toISOString().split('T')[0] : todayStr,
  time: '10:00',
  durationHours: '1',
  notes: '',
})

const isSubmitting = ref(false)

watch(() => props.initialDate, (d) => {
  if (d) form.value.date = d.toISOString().split('T')[0]
})

const isValid = computed(() => {
  const needsTeacher = props.userRole === 'student' || props.userRole === 'admin'
  const needsStudent = props.userRole === 'teacher' || props.userRole === 'admin'
  return (
    form.value.date &&
    form.value.time &&
    (!needsTeacher || form.value.teacherId) &&
    (!needsStudent || form.value.studentId)
  )
})

const submitLabel = computed(() => {
  if (isSubmitting.value) return 'Submitting...'
  if (props.userRole === 'admin') return 'Schedule Session'
  return 'Send Proposal'
})

async function submit() {
  if (!isValid.value || isSubmitting.value) return
  isSubmitting.value = true
  try {
    const startDt = new Date(`${form.value.date}T${form.value.time}:00`)
    const endDt = new Date(startDt.getTime() + parseFloat(form.value.durationHours) * 3600000)

    emit('submitted', {
      id: '',
      teacherId: form.value.teacherId,
      studentId: form.value.studentId,
      startTime: startDt.toISOString(),
      endTime: endDt.toISOString(),
      status: 'scheduled',
      notes: form.value.notes || undefined,
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
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="$emit('close')" />

        <div class="relative w-full max-w-md liquid-glass rounded-3xl border border-white/10 shadow-2xl">
          <!-- Header -->
          <div class="flex items-center justify-between p-6 border-b border-white/5">
            <div>
              <p class="text-[10px] font-black text-orange-500 uppercase tracking-widest mb-1">
                {{ userRole === 'admin' ? 'Direct Schedule' : 'Propose Session' }}
              </p>
              <h3 class="text-xl font-black text-white">New Session Request</h3>
            </div>
            <button
              @click="$emit('close')"
              class="w-10 h-10 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center text-zinc-400 hover:text-white transition-all"
            >
              <span class="material-symbols-outlined text-lg">close</span>
            </button>
          </div>

          <!-- Form -->
          <div class="p-6 space-y-5">
            <!-- Teacher select (for student / admin) -->
            <div v-if="userRole === 'student' || userRole === 'admin'">
              <label class="block text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">Teacher</label>
              <select
                v-model="form.teacherId"
                class="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50"
              >
                <option value="" disabled class="bg-zinc-900">Select a teacher</option>
                <option v-for="t in teachers" :key="t.id" :value="t.id" class="bg-zinc-900">{{ t.name }}</option>
              </select>
            </div>

            <!-- Student select (for teacher / admin) -->
            <div v-if="userRole === 'teacher' || userRole === 'admin'">
              <label class="block text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">Student</label>
              <select
                v-model="form.studentId"
                class="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50"
              >
                <option value="" disabled class="bg-zinc-900">Select a student</option>
                <option v-for="s in students" :key="s.id" :value="s.id" class="bg-zinc-900">{{ s.name }}</option>
              </select>
            </div>

            <!-- Date & Time -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">Date</label>
                <input
                  type="date"
                  v-model="form.date"
                  :min="todayStr"
                  class="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50"
                />
              </div>
              <div>
                <label class="block text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">Time</label>
                <input
                  type="time"
                  v-model="form.time"
                  class="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50"
                />
              </div>
            </div>

            <!-- Duration -->
            <div>
              <label class="block text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">Duration</label>
              <select
                v-model="form.durationHours"
                class="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50"
              >
                <option value="0.5" class="bg-zinc-900">30 minutes</option>
                <option value="1" class="bg-zinc-900">1 hour</option>
                <option value="1.5" class="bg-zinc-900">1.5 hours</option>
                <option value="2" class="bg-zinc-900">2 hours</option>
              </select>
            </div>

            <!-- Notes -->
            <div>
              <label class="block text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2">Notes <span class="text-zinc-600 normal-case font-medium">(optional)</span></label>
              <textarea
                v-model="form.notes"
                rows="3"
                placeholder="Add context, instrument focus, or any special requests..."
                class="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-white text-sm placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 resize-none"
              />
            </div>

            <!-- Approval notice for non-admin -->
            <div v-if="userRole !== 'admin'" class="flex items-start gap-2.5 p-3 rounded-2xl bg-blue-500/5 border border-blue-500/20">
              <span class="material-symbols-outlined text-blue-400 text-base mt-0.5">info</span>
              <p class="text-blue-300 text-xs leading-relaxed">
                <template v-if="userRole === 'student'">Your request will be sent to your teacher for review, then forwarded to admin for final approval.</template>
                <template v-else>Your proposal will be sent to admin for final approval before being confirmed.</template>
              </p>
            </div>
          </div>

          <!-- Footer -->
          <div class="p-4 border-t border-white/5 flex gap-3">
            <button
              @click="submit"
              :disabled="!isValid || isSubmitting"
              class="flex-1 py-3 bg-gradient-to-br from-orange-500 to-orange-700 text-white font-bold rounded-2xl shadow-lg shadow-orange-900/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-2 text-sm disabled:opacity-40 disabled:cursor-not-allowed disabled:scale-100"
            >
              <span v-if="isSubmitting" class="material-symbols-outlined text-base animate-spin">refresh</span>
              <span v-else class="material-symbols-outlined text-base">send</span>
              {{ submitLabel }}
            </button>
            <button
              @click="$emit('close')"
              class="px-5 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-400 hover:text-white font-bold rounded-2xl transition-all text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>


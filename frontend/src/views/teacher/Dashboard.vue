<template>
  <div class="flex">
    <TeacherSidebar />
    <div class="ml-64 w-full min-h-screen p-8 pt-10">

      <!-- Header -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-orange-500 mb-1">Teacher Hub</p>
          <h2 class="text-4xl font-black text-white tracking-tight">
            Welcome back, <span class="text-orange-500">Maestro.</span>
          </h2>
          <p class="text-zinc-500 mt-1 text-sm">
            You have <span class="text-white font-bold">{{ todaySessions.length }}</span> sessions today.
          </p>
        </div>
        <div class="flex items-center gap-3">
          <!-- Next session pill -->
          <div v-if="nextSession" class="flex items-center gap-3 bg-zinc-900/80 border border-zinc-700 rounded-2xl px-4 py-3">
            <div class="w-8 h-8 rounded-full bg-orange-500 flex items-center justify-center shrink-0">
              <span class="material-symbols-outlined text-white text-sm" style="font-variation-settings:'FILL' 1" aria-hidden="true">schedule</span>
            </div>
            <div>
              <p class="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">Next Up</p>
              <p class="text-sm font-black text-white">{{ formatTime(nextSession.startTime) }} • Session #{{ nextSession.id }}</p>
            </div>
          </div>
          <button @click="showScheduleModal = true"
            class="flex items-center gap-2 px-5 py-3 bg-orange-600 hover:bg-orange-500 text-white rounded-2xl font-black text-sm transition-all active:scale-95 shadow-lg shadow-orange-900/30 focus:outline-none focus:ring-2 focus:ring-orange-500/50"
            aria-label="Schedule a new session">
            <span class="material-symbols-outlined text-sm" aria-hidden="true">add</span>
            New Schedule
          </button>
        </div>
      </div>

      <div class="grid grid-cols-3 gap-4">
        <!-- Left column: Student Roster + Weekly Schedule -->
        <div class="col-span-2 space-y-4">

          <!-- Student Roster -->
          <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl overflow-hidden">
            <div class="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-orange-400" style="font-variation-settings:'FILL' 1" aria-hidden="true">group</span>
                <h3 class="font-black text-white">Student Roster</h3>
              </div>
              <button class="text-xs text-orange-500 font-bold hover:text-orange-400 transition-colors">
                VIEW ALL ROSTER
              </button>
            </div>

            <div v-if="scheduleStore.isLoading" class="p-6 grid grid-cols-2 gap-3">
              <div v-for="i in 2" :key="i" class="h-24 rounded-xl bg-zinc-800 animate-pulse" />
            </div>

            <div v-else-if="myStudents.length === 0" class="p-8 text-center">
              <span class="material-symbols-outlined text-4xl text-zinc-700 mb-2 block" aria-hidden="true">person_off</span>
              <p class="text-zinc-500 text-sm">No students assigned yet.</p>
            </div>

            <div v-else class="p-4 grid grid-cols-2 gap-3">
              <div v-for="student in myStudents.slice(0, 4)" :key="student.sessionId"
                class="bg-zinc-800/50 border border-zinc-700/50 rounded-xl p-4 hover:border-orange-500/30 transition-colors">
                <div class="flex items-center gap-3 mb-3">
                  <div class="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center text-white font-black shrink-0">
                    {{ student.name.charAt(0) }}
                  </div>
                  <div class="min-w-0">
                    <p class="font-bold text-white text-sm truncate">{{ student.name }}</p>
                    <p class="text-[10px] text-zinc-500">STUDENT</p>
                  </div>
                  <button class="ml-auto text-zinc-600 hover:text-white transition-colors" aria-label="View student details">
                    <span class="material-symbols-outlined text-base" aria-hidden="true">chevron_right</span>
                  </button>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-semibold">
                    {{ formatDay(student.startTime) }}
                  </span>
                  <span class="text-xs px-2 py-0.5 rounded-full font-semibold"
                    :class="student.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'">
                    {{ student.status === 'completed' ? 'HIGH' : 'PROGRESS' }}
                  </span>
                </div>
              </div>
              <!-- Enroll new -->
              <button @click="showScheduleModal = true"
                class="border-2 border-dashed border-zinc-700 rounded-xl p-4 flex flex-col items-center justify-center gap-2 text-zinc-600 hover:border-orange-500/50 hover:text-orange-500 transition-all">
                <span class="material-symbols-outlined text-2xl" aria-hidden="true">person_add</span>
                <span class="text-xs font-semibold uppercase tracking-wider">Enroll New</span>
              </button>
            </div>
          </div>

          <!-- Weekly Schedule -->
          <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl overflow-hidden">
            <div class="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-orange-400" style="font-variation-settings:'FILL' 1" aria-hidden="true">calendar_month</span>
                <h3 class="font-black text-white">Weekly Schedule</h3>
              </div>
              <div class="flex items-center gap-2">
                <button class="w-8 h-8 rounded-lg bg-zinc-800 hover:bg-zinc-700 flex items-center justify-center transition-colors" aria-label="Previous week">
                  <span class="material-symbols-outlined text-sm text-zinc-400" aria-hidden="true">chevron_left</span>
                </button>
                <button class="w-8 h-8 rounded-lg bg-zinc-800 hover:bg-zinc-700 flex items-center justify-center transition-colors" aria-label="Next week">
                  <span class="material-symbols-outlined text-sm text-zinc-400" aria-hidden="true">chevron_right</span>
                </button>
              </div>
            </div>
            <div class="p-4">
              <div class="grid grid-cols-5 gap-2">
                <div v-for="day in weekDays" :key="day.label" class="flex flex-col gap-2">
                  <p class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest text-center">{{ day.label }}</p>
                  <div v-if="day.session"
                    class="bg-orange-500/15 border border-orange-500/30 rounded-xl p-2.5 text-center hover:bg-orange-500/25 transition-colors cursor-pointer">
                    <p class="text-xs font-black text-orange-400">{{ formatTime(day.session.startTime) }}</p>
                    <p class="text-[10px] text-white font-semibold mt-0.5 truncate">Session #{{ day.session.id }}</p>
                  </div>
                  <button v-else @click="showScheduleModal = true"
                    class="border-2 border-dashed border-zinc-800 rounded-xl p-3 flex items-center justify-center text-zinc-700 hover:border-zinc-600 hover:text-zinc-500 transition-all"
                    :aria-label="`Add session on ${day.label}`">
                    <span class="material-symbols-outlined text-base" aria-hidden="true">add</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

        </div>

        <!-- Right column: Live session card + Stats -->
        <div class="space-y-4">

          <!-- Live / Current Session -->
          <div v-if="nextSession" class="bg-orange-600 rounded-2xl p-5 shadow-xl shadow-orange-900/40">
            <div class="flex items-center justify-between mb-4">
              <span class="text-xs font-black bg-white/20 text-white px-3 py-1 rounded-full uppercase tracking-wider">
                {{ todaySessions.length > 0 ? 'Live Session' : 'Next Session' }}
              </span>
              <button class="text-white/50 hover:text-white transition-colors" aria-label="More options">
                <span class="material-symbols-outlined text-base" aria-hidden="true">more_horiz</span>
              </button>
            </div>
            <h4 class="text-xl font-black text-white leading-tight mb-1">Session #{{ nextSession.id }}</h4>
            <p class="text-xs text-orange-200/80">ID: #{{ nextSession.id.padStart(4, '0') }} • {{ formatTime(nextSession.startTime) }}</p>

            <div class="mt-5">
              <p class="text-[10px] text-orange-200/60 uppercase tracking-widest font-bold mb-2">Visual Evidence</p>
              <label class="block border-2 border-dashed border-white/20 rounded-xl p-4 text-center cursor-pointer hover:border-white/40 transition-colors"
                :aria-label="`Upload session proof for session ${nextSession.id}`">
                <span class="material-symbols-outlined text-3xl text-white/40 block mb-1" style="font-variation-settings:'FILL' 1" aria-hidden="true">photo_camera_add</span>
                <span class="text-xs text-white/60 font-semibold">TAKE PHOTO OR UPLOAD</span>
                <input type="file" accept="image/*" class="hidden" @change="handleProofUpload(nextSession!.id, $event)" />
              </label>
            </div>

            <div class="mt-4">
              <p class="text-[10px] text-orange-200/60 uppercase tracking-widest font-bold mb-2">Practice Goals</p>
              <textarea v-model="practiceNotes" rows="2"
                class="w-full bg-white/10 text-white placeholder-white/30 rounded-xl px-3 py-2 text-xs resize-none focus:outline-none focus:ring-2 focus:ring-white/30 border border-transparent"
                placeholder="E.g. Focus on paradiddle transitions at 120bpm..."
                aria-label="Next week practice goals"
              />
            </div>

            <button @click="completeSession(nextSession.id)"
              class="w-full mt-4 py-3 bg-white text-orange-600 rounded-xl font-black text-sm hover:bg-orange-50 active:scale-95 transition-all focus:outline-none focus:ring-2 focus:ring-white/50">
              COMPLETE SESSION
            </button>
          </div>

          <!-- No active session placeholder -->
          <div v-else class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6 text-center">
            <span class="material-symbols-outlined text-4xl text-zinc-700 block mb-2" aria-hidden="true">event_available</span>
            <p class="text-zinc-400 font-semibold text-sm">No upcoming sessions</p>
            <button @click="showScheduleModal = true"
              class="mt-3 text-xs text-orange-500 hover:text-orange-400 font-bold transition-colors">
              Schedule one →
            </button>
          </div>

          <!-- Stats row -->
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-4">
              <p class="text-3xl font-black text-orange-500">{{ mySessions.length }}</p>
              <p class="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mt-1">Active Roster</p>
              <p class="text-xs text-zinc-600 mt-0.5">Total assigned sessions</p>
            </div>
            <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-4">
              <p class="text-3xl font-black text-amber-400">
                {{ mySessions.filter(s => s.homeworkAssigned && !s.homeworkCompleted).length }}
              </p>
              <p class="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mt-1">HW Pending</p>
              <p class="text-xs text-zinc-600 mt-0.5">Awaiting student submission</p>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>

  <!-- Schedule Session Modal -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showScheduleModal"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        role="dialog" aria-modal="true" aria-labelledby="schedule-modal-title"
        @click.self="showScheduleModal = false">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="showScheduleModal = false" />
        <div class="relative w-full max-w-md bg-zinc-900 border border-zinc-700 rounded-2xl p-6 shadow-2xl">
          <div class="flex items-center justify-between mb-6">
            <h3 id="schedule-modal-title" class="text-xl font-black text-white">Schedule a Session</h3>
            <button @click="showScheduleModal = false"
              class="text-zinc-500 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-500 rounded-lg p-1"
              aria-label="Close modal">
              <span class="material-symbols-outlined" aria-hidden="true">close</span>
            </button>
          </div>
          <form @submit.prevent="submitSchedule" class="space-y-4">
            <div>
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 block" for="sched-student">Student</label>
              <select id="sched-student" v-model="schedForm.studentId" required
                class="w-full bg-zinc-800 border border-zinc-700 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50">
                <option value="">Choose a student...</option>
                <option v-for="s in allStudents" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
            </div>
            <div>
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 block" for="sched-date">Date &amp; Time</label>
              <input id="sched-date" type="datetime-local" v-model="schedForm.startTime" required
                class="w-full bg-zinc-800 border border-zinc-700 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50" />
            </div>
            <div>
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 block" for="sched-hw">Homework Assignment <span class="text-zinc-600 normal-case">(optional)</span></label>
              <textarea id="sched-hw" v-model="schedForm.homework" rows="2"
                placeholder="e.g. Practice C major scales for 15 minutes..."
                class="w-full bg-zinc-800 border border-zinc-700 text-white placeholder-zinc-600 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-orange-500/50" />
            </div>
            <div class="flex gap-3 pt-2">
              <button type="button" @click="showScheduleModal = false"
                class="flex-1 py-3 rounded-xl border border-zinc-700 text-zinc-400 hover:text-white text-sm font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-zinc-500/50">
                Cancel
              </button>
              <button type="submit" :disabled="scheduleStore.isLoading"
                class="flex-1 py-3 rounded-xl bg-orange-600 hover:bg-orange-500 text-white text-sm font-black transition-all active:scale-95 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-orange-500/50">
                {{ scheduleStore.isLoading ? 'Scheduling...' : 'Schedule Session' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted, computed, ref, reactive } from 'vue'
import TeacherSidebar from '../../components/TeacherSidebar.vue'
import { useScheduleStore } from '../../stores/schedule'
import { useUsersStore } from '../../stores/users'
import { useAuthStore } from '../../stores/auth'
import { useToastStore } from '../../stores/toast'
import { useInteractionsStore } from '../../stores/interactions'
import axios from 'axios'

const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()
const toast = useToastStore()
const interactionsStore = useInteractionsStore()

const showScheduleModal = ref(false)
const practiceNotes = ref('')

const schedForm = reactive({ studentId: '', startTime: '', homework: '' })

onMounted(async () => {
  if (authStore.currentUser?.id) {
    await Promise.all([
      scheduleStore.fetchUserSessions(authStore.currentUser.id),
      usersStore.fetchUsersByRole('student'),
    ])
  }
})

const myId = computed(() => authStore.currentUser?.id ?? '')

const mySessions = computed(() =>
  scheduleStore.allSessions.filter(s => s.teacherId === myId.value)
)

const todaySessions = computed(() => {
  const today = new Date().toDateString()
  return mySessions.value.filter(s => s.startTime && new Date(s.startTime).toDateString() === today)
})

const nextSession = computed(() =>
  mySessions.value
    .filter(s => s.status === 'scheduled')
    .sort((a, b) => new Date(a.startTime!).getTime() - new Date(b.startTime!).getTime())[0] ?? null
)

// Build unique student-session pairs for the roster
const myStudents = computed(() => {
  const seen = new Set<string>()
  return mySessions.value
    .filter(s => { if (seen.has(s.studentId)) return false; seen.add(s.studentId); return true })
    .map(s => {
      const user = usersStore.users.find(u => u.id === s.studentId)
      return { sessionId: s.id, studentId: s.studentId, name: user?.name ?? `Student #${s.studentId}`, startTime: s.startTime, status: s.status }
    })
})

const allStudents = computed(() => usersStore.getUsersByRole('student'))

// 5-day week grid (Mon–Fri of current week)
const weekDays = computed(() => {
  const days = ['MON', 'TUE', 'WED', 'THU', 'FRI']
  const now = new Date()
  const dayOfWeek = now.getDay() || 7
  const monday = new Date(now)
  monday.setDate(now.getDate() - dayOfWeek + 1)
  monday.setHours(0, 0, 0, 0)

  return days.map((label, i) => {
    const date = new Date(monday)
    date.setDate(monday.getDate() + i)
    const session = mySessions.value.find(s => {
      if (!s.startTime) return false
      const d = new Date(s.startTime)
      return d.toDateString() === date.toDateString()
    })
    return { label, date, session: session ?? null }
  })
})

const formatTime = (dt: string | undefined) => {
  if (!dt) return '—'
  return new Date(dt).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
}
const formatDay = (dt: string | undefined) => {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString('en-US', { weekday: 'short', hour: '2-digit', minute: '2-digit' })
}

async function submitSchedule() {
  if (!schedForm.studentId || !schedForm.startTime) return
  try {
    const start = new Date(schedForm.startTime)
    const end = new Date(start.getTime() + 60 * 60 * 1000)
    const session = await scheduleStore.bookSession({
      teacherId: myId.value,
      studentId: schedForm.studentId,
      startTime: start.toISOString(),
      endTime: end.toISOString(),
    })
    if (schedForm.homework && session) {
      await interactionsStore.assignHomework(session.id, schedForm.homework)
    }
    toast.success('Session scheduled!', 'Your student has been notified.')
    showScheduleModal.value = false
    Object.assign(schedForm, { studentId: '', startTime: '', homework: '' })
  } catch {
    toast.error('Scheduling failed', 'Please check the details and try again.')
  }
}

async function completeSession(sessionId: string) {
  try {
    const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    await axios.put(`${API_URL}/sessions/${sessionId}`, {
      status: 'completed',
      teacher_id: parseInt(myId.value),
      student_id: parseInt(mySessions.value.find(s => s.id === sessionId)?.studentId ?? '0'),
      start_time: mySessions.value.find(s => s.id === sessionId)?.startTime,
      end_time: mySessions.value.find(s => s.id === sessionId)?.endTime,
    })
    const s = scheduleStore.allSessions.find(x => x.id === sessionId)
    if (s) s.status = 'completed'
    toast.success('Session complete!', 'Well done, Maestro.')
  } catch {
    toast.error('Could not complete session', 'Please try again.')
  }
}

async function handleProofUpload(sessionId: string, event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.[0]) return
  await interactionsStore.uploadImageProof(sessionId, input.files[0])
}
</script>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>

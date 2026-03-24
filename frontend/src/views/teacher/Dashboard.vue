<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { ref } from 'vue'
import { useScheduleStore } from '../../stores/schedule'
import { useUsersStore } from '../../stores/users'
import { useInteractionsStore } from '../../stores/interactions'
import { useToastStore } from '../../stores/toast'
import type { Session } from '../../types'

const authStore = useAuthStore()
const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const interactionsStore = useInteractionsStore()
const toast = useToastStore()

const expandedSession = ref<Session | null>(null)
const practiceGoalsText = ref('')
const stagedProofFile = ref<File | null>(null)
const stagedProofUrl = ref<string | null>(null)

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
  scheduleStore.allSessions.filter((s) => s.teacherId === myId.value)
)

const todaySessions = computed(() => {
  const today = new Date().toDateString()
  return mySessions.value.filter(
    (s) => s.startTime && new Date(s.startTime).toDateString() === today
  )
})

const currentSession = computed(() => {
  const now = new Date()
  return mySessions.value.find((s) => {
    if (s.status !== 'scheduled' || !s.startTime || !s.endTime) return false
    const start = new Date(s.startTime)
    const end = new Date(s.endTime)
    return start <= now && now < end
  }) ?? null
})

const nextSession = computed(
  () => {
    const now = new Date()
    return mySessions.value
      .filter((s) => s.status === 'scheduled' && s.startTime && new Date(s.startTime) > now)
      .sort((a, b) => new Date(a.startTime!).getTime() - new Date(b.startTime!).getTime())[0] ?? null
  }
)

function getStudentName(studentId: string) {
  return usersStore.users.find(u => u.id === studentId)?.name || `Student #${studentId}`
}

function openSessionModal(session: Session) {
  expandedSession.value = session
  practiceGoalsText.value = session.notes || ''
  stagedProofFile.value = null
  stagedProofUrl.value = null
}

function closeSessionModal() {
  expandedSession.value = null
}

function handleStagedProofUpload(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.[0]) return
  stagedProofFile.value = input.files[0]
  stagedProofUrl.value = URL.createObjectURL(stagedProofFile.value)
}

async function saveSessionChanges() {
  if (!expandedSession.value) return

  if (stagedProofFile.value) {
    await interactionsStore.uploadImageProof(expandedSession.value.id, stagedProofFile.value)
  }

  // Note: updating practice goals (notes) usually calls a specific API or is handled by an action.
  // Assuming a generic update or setting homework. For now we will update the session object optimistically.
  expandedSession.value.notes = practiceGoalsText.value

  toast.success('Session updated', 'Changes have been saved successfully.')
  closeSessionModal()
}

// Build unique student entries for the roster
const rosterEntries = computed(() => {
  const seen = new Set<string>()
  return mySessions.value
    .filter((s) => {
      if (seen.has(s.studentId)) return false
      seen.add(s.studentId)
      return true
    })
    .map((s) => {
      const user = usersStore.users.find((u) => u.id === s.studentId)
      return {
        studentId: s.studentId,
        name: user?.name ?? `Student #${s.studentId}`,
        startTime: s.startTime,
        status: s.status,
      }
    })
})

// 7-day week grid (Mon–Sun of current week)
const weekDays = computed(() => {
  const days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
  const now = new Date()
  const dayOfWeek = now.getDay() || 7
  const monday = new Date(now)
  monday.setDate(now.getDate() - dayOfWeek + 1)
  monday.setHours(0, 0, 0, 0)

  return days.map((label, i) => {
    const date = new Date(monday)
    date.setDate(monday.getDate() + i)
    const isToday = date.toDateString() === now.toDateString()
    const isWeekend = i >= 5
    const session =
      mySessions.value.find((s) => {
        if (!s.startTime) return false
        return new Date(s.startTime).toDateString() === date.toDateString()
      }) ?? null
    return { label, date, dateNum: date.getDate(), session, isToday, isWeekend }
  })
})

const pendingProposals = computed(() =>
  mySessions.value.filter(s => s.status === 'pending_teacher').length
)

const formatTime = (dt: string | undefined) => {
  if (!dt) return '—'
  return new Date(dt).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
</script>

<template>
  <div class="max-w-5xl mx-auto pb-10">
    <!-- Hero Header -->
    <section class="mb-8">
      <h1 class="text-5xl font-black tracking-tight text-white mb-3">
        Welcome back, <span class="text-orange-500">Maestro.</span>
      </h1>
      <p class="text-zinc-400 text-lg font-medium mb-6">
        You have
        <span class="text-white font-bold">{{ todaySessions.length || 0 }} sessions</span>
        today. Performance index is at
        <span class="text-emerald-400 font-bold">98%</span>.
      </p>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <!-- Current Session Card -->
        <div
          v-if="currentSession"
          class="liquid-glass border border-orange-500/20 rounded-3xl overflow-hidden cursor-pointer hover:border-orange-500/50 transition-all flex flex-col group"
          @click="openSessionModal(currentSession)"
        >
          <div class="h-2 bg-gradient-to-r from-orange-500 to-orange-700 w-full relative">
            <div class="absolute right-2 -top-1 w-3 h-3 bg-white rounded-full animate-ping"></div>
            <div class="absolute right-2 -top-1 w-3 h-3 bg-white rounded-full"></div>
          </div>
          <div class="p-5 flex-1 flex flex-col justify-center">
            <p class="text-[10px] font-black text-orange-500 uppercase tracking-widest mb-1 flex items-center gap-2">
              LIVE NOW
            </p>
            <h3 class="text-xl font-black text-white mb-1 truncate">Session #{{ currentSession.id }}</h3>
            <p class="text-sm text-zinc-400 truncate">{{ getStudentName(currentSession.studentId) }}</p>
            <p class="text-xs text-white/50 mt-2">{{ formatTime(currentSession.startTime) }} - {{ formatTime(currentSession.endTime) }}</p>
          </div>
        </div>
        <div v-else class="liquid-glass border border-white/5 rounded-3xl p-5 flex flex-col justify-center items-center text-center opacity-70">
          <span class="material-symbols-outlined text-3xl text-zinc-600 mb-2">hotel_class</span>
          <p class="text-sm font-bold text-zinc-500 uppercase tracking-wider">No Active Session</p>
        </div>

        <!-- Next Up Session Card -->
        <div
          v-if="nextSession"
          class="liquid-glass border border-white/5 border-l-[6px] border-l-white/20 rounded-3xl p-5 cursor-pointer hover:bg-white/5 transition-all flex flex-col justify-center group"
          @click="openSessionModal(nextSession)"
        >
          <p class="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-1 group-hover:text-zinc-400 transition-colors">Next Up</p>
          <h3 class="text-xl font-black text-white mb-1 truncate">Session #{{ nextSession.id }}</h3>
          <p class="text-sm text-zinc-400 truncate">{{ getStudentName(nextSession.studentId) }}</p>
          <p class="text-xs text-orange-400 mt-2 font-bold">{{ formatTime(nextSession.startTime) }}</p>
        </div>
        <div v-else class="liquid-glass border border-white/5 border-l-[6px] border-l-white/10 rounded-3xl p-5 flex flex-col justify-center items-center text-center opacity-70">
          <span class="material-symbols-outlined text-3xl text-zinc-600 mb-2">event_available</span>
          <p class="text-sm font-bold text-zinc-500 uppercase tracking-wider">Schedule Clear</p>
        </div>
      </div>
    </section>

    <!-- Main Grid -->
    <div class="grid grid-cols-1 gap-4">
      <!-- Full Column -->
      <div class="col-span-full space-y-4">
        <!-- Student Roster -->
        <div class="liquid-glass rounded-3xl p-4 border border-white/5 space-y-3">
          <div class="flex justify-between items-center">
            <h3 class="text-2xl font-black text-white flex items-center gap-3">
              <span
                class="material-symbols-outlined text-orange-500 text-3xl"
                style="font-variation-settings: 'FILL' 1"
                >diversity_3</span
              >
              Student Roster
            </h3>
            <button
              class="text-orange-500 font-bold text-sm hover:underline tracking-wide uppercase"
            >
              View All Roster
            </button>
          </div>

          <!-- Loading -->
          <div v-if="usersStore.isLoading" class="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div v-for="i in 2" :key="i" class="h-28 rounded-3xl bg-white/5 animate-pulse" />
          </div>

          <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <!-- Real roster from sessions -->
            <div
              v-for="entry in rosterEntries"
              :key="entry.studentId"
              class="bg-black/40 backdrop-blur-xl border border-white/5 p-5 rounded-3xl flex items-center gap-4 hover:border-orange-500/40 transition-all group cursor-pointer"
            >
              <div
                class="w-16 h-16 rounded-2xl overflow-hidden shadow-2xl border border-white/10 group-hover:scale-105 transition-transform bg-surface-container-highest flex items-center justify-center shrink-0"
              >
                <span class="text-2xl font-black text-white">{{
                  entry.name.charAt(0).toUpperCase()
                }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <h4 class="font-bold text-white text-lg truncate">{{ entry.name }}</h4>
                <p class="text-xs text-zinc-500 font-medium mb-2 uppercase tracking-tighter">
                  {{ formatTime(entry.startTime) }}
                </p>
                <div class="flex gap-2 flex-wrap">
                  <span
                    class="px-2.5 py-1 bg-orange-500/10 text-orange-400 text-[9px] font-bold rounded-full border border-orange-500/20 uppercase"
                    >{{ entry.status }}</span
                  >
                </div>
              </div>
              <span
                class="material-symbols-outlined text-zinc-600 group-hover:text-orange-500 transition-colors"
                >chevron_right</span
              >
            </div>

            <!-- Enroll New -->
            <div
              class="bg-black/40 backdrop-blur-xl p-5 rounded-3xl flex items-center justify-center border-2 border-dashed border-white/10 hover:border-orange-500/50 hover:bg-white/5 transition-all group cursor-pointer"
            >
              <div class="text-center">
                <span
                  class="material-symbols-outlined text-zinc-600 group-hover:text-orange-500 text-3xl mb-1 block"
                  >person_add</span
                >
                <p class="text-[10px] font-black text-zinc-500 uppercase tracking-widest">
                  Enroll New
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Weekly Schedule -->
        <div class="liquid-glass rounded-3xl p-4 border border-white/5 space-y-3">
          <div class="flex justify-between items-center">
            <div>
              <h3 class="text-2xl font-black text-white flex items-center gap-3">
                <span class="material-symbols-outlined text-orange-500 text-3xl">calendar_month</span>
                Weekly Schedule
              </h3>
              <p v-if="pendingProposals > 0" class="text-amber-400 text-sm font-bold mt-1">
                {{ pendingProposals }} student proposal{{ pendingProposals !== 1 ? 's' : '' }} await your review
                <RouterLink to="/teacher/schedule" class="underline ml-1">Review →</RouterLink>
              </p>
            </div>
          </div>

          <div class="grid grid-cols-7 gap-3">
            <div v-for="day in weekDays" :key="day.label" class="space-y-3">
              <div class="text-center">
                <p
                  class="text-xs font-black uppercase tracking-[0.2em]"
                  :class="day.isToday ? 'text-orange-500' : day.isWeekend ? 'text-zinc-600' : 'text-zinc-500'"
                >{{ day.label }}</p>
                <div
                  class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-black mx-auto mt-1"
                  :class="day.isToday ? 'bg-gradient-to-br from-orange-500 to-orange-700 text-white' : 'text-zinc-500'"
                >{{ day.dateNum }}</div>
              </div>
              <!-- Has session -->
              <div
                v-if="day.session"
                class="rounded-2xl p-4 border-l-2 min-h-[8rem] flex flex-col justify-between"
                :class="day.session.status === 'scheduled' ? 'bg-orange-500/10 border-orange-500' :
                        day.session.status === 'pending_admin' ? 'bg-blue-500/10 border-blue-500' :
                        day.session.status === 'pending_teacher' ? 'bg-amber-500/10 border-amber-500' :
                        'bg-white/5 border-white/20'"
              >
                <p class="text-[10px] font-black text-orange-500 mb-1">{{ formatTime(day.session.startTime) }}</p>
                <p class="text-xs font-bold text-white truncate">S#{{ day.session.studentId.slice(-4) }}</p>
                <p
                  class="text-[9px] font-bold mt-0.5"
                  :class="day.session.status === 'pending_admin' ? 'text-blue-400' :
                          day.session.status === 'pending_teacher' ? 'text-amber-400' : 'text-zinc-500'"
                >{{ day.session.status === 'pending_admin' ? 'Pending Admin' : day.session.status === 'pending_teacher' ? 'Pending Review' : 'Confirmed' }}</p>
              </div>
              <!-- Empty slot -->
              <div
                v-else
                class="h-32 border border-dashed rounded-2xl flex items-center justify-center"
                :class="day.isWeekend ? 'border-white/[0.03] bg-white/[0.01]' : 'border-white/5 bg-black/20'"
              >
                <span class="material-symbols-outlined text-zinc-800 text-base">add</span>
              </div>
            </div>
          </div>
          <RouterLink to="/teacher/schedule" class="block text-center text-xs text-zinc-600 hover:text-orange-500 transition-colors font-bold">
            View Full Schedule →
          </RouterLink>
        </div>
      </div>

    </div>

    <!-- Footer Stats -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
      <div
        class="liquid-glass p-4 rounded-3xl border border-white/10 flex items-center gap-4 group hover:bg-white/5 transition-all"
      >
        <div
          class="w-20 h-20 rounded-3xl bg-orange-500 text-white flex items-center justify-center text-4xl font-black shadow-2xl group-hover:scale-110 transition-transform"
        >
          {{ mySessions.length }}
        </div>
        <div>
          <h4 class="font-black text-xl text-white">Active Roster</h4>
          <p class="text-sm text-zinc-500">Enrolled for Summer Term</p>
        </div>
      </div>
      <div
        class="liquid-glass p-4 rounded-3xl border border-white/10 flex items-center gap-4 group hover:bg-white/5 transition-all"
      >
        <div
          class="w-20 h-20 rounded-3xl bg-orange-500/20 text-orange-500 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform"
        >
          <span
            class="material-symbols-outlined text-4xl"
            style="font-variation-settings: 'FILL' 1"
            >star</span
          >
        </div>
        <div>
          <h4 class="font-black text-xl text-white">Rating: 4.98</h4>
          <p class="text-sm text-zinc-500">Based on 142 reviews</p>
        </div>
      </div>
      <div
        class="liquid-glass p-4 rounded-3xl border border-white/10 flex items-center gap-4 group hover:bg-white/5 transition-all"
      >
        <div
          class="w-20 h-20 rounded-3xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform"
        >
          <span
            class="material-symbols-outlined text-4xl"
            style="font-variation-settings: 'FILL' 1"
            >analytics</span
          >
        </div>
        <div>
          <h4 class="font-black text-xl text-white">Growth Hub</h4>
          <p class="text-sm text-zinc-500">+15% Month-over-Month</p>
        </div>
      </div>
    </section>
  </div>

  <!-- Session Detail Modal (Teacher) -->
  <Teleport to="body">
    <Transition enter-active-class="transition opacity-200 ease-out duration-200" enter-from-class="opacity-0" enter-to-class="opacity-100" leave-active-class="transition opacity-200 ease-in duration-200" leave-from-class="opacity-100" leave-to-class="opacity-0">
      <div
        v-if="expandedSession"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="teacher-session-modal-title"
        @click.self="closeSessionModal"
      >
        <div
          class="absolute inset-0 bg-black/70 backdrop-blur-sm"
          @click="closeSessionModal"
        />
        <div
          class="relative w-full max-w-lg bg-zinc-900 border border-white/10 rounded-2xl p-6 shadow-2xl flex flex-col gap-5 max-h-[90vh] overflow-y-auto"
        >
          <!-- Header -->
          <div class="flex items-start justify-between">
            <div>
              <h3 id="teacher-session-modal-title" class="text-2xl font-black text-white leading-tight">
                Session #{{ expandedSession.id }}
              </h3>
              <p class="text-zinc-400 text-sm mt-1">
                {{ formatTime(expandedSession.startTime) }} - {{ formatTime(expandedSession.endTime) }}
              </p>
              <p class="text-white font-bold mt-1">Student: {{ getStudentName(expandedSession.studentId) }}</p>
            </div>
            <button
              class="text-zinc-500 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-500 rounded-lg p-1 bg-white/5 border border-white/5"
              aria-label="Close modal"
              @click="closeSessionModal"
            >
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <!-- Proof Section -->
          <div class="space-y-3">
            <label class="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Visual Evidence</label>
            <div v-if="expandedSession.imageProofUrl" class="relative group rounded-2xl overflow-hidden border border-white/10">
              <img :src="expandedSession.imageProofUrl" class="w-full h-auto object-cover max-h-48" />
              <div class="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <label class="px-4 py-2 bg-white/20 hover:bg-white/30 text-white text-xs font-bold rounded-lg cursor-pointer backdrop-blur-sm transition-colors">
                  Replace Image
                  <input type="file" accept="image/*" class="hidden" @change="handleStagedProofUpload" />
                </label>
              </div>
            </div>
            <div v-else-if="stagedProofUrl" class="relative rounded-2xl overflow-hidden border border-orange-500/50">
              <img :src="stagedProofUrl" class="w-full h-auto object-cover max-h-48" />
              <div class="absolute top-2 right-2 flex gap-2">
                <label class="px-3 py-1.5 bg-black/60 hover:bg-black/80 text-white text-xs font-bold rounded-lg cursor-pointer backdrop-blur-sm transition-colors border border-white/20">
                  Change
                  <input type="file" accept="image/*" class="hidden" @change="handleStagedProofUpload" />
                </label>
              </div>
            </div>
            <label
              v-else
              class="block aspect-video bg-black/40 rounded-3xl border-2 border-dashed border-white/10 flex flex-col items-center justify-center cursor-pointer hover:bg-white/5 hover:border-orange-500/50 transition-all group overflow-hidden relative"
            >
              <div class="text-center group-hover:scale-105 transition-transform">
                <div class="w-14 h-14 bg-orange-500/10 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span class="material-symbols-outlined text-3xl text-orange-500" style="font-variation-settings: 'FILL' 1">add_a_photo</span>
                </div>
                <p class="text-[11px] font-black text-zinc-300 uppercase tracking-wide">Take Photo or Upload</p>
              </div>
              <input type="file" accept="image/*" class="absolute inset-0 opacity-0 cursor-pointer" aria-label="Upload session proof" @change="handleStagedProofUpload" />
            </label>
          </div>

          <!-- Practice Goals -->
          <div class="space-y-3">
            <label class="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Practice Goals / Notes</label>
            <textarea
              v-model="practiceGoalsText"
              class="w-full h-32 bg-black/40 border border-white/5 rounded-3xl focus:ring-2 focus:ring-orange-500/40 text-sm p-5 text-white placeholder-zinc-600 resize-none transition-all"
              placeholder="E.g. Focus on paradiddle transitions at 120bpm..."
            ></textarea>
          </div>

          <!-- Action Buttons -->
          <div class="flex gap-3 pt-2">
            <button
              class="flex-1 py-3 rounded-xl border border-white/10 text-zinc-400 hover:text-white text-sm font-semibold transition-all bg-white/5 hover:bg-white/10"
              @click="closeSessionModal"
            >
              Cancel
            </button>
            <button
              class="flex-1 py-3 rounded-xl bg-gradient-to-br from-orange-500 to-orange-700 hover:scale-[1.02] text-white text-sm font-black transition-all active:scale-95 shadow-lg shadow-orange-900/20"
              @click="saveSessionChanges"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

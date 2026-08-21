<script setup lang="ts">
import { useRouter } from 'vue-router'
import { computed, onMounted } from 'vue'
import { useAuthStore } from '@stores/auth'
import { ref } from 'vue'
import { useScheduleStore } from '@stores/schedule'
import { useUsersStore } from '@stores/users'
import { useInteractionsStore } from '@stores/interactions'
import { useToastStore } from '@stores/toast'
import type { Session } from '@types'
import ProposeSessionModal from '@components/ProposeSessionModal.vue'

const router = useRouter()
const authStore = useAuthStore()
const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const interactionsStore = useInteractionsStore()
const toast = useToastStore()

const expandedSession = ref<Session | null>(null)
const showProposeModal = ref(false)
const proposeForDate = ref<Date | undefined>(undefined)
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

const myId = computed(() => authStore.currentUser?.id ?? 0)

const mySessions = computed(() =>
  scheduleStore.allSessions.filter((s: any) => s.teacherId === myId.value)
)

const todaySessions = computed(() => {
  const today = new Date().toDateString()
  return mySessions.value.filter(
    (s: any) => s.startTime && new Date(s.startTime).toDateString() === today
  )
})

const currentSession = computed(() => {
  const now = new Date()
  return (
    mySessions.value.find((s: any) => {
      if (s.status !== 'scheduled' || !s.startTime || !s.endTime) return false
      const start = new Date(s.startTime)
      const end = new Date(s.endTime)
      return start <= now && now < end
    }) ?? null
  )
})

const nextSession = computed(() => {
  const now = new Date()
  return (
    mySessions.value
      .filter((s: any) => s.status === 'scheduled' && s.startTime && new Date(s.startTime) > now)
      .sort((a: any, b: any) => new Date(a.startTime!).getTime() - new Date(b.startTime!).getTime())[0] ??
    null
  )
})

const getStudentName = function(studentId: number) {
  return usersStore.users.find((u: any) => u.id === studentId)?.name || `Student #${studentId}`
}

const openSessionModal = function(session: Session) {
  expandedSession.value = session
  practiceGoalsText.value = session.notes || ''
  stagedProofFile.value = null
  stagedProofUrl.value = null
}

const closeSessionModal = function() {
  expandedSession.value = null
}

const handleStagedProofUpload = function(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.[0]) return
  stagedProofFile.value = input.files[0]
  stagedProofUrl.value = window.URL.createObjectURL(stagedProofFile.value)
}

const saveSessionChanges = async function() {
  if (!expandedSession.value) return

  try {
    if (stagedProofFile.value) {
      await interactionsStore.uploadImageProof(expandedSession.value.id, stagedProofFile.value)
    }

    // Call editSession to persist notes (practice goals) to the backend
    await scheduleStore.editSession(expandedSession.value.id, {
      notes: practiceGoalsText.value
    })

    toast.success('Session updated', 'Changes have been saved successfully.')
    closeSessionModal()
    // Refresh sessions to reflect changes
    if (authStore.currentUser?.id) {
       await scheduleStore.fetchUserSessions(authStore.currentUser.id)
    }
  } catch (err: any) {
    toast.error('Update Failed', err.message || 'Could not save changes.')
  }
}

const handleApprove = async function(sessionId: number) {
  try {
    await scheduleStore.approveAsTeacher(sessionId)
    toast.success('Approved!', 'The session is now awaiting admin confirmation.')
    closeSessionModal()
    await scheduleStore.fetchUserSessions(myId.value)
  } catch {
    toast.error('Failed to approve')
  }
}

const handleReject = async function(sessionId: number, notes?: string) {
  try {
    await scheduleStore.rejectAsTeacher(sessionId, notes)
    toast.success('Declined', 'The student has been notified.')
    closeSessionModal()
    await scheduleStore.fetchUserSessions(myId.value)
  } catch {
    toast.error('Failed to decline')
  }
}

const showCounterModal = ref(false)
const counterForm = ref({ startTime: '', endTime: '', notes: '' })

const openCounter = function() {
  if (!expandedSession.value) return
  counterForm.value = {
    startTime: expandedSession.value.startTime.slice(0, 16),
    endTime: expandedSession.value.endTime?.slice(0, 16) || '',
    notes: 'Suggesting a different time.'
  }
  showCounterModal.value = true
}

const submitCounter = async function() {
  if (!expandedSession.value) return
  try {
    const start = new Date(counterForm.value.startTime).toISOString()
    const end = counterForm.value.endTime 
        ? new Date(counterForm.value.endTime).toISOString()
        : new Date(new Date(start).getTime() + 60*60*1000).toISOString()
        
    await scheduleStore.counterAsTeacher(expandedSession.value.id, {
      startTime: start,
      endTime: end,
      notes: counterForm.value.notes
    })
    toast.success('Counter sent!', 'Awaiting student review.')
    showCounterModal.value = false
    closeSessionModal()
    await scheduleStore.fetchUserSessions(myId.value)
  } catch {
    toast.error('Failed to send counter')
  }
}

// Build unique student entries for the roster
const rosterEntries = computed(() => {
  const seen = new Set<number>()
  return mySessions.value
    .filter((s: any) => {
      if (seen.has(s.studentId)) return false
      seen.add(s.studentId)
      return true
    })
    .map((s: any) => {
      const user = usersStore.users.find((u: any) => u.id === s.studentId)
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
      mySessions.value.find((s: any) => {
        if (!s.startTime) return false
        return new Date(s.startTime).toDateString() === date.toDateString()
      }) ?? null
    return { label, date, dateNum: date.getDate(), session, isToday, isWeekend }
  })
})

const pendingProposals = computed(
  () => mySessions.value.filter((s: any) => s.status === 'pending_teacher').length
)

const students = computed(() => usersStore.getUsersByRole('student'))

const openProposeForDate = function(date: Date) {
  proposeForDate.value = date
  showProposeModal.value = true
}

const openRosterSession = function(studentId: number) {
  const sessions = mySessions.value.filter((s: any) => s.studentId === studentId)
  if (sessions.length === 0) return
  const now = new Date()
  const upcoming = sessions
    .filter((s: any) => s.startTime && new Date(s.startTime) > now)
    .sort((a: any, b: any) => new Date(a.startTime!).getTime() - new Date(b.startTime!).getTime())
  const target =
    upcoming[0] ??
    [...sessions].sort((a: any, b: any) => new Date(b.startTime!).getTime() - new Date(a.startTime!).getTime())[0]
  openSessionModal(target)
}

const onTeacherProposeSubmit = async function(session: Session) {
  try {
    await scheduleStore.proposeSessionAsTeacher({
      teacherId: session.teacherId,
      studentId: session.studentId,
      startTime: session.startTime,
      endTime: session.endTime,
      notes: session.notes,
    })
    toast.success('Session proposed!', 'Awaiting admin approval.')
    showProposeModal.value = false
    if (authStore.currentUser?.id) {
      await scheduleStore.fetchUserSessions(authStore.currentUser.id)
    }
  } catch {
    toast.error('Failed to propose', 'Please check the details and try again.')
  }
}

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
  <div class="w-full mx-auto pb-10">
    <!-- Hero Header -->
    <section class="mb-8">
      <h1 class="text-5xl font-semibold tracking-tight text-on-surface dark:text-on-surface mb-3">
        Welcome back, <span class="text-primary">Maestro.</span>
      </h1>
      <p class="text-on-surface-variant dark:text-on-surface-variant text-lg font-medium mb-6">
        You have
        <span class="text-on-surface dark:text-on-surface font-bold">{{ todaySessions.length || 0 }} sessions</span>
        today. Performance index is at
        <span class="text-emerald-400 font-bold">98%</span>.
      </p>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <!-- Current Session Card -->
        <div
          v-if="currentSession"
          class="liquid-glass border border-primary/20 rounded-3xl overflow-hidden cursor-pointer hover:border-primary/50 transition-all flex flex-col group"
          @click="openSessionModal(currentSession)"
        >
          <div class="h-2 bg-primary w-full relative">
            <div class="absolute right-2 -top-1 size-3 bg-surface-container-lowest rounded-full animate-ping"></div>
            <div class="absolute right-2 -top-1 size-3 bg-surface-container-lowest rounded-full"></div>
          </div>
          <div class="p-4 flex-1 flex flex-col justify-center">
            <p
              class="text-xs font-semibold text-primary uppercase mb-1 flex items-center gap-2"
            >
              LIVE NOW
            </p>
            <h3 class="text-xl font-semibold text-on-surface dark:text-on-surface mb-1 truncate">
              Session #{{ currentSession.id }}
            </h3>
            <p class="text-sm text-on-surface-variant dark:text-on-surface-variant truncate">
              {{ getStudentName(currentSession.studentId) }}
            </p>
            <p class="text-xs text-on-surface-variant dark:text-on-surface-variant mt-2">
              {{ formatTime(currentSession.startTime) }} - {{ formatTime(currentSession.endTime) }}
            </p>
          </div>
        </div>
        <div
          v-else
          class="liquid-glass border border-on-surface/[0.04] dark:border-on-surface/5 rounded-3xl p-4 flex flex-col justify-center items-center text-center opacity-70"
        >
          <span class="material-symbols-outlined text-3xl text-on-surface-variant dark:text-on-surface-variant mb-2">hotel_class</span>
          <p class="text-sm font-bold text-on-surface-variant dark:text-on-surface-variant uppercase">No Active Session</p>
        </div>

        <!-- Next Up Session Card -->
        <div
          v-if="nextSession"
          class="liquid-glass border border-on-surface/[0.04] dark:border-on-surface/5 border-l-[6px] border-l-outline-variant dark:border-l-on-surface/20 rounded-3xl p-4 cursor-pointer hover:bg-on-surface/5 dark:hover:bg-on-surface/5 transition-all flex flex-col justify-center group"
          @click="openSessionModal(nextSession)"
        >
          <p
            class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase mb-1 group-hover:text-on-surface-variant transition-colors"
          >
            Next Up
          </p>
          <h3 class="text-xl font-semibold text-on-surface dark:text-on-surface mb-1 truncate">Session #{{ nextSession.id }}</h3>
          <p class="text-sm text-on-surface-variant dark:text-on-surface-variant truncate">{{ getStudentName(nextSession.studentId) }}</p>
          <p class="text-xs text-primary mt-2 font-bold">
            {{ formatTime(nextSession.startTime) }}
          </p>
        </div>
        <div
          v-else
          class="liquid-glass border border-on-surface/[0.04] dark:border-on-surface/5 border-l-[6px] border-l-outline-variant dark:border-l-on-surface/10 rounded-3xl p-4 flex flex-col justify-center items-center text-center opacity-70"
        >
          <span class="material-symbols-outlined text-3xl text-on-surface-variant dark:text-on-surface-variant mb-2">event_available</span>
          <p class="text-sm font-bold text-on-surface-variant dark:text-on-surface-variant uppercase">Schedule Clear</p>
        </div>
      </div>
    </section>

    <!-- Main Grid -->
    <div class="grid grid-cols-1 gap-4">
      <!-- Full Column -->
      <div class="col-span-full space-y-4">
        <!-- Student Roster -->
        <div class="liquid-glass rounded-3xl p-4 border border-on-surface/[0.04] dark:border-on-surface/5 space-y-3">
          <div class="flex justify-between items-center">
            <h3 class="text-2xl font-semibold text-on-surface dark:text-on-surface flex items-center gap-3">
              <span
                class="material-symbols-outlined text-primary text-3xl"
                style="font-variation-settings: 'FILL' 1"
                >diversity_3</span
              >
              Student Roster
            </h3>
            <button
              class="text-primary font-bold text-sm hover:underline tracking-wide uppercase"
              @click="router.push('/teacher/students')"
            >
              View All Roster
            </button>
          </div>

          <!-- Loading -->
          <div v-if="usersStore.isLoading" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div v-for="i in 2" :key="i" class="h-28 rounded-3xl bg-on-surface/[0.04] dark:bg-on-surface/5 animate-pulse" />
          </div>

          <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <!-- Real roster from sessions -->
            <div
              v-for="entry in rosterEntries"
              :key="entry.studentId"
              class="bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.04] dark:border-on-surface/5 p-4 rounded-3xl flex items-center gap-4 hover:border-primary/40 transition-all group cursor-pointer"
              @click="openRosterSession(entry.studentId)"
            >
              <div
                class="size-16 rounded-2xl overflow-hidden shadow-2xl border border-on-surface/[0.08] dark:border-on-surface/10 group-hover:scale-105 transition-transform bg-surface-container-highest flex items-center justify-center shrink-0"
              >
                <span class="text-2xl font-semibold text-on-surface dark:text-on-surface">{{
                  entry.name.charAt(0).toUpperCase()
                }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <h4 class="font-bold text-on-surface dark:text-on-surface text-lg truncate">{{ entry.name }}</h4>
                <p class="text-xs text-on-surface-variant dark:text-on-surface-variant font-medium mb-2 uppercase tracking-tighter">
                  {{ formatTime(entry.startTime) }}
                </p>
                <div class="flex gap-2 flex-wrap">
                  <span
                    class="px-2 py-1 bg-primary/10 text-primary text-xs font-bold rounded-full border border-primary/20 uppercase"
                    >{{ entry.status }}</span
                  >
                </div>
              </div>
              <span
                class="material-symbols-outlined text-on-surface-variant dark:text-on-surface-variant group-hover:text-primary transition-colors"
                >chevron_right</span
              >
            </div>

            <!-- Enroll New -->
            <div
              class="bg-on-surface/[0.04] dark:bg-on-surface/5 p-4 rounded-3xl flex items-center justify-center border-2 border-dashed border-on-surface/[0.08] dark:border-on-surface/10 hover:border-primary/50 hover:bg-on-surface/[0.06] dark:hover:bg-on-surface/[0.08] transition-all group cursor-pointer"
            >
              <div class="text-center">
                <span
                  class="material-symbols-outlined text-on-surface-variant dark:text-on-surface-variant group-hover:text-primary text-3xl mb-1 block"
                  >person_add</span
                >
                <p class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase">
                  Enroll New
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Weekly Schedule -->
        <div class="liquid-glass rounded-3xl p-4 border border-on-surface/[0.04] dark:border-on-surface/5 space-y-3">
          <div class="flex justify-between items-center">
            <div>
              <h3 class="text-2xl font-semibold text-on-surface dark:text-on-surface flex items-center gap-3">
                <span class="material-symbols-outlined text-primary text-3xl"
                  >calendar_month</span
                >
                Weekly Schedule
              </h3>
              <p v-if="pendingProposals > 0" class="text-amber-400 text-sm font-bold mt-1">
                {{ pendingProposals }} student proposal{{ pendingProposals !== 1 ? 's' : '' }} await
                your review
                <RouterLink to="/teacher/schedule" class="underline ml-1">Review →</RouterLink>
              </p>
            </div>
          </div>

          <div class="grid grid-cols-7 gap-3">
            <div v-for="day in weekDays" :key="day.label" class="space-y-3">
              <div class="text-center">
                <p
                  class="text-xs font-semibold uppercase"
                  :class="day.isToday ? 'text-primary' : day.isWeekend ? 'text-on-surface-variant' : 'text-on-surface-variant'"
                >
                  {{ day.label }}
                </p>
                <div
                  class="size-8 rounded-full flex items-center justify-center text-sm font-semibold mx-auto mt-1"
                  :class="day.isToday ? 'bg-primary text-on-primary' : 'text-on-surface-variant'"
                >
                  {{ day.dateNum }}
                </div>
              </div>
              <!-- Has session -->
              <div
                v-if="day.session"
                class="rounded-2xl p-4 border-l-2 min-h-[8rem] flex flex-col justify-between cursor-pointer hover:opacity-80 transition-opacity"
                :class="day.session.status === 'scheduled' ? 'bg-primary/10 border-primary' : day.session.status === 'pending_admin' ? 'bg-blue-500/10 border-blue-500' : day.session.status === 'pending_teacher' ? 'bg-amber-500/10 border-amber-500' : 'bg-on-surface/5 dark:bg-on-surface/5 border-on-surface/10 dark:border-on-surface/20'"
                @click="day.session && openSessionModal(day.session)"
              >
                <p class="text-xs font-semibold text-primary mb-1">
                  {{ formatTime(day.session.startTime) }}
                </p>
                <p class="text-xs font-bold text-on-surface dark:text-on-surface truncate">
                  S#{{ day.session.studentId }}
                </p>
                <p
                  class="text-xs font-bold mt-0.5"
                  :class="day.session.status === 'pending_admin' ? 'text-blue-400' : day.session.status === 'pending_teacher' ? 'text-amber-400' : 'text-on-surface-variant'"
                >
                  {{
                    day.session.status === 'pending_admin'
                      ? 'Pending Admin'
                      : day.session.status === 'pending_teacher'
                        ? 'Pending Review'
                        : 'Confirmed'
                  }}
                </p>
              </div>
              <!-- Empty slot -->
              <div
                v-else
                class="h-32 border border-dashed rounded-2xl flex items-center justify-center cursor-pointer hover:border-primary/40 hover:bg-primary/5 transition-colors"
                :class="day.isWeekend ? 'border-on-surface/[0.04] dark:border-on-surface/[0.03] bg-on-surface/[0.02] dark:bg-on-surface/[0.01]' : 'border-on-surface/[0.06] dark:border-on-surface/5 bg-on-surface/[0.03] dark:bg-on-surface/20'"
                @click="openProposeForDate(day.date)"
              >
                <span class="material-symbols-outlined text-on-surface-variant text-base">add</span>
              </div>
            </div>
          </div>
          <RouterLink
            to="/teacher/schedule"
            class="block text-center text-xs text-on-surface-variant dark:text-on-surface-variant hover:text-primary transition-colors font-bold"
          >
            View Full Schedule →
          </RouterLink>
        </div>
      </div>
    </div>

    <!-- Footer Stats -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
      <div
        class="liquid-glass p-4 rounded-3xl border border-on-surface/[0.08] dark:border-on-surface/10 flex items-center gap-4 group hover:bg-on-surface/5 dark:hover:bg-on-surface/5 transition-all"
      >
        <div
          class="size-20 rounded-3xl bg-primary text-on-surface flex items-center justify-center text-4xl font-semibold shadow-2xl group-hover:scale-110 transition-transform"
        >
          {{ mySessions.length }}
        </div>
        <div>
          <h4 class="font-semibold text-xl text-on-surface dark:text-on-surface">Active Roster</h4>
          <p class="text-sm text-on-surface-variant dark:text-on-surface-variant">Enrolled for Summer Term</p>
        </div>
      </div>
      <div
        class="liquid-glass p-4 rounded-3xl border border-on-surface/[0.08] dark:border-on-surface/10 flex items-center gap-4 group hover:bg-on-surface/5 dark:hover:bg-on-surface/5 transition-all"
      >
        <div
          class="size-20 rounded-3xl bg-primary/20 text-primary flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform"
        >
          <span class="material-symbols-outlined text-4xl" style="font-variation-settings: 'FILL' 1"
            >star</span
          >
        </div>
        <div>
          <h4 class="font-semibold text-xl text-on-surface dark:text-on-surface">Rating: 4.98</h4>
          <p class="text-sm text-on-surface-variant dark:text-on-surface-variant">Based on 142 reviews</p>
        </div>
      </div>
      <div
        class="liquid-glass p-4 rounded-3xl border border-on-surface/[0.08] dark:border-on-surface/10 flex items-center gap-4 group hover:bg-on-surface/5 dark:hover:bg-on-surface/5 transition-all"
      >
        <div
          class="size-20 rounded-3xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform"
        >
          <span class="material-symbols-outlined text-4xl" style="font-variation-settings: 'FILL' 1"
            >analytics</span
          >
        </div>
        <div>
          <h4 class="font-semibold text-xl text-on-surface dark:text-on-surface">Growth Hub</h4>
          <p class="text-sm text-on-surface-variant dark:text-on-surface-variant">+15% Month-over-Month</p>
        </div>
      </div>
    </section>
  </div>

  <!-- Propose Session Modal -->
  <ProposeSessionModal
    v-if="showProposeModal"
    :is-open="showProposeModal"
    user-role="teacher"
    :current-user-id="myId"
    :teachers="[]"
    :students="students"
    :initial-date="proposeForDate"
    @close="showProposeModal = false"
    @submitted="onTeacherProposeSubmit"
  />

  <!-- Session Detail Modal (Teacher) -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition opacity-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition opacity-200 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="expandedSession"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="teacher-session-modal-title"
        @click.self="closeSessionModal"
      >
        <div class="absolute inset-0 bg-on-surface/30 dark:bg-on-surface/70" @click="closeSessionModal" />
        <div
          class="relative w-full max-w-lg bg-surface-container-high dark:bg-surface-container-high border border-outline-variant dark:border-outline-variant rounded-2xl p-6 shadow-2xl flex flex-col gap-4 max-h-[90vh] overflow-y-auto"
        >
          <!-- Header -->
          <div class="flex items-start justify-between">
            <div>
              <h3
                id="teacher-session-modal-title"
                class="text-2xl font-semibold text-on-surface dark:text-on-surface leading-tight"
              >
                Session #{{ expandedSession.id }}
              </h3>
              <p class="text-on-surface-variant dark:text-on-surface-variant text-sm mt-1">
                {{ formatTime(expandedSession.startTime) }} -
                {{ formatTime(expandedSession.endTime) }}
              </p>
              <p class="text-on-surface dark:text-on-surface font-bold mt-1">
                Student: {{ getStudentName(expandedSession.studentId) }}
              </p>
            </div>
            <button
              class="text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-500 rounded-lg p-1 bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.04] dark:border-on-surface/5"
              aria-label="Close modal"
              @click="closeSessionModal"
            >
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <!-- Proof Section -->
          <div class="space-y-3">
            <div class="flex items-center justify-between mb-2">
              <label class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase">Visual Evidence</label>
            </div>
            
            <div class="space-y-2 mb-4 bg-on-surface/[0.04] dark:bg-on-surface/5 p-3 rounded-xl border border-on-surface/[0.04] dark:border-on-surface/5">
              <div class="flex items-center justify-between text-sm">
                <span class="text-on-surface-variant">Your Proof</span>
                <span class="font-bold" :class="expandedSession.proofs?.some(p => p.uploaderRole === 'teacher') ? 'text-emerald-500' : 'text-amber-500'">
                  {{ expandedSession.proofs?.some(p => p.uploaderRole === 'teacher') ? 'Uploaded ✓' : 'Pending' }}
                </span>
              </div>
              <div class="flex items-center justify-between text-sm">
                <span class="text-on-surface-variant">Student's Proof</span>
                <span class="font-bold" :class="expandedSession.proofs?.some(p => p.uploaderRole === 'student') ? 'text-emerald-500' : 'text-amber-500'">
                  {{ expandedSession.proofs?.some(p => p.uploaderRole === 'student') ? 'Uploaded ✓' : 'Pending' }}
                </span>
              </div>
            </div>

            <div
              v-if="expandedSession.proofs?.some(p => p.uploaderRole === 'teacher')"
              class="relative group rounded-2xl overflow-hidden border border-on-surface/[0.08] dark:border-on-surface/10"
            >
              <img
                :src="expandedSession.proofs.find(p => p.uploaderRole === 'teacher')?.imageUrl"
                class="w-full h-auto object-cover max-h-48"
              />
              <div
                class="absolute inset-0 bg-on-surface/30 dark:bg-on-surface/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
              >
                <label
                  class="px-4 py-2 bg-on-surface/20 hover:bg-on-surface/10 dark:hover:bg-on-surface/30 text-on-surface dark:text-on-surface text-xs font-bold rounded-lg cursor-pointer transition-colors"
                >
                  Replace Image
                  <input
                    type="file"
                    accept="image/*"
                    class="hidden"
                    @change="handleStagedProofUpload"
                  />
                </label>
              </div>
            </div>
            <div
              v-else-if="stagedProofUrl"
              class="relative rounded-2xl overflow-hidden border border-primary/50"
            >
              <img :src="stagedProofUrl" class="w-full h-auto object-cover max-h-48" />
              <div class="absolute top-2 right-2 flex gap-2">
                <label
                  class="px-3 py-1.5 bg-on-surface/30 dark:bg-on-surface/60 hover:bg-on-surface/80 text-on-surface dark:text-on-surface text-xs font-bold rounded-lg cursor-pointer transition-colors border border-on-surface/20"
                >
                  Change
                  <input
                    type="file"
                    accept="image/*"
                    class="hidden"
                    @change="handleStagedProofUpload"
                  />
                </label>
              </div>
            </div>
            <label
              v-else
              class="aspect-video bg-on-surface/[0.04] dark:bg-on-surface/5 rounded-3xl border-2 border-dashed border-on-surface/[0.08] dark:border-on-surface/10 flex flex-col items-center justify-center cursor-pointer hover:bg-on-surface/[0.06] dark:hover:bg-on-surface/[0.08] hover:border-primary/50 transition-all group overflow-hidden relative"
            >
              <div class="text-center group-hover:scale-105 transition-transform">
                <div
                  class="size-14 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-3"
                >
                  <span
                    class="material-symbols-outlined text-3xl text-primary"
                    style="font-variation-settings: 'FILL' 1"
                    >add_a_photo</span
                  >
                </div>
                <p class="text-xs font-semibold text-on-surface-variant uppercase tracking-wide">
                  Take Photo or Upload
                </p>
              </div>
              <input
                type="file"
                accept="image/*"
                class="absolute inset-0 opacity-0 cursor-pointer"
                aria-label="Upload session proof"
                @change="handleStagedProofUpload"
              />
            </label>
          </div>


          <!-- Negotiation Buttons -->
          <div v-if="expandedSession.status === 'pending_teacher'" class="p-4 bg-primary/5 border border-primary/20 rounded-3xl space-y-3">
             <div class="flex items-center gap-2 mb-2">
                <span class="material-symbols-outlined text-primary text-sm">schedule_send</span>
                <span class="text-xs font-bold text-primary uppercase">Student Proposal</span>
             </div>
             <div class="flex gap-3">
                <button 
                  class="flex-1 py-3 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 font-bold rounded-2xl text-xs transition-all flex items-center justify-center gap-2"
                  @click="handleApprove(expandedSession.id)"
                >
                  <span class="material-symbols-outlined text-sm">check_circle</span>
                  Approve Time
                </button>
                <button 
                  class="flex-1 py-3 bg-primary/20 hover:bg-primary/30 border border-primary/30 text-primary font-bold rounded-2xl text-xs transition-all flex items-center justify-center gap-2"
                  @click="openCounter"
                >
                  <span class="material-symbols-outlined text-sm">edit_calendar</span>
                  Suggest Other
                </button>
             </div>
             <button 
                class="w-full py-2 text-red-500/60 hover:text-red-500 text-xs font-bold uppercase transition-colors"
                @click="handleReject(expandedSession.id, 'Time does not work for me.')"
             >
                Decline Request
             </button>
          </div>

          <!-- Practice Goals -->
          <div class="space-y-3">
            <label class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase"
              >Practice Goals / Notes</label
            >
            <textarea
              v-model="practiceGoalsText"
              class="input h-32 resize-none"
              placeholder="E.g. Focus on paradiddle transitions at 120bpm..."
            ></textarea>
          </div>

          <!-- Action Buttons -->
          <div class="flex gap-3 pt-2">
            <button
              class="flex-1 py-3 rounded-xl border border-on-surface/[0.08] dark:border-on-surface/10 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface text-sm font-semibold transition-all bg-on-surface/[0.04] dark:bg-on-surface/5 hover:bg-on-surface/5 dark:hover:bg-on-surface/10"
              @click="closeSessionModal"
            >
              Cancel
            </button>
            <button
              class="flex-1 py-3 rounded-xl bg-primary hover:scale-[1.02] text-on-primary text-sm font-semibold transition-all active:scale-95 shadow-lg"
              @click="saveSessionChanges"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Teacher Counter Modal -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition opacity-150 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition opacity-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="showCounterModal"
        class="fixed inset-0 z-[250] flex items-center justify-center p-4"
        @click.self="showCounterModal = false"
      >
        <div class="absolute inset-0 bg-on-surface/40" @click="showCounterModal = false" />
        <div class="relative w-full max-w-sm liquid-glass border border-on-surface/10 rounded-3xl p-6 space-y-4 shadow-2xl">
          <h3 class="text-lg font-semibold text-on-surface dark:text-on-surface">Suggest New Time</h3>
          <div class="space-y-4">
            <div>
              <label class="text-xs font-semibold uppercase text-on-surface-variant block mb-1">Start Time</label>
              <input v-model="counterForm.startTime" type="datetime-local" class="w-full bg-on-surface/20 border border-on-surface/10 rounded-xl px-4 py-3 text-sm [color-scheme:dark]" />
            </div>
            <div>
              <label class="text-xs font-semibold uppercase text-on-surface-variant block mb-1">Notes</label>
              <textarea v-model="counterForm.notes" rows="2" class="w-full bg-on-surface/20 border border-on-surface/10 rounded-xl px-4 py-3 text-sm resize-none"></textarea>
            </div>
            <div class="flex gap-3">
               <button class="flex-1 py-3 bg-primary text-on-surface font-bold rounded-2xl text-sm" @click="submitCounter">Send Proposal</button>
               <button class="px-4 py-3 bg-on-surface/5 text-on-surface-variant font-bold rounded-2xl text-sm" @click="showCounterModal = false">Cancel</button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

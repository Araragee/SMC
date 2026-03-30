<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useScheduleStore } from '../../stores/schedule'
import { useUsersStore } from '../../stores/users'
import { useAuthStore } from '../../stores/auth'
import { useNotificationStore } from '../../stores/notification'
import { useToastStore } from '../../stores/toast'
import BaseCalendar from '../../components/BaseCalendar.vue'
import SessionDetailModal from '../../components/SessionDetailModal.vue'
import ProposeSessionModal from '../../components/ProposeSessionModal.vue'
import type { Session } from '../../types'

const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()
const notifStore = useNotificationStore()
const toast = useToastStore()

const selectedDate = ref<Date | null>(null)
const selectedDaySessions = ref<Session[]>([])
const selectedSession = ref<Session | null>(null)
const showProposeModal = ref(false)
const rejectModal = ref({ open: false, sessionId: '', notes: '' })
const counterModal = ref({ open: false, sessionId: '', startTime: '', endTime: '', notes: '' })

const myId = computed(() => authStore.currentUser?.id ?? '')
const students = computed(() => usersStore.getUsersByRole('student'))
const allUsers = computed(() => usersStore.users)

const mySessions = computed(() =>
  scheduleStore.allSessions.filter((s) => s.teacherId === myId.value)
)

const studentProposals = computed(() =>
  mySessions.value.filter((s) => s.status === 'pending_teacher')
)

const upcomingSessions = computed(() => {
  const now = new Date()
  return mySessions.value
    .filter((s) => s.status === 'scheduled' && new Date(s.startTime) >= now)
    .sort((a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime())
    .slice(0, 10)
})

onMounted(async () => {
  await Promise.all([
    scheduleStore.fetchUserSessions(myId.value),
    usersStore.fetchUsersByRole('student'),
    usersStore.fetchUsersByRole('teacher'),
    notifStore.fetchNotifications(myId.value),
  ])
})

const getStudentName = function(id: string): string  {
  return usersStore.users.find((u) => u.id === id)?.name ?? `Student #${id}`
}

const onDayClick = function({ date, sessions }: { date: Date; sessions: Session[] }) {
  selectedDate.value = date
  selectedDaySessions.value = sessions
}

const onSessionClick = function(session: Session) {
  selectedSession.value = session
}

const handleApproveStudent = async function(sessionId: string) {
  try {
    await scheduleStore.approveAsTeacher(sessionId)
    toast.success('Request approved!', 'Forwarded to admin for final approval.')
    selectedDate.value = null
    await scheduleStore.fetchUserSessions(myId.value);
  } catch {
    toast.error('Failed to approve request')
  }
}

const openReject = function(sessionId: string) {
  rejectModal.value = { open: true, sessionId, notes: '' }
  selectedDate.value = null
}

const confirmReject = async function() {
  try {
    await scheduleStore.rejectAsTeacher(rejectModal.value.sessionId, rejectModal.value.notes)
    toast.success('Request declined', 'The student has been notified.')
    rejectModal.value.open = false
    await scheduleStore.fetchUserSessions(myId.value);
  } catch {
    toast.error('Failed to decline request')
  }
}

const openCounter = function(session: Session) {
  counterModal.value = {
    open: true,
    sessionId: session.id,
    startTime: session.startTime.slice(0, 16),
    endTime: session.endTime?.slice(0, 16) || '',
    notes: `Counter proposal: Original time didn't work for me.`
  }
}

const confirmCounter = async function() {
  try {
    const startTime = new Date(counterModal.value.startTime).toISOString();
    let endTime = '';
    if (counterModal.value.endTime) {
        endTime = new Date(counterModal.value.endTime).toISOString();
    } else {
        // Default to 1 hour after start if missing
        endTime = new Date(new Date(startTime).getTime() + 60 * 60 * 1000).toISOString();
    }

    await scheduleStore.counterAsTeacher(counterModal.value.sessionId, {
      startTime,
      endTime,
      notes: counterModal.value.notes
    })
    toast.success('Counter proposal sent!', 'The student has been notified.')
    counterModal.value.open = false
    await scheduleStore.fetchUserSessions(myId.value);
  } catch {
    toast.error('Failed to send counter proposal')
  }
}

const onProposeSubmit = async function(session: Session) {
  try {
    await scheduleStore.proposeSessionAsTeacher({
      teacherId: myId.value,
      studentId: session.studentId,
      startTime: session.startTime,
      endTime: session.endTime,
      notes: session.notes,
    })
    toast.success('Proposal submitted!', 'Awaiting admin approval.')
    showProposeModal.value = false
  } catch {
    toast.error('Failed to submit proposal')
  }
}

const formatDateTime = function(iso: string): string  {
  return new Date(iso).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

const formatTime = function(iso: string): string  {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

const formatMonth = function(iso: string): string  {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short' })
}

const formatDay = function(iso: string): string  {
  return String(new Date(iso).getDate())
}
</script>

<template>
  <div class="w-full mx-auto pb-28 space-y-4">
    <!-- Header -->
    <div
      class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 md:gap-6"
    >
      <div>
        <h1 class="text-5xl font-black tracking-tight text-on-surface dark:text-on-surface mb-2">My Schedule</h1>
        <p class="text-on-surface-variant dark:text-on-surface-variant font-medium">
          <span class="text-on-surface dark:text-on-surface font-bold">{{ mySessions.length }}</span> total sessions,
          <span class="text-amber-400 font-bold">{{ studentProposals.length }}</span> student
          proposals awaiting review.
        </p>
      </div>
      <div class="shrink-0 flex items-start gap-4">
        <button
          class="px-6 py-3 bg-gradient-to-br from-orange-500 to-orange-700 text-white font-bold rounded-3xl shadow-lg shadow-orange-900/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2"
          @click="showProposeModal = true"
        >
          <span class="material-symbols-outlined text-lg">add_circle</span>
          Propose Session
        </button>
      </div>
    </div>

    <!-- Student Proposals Panel -->
    <section
      v-if="studentProposals.length > 0"
      class="liquid-glass rounded-3xl p-6 border border-amber-500/20"
    >
      <div class="flex items-center gap-3 mb-5">
        <div class="w-10 h-10 rounded-2xl bg-amber-500/20 flex items-center justify-center">
          <span
            class="material-symbols-outlined text-amber-400"
            style="font-variation-settings: 'FILL' 1"
            >pending_actions</span
          >
        </div>
        <div>
          <h3 class="text-lg font-black text-on-surface dark:text-on-surface">Student Proposals</h3>
          <p class="text-on-surface-variant dark:text-on-surface-variant text-sm">
            {{ studentProposals.length }} request{{ studentProposals.length !== 1 ? 's' : '' }}
            awaiting your review
          </p>
        </div>
      </div>

      <div class="space-y-3">
        <div
          v-for="session in studentProposals"
          :key="session.id"
          class="flex items-center gap-4 p-4 rounded-2xl bg-amber-500/5 border border-amber-500/20"
        >
          <div
            class="w-10 h-10 rounded-full bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400 font-black text-sm shrink-0"
          >
            {{ getStudentName(session.studentId).charAt(0) }}
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-on-surface dark:text-on-surface font-bold text-sm">{{ getStudentName(session.studentId) }}</p>
            <p class="text-on-surface-variant dark:text-on-surface-variant text-xs">{{ formatDateTime(session.startTime) }}</p>
            <p v-if="session.notes" class="text-on-surface-variant dark:text-on-surface-variant text-xs mt-0.5 italic">
              "{{ session.notes }}"
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button
              class="px-4 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-xs font-bold transition-all flex items-center gap-1.5"
              @click="handleApproveStudent(session.id)"
            >
              <span class="material-symbols-outlined text-sm">check_circle</span>
              Approve
            </button>
            <button
              class="px-4 py-2 rounded-xl bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/30 text-orange-400 text-xs font-bold transition-all flex items-center gap-1.5"
              @click="openCounter(session)"
            >
              <span class="material-symbols-outlined text-sm">swap_horiz</span>
              Counter
            </button>
            <button
              class="px-4 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 text-xs font-bold transition-all flex items-center gap-1.5"
              @click="openReject(session.id)"
            >
              <span class="material-symbols-outlined text-sm">cancel</span>
              Decline
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- Weekly Calendar -->
    <section class="liquid-glass rounded-3xl p-4 border border-black/[0.04] dark:border-white/5">
      <h3 class="text-xl font-black text-on-surface dark:text-on-surface flex items-center gap-3 mb-6">
        <span class="w-10 h-10 rounded-2xl bg-teal-500/10 flex items-center justify-center text-teal-500">
          <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1">calendar_month</span>
        </span>
        Weekly Schedule
      </h3>
      <BaseCalendar :sessions="mySessions" @day-click="onDayClick" @session-click="onSessionClick" />
    </section>

    <!-- Upcoming Confirmed Sessions -->
    <section class="liquid-glass rounded-3xl p-4 border border-black/[0.04] dark:border-white/5">
      <h3 class="text-xl font-black text-on-surface dark:text-on-surface mb-6 flex items-center gap-3">
        <span class="w-10 h-10 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
          <span
            class="material-symbols-outlined text-emerald-400"
            style="font-variation-settings: 'FILL' 1"
            >event_available</span
          >
        </span>
        Upcoming Sessions
      </h3>
      <div class="space-y-3">
        <div
          v-for="session in upcomingSessions"
          :key="session.id"
          class="flex items-center gap-4 p-4 rounded-2xl bg-black/[0.02] dark:bg-white/[0.02] border border-black/[0.04] dark:border-white/5 hover:bg-black/5 dark:hover:bg-white/5 transition-all"
        >
          <div class="text-center w-14 shrink-0">
            <p class="text-[10px] font-black text-orange-500 uppercase">
              {{ formatMonth(session.startTime) }}
            </p>
            <p class="text-2xl font-black text-on-surface dark:text-on-surface">{{ formatDay(session.startTime) }}</p>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-on-surface dark:text-on-surface font-bold text-sm">{{ getStudentName(session.studentId) }}</p>
            <p class="text-on-surface-variant dark:text-on-surface-variant text-xs">
              {{ formatTime(session.startTime) }} – {{ formatTime(session.endTime) }}
            </p>
          </div>
          <span class="w-2 h-2 rounded-full bg-orange-500 shrink-0"></span>
        </div>
        <div v-if="upcomingSessions.length === 0" class="text-center py-6 text-on-surface-variant dark:text-on-surface-variant">
          No upcoming sessions
        </div>
      </div>
    </section>

    <!-- Reject Modal -->
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
          v-if="rejectModal.open"
          class="fixed inset-0 z-[250] flex items-center justify-center p-4"
        >
          <div
            class="absolute inset-0 bg-black/30 dark:bg-black/60 backdrop-blur-sm"
            @click="rejectModal.open = false"
          />
          <div
            class="relative w-full max-w-sm liquid-glass rounded-3xl border border-black/[0.08] dark:border-white/10 p-6 space-y-4"
          >
            <div class="flex items-center justify-between">
              <h3 class="text-lg font-black text-on-surface dark:text-on-surface">Decline Session Request</h3>
              <button class="w-8 h-8 rounded-xl bg-black/[0.04] dark:bg-white/5 flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-all" @click="rejectModal.open = false"><span class="material-symbols-outlined text-base">close</span></button>
            </div>
            <textarea
              v-model="rejectModal.notes"
              rows="3"
              placeholder="Reason for declining (optional)..."
              class="w-full bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-4 py-3 text-on-surface dark:text-on-surface text-sm placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-red-500/50 resize-none"
            />
            <div class="flex gap-3">
              <button
                class="flex-1 py-3 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 font-bold rounded-2xl text-sm transition-all"
                @click="confirmReject"
              >
                Confirm Decline
              </button>
              <button
                class="px-5 py-3 bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 text-on-surface-variant dark:text-on-surface-variant font-bold rounded-2xl text-sm"
                @click="rejectModal.open = false"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Counter Modal -->
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
          v-if="counterModal.open"
          class="fixed inset-0 z-[250] flex items-center justify-center p-4"
        >
          <div
            class="absolute inset-0 bg-black/30 dark:bg-black/60 backdrop-blur-sm"
            @click="counterModal.open = false"
          />
          <div
            class="relative w-full max-w-md liquid-glass rounded-3xl border border-black/[0.08] dark:border-white/10 p-6 space-y-4"
          >
            <div class="flex items-center justify-between">
              <h3 class="text-xl font-black text-on-surface dark:text-on-surface">Counter Proposal</h3>
              <button class="w-8 h-8 rounded-xl bg-black/[0.04] dark:bg-white/5 flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-all" @click="counterModal.open = false"><span class="material-symbols-outlined text-base">close</span></button>
            </div>
            
            <div class="space-y-4">
              <div>
                <label class="text-[10px] font-black uppercase tracking-widest text-on-surface-variant mb-2 block">New Start Time</label>
                <input
                  v-model="counterModal.startTime"
                  type="datetime-local"
                  class="w-full bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-4 py-3 text-on-surface dark:text-on-surface text-sm focus:ring-2 focus:ring-orange-500/50 [color-scheme:dark]"
                />
              </div>
              <div>
                <label class="text-[10px] font-black uppercase tracking-widest text-on-surface-variant mb-2 block">New End Time</label>
                <input
                  v-model="counterModal.endTime"
                  type="datetime-local"
                  class="w-full bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-4 py-3 text-on-surface dark:text-on-surface text-sm focus:ring-2 focus:ring-orange-500/50 [color-scheme:dark]"
                />
              </div>
              <div>
                <label class="text-[10px] font-black uppercase tracking-widest text-on-surface-variant mb-2 block">Notes to Student</label>
                <textarea
                  v-model="counterModal.notes"
                  rows="3"
                  class="w-full bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-4 py-3 text-on-surface dark:text-on-surface text-sm focus:ring-2 focus:ring-orange-500/50 resize-none"
                />
              </div>
            </div>

            <div class="flex gap-3 pt-2">
              <button
                class="flex-1 py-3 bg-gradient-to-br from-orange-500 to-orange-700 text-white font-black rounded-2xl text-sm shadow-lg shadow-orange-900/20 hover:scale-[1.02] active:scale-95 transition-all"
                @click="confirmCounter"
              >
                Send Counter
              </button>
              <button
                class="px-5 py-3 bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 text-on-surface-variant dark:text-on-surface-variant font-bold rounded-2xl text-sm"
                @click="counterModal.open = false"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
    <SessionDetailModal
      :session="selectedSession"
      user-role="teacher"
      :current-user-id="authStore.currentUser?.id ?? ''"
      :users="allUsers"
      @close="selectedSession = null"
    @approve-teacher="(id: string) => { handleApproveStudent(id); selectedSession = null }"
    @reject-teacher="(id: string) => { openReject(id); selectedSession = null }"
    @counter-teacher="(s: any) => { openCounter(s); selectedSession = null }"
    @nudge="(id: string) => { scheduleStore.nudgeSession(id); selectedSession = null }"
    />

    <!-- Propose Modal -->
    <ProposeSessionModal :is-open="showProposeModal"
      v-if="showProposeModal"
      user-role="teacher"
      :current-user-id="authStore.currentUser?.id ?? ''"
      :teachers="[]"
      :students="students"
      :initial-date="selectedDate ?? undefined"
      @close="showProposeModal = false"
      @submitted="onProposeSubmit"
    />
  </div>
</template>

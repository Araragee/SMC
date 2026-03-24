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
const showProposeModal = ref(false)
const rejectModal = ref({ open: false, sessionId: '', notes: '' })

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

function getStudentName(id: string): string {
  return usersStore.users.find((u) => u.id === id)?.name ?? `Student #${id}`
}

function onDayClick({ date, sessions }: { date: Date; sessions: Session[] }) {
  selectedDate.value = date
  selectedDaySessions.value = sessions
}

async function handleApproveStudent(sessionId: string) {
  try {
    await scheduleStore.approveAsTeacher(sessionId)
    toast.success('Request approved!', 'Forwarded to admin for final approval.')
    selectedDate.value = null
  } catch {
    toast.error('Failed to approve request')
  }
}

function openReject(sessionId: string) {
  rejectModal.value = { open: true, sessionId, notes: '' }
  selectedDate.value = null
}

async function confirmReject() {
  try {
    await scheduleStore.rejectAsTeacher(rejectModal.value.sessionId, rejectModal.value.notes)
    toast.success('Request declined', 'The student has been notified.')
    rejectModal.value.open = false
  } catch {
    toast.error('Failed to decline request')
  }
}

async function onProposeSubmit(session: Session) {
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

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

function formatMonth(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short' })
}

function formatDay(iso: string): string {
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
        <h1 class="text-5xl font-black tracking-tight text-zinc-900 dark:text-white mb-2">My Schedule</h1>
        <p class="text-zinc-600 dark:text-zinc-500 font-medium">
          <span class="text-zinc-900 dark:text-white font-bold">{{ mySessions.length }}</span> total sessions,
          <span class="text-amber-400 font-bold">{{ studentProposals.length }}</span> student
          proposals awaiting review.
        </p>
      </div>
      <div class="shrink-0 flex items-start gap-4">
        <button
          @click="showProposeModal = true"
          class="px-6 py-3 bg-gradient-to-br from-orange-500 to-orange-700 text-zinc-900 dark:text-white font-bold rounded-3xl shadow-lg shadow-orange-900/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2"
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
          <h3 class="text-lg font-black text-zinc-900 dark:text-white">Student Proposals</h3>
          <p class="text-zinc-600 dark:text-zinc-500 text-sm">
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
            <p class="text-zinc-900 dark:text-white font-bold text-sm">{{ getStudentName(session.studentId) }}</p>
            <p class="text-zinc-500 dark:text-zinc-400 text-xs">{{ formatDateTime(session.startTime) }}</p>
            <p v-if="session.notes" class="text-zinc-600 dark:text-zinc-500 text-xs mt-0.5 italic">
              "{{ session.notes }}"
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button
              @click="handleApproveStudent(session.id)"
              class="px-4 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-xs font-bold transition-all flex items-center gap-1.5"
            >
              <span class="material-symbols-outlined text-sm">check_circle</span>
              Approve
            </button>
            <button
              @click="openReject(session.id)"
              class="px-4 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 text-xs font-bold transition-all flex items-center gap-1.5"
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
      <div class="flex items-center justify-between mb-6">
        <h3 class="text-xl font-black text-zinc-900 dark:text-white flex items-center gap-3">
          <span
            class="w-10 h-10 rounded-2xl bg-orange-500/10 flex items-center justify-center text-orange-500"
          >
            <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
              >calendar_month</span
            >
          </span>
          Weekly Schedule
        </h3>
        <div class="flex items-center gap-3 text-[10px] font-bold uppercase tracking-wider">
          <span class="flex items-center gap-1.5 text-orange-400"
            ><span class="w-2 h-2 rounded-full bg-orange-400"></span>Confirmed</span
          >
          <span class="flex items-center gap-1.5 text-blue-400"
            ><span class="w-2 h-2 rounded-full bg-blue-400"></span>Pending Admin</span
          >
          <span class="flex items-center gap-1.5 text-amber-400"
            ><span class="w-2 h-2 rounded-full bg-amber-400"></span>Pending Review</span
          >
        </div>
      </div>
      <BaseCalendar :sessions="mySessions" @dayClick="onDayClick" />
    </section>

    <!-- Upcoming Confirmed Sessions -->
    <section class="liquid-glass rounded-3xl p-4 border border-black/[0.04] dark:border-white/5">
      <h3 class="text-xl font-black text-zinc-900 dark:text-white mb-6 flex items-center gap-3">
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
          class="flex items-center gap-4 p-4 rounded-2xl bg-black/[0.02] dark:bg-white/[0.02] border border-black/[0.04] dark:border-white/5 hover:bg-white/5 transition-all"
        >
          <div class="text-center w-14 shrink-0">
            <p class="text-[10px] font-black text-orange-500 uppercase">
              {{ formatMonth(session.startTime) }}
            </p>
            <p class="text-2xl font-black text-zinc-900 dark:text-white">{{ formatDay(session.startTime) }}</p>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-zinc-900 dark:text-white font-bold text-sm">{{ getStudentName(session.studentId) }}</p>
            <p class="text-zinc-600 dark:text-zinc-500 text-xs">
              {{ formatTime(session.startTime) }} – {{ formatTime(session.endTime) }}
            </p>
          </div>
          <span class="w-2 h-2 rounded-full bg-orange-500 shrink-0"></span>
        </div>
        <div v-if="upcomingSessions.length === 0" class="text-center py-6 text-zinc-500 dark:text-zinc-600">
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
            <h3 class="text-lg font-black text-zinc-900 dark:text-white">Decline Session Request</h3>
            <textarea
              v-model="rejectModal.notes"
              rows="3"
              placeholder="Reason for declining (optional)..."
              class="w-full bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-4 py-3 text-zinc-900 dark:text-white text-sm placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-red-500/50 resize-none"
            />
            <div class="flex gap-3">
              <button
                @click="confirmReject"
                class="flex-1 py-3 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 font-bold rounded-2xl text-sm transition-all"
              >
                Confirm Decline
              </button>
              <button
                @click="rejectModal.open = false"
                class="px-5 py-3 bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 text-zinc-500 dark:text-zinc-400 font-bold rounded-2xl text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Session Detail Modal -->
    <SessionDetailModal
      :date="selectedDate"
      :sessions="selectedDaySessions"
      user-role="teacher"
      :current-user-id="authStore.currentUser?.id ?? ''"
      :users="allUsers"
      @close="selectedDate = null"
      @propose="((showProposeModal = true), (selectedDate = null))"
      @approve-teacher="handleApproveStudent"
      @reject-teacher="openReject"
    />

    <!-- Propose Modal -->
    <ProposeSessionModal
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

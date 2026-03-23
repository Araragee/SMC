<template>
  <div class="max-w-5xl mx-auto pb-28 space-y-4">

    <!-- Header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-5xl font-black tracking-tight text-white mb-2">My Schedule</h1>
        <p class="text-zinc-500 font-medium">
          <span class="text-white font-bold">{{ confirmedSessions.length }}</span> confirmed sessions this month.
          <template v-if="pendingCount > 0">
            <span class="text-amber-400 font-bold">{{ pendingCount }}</span> pending approval.
          </template>
        </p>
      </div>
      <div class="shrink-0 flex items-start gap-4">
        <button
          @click="showProposeModal = true"
          class="px-6 py-3 bg-gradient-to-br from-orange-500 to-orange-700 text-white font-bold rounded-3xl shadow-lg shadow-orange-900/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-lg">add_circle</span>
          Request Session
        </button>
      </div>
    </div>

    <!-- Pending Sessions Notice -->
    <section v-if="pendingSessions.length > 0" class="liquid-glass rounded-3xl p-5 border border-amber-500/20">
      <div class="flex items-start gap-3">
        <span class="material-symbols-outlined text-amber-400 text-xl mt-0.5" style="font-variation-settings: 'FILL' 1">pending_actions</span>
        <div class="flex-1">
          <p class="text-white font-bold text-sm mb-3">{{ pendingSessions.length }} session{{ pendingSessions.length !== 1 ? 's' : '' }} in progress</p>
          <div class="space-y-2">
            <div
              v-for="session in pendingSessions"
              :key="session.id"
              class="flex items-center justify-between p-3 rounded-2xl border"
              :class="session.status === 'pending_admin' ? 'bg-blue-500/5 border-blue-500/20' : 'bg-amber-500/5 border-amber-500/20'"
            >
              <div>
                <p class="text-white text-sm font-bold">{{ formatDateTime(session.startTime) }}</p>
                <p class="text-zinc-500 text-xs">with {{ getTeacherName(session.teacherId) }}</p>
              </div>
              <span
                class="px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider border"
                :class="session.status === 'pending_admin' ? 'bg-blue-500/20 border-blue-500/30 text-blue-400' : 'bg-amber-500/20 border-amber-500/30 text-amber-400'"
              >
                {{ session.status === 'pending_admin' ? 'Awaiting Admin' : 'Awaiting Teacher' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Weekly Calendar -->
    <section class="liquid-glass rounded-3xl p-4 border border-white/5">
      <div class="flex items-center justify-between mb-6">
        <h3 class="text-xl font-black text-white flex items-center gap-3">
          <span class="w-10 h-10 rounded-2xl bg-orange-500/10 flex items-center justify-center text-orange-500">
            <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1">calendar_month</span>
          </span>
          My Calendar
        </h3>
        <div class="flex items-center gap-3 text-[10px] font-bold uppercase tracking-wider">
          <span class="flex items-center gap-1.5 text-orange-400"><span class="w-2 h-2 rounded-full bg-orange-400"></span>Confirmed</span>
          <span class="flex items-center gap-1.5 text-blue-400"><span class="w-2 h-2 rounded-full bg-blue-400"></span>Pending Admin</span>
          <span class="flex items-center gap-1.5 text-amber-400"><span class="w-2 h-2 rounded-full bg-amber-400"></span>Pending Teacher</span>
        </div>
      </div>
      <WeeklyCalendarGrid
        :sessions="mySessions"
        @dayClick="onDayClick"
      />
    </section>

    <!-- Upcoming Sessions -->
    <section class="liquid-glass rounded-3xl p-4 border border-white/5">
      <h3 class="text-xl font-black text-white mb-6 flex items-center gap-3">
        <span class="w-10 h-10 rounded-2xl bg-orange-500/10 flex items-center justify-center">
          <span class="material-symbols-outlined text-orange-500" style="font-variation-settings: 'FILL' 1">event_upcoming</span>
        </span>
        Upcoming Sessions
      </h3>

      <div v-if="upcomingSessions.length > 0" class="space-y-3">
        <div
          v-for="session in upcomingSessions"
          :key="session.id"
          class="flex items-center gap-5 p-5 rounded-2xl bg-white/[0.02] border border-white/5 hover:bg-white/5 hover:border-white/10 transition-all group"
        >
          <!-- Date badge -->
          <div class="w-14 h-14 rounded-2xl bg-orange-500/20 border border-orange-500/20 flex flex-col items-center justify-center shrink-0">
            <p class="text-[10px] font-black text-orange-500 uppercase tracking-wider">{{ formatMonth(session.startTime) }}</p>
            <p class="text-xl font-black text-white leading-none">{{ formatDay(session.startTime) }}</p>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-white font-bold">{{ getTeacherName(session.teacherId) }}</p>
            <p class="text-zinc-500 text-sm">{{ formatTime(session.startTime) }} – {{ formatTime(session.endTime) }}</p>
            <p v-if="session.notes" class="text-zinc-600 text-xs mt-1 italic">{{ session.notes }}</p>
          </div>
          <span class="material-symbols-outlined text-zinc-700 group-hover:text-zinc-400 group-hover:translate-x-1 transition-all">arrow_forward</span>
        </div>
      </div>
      <div v-else class="text-center py-8 text-zinc-600">
        <span class="material-symbols-outlined text-4xl mb-3 block">calendar_today</span>
        No upcoming sessions. Request one!
      </div>
    </section>

    <!-- Session Detail Modal -->
    <SessionDetailModal
      :date="selectedDate"
      :sessions="selectedDaySessions"
      user-role="student"
      :current-user-id="authStore.currentUser?.id ?? ''"
      :users="allUsers"
      @close="selectedDate = null"
      @propose="showProposeModal = true; selectedDate = null"
    />

    <!-- Propose Modal -->
    <ProposeSessionModal
      v-if="showProposeModal"
      user-role="student"
      :current-user-id="authStore.currentUser?.id ?? ''"
      :teachers="teachers"
      :students="[]"
      :initial-date="selectedDate ?? undefined"
      @close="showProposeModal = false"
      @submitted="onProposeSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useScheduleStore } from '../../stores/schedule'
import { useUsersStore } from '../../stores/users'
import { useAuthStore } from '../../stores/auth'
import { useNotificationStore } from '../../stores/notification'
import { useToastStore } from '../../stores/toast'
import WeeklyCalendarGrid from '../../components/WeeklyCalendarGrid.vue'
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

const myId = computed(() => authStore.currentUser?.id ?? '')
const teachers = computed(() => usersStore.getUsersByRole('teacher'))
const allUsers = computed(() => usersStore.users)

const mySessions = computed(() =>
  scheduleStore.allSessions.filter(s => s.studentId === myId.value)
)

const confirmedSessions = computed(() =>
  mySessions.value.filter(s => s.status === 'scheduled')
)

const pendingSessions = computed(() =>
  mySessions.value.filter(s => s.status === 'pending_teacher' || s.status === 'pending_admin')
)

const pendingCount = computed(() => pendingSessions.value.length)

const upcomingSessions = computed(() => {
  const now = new Date()
  return confirmedSessions.value
    .filter(s => new Date(s.startTime) >= now)
    .sort((a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime())
    .slice(0, 8)
})

onMounted(async () => {
  await Promise.all([
    scheduleStore.fetchUserSessions(myId.value),
    usersStore.fetchUsersByRole('teacher'),
    usersStore.fetchUsersByRole('student'),
    notifStore.fetchNotifications(myId.value),
  ])
})

function getTeacherName(id: string): string {
  return usersStore.users.find(u => u.id === id)?.name ?? `Teacher #${id}`
}

function onDayClick({ date, sessions }: { date: Date; sessions: Session[] }) {
  selectedDate.value = date
  selectedDaySessions.value = sessions
}

async function onProposeSubmit(session: Session) {
  try {
    await scheduleStore.proposeSessionAsStudent({
      teacherId: session.teacherId,
      studentId: myId.value,
      startTime: session.startTime,
      endTime: session.endTime,
      notes: session.notes,
    })
    toast.success('Request submitted!', 'Your teacher will review it and forward to admin.')
    showProposeModal.value = false
  } catch {
    toast.error('Failed to submit request')
  }
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit', hour12: true,
  })
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

function formatMonth(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short' })
}

function formatDay(iso: string): string {
  return String(new Date(iso).getDate())
}
</script>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.15s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>

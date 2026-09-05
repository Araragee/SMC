<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useScheduleStore } from '@stores/schedule'
import { useUsersStore } from '@stores/users'
import { useInteractionsStore } from '@stores/interactions'
import { useAuthStore } from '@stores/auth'
import { useNotificationStore } from '@stores/notification'
import { useToastStore } from '@stores/toast'
import BaseCalendar from '@components/BaseCalendar.vue'
import SessionDetailModal from '@components/SessionDetailModal.vue'
import ProposeSessionModal from '@components/ProposeSessionModal.vue'
import type { Session } from '@types'

const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const interactionsStore = useInteractionsStore()
const authStore = useAuthStore()
const notifStore = useNotificationStore()
const toast = useToastStore()

const selectedDate = ref<Date | null>(null)
const selectedDaySessions = ref<Session[]>([])
const selectedSession = ref<Session | null>(null)
const showProposeModal = ref(false)

const myId = computed(() => authStore.currentUser?.id ?? 0)
// Only teachers with an approved enrollment — the full list would offer
// teachers the booking guard rejects.
const teachers = computed(() => interactionsStore.myTeachers)
const allUsers = computed(() => usersStore.users)

const mySessions = computed(() =>
  scheduleStore.allSessions.filter((s: any) => s.studentId === myId.value)
)

const confirmedSessions = computed(() =>
  mySessions.value.filter((s: any) => s.status === 'scheduled')
)

const pendingSessions = computed(() =>
  mySessions.value.filter(
    (s: any) => s.status === 'pending_teacher' || s.status === 'pending_admin'
  )
)

const pendingCount = computed(() => pendingSessions.value.length)

const upcomingSessions = computed(() => {
  const now = new Date()
  return confirmedSessions.value
    .filter((s: any) => new Date(s.startTime) >= now)
    .sort((a: any, b: any) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime())
    .slice(0, 8)
})

onMounted(async () => {
  interactionsStore.fetchMyTeachers()
  const tasks: Promise<any>[] = [
    usersStore.fetchUsersByRole('teacher'),
    usersStore.fetchUsersByRole('student'),
    usersStore.fetchInstruments(),
  ]
  if (myId.value > 0) {
    tasks.push(
      scheduleStore.fetchUserSessions(myId.value),
      notifStore.fetchNotifications(myId.value)
    )
  }
  await Promise.all(tasks)
})

watch(myId, (newId) => {
  if (newId > 0) {
    scheduleStore.fetchUserSessions(newId)
    notifStore.fetchNotifications(newId)
  }
})

const getTeacherName = function (id: number): string {
  return usersStore.users.find((u: any) => u.id === id)?.name ?? `Teacher #${id}`
}

const onDayClick = function ({ date, sessions }: { date: Date; sessions: Session[] }) {
  selectedDate.value = date
  selectedDaySessions.value = sessions
}

const onSessionClick = function (session: Session) {
  selectedSession.value = session
}

const onProposeSubmit = async function (session: Session) {
  try {
    await scheduleStore.proposeSessionAsStudent({
      teacherId: session.teacherId,
      studentId: myId.value,
      startTime: session.startTime,
      endTime: session.endTime,
      notes: session.notes,
      instrumentId: session.instrumentId ?? null,
    })
    toast.success('Request submitted!', 'Your teacher will review it and forward to admin.')
    showProposeModal.value = false
  } catch {
    // Error is toasted with detailed server message by scheduleStore
  }
}

const formatDateTime = function (iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

const formatTime = function (iso: string): string {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

const formatMonth = function (iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short' })
}

const formatDay = function (iso: string): string {
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
        <h1 class="text-5xl font-semibold tracking-tight text-on-surface mb-2">My Schedule</h1>
        <p class="text-on-surface-variant font-medium">
          <span class="text-on-surface font-bold">{{ confirmedSessions.length }}</span>
          confirmed sessions this month.
          <template v-if="pendingCount > 0">
            <span class="text-warning font-bold">{{ pendingCount }}</span> pending approval.
          </template>
        </p>
      </div>
      <div class="shrink-0 flex items-start gap-4">
        <button
          class="px-6 py-3 bg-primary text-on-primary font-bold rounded-3xl shadow-lg hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2"
          @click="showProposeModal = true"
        >
          <span class="material-symbols-outlined text-lg">add_circle</span>
          Request Session
        </button>
      </div>
    </div>

    <!-- Pending Sessions Notice -->
    <section
      v-if="pendingSessions.length > 0"
      class="liquid-glass rounded-3xl p-4 border border-warning/20"
    >
      <div class="flex items-start gap-3">
        <span
          class="material-symbols-outlined text-warning text-xl mt-0.5"
          style="font-variation-settings: 'FILL' 1"
          >pending_actions</span
        >
        <div class="flex-1">
          <p class="text-on-surface font-bold text-sm mb-3">
            {{ pendingSessions.length }} session{{ pendingSessions.length !== 1 ? 's' : '' }} in
            progress
          </p>
          <div class="space-y-2">
            <div
              v-for="session in pendingSessions"
              :key="session.id"
              class="flex items-center justify-between p-3 rounded-2xl border"
              :class="
                session.status === 'pending_admin'
                  ? 'bg-tertiary/5 border-tertiary/20'
                  : 'bg-warning/5 border-warning/20'
              "
            >
              <div>
                <p class="text-on-surface text-sm font-bold">
                  {{ formatDateTime(session.startTime) }}
                </p>
                <p class="text-on-surface-variant text-xs">
                  with {{ getTeacherName(session.teacherId) }}
                </p>
              </div>
              <span
                class="px-2 py-1 rounded-full text-xs font-semibold uppercase border"
                :class="
                  session.status === 'pending_admin'
                    ? 'bg-tertiary/20 border-tertiary/30 text-tertiary'
                    : 'bg-warning/20 border-warning/30 text-warning'
                "
              >
                {{ session.status === 'pending_admin' ? 'Awaiting Admin' : 'Awaiting Teacher' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Weekly Calendar -->
    <section
      class="liquid-glass rounded-3xl p-4 border border-on-surface/[0.04] dark:border-on-surface/5"
    >
      <h3 class="text-xl font-semibold text-on-surface flex items-center gap-3 mb-6">
        <span
          class="size-10 rounded-2xl bg-success/10 flex items-center justify-center text-success"
        >
          <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
            >calendar_month</span
          >
        </span>
        My Calendar
      </h3>
      <BaseCalendar
        :sessions="mySessions"
        @day-click="onDayClick"
        @session-click="onSessionClick"
      />
    </section>

    <!-- Upcoming Sessions -->
    <section
      class="liquid-glass rounded-3xl p-4 border border-on-surface/[0.04] dark:border-on-surface/5"
    >
      <h3 class="text-xl font-semibold text-on-surface mb-6 flex items-center gap-3">
        <span class="size-10 rounded-2xl bg-primary/10 flex items-center justify-center">
          <span
            class="material-symbols-outlined text-primary"
            style="font-variation-settings: 'FILL' 1"
            >event_upcoming</span
          >
        </span>
        Upcoming Sessions
      </h3>

      <div v-if="upcomingSessions.length > 0" class="space-y-3">
        <div
          v-for="session in upcomingSessions"
          :key="session.id"
          class="flex items-center gap-4 p-4 rounded-2xl bg-on-surface/[0.02] dark:bg-on-surface/[0.02] border border-on-surface/[0.04] dark:border-on-surface/5 hover:bg-on-surface/5 dark:hover:bg-on-surface/5 hover:border-on-surface/10 transition-all group"
        >
          <!-- Date badge -->
          <div
            class="size-14 rounded-2xl bg-primary/20 border border-primary/20 flex flex-col items-center justify-center shrink-0"
          >
            <p class="text-xs font-semibold text-primary uppercase">
              {{ formatMonth(session.startTime) }}
            </p>
            <p class="text-xl font-semibold text-on-surface leading-none">
              {{ formatDay(session.startTime) }}
            </p>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-on-surface font-bold">
              {{ getTeacherName(session.teacherId) }}
            </p>
            <p class="text-on-surface-variant text-sm">
              {{ formatTime(session.startTime) }} – {{ formatTime(session.endTime) }}
            </p>
            <p v-if="session.notes" class="text-on-surface-variant text-xs mt-1 italic">
              {{ session.notes }}
            </p>
          </div>
          <span
            class="material-symbols-outlined text-on-surface-variant/50 dark:text-on-surface-variant/40 group-hover:text-on-surface-variant group-hover:translate-x-1 transition-all"
            >arrow_forward</span
          >
        </div>
      </div>
      <div v-else class="text-center py-8 text-on-surface-variant">
        <span class="material-symbols-outlined text-4xl mb-3 block">calendar_today</span>
        No upcoming sessions. Request one!
      </div>
    </section>

    <!-- Session Detail Modal -->
    <SessionDetailModal
      :session="selectedSession"
      user-role="student"
      :current-user-id="authStore.currentUser?.id ?? 0"
      :users="allUsers"
      @close="selectedSession = null"
      @approve-student="
        async (id) => {
          await scheduleStore.approveAsStudent(id)
          selectedSession = null
          await scheduleStore.fetchUserSessions(myId)
        }
      "
      @reject-student="
        async (id) => {
          await scheduleStore.rejectAsStudent(id)
          selectedSession = null
          await scheduleStore.fetchUserSessions(myId)
        }
      "
      @counter-student="
        () => {
          selectedSession = null
          showProposeModal = true
        }
      "
      @nudge="
        (id: number) => {
          scheduleStore.nudgeSession(id)
          selectedSession = null
        }
      "
    />

    <!-- Propose Modal -->
    <ProposeSessionModal
      :is-open="showProposeModal"
      v-if="showProposeModal"
      user-role="student"
      :current-user-id="authStore.currentUser?.id ?? 0"
      :teachers="teachers"
      :students="[]"
      :instruments="usersStore.instruments"
      :initial-date="selectedDate ?? undefined"
      @close="showProposeModal = false"
      @submitted="onProposeSubmit"
    />
  </div>
</template>

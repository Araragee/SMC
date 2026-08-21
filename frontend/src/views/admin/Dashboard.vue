<script setup lang="ts">
import { PAGE_SIZE } from '@typescript/constants'
import { onMounted, computed, ref } from 'vue'
import { useScheduleStore } from '@stores/schedule'
import { useUsersStore } from '@stores/users'
import { useAuthStore } from '@stores/auth'
import { useNotificationStore } from '@stores/notification'
import { useToastStore } from '@stores/toast'
import { usePaymentsStore } from '@stores/payments'
import { useRosterStore } from '@stores/roster'
import ProposeSessionModal from '@components/ProposeSessionModal.vue'
import SessionDetailModal from '@components/SessionDetailModal.vue'
import type { Session } from '@types'
import { useDialog } from '@composables/useDialog'

const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()
const notifStore = useNotificationStore()
const toast = useToastStore()
const paymentsStore = usePaymentsStore()
const rosterStore = useRosterStore()
const dialog = useDialog()

const showAddSessionModal = ref(false)
const detailDate = ref<Date | null>(null)
const detailSessions = ref<Session[]>([])
const selectedSession = ref<Session | null>(null)
const sessionPage = ref(0)
const viewMode = ref<'daily' | 'weekly'>('daily')
const quickTeacherId = ref('')
const quickStudentId = ref('')
const isQuickAssigning = ref(false)
const quickDate = ref(new Date().toISOString().split('T')[0])
const quickTime = ref(
  new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
)
const unassignedStudents = computed(() => {
  const assigned = new Set(rosterStore.assignments.map((a) => a.studentId))
  return students.value.filter((s) => !assigned.has(s.id))
})
const activeEnrollments = computed(
  () => rosterStore.enrollments.filter((e) => e.isActive !== false).length
)

const teacherSearch = ref('')
const showTeacherSearch = ref(false)

onMounted(async () => {
  await Promise.all([
    scheduleStore.fetchAllSessions(),
    scheduleStore.fetchPendingSessions(),
    scheduleStore.fetchStats(),
    usersStore.fetchUsersByRole('teacher'),
    usersStore.fetchUsersByRole('student'),
    paymentsStore.fetchPayments(),
    // Best-effort: the rest of the dashboard still renders if roster
    // endpoints are unavailable.
    rosterStore.fetchAll().catch(() => {}),
  ])
  if (authStore.currentUser?.id) {
    notifStore.fetchNotifications(authStore.currentUser.id)
  }
})

const teachers = computed(() => usersStore.getUsersByRole('teacher'))
const filteredTeachers = computed(() => {
  if (!teacherSearch.value) return teachers.value
  const s = teacherSearch.value.toLowerCase()
  return teachers.value.filter(
    (t) => t.name.toLowerCase().includes(s) || t.email.toLowerCase().includes(s)
  )
})
const students = computed(() => usersStore.getUsersByRole('student'))
const allUsers = computed(() => [...teachers.value, ...students.value])
const pagedSessions = computed(() => {
  const start = sessionPage.value * PAGE_SIZE
  return scheduleStore.allSessions.slice(start, start + PAGE_SIZE)
})
const canGoPrev = computed(() => sessionPage.value > 0)
const canGoNext = computed(
  () => (sessionPage.value + 1) * PAGE_SIZE < scheduleStore.allSessions.length
)

const stats = computed(() => {
  return scheduleStore.stats || {
    totalSessions: 0,
    scheduledSessions: 0,
    completedSessions: 0,
    completionRate: 0,
    overdueSessions: 0,
    pendingSessions: 0,
    awaitingAdmin: 0,
  }
})

const thisMonthRevenue = computed(() => {
  const now = new Date()
  return paymentsStore.payments
    .filter((p) => {
      const d = new Date(p.date)
      return (
        p.status === 'completed' &&
        d.getMonth() === now.getMonth() &&
        d.getFullYear() === now.getFullYear()
      )
    })
    .reduce((s, p) => s + p.amount, 0)
})

const formatRevenue = (cents: number) =>
  new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP', maximumFractionDigits: 0 }).format(cents / 100)

const topInstruments = computed(() => {
  const counts: Record<string, number> = {}
  scheduleStore.allSessions.forEach((s: any) => {
    const name = s.instrument?.name || 'Theory'
    counts[name] = (counts[name] || 0) + 1
  })
  return Object.entries(counts)
    .map(([name, count]) => ({ name, count }))
    .sort((a: any, b: any) => b.count - a.count)
    .slice(0, 3)
})

const hourlyDistribution = computed(() => {
  const hours = new Array(8).fill(0) // 9am to 5pm
  scheduleStore.allSessions.forEach((s: any) => {
    const hr = new Date(s.startTime).getHours()
    if (hr >= 9 && hr <= 16) hours[hr - 9]++
  })
  const max = Math.max(...hours, 1)
  return hours.map((v) => (v / max) * 100)
})

const todaySessions = computed(() => {
  const today = new Date().toDateString()
  return scheduleStore.allSessions.filter(
    (s: any) => new Date(s.startTime).toDateString() === today
  )
})

const weeklySessions = computed(() => {
  const now = new Date()
  const grouped: Record<string, Session[]> = {}

  // Fill 7 days
  for (let i = 0; i < 7; i++) {
    const d = new Date(now.getTime() + i * 24 * 60 * 60 * 1000)
    grouped[d.toDateString()] = []
  }

  scheduleStore.allSessions.forEach((s: any) => {
    const d = new Date(s.startTime).toDateString()
    if (grouped[d]) grouped[d].push(s)
  })

  return Object.entries(grouped).map(([date, sessions]) => ({
    date: new Date(date),
    sessions: sessions.sort(
      (a: any, b: any) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime()
    ),
  }))
})

const formatTime = (dt: string | undefined) => {
  if (!dt) return '—'
  return new Date(dt).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
const formatAmPm = (dt: string | undefined) => {
  if (!dt) return ''
  return new Date(dt).toLocaleTimeString('en-US', { hour12: true }).slice(-2)
}

const statusClass = (status: string) => ({
  'bg-emerald-500/20 text-emerald-400': status === 'completed',
  'bg-blue-500/20 text-blue-400': status === 'scheduled',
  'bg-amber-500/20 text-amber-400': status === 'pending_teacher' || status === 'ongoing',
  'bg-primary/20 text-primary': status === 'pending_student',
  'bg-blue-600/20 text-blue-300': status === 'pending_admin',
  'bg-red-500/20 text-red-400': status === 'rejected' || status === 'cancelled',
})

const borderColor = (status: string) => ({
  'border-emerald-500 dark:border-emerald-400/20': status === 'completed',
  'border-primary dark:border-primary/20': status === 'scheduled' || status === 'pending_student',
  'border-amber-500 dark:border-amber-400/20': status === 'pending_teacher' || status === 'ongoing',
  'border-blue-500 dark:border-blue-400/20': status === 'pending_admin',
  'border-red-500 dark:border-red-400/20': status === 'rejected' || status === 'cancelled',
})

const iconClass = (status: string) => ({
  'bg-emerald-500/10 text-emerald-400 border-emerald-500/20': status === 'completed',
  'bg-primary/10 text-primary border-primary/20':
    status === 'scheduled' || status === 'pending_student',
  'bg-amber-500/10 text-amber-400 border-amber-500/20':
    status === 'pending_teacher' || status === 'ongoing',
  'bg-blue-500/10 text-blue-400 border-blue-500/20': status === 'pending_admin',
  'bg-red-500/10 text-red-400 border-red-500/20': status === 'rejected' || status === 'cancelled',
})

const onProposeSubmit = async function (session: Session) {
  try {
    await scheduleStore.bookSession({
      teacherId: session.teacherId,
      studentId: session.studentId,
      startTime: session.startTime,
      endTime: session.endTime,
      notes: session.notes,
    })
    toast.success('Session scheduled!', 'The session has been added to the calendar.')
    showAddSessionModal.value = false
  } catch {
    toast.error('Failed to schedule', 'Please check the details and try again.')
  }
}

const openSessionDetail = function (session: Session) {
  selectedSession.value = session
}

const refreshDetailSessions = function () {
  if (!detailDate.value) return
  const dateStr = detailDate.value.toDateString()
  detailSessions.value = scheduleStore.allSessions.filter(
    (s: any) => new Date(s.startTime).toDateString() === dateStr
  )
}

const handleApproveAdmin = async function (sessionId: number) {
  const session = scheduleStore.allSessions.find((s: any) => s.id === sessionId)
  try {
    if (session?.status === 'pending_teacher') {
      await scheduleStore.approveAsTeacher(sessionId)
    } else if (session?.status === 'pending_student') {
      await scheduleStore.approveAsStudent(sessionId)
    } else {
      await scheduleStore.approveAsAdmin(sessionId)
    }
    toast.success('Success', `Session ${sessionId} advanced.`)
    await scheduleStore.fetchAllSessions()
    refreshDetailSessions()
  } catch {
    toast.error('Failed', 'Action could not be completed.')
  }
}

const handleRejectAdmin = async function (sessionId: number) {
  const session = scheduleStore.allSessions.find((s: any) => s.id === sessionId)
  try {
    if (session?.status === 'pending_teacher') {
      await scheduleStore.rejectAsTeacher(sessionId, 'Decline by Admin')
    } else {
      await scheduleStore.rejectAsAdmin(sessionId, 'Reject by Admin')
    }
    toast.success('Rejected', 'Session has been updated.')
    refreshDetailSessions()
  } catch {
    toast.error('Failed', 'Could not reject session.')
  }
}

const handleCompleteAdmin = async function (sessionId: number) {
  try {
    await scheduleStore.completeSession(sessionId)
    toast.success('Session Completed', 'The session has been successfully finalized.')
    await scheduleStore.fetchAllSessions()
    refreshDetailSessions()
  } catch (err: any) {
    toast.error('Failed to complete', err.message || 'Something went wrong.')
  }
}

const handleRejectProofAdmin = async function (sessionId: number) {
  const reason = await dialog.prompt('Enter a reason for rejecting this proof:', {
    title: 'Reject Proof',
    placeholder: 'e.g. Image is unclear or incorrect session'
  })
  if (!reason) return
  try {
    await scheduleStore.rejectProof(sessionId, reason)
    toast.success('Proof Rejected', 'The student has been notified to re-upload.')
    await scheduleStore.fetchAllSessions()
    refreshDetailSessions()
  } catch (err: any) {
    toast.error('Failed to reject proof', err.message || 'Something went wrong.')
  }
}

const confirmQuickAssign = async function () {
  if (!quickTeacherId.value || !quickStudentId.value) return
  isQuickAssigning.value = true
  try {
    const [y, m, d] = quickDate.value.split('-').map(Number)
    const [hr, min] = quickTime.value.split(':').map(Number)
    const startTime = new Date(y, m - 1, d, hr, min)
    const endTime = new Date(startTime.getTime() + 60 * 60 * 1000) // 1hr
    await scheduleStore.bookSession({
      teacherId: Number(quickTeacherId.value),
      studentId: Number(quickStudentId.value),
      startTime: startTime.toISOString(),
      endTime: endTime.toISOString(),
    })
    toast.success('Session assigned!', 'The session has been successfully scheduled.')
    quickTeacherId.value = ''
    quickStudentId.value = ''
  } catch (err: any) {
    toast.error('Assignment failed', err.message || 'Check connection.')
  } finally {
    isQuickAssigning.value = false
  }
}

const handleDeleteTeacher = async function (teacher: any) {
  const ok = await dialog.confirm(`Deactivate ${teacher.name}? They will lose access immediately.`, {
    title: 'Deactivate Teacher',
    destructive: true
  })
  if (!ok) return
  try {
    await usersStore.deleteUser(teacher.id)
    toast.success('Member deactivated', `${teacher.name} has been removed from active faculty.`)
  } catch (err: any) {
    toast.error('Failed to deactivate', err.message || 'Something went wrong.')
  }
}

const handleMarkRead = async function (notifId: number) {
  await notifStore.markAsRead(notifId)
}

const handleClearAll = async function () {
  if (authStore.currentUser?.id) {
    await notifStore.markAllAsRead(authStore.currentUser.id)
  }
}

const openLiveAnalytics = function () {
  detailDate.value = new Date()
  detailSessions.value = todaySessions.value
}
</script>

<template>
  <div class="page">
    <!-- Page Header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-5xl font-semibold tracking-tight text-on-surface dark:text-on-surface mb-2">
          Admin Dashboard
        </h1>
        <p class="text-on-surface-variant dark:text-on-surface-variant font-medium">
          Sernan's Music Clinic — Overview
        </p>
      </div>
    </div>

    <!-- Bento Stats Grid -->
    <section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
      <!-- Live Analytics (col-span-1 md:col-span-2 lg:col-span-3 xl:col-span-2) -->
      <div
        class="col-span-1 md:col-span-2 lg:col-span-3 xl:col-span-2 liquid-glass p-6 rounded-3xl border border-on-surface/[0.04] dark:border-on-surface/5 flex flex-col justify-between cursor-pointer hover:bg-on-surface/5 dark:hover:bg-on-surface/5 transition-all group active:scale-[0.99] shadow-lg shadow-e2/[0.02]"
        @click="openLiveAnalytics"
      >
        <div class="flex justify-between items-start">
          <div>
            <span class="text-xs font-semibold text-primary uppercase"
              >Live Analytics</span
            >
            <div
              v-if="scheduleStore.isLoading"
              class="h-10 w-48 rounded bg-on-surface/[0.04] dark:bg-on-surface/5 animate-pulse mt-2"
            />
            <h2
              v-else
              class="text-3xl font-semibold mt-2 tracking-tight text-on-surface dark:text-on-surface"
            >
              {{ stats.scheduledSessions }} Active Today
            </h2>
            <p class="text-on-surface-variant dark:text-on-surface-variant text-sm mt-1">
              Real-time occupancy ·
              <span v-if="stats.awaitingAdmin > 0" class="text-amber-400 font-bold">{{ stats.awaitingAdmin }} awaiting admin</span>
              <span v-else class="opacity-60">all clear</span>
            </p>
          </div>
          <div class="flex gap-1 h-8 items-end">
            <div
              v-for="(h, i) in hourlyDistribution"
              :key="i"
              class="w-2 bg-primary/20 rounded-t-sm transition-all"
              :style="{
                height: `${h}%`,
                backgroundColor: h > 70 ? 'var(--md-sys-color-primary)' : '',
              }"
            ></div>
          </div>
        </div>

        <div class="space-y-4 mt-8">
          <div
            class="flex items-center justify-between text-xs font-semibold uppercase text-on-surface-variant"
          >
            <span>Popular Instruments</span>
            <span>Sessions</span>
          </div>
          <div class="flex flex-wrap gap-2">
            <div
              v-for="inst in topInstruments"
              :key="inst.name"
              class="px-4 py-2 bg-primary/5 border border-primary/20 rounded-2xl flex items-center gap-3 group hover:bg-primary/10 transition-all cursor-default"
            >
              <span
                class="size-1.5 rounded-full bg-primary shadow-[0_0_8px_rgba(var(--primary-rgb),0.5)]"
              ></span>
              <span class="text-xs font-semibold text-on-surface uppercase">{{
                inst.name
              }}</span>
              <span class="text-xs font-bold text-primary opacity-60">{{ inst.count }}</span>
            </div>
            <div
              v-if="topInstruments.length === 0"
              class="text-xs text-on-surface-variant italic opacity-50"
            >
              No session data available for analysis.
            </div>
          </div>
        </div>
      </div>

      <!-- Retention Rate (orange gradient) -->
      <div
        class="bg-primary-container text-on-primary-container p-4 rounded-3xl shadow-e1 flex flex-col justify-between relative overflow-hidden group"
      >
        <div class="absolute -right-6 -bottom-6 opacity-20 size-40">
          <img src="/logo.png" alt="Logo" class="w-full h-full object-contain" />
        </div>
        <div class="relative z-10">
          <span class="text-xs font-semibold text-on-surface/70 uppercase"
            >Retention Rate</span
          >
          <div
            v-if="scheduleStore.isLoading"
            class="h-14 w-20 rounded bg-on-surface/20 animate-pulse mt-2"
          />
          <h2 v-else class="text-5xl font-semibold mt-2 tracking-tighter text-on-surface">
            {{ stats.completionRate }}%
          </h2>
        </div>
        <p class="text-xs text-on-surface/80 font-medium relative z-10">
          Exceeding national music academy benchmarks
        </p>
      </div>

      <!-- New Registrations -->
      <div
        class="liquid-glass p-4 rounded-3xl border border-on-surface/[0.04] dark:border-on-surface/5 flex flex-col justify-between"
      >
        <div>
          <span
            class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase"
            >New Registrations</span
          >
          <div
            v-if="usersStore.isLoading"
            class="h-14 w-16 rounded bg-on-surface/[0.04] dark:bg-on-surface/5 animate-pulse mt-2"
          />
          <h2
            v-else
            class="text-5xl font-semibold mt-2 tracking-tighter text-on-surface dark:text-on-surface"
          >
            {{ students.length }}
          </h2>
        </div>
        <div class="flex -space-x-3 mt-6">
          <div
            v-for="(s, i) in students.slice(0, 3)"
            :key="s.id"
            class="size-10 rounded-full border-2 border-surface-container-highest bg-surface-container-highest flex items-center justify-center text-on-surface dark:text-on-surface font-semibold text-xs"
            :style="{ zIndex: 3 - i }"
          >
            {{ s.name.charAt(0) }}
          </div>
          <div
            v-if="students.length > 3"
            class="size-10 rounded-full border-2 border-surface-container-highest bg-primary text-on-primary text-xs font-semibold flex items-center justify-center"
          >
            +{{ students.length - 3 }}
          </div>
        </div>
      </div>

      <!-- Pending Approvals -->
      <RouterLink
        to="/admin/schedule"
        class="liquid-glass p-4 rounded-3xl border border-amber-500/20 flex flex-col justify-between hover:bg-amber-500/5 transition-all group"
      >
        <div>
          <span class="text-xs font-semibold text-amber-500 uppercase"
            >Pending Approvals</span
          >
          <div
            v-if="scheduleStore.isLoading"
            class="h-14 w-16 rounded bg-on-surface/[0.04] dark:bg-on-surface/5 animate-pulse mt-2"
          />
          <h2
            v-else
            class="text-5xl font-semibold mt-2 tracking-tighter"
            :class="scheduleStore.pendingSessions.length > 0 ? 'text-amber-400' : 'text-on-surface dark:text-on-surface'"
          >
            {{ scheduleStore.pendingSessions.length }}
          </h2>
        </div>
        <p
          class="text-on-surface-variant dark:text-on-surface-variant text-xs font-bold group-hover:text-amber-500 transition-colors mt-6"
        >
          Review →
        </p>
      </RouterLink>

      <!-- Monthly Revenue -->
      <RouterLink
        to="/admin/payments"
        class="liquid-glass p-4 rounded-3xl border border-emerald-500/20 flex flex-col justify-between hover:bg-emerald-500/5 transition-all group"
      >
        <div>
          <span class="text-xs font-semibold text-emerald-500 uppercase"
            >Monthly Revenue</span
          >
          <div
            v-if="paymentsStore.isLoading"
            class="h-14 w-24 rounded bg-on-surface/[0.04] dark:bg-on-surface/5 animate-pulse mt-2"
          />
          <h2
            v-else
            class="text-3xl font-semibold mt-2 tracking-tighter text-emerald-400 leading-none"
          >
            {{ formatRevenue(thisMonthRevenue) }}
          </h2>
        </div>
        <p
          class="text-on-surface-variant dark:text-on-surface-variant text-xs font-bold group-hover:text-emerald-500 transition-colors mt-6"
        >
          View Ledger →
        </p>
      </RouterLink>

      <!-- Overdue Sessions -->
      <RouterLink
        to="/admin/schedule"
        class="liquid-glass p-4 rounded-3xl border border-rose-500/20 flex flex-col justify-between hover:bg-rose-500/5 transition-all group"
      >
        <div>
          <span class="text-xs font-semibold text-rose-500 uppercase"
            >Overdue</span
          >
          <div
            v-if="scheduleStore.isLoading"
            class="h-14 w-16 rounded bg-on-surface/[0.04] dark:bg-on-surface/5 animate-pulse mt-2"
          />
          <h2
            v-else
            class="text-5xl font-semibold mt-2 tracking-tighter"
            :class="stats.overdueSessions > 0 ? 'text-rose-400' : 'text-on-surface dark:text-on-surface'"
          >
            {{ stats.overdueSessions }}
          </h2>
        </div>
        <p
          class="text-on-surface-variant dark:text-on-surface-variant text-xs font-bold group-hover:text-rose-500 transition-colors mt-6"
        >
          Action Required →
        </p>
      </RouterLink>
    </section>

    <!-- Main Layout -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <!-- Left: Schedule + Faculty -->
      <div class="col-span-1 md:col-span-2 lg:col-span-3 xl:col-span-2 space-y-4">
        <!-- Music Schedule -->
        <section
          class="liquid-glass rounded-3xl p-6 border border-on-surface/[0.04] dark:border-on-surface/5"
        >
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
            <div>
              <h3 class="text-2xl font-semibold tracking-tight text-on-surface dark:text-on-surface">
                Music Schedule
              </h3>
              <p class="text-on-surface-variant dark:text-on-surface-variant text-sm">
                {{ viewMode === 'daily' ? 'Managing for today' : 'Upcoming week overview' }}
              </p>
            </div>
            <div class="flex items-center gap-2">
              <!-- View Mode Toggle -->
              <div
                class="flex bg-on-surface/5 dark:bg-on-surface/5 p-1 rounded-2xl border border-on-surface/5 dark:border-on-surface/5 mr-2"
              >
                <button
                  class="px-4 py-2 rounded-xl text-xs font-semibold uppercase transition-all"
                  :class="viewMode === 'daily' ? 'bg-primary text-on-primary shadow-md' : 'text-on-surface-variant hover:text-on-surface'"
                  @click="viewMode = 'daily'"
                >
                  Today
                </button>
                <button
                  class="px-4 py-2 rounded-xl text-xs font-semibold uppercase transition-all"
                  :class="viewMode === 'weekly' ? 'bg-primary text-on-primary shadow-md' : 'text-on-surface-variant hover:text-on-surface'"
                  @click="viewMode = 'weekly'"
                >
                  Weekly
                </button>
              </div>

              <div v-if="viewMode === 'daily'" class="flex gap-2">
                <button
                  class="p-2 bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.08] dark:border-on-surface/10 rounded-xl hover:bg-on-surface/5 dark:hover:bg-on-surface/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                  :disabled="!canGoPrev"
                  @click="sessionPage--"
                >
                  <span class="material-symbols-outlined text-sm">chevron_left</span>
                </button>
                <button
                  class="p-2 bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.08] dark:border-on-surface/10 rounded-xl hover:bg-on-surface/5 dark:hover:bg-on-surface/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                  :disabled="!canGoNext"
                  @click="sessionPage++"
                >
                  <span class="material-symbols-outlined text-sm">chevron_right</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Daily List View -->
          <div v-if="viewMode === 'daily'">
            <!-- Column headers -->
            <div
              class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 py-2 border-b border-on-surface/[0.04] dark:border-on-surface/5 mb-4 px-2"
            >
              <div
                class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase col-span-1"
              >
                Time
              </div>
              <div
                class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase col-span-5"
              >
                Sessions &amp; Instructors
              </div>
            </div>

            <!-- Loading -->
            <div v-if="scheduleStore.isLoading" class="space-y-4">
              <div
                v-for="i in 3"
                :key="i"
                class="h-20 rounded-3xl bg-on-surface/[0.04] dark:bg-on-surface/5 animate-pulse"
              />
            </div>

            <!-- Empty -->
            <div
              v-else-if="scheduleStore.allSessions.length === 0"
              class="py-10 flex flex-col items-center text-center"
            >
              <span
                class="material-symbols-outlined text-4xl text-on-surface-variant/50 dark:text-on-surface-variant/40 mb-3"
                >event_busy</span
              >
              <p class="font-bold text-on-surface dark:text-on-surface text-sm mb-1">
                No sessions scheduled
              </p>
              <p class="text-xs text-on-surface-variant dark:text-on-surface-variant">
                Use "Assign New" to create your first session.
              </p>
            </div>

            <!-- Session rows -->
            <div v-else class="space-y-2">
              <div
                v-for="session in pagedSessions"
                :key="session.id"
                class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 group hover:bg-on-surface/5 dark:hover:bg-on-surface/5 transition-all rounded-3xl p-2 px-4 -mx-2"
              >
                <div class="col-span-1 flex flex-col justify-center">
                  <span class="text-sm font-semibold">{{ formatTime(session.startTime) }}</span>
                  <span
                    class="text-xs text-on-surface-variant dark:text-on-surface-variant uppercase font-bold"
                    >{{ formatAmPm(session.startTime) }}</span
                  >
                </div>
                <div
                  class="col-span-5 bg-on-surface/[0.04] dark:bg-on-surface/5 border-y p-3 rounded-3xl flex items-center justify-between cursor-pointer hover:bg-on-surface/[0.08] dark:hover:bg-on-surface/10 transition-colors"
                  :class="borderColor(session.status)"
                  @click="openSessionDetail(session)"
                >
                  <div class="flex items-center gap-4">
                    <div
                      class="size-10 rounded-xl flex items-center justify-center shadow-sm border"
                      :class="iconClass(session.status)"
                    >
                      <span class="material-symbols-outlined">music_note</span>
                    </div>
                    <div>
                      <h4 class="text-sm font-bold text-on-surface dark:text-on-surface">
                        Session #{{ session.id }}
                      </h4>
                      <p class="text-xs text-on-surface-variant dark:text-on-surface-variant">
                        T:{{ session.teacherId }} • S:{{ session.studentId }}
                      </p>
                    </div>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <span
                      class="text-xs px-3 py-1 rounded-full font-semibold uppercase"
                      :class="statusClass(session.status)"
                      >{{ session.status }}</span
                    >
                    <button
                      class="p-2 opacity-0 group-hover:opacity-100 transition-opacity text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface"
                    >
                      <span class="material-symbols-outlined">more_vert</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Weekly Grid View -->
          <div v-else class="space-y-6">
            <div class="overflow-x-auto pb-4 custom-scrollbar">
              <div class="flex gap-4 min-w-[1000px]">
                <div
                  v-for="day in weeklySessions"
                  :key="day.date.toDateString()"
                  class="flex-1 min-w-[180px] bg-on-surface/[0.02] dark:bg-on-surface/[0.02] rounded-3xl p-4 border border-on-surface/[0.04] dark:border-on-surface/5 flex flex-col"
                >
                  <div class="mb-4 text-center">
                    <p class="text-xs font-semibold text-primary uppercase mb-1">
                      {{ day.date.toLocaleDateString('en-US', { weekday: 'short' }) }}
                    </p>
                    <p class="text-lg font-semibold text-on-surface">{{ day.date.getDate() }}</p>
                  </div>

                  <div class="space-y-2 flex-1">
                    <div
                      v-for="session in day.sessions"
                      :key="session.id"
                      class="bg-surface-container-lowest dark:bg-on-surface/5 p-3 rounded-2xl border-l-[3px] border shadow-sm hover:scale-[1.02] transition-all cursor-pointer"
                      :class="[borderColor(session.status), 'border-on-surface/5 dark:border-on-surface/10']"
                      @click="openSessionDetail(session)"
                    >
                      <p class="text-[8px] font-bold text-on-surface-variant uppercase mb-1">
                        {{ formatTime(session.startTime) }}
                      </p>
                      <p class="text-xs font-semibold text-on-surface truncate">
                        #{{ session.id }} {{ session.instrument?.name || 'Session' }}
                      </p>
                    </div>

                    <div
                      v-if="day.sessions.length === 0"
                      class="h-20 border border-dashed border-on-surface/10 dark:border-on-surface/10 rounded-2xl flex items-center justify-center opacity-30"
                    >
                      <span class="material-symbols-outlined text-sm">event_busy</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Global Add Section -->
          <div
            class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 p-2 px-4 -mx-2 mt-4"
          >
            <div class="col-span-1"></div>
            <button
              class="col-span-5 border-2 border-dashed border-on-surface/[0.08] dark:border-on-surface/10 rounded-3xl p-4 flex items-center justify-center gap-2 text-on-surface-variant dark:text-on-surface-variant hover:border-primary/50 hover:text-primary transition-all cursor-pointer bg-on-surface/[0.02] dark:bg-on-surface/[0.02] uppercase text-sm font-bold"
              @click="showAddSessionModal = true"
            >
              <span class="material-symbols-outlined">add_circle</span>
              Assign New Session
            </button>
          </div>
        </section>

        <!-- Faculty & Staff -->
        <section
          class="liquid-glass rounded-3xl p-4 border border-on-surface/[0.04] dark:border-on-surface/5 overflow-hidden"
        >
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <h3 class="text-2xl font-semibold tracking-tight text-on-surface dark:text-on-surface">
              Faculty &amp; Staff
            </h3>
            <div class="flex items-center gap-3">
              <div v-if="showTeacherSearch" class="relative">
                <input
                  v-model="teacherSearch"
                  type="text"
                  placeholder="Search faculty..."
                  class="pl-10 pr-4 py-2 bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.08] dark:border-on-surface/10 rounded-2xl text-xs focus:outline-none focus:ring-1 focus:ring-primary/50 w-48 transition-all"
                  @keyup.esc="showTeacherSearch = false; teacherSearch = ''"
                />
                <span
                  class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-sm text-on-surface-variant"
                  >search</span
                >
              </div>
              <button
                :class="{ 'text-primary bg-primary/5': showTeacherSearch }"
                class="px-4 py-2 bg-on-surface/[0.04] dark:bg-on-surface/5 text-on-surface-variant dark:text-on-surface-variant text-xs font-semibold uppercase border border-on-surface/[0.08] dark:border-on-surface/10 rounded-2xl hover:bg-on-surface/5 dark:hover:bg-on-surface/10 transition-colors flex items-center gap-2"
                @click="showTeacherSearch = !showTeacherSearch"
              >
                <span class="material-symbols-outlined text-sm">filter_list</span>
                Filter
              </button>
              <RouterLink
                to="/admin/users?action=create"
                class="px-4 py-2 bg-primary text-on-primary text-xs font-semibold uppercase rounded-2xl hover:opacity-90 transition-opacity flex items-center gap-2 shadow-lg"
              >
                <span class="material-symbols-outlined text-sm">person_add</span>
                Add Member
              </RouterLink>
            </div>
          </div>

          <div v-if="usersStore.isLoading" class="space-y-4">
            <div
              v-for="i in 3"
              :key="i"
              class="h-16 rounded-2xl bg-on-surface/[0.04] dark:bg-on-surface/5 animate-pulse"
            />
          </div>

          <div v-else-if="teachers.length === 0" class="py-10 text-center">
            <span
              class="material-symbols-outlined text-4xl text-on-surface-variant/50 dark:text-on-surface-variant/40 mb-2 block"
              >group_off</span
            >
            <p class="text-sm font-bold text-on-surface dark:text-on-surface mb-1">
              No faculty members yet
            </p>
          </div>

          <div v-else class="overflow-x-auto">
            <table class="data-table">
              <thead>
                <tr
                  class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase"
                >
                  <th class="pb-6">Member</th>
                  <th class="pb-6">Department</th>
                  <th class="pb-6">Status</th>
                  <th class="pb-6">Sessions</th>
                  <th class="pb-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-on-surface/[0.04] dark:divide-on-surface/5">
                <tr
                  v-for="teacher in filteredTeachers"
                  :key="teacher.id"
                  class="group hover:bg-on-surface/[0.02] dark:hover:bg-on-surface/[0.02] transition-colors"
                >
                  <td>
                    <div class="flex items-center gap-4">
                      <div
                        class="size-12 rounded-[18px] bg-surface-container-highest border border-on-surface/[0.08] dark:border-on-surface/10 flex items-center justify-center text-on-surface dark:text-on-surface font-semibold text-lg"
                      >
                        {{ teacher.name.charAt(0) }}
                      </div>
                      <div>
                        <p class="text-sm font-semibold text-on-surface dark:text-on-surface">
                          {{ teacher.name }}
                        </p>
                        <p class="text-xs text-on-surface-variant dark:text-on-surface-variant">
                          {{ teacher.email }}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span class="text-xs font-medium text-on-surface-variant">Music Faculty</span>
                  </td>
                  <td>
                    <span
                      class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    >
                      <span
                        class="size-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(52,211,153,0.5)]"
                      ></span>
                      Available
                    </span>
                  </td>
                  <td>
                    <span class="text-sm font-semibold text-on-surface dark:text-on-surface">
                      {{
                        scheduleStore.allSessions.filter((s: any) => s.teacherId === teacher.id)
                          .length
                      }}
                    </span>
                  </td>
                  <td class="text-right">
                    <div class="flex items-center justify-end gap-1">
                      <RouterLink
                        :to="`/admin/users?edit=${teacher.id}`"
                        class="p-2 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface transition-colors"
                      >
                        <span class="material-symbols-outlined text-lg">edit</span>
                      </RouterLink>
                      <button
                        class="p-2 text-on-surface-variant dark:text-on-surface-variant hover:text-red-400 transition-colors"
                        title="Deactivate Member"
                        @click="handleDeleteTeacher(teacher)"
                      >
                        <span class="material-symbols-outlined text-lg">delete</span>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <!-- Right: Alerts + Quick Assign -->
      <div class="space-y-4">
        <!-- Alerts & Updates -->
        <section
          class="liquid-glass rounded-3xl p-4 border border-on-surface/[0.04] dark:border-on-surface/5"
        >
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-lg font-semibold tracking-tight text-on-surface dark:text-on-surface">
              Alerts &amp; Updates
            </h3>
            <div class="flex items-center gap-2">
              <span
                v-if="notifStore.unreadCount > 0"
                class="text-xs font-semibold text-primary bg-primary/10 px-3 py-1 rounded-full border border-primary/20 flex items-center gap-1"
              >
                <span class="size-1.5 rounded-full bg-primary animate-pulse"></span>
                {{ notifStore.unreadCount }} NEW
              </span>
              <button
                v-if="notifStore.notifications.length > 0"
                class="text-xs font-semibold text-on-surface-variant hover:text-primary transition-colors uppercase"
                @click="handleClearAll"
              >
                Clear
              </button>
            </div>
          </div>
          <div class="space-y-4 max-h-[400px] overflow-y-auto p-1.5 custom-scrollbar">
            <!-- System Status (always show if relevant) -->
            <div
              v-if="stats.scheduledSessions > 0"
              class="bg-on-surface/[0.04] dark:bg-on-surface/5 p-3 rounded-3xl border-y border-primary/40 hover:bg-on-surface/5 dark:hover:bg-on-surface/10 transition-colors"
            >
              <div class="flex gap-4">
                <span class="material-symbols-outlined text-primary text-xl">warning</span>
                <div>
                  <h4
                    class="text-xs font-semibold uppercase mb-1 text-primary"
                  >
                    Schedule Alert
                  </h4>
                  <p class="text-xs text-on-surface-variant leading-relaxed">
                    {{ stats.scheduledSessions }} sessions running today
                  </p>
                </div>
              </div>
            </div>

            <!-- Dynamic Notifications -->
            <div
              v-if="notifStore.notifications.length === 0 && stats.scheduledSessions === 0"
              class="py-12 text-center opacity-40"
            >
              <span class="material-symbols-outlined text-3xl mb-2">notifications_off</span>
              <p class="text-xs font-bold uppercase">No recent updates</p>
            </div>

            <div
              v-for="notif in notifStore.notifications"
              :key="notif.id"
              class="bg-on-surface/[0.04] dark:bg-on-surface/5 p-3 rounded-3xl border-y transition-all hover:bg-on-surface/5 dark:hover:bg-on-surface/10 relative group"
              :class="[ notif.isRead ? 'border-zinc-500 opacity-60' : 'border-primary/30 ring-1 ring-primary/10 shadow-lg shadow-primary/5', ]"
            >
              <div class="flex gap-4">
                <span
                  class="material-symbols-outlined text-on-surface-variant dark:text-on-surface-variant text-xl"
                >
                  {{ notif.type === 'warning' ? 'warning' : 'info' }}
                </span>
                <div class="flex-1">
                  <h4
                    class="text-xs font-semibold uppercase mb-1"
                    :class="[notif.isRead ? 'text-zinc-500' : 'text-primary']"
                  >
                    {{ notif.title || 'Notification' }}
                  </h4>
                  <p class="text-xs text-on-surface dark:text-on-surface leading-relaxed">
                    {{ notif.message }}
                  </p>
                  <div class="flex items-center justify-between mt-3">
                    <p
                      class="text-xs text-on-surface-variant dark:text-on-surface-variant font-bold uppercase"
                    >
                      {{
                        new Date(notif.createdAt).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      }}
                    </p>
                    <button
                      v-if="!notif.isRead"
                      class="text-xs font-semibold text-primary uppercase hover:underline"
                      @click="handleMarkRead(notif.id)"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
              <RouterLink
                v-if="notif.link"
                :to="notif.link"
                class="absolute inset-0 z-0 cursor-pointer"
              />
            </div>
          </div>
          <RouterLink
            to="/admin/activity-log"
            class="flex items-center justify-center gap-2 w-full mt-8 py-4 text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.08] dark:border-on-surface/10 rounded-3xl hover:bg-on-surface/5 dark:hover:bg-on-surface/10 hover:text-on-surface dark:hover:text-on-surface transition-all uppercase"
          >
            <span class="material-symbols-outlined text-base">history</span>
            View All Activity
          </RouterLink>
        </section>

        <!-- Roster -->
        <section class="card card-pad space-y-6">
          <div class="flex items-start justify-between gap-4">
            <div class="space-y-1">
              <h3 class="section-title">Roster</h3>
              <p class="section-caption">Students on teacher rosters and their enrollments.</p>
            </div>
            <RouterLink to="/admin/roster" class="btn-subtle btn-sm">Manage</RouterLink>
          </div>

          <dl class="grid grid-cols-3 gap-4">
            <div class="space-y-1">
              <dd class="num text-2xl font-semibold text-on-surface">{{ rosterStore.assignments.length }}</dd>
              <dt class="text-xs text-on-surface-variant">Assignments</dt>
            </div>
            <div class="space-y-1">
              <dd class="num text-2xl font-semibold text-on-surface">{{ activeEnrollments }}</dd>
              <dt class="text-xs text-on-surface-variant">Active enrollments</dt>
            </div>
            <div class="space-y-1">
              <dd class="num text-2xl font-semibold text-on-surface">{{ unassignedStudents.length }}</dd>
              <dt class="text-xs text-on-surface-variant">Unassigned</dt>
            </div>
          </dl>

          <div v-if="unassignedStudents.length" class="space-y-3">
            <p class="field-hint">Not on any teacher's roster yet</p>
            <ul class="space-y-2">
              <li
                v-for="student in unassignedStudents.slice(0, 3)"
                :key="student.id"
                class="flex items-center justify-between gap-3 rounded-xl border border-outline-variant/20 px-4 py-3"
              >
                <span class="truncate text-sm text-on-surface">{{ student.name }}</span>
                <span class="num shrink-0 text-xs text-on-surface-variant">{{ student.sessionsLeft ?? 0 }} credits</span>
              </li>
            </ul>
            <RouterLink to="/admin/roster" class="btn-primary btn-sm w-full">Add students to a roster</RouterLink>
          </div>
          <p v-else class="section-caption">Every student is on a roster.</p>
        </section>

        <!-- Quick Assign -->
        <section
          class="bg-primary-container text-on-primary-container rounded-3xl p-4 shadow-e1 relative overflow-hidden"
        >
          <div
            class="absolute -top-10 -right-10 size-40 bg-on-surface/[0.06] dark:bg-on-surface/10 rounded-full blur-3xl"
          ></div>
          <div class="relative z-10">
            <h3 class="text-xl font-semibold mb-6 tracking-tight">Quick Assign</h3>
            <div class="space-y-4">
              <div>
                <label
                  class="text-xs font-semibold uppercase text-on-surface/60 block mb-2"
                  >Teacher</label
                >
                <select
                  v-model="quickTeacherId"
                  class="input appearance-none"
                >
                  <option value="" class="text-on-surface">Select Faculty</option>
                  <option v-for="t in teachers" :key="t.id" :value="t.id" class="text-zinc-900">
                    {{ t.name }}
                  </option>
                </select>
              </div>
              <div>
                <label
                  class="text-xs font-semibold uppercase text-on-surface/60 block mb-2"
                  >Student</label
                >
                <select
                  v-model="quickStudentId"
                  class="input appearance-none"
                >
                  <option value="" class="text-on-surface">Select Student</option>
                  <option v-for="s in students" :key="s.id" :value="s.id" class="text-zinc-900">
                    {{ s.name }}
                  </option>
                </select>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label
                    class="text-xs font-semibold uppercase text-on-surface/60 block mb-2"
                    >Date</label
                  >
                  <input
                    v-model="quickDate"
                    type="date"
                    class="input [color-scheme:dark]"
                  />
                </div>
                <div>
                  <label
                    class="text-xs font-semibold uppercase text-on-surface/60 block mb-2"
                    >Time</label
                  >
                  <input
                    v-model="quickTime"
                    type="time"
                    class="input [color-scheme:dark]"
                  />
                </div>
              </div>
              <button
                :disabled="!quickTeacherId || !quickStudentId || isQuickAssigning"
                class="w-full bg-on-surface/30 border border-on-surface/20 text-on-surface font-semibold py-4 rounded-3xl shadow-lg mt-4 active:scale-95 transition-all uppercase text-xs disabled:opacity-50 disabled:cursor-not-allowed"
                @click="confirmQuickAssign"
              >
                {{ isQuickAssigning ? 'Scheduling...' : 'Confirm Schedule' }}
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>

  <!-- Session Detail Modal -->
  <SessionDetailModal
    :session="selectedSession"
    user-role="admin"
    :current-user-id="authStore.currentUser?.id ?? 0"
    :users="allUsers"
    @close="selectedSession = null"
    @approve-admin="
      (id: number) => {
        handleApproveAdmin(id)
        selectedSession = null
      }
    "
    @reject-admin="
      (id: number) => {
        handleRejectAdmin(id)
        selectedSession = null
      }
    "
    @complete-admin="
      (id: number) => {
        handleCompleteAdmin(id)
        selectedSession = null
      }
    "
    @reject-proof-admin="
      (id: number) => {
        handleRejectProofAdmin(id)
        selectedSession = null
      }
    "
    @approve-teacher="
      (id: number) => {
        handleApproveAdmin(id)
        selectedSession = null
      }
    "
    @reject-teacher="
      (id: number) => {
        handleRejectAdmin(id)
        selectedSession = null
      }
    "
    @counter-teacher="
      (s: any) => {
        handleApproveAdmin(s.id)
        selectedSession = null
      }
    "
    @approve-student="
      (id: number) => {
        handleApproveAdmin(id)
        selectedSession = null
      }
    "
    @reject-student="
      async (id: number) => {
        try { await scheduleStore.rejectAsStudent(id); await scheduleStore.fetchAllSessions() } catch { toast.error('Action failed') }
        selectedSession = null
      }
    "
    @counter-student="
      (s: any) => {
        handleApproveAdmin(s.id)
        selectedSession = null
      }
    "
    @edit-admin="
      () => {
        selectedSession = null
        showAddSessionModal = true
      }
    "
    @nudge="
      (id: number) => {
        scheduleStore.nudgeSession(id)
        selectedSession = null
      }
    "
  />

  <!-- Add Session Modal -->
  <ProposeSessionModal
    v-if="showAddSessionModal"
    :is-open="showAddSessionModal"
    user-role="admin"
    :current-user-id="authStore.currentUser?.id ?? 0"
    :teachers="teachers"
    :students="students"
    @close="showAddSessionModal = false"
    @submitted="onProposeSubmit"
  />
</template>

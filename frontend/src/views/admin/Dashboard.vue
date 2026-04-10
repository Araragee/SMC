<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useScheduleStore } from '../../stores/schedule'
import { useUsersStore } from '../../stores/users'
import { useAuthStore } from '../../stores/auth'
import { useNotificationStore } from '../../stores/notification'
import { useToastStore } from '../../stores/toast'
import ProposeSessionModal from '../../components/ProposeSessionModal.vue'
import SessionDetailModal from '../../components/SessionDetailModal.vue'
import type { Session } from '../../types'

const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()
const notifStore = useNotificationStore()
const toast = useToastStore()

const showAddSessionModal = ref(false)
const detailDate = ref<Date | null>(null)
const detailSessions = ref<Session[]>([])
const selectedSession = ref<Session | null>(null)
const sessionPage = ref(0)
const PAGE_SIZE = 5
const viewMode = ref<'daily' | 'weekly'>('daily')
const quickTeacherId = ref('')
const quickStudentId = ref('')
const isQuickAssigning = ref(false)
const quickDate = ref(new Date().toISOString().split('T')[0])
const quickTime = ref(new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }))
const teacherSearch = ref('')
const showTeacherSearch = ref(false)

onMounted(async () => {
  await Promise.all([
    scheduleStore.fetchAllSessions(),
    scheduleStore.fetchPendingSessions(),
    usersStore.fetchUsersByRole('teacher'),
    usersStore.fetchUsersByRole('student'),
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
  const sessions = scheduleStore.allSessions
  const completed = sessions.filter((s) => s.status === 'completed').length
  const rate = sessions.length ? Math.round((completed / sessions.length) * 100) : 0
  return {
    totalSessions: sessions.length,
    scheduledSessions: sessions.filter((s) => s.status === 'scheduled').length,
    completedSessions: completed,
    completionRate: rate,
  }
})

const topInstruments = computed(() => {
  const counts: Record<string, number> = {}
  scheduleStore.allSessions.forEach((s) => {
    const name = s.instrument?.name || 'Theory'
    counts[name] = (counts[name] || 0) + 1
  })
  return Object.entries(counts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 3)
})

const hourlyDistribution = computed(() => {
  const hours = new Array(8).fill(0) // 9am to 5pm
  scheduleStore.allSessions.forEach((s) => {
    const hr = new Date(s.startTime).getHours()
    if (hr >= 9 && hr <= 16) hours[hr - 9]++
  })
  const max = Math.max(...hours, 1)
  return hours.map((v) => (v / max) * 100)
})

const todaySessions = computed(() => {
  const today = new Date().toDateString()
  return scheduleStore.allSessions.filter((s) => new Date(s.startTime).toDateString() === today)
})

const weeklySessions = computed(() => {
  const now = new Date()
  const grouped: Record<string, Session[]> = {}

  // Fill 7 days
  for (let i = 0; i < 7; i++) {
    const d = new Date(now.getTime() + i * 24 * 60 * 60 * 1000)
    grouped[d.toDateString()] = []
  }

  scheduleStore.allSessions.forEach((s) => {
    const d = new Date(s.startTime).toDateString()
    if (grouped[d]) grouped[d].push(s)
  })

  return Object.entries(grouped).map(([date, sessions]) => ({
    date: new Date(date),
    sessions: sessions.sort(
      (a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime()
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
  'bg-orange-500/20 text-orange-400': status === 'pending_student',
  'bg-blue-600/20 text-blue-300': status === 'pending_admin',
  'bg-red-500/20 text-red-400': status === 'rejected' || status === 'cancelled',
})

const borderColor = (status: string) => ({
  'border-l-emerald-500': status === 'completed',
  'border-l-orange-500': status === 'scheduled' || status === 'pending_student',
  'border-l-amber-500': status === 'pending_teacher' || status === 'ongoing',
  'border-l-blue-500': status === 'pending_admin',
  'border-l-red-500': status === 'rejected' || status === 'cancelled',
})

const iconClass = (status: string) => ({
  'bg-emerald-500/10 text-emerald-400 border-emerald-500/20': status === 'completed',
  'bg-orange-500/10 text-orange-400 border-orange-500/20': status === 'scheduled' || status === 'pending_student',
  'bg-amber-500/10 text-amber-400 border-amber-500/20': status === 'pending_teacher' || status === 'ongoing',
  'bg-blue-500/10 text-blue-400 border-blue-500/20': status === 'pending_admin',
  'bg-red-500/10 text-red-400 border-red-500/20': status === 'rejected' || status === 'cancelled',
})

const onProposeSubmit = async function(session: Session) {
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

const openSessionDetail = function(session: Session) {
  selectedSession.value = session
}

const refreshDetailSessions = function() {
  if (!detailDate.value) return
  const dateStr = detailDate.value.toDateString()
  detailSessions.value = scheduleStore.allSessions.filter(
    (s) => new Date(s.startTime).toDateString() === dateStr
  )
}

const handleApproveAdmin = async function(sessionId: string) {
  const session = scheduleStore.allSessions.find((s) => s.id === sessionId)
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

const handleRejectAdmin = async function(sessionId: string) {
  const session = scheduleStore.allSessions.find((s) => s.id === sessionId)
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

const handleCompleteAdmin = async function(sessionId: string) {
  try {
    await scheduleStore.completeSession(sessionId)
    toast.success('Session Completed', 'The session has been successfully finalized.')
    await scheduleStore.fetchAllSessions()
    refreshDetailSessions()
  } catch (err: any) {
    toast.error('Failed to complete', err.message || 'Something went wrong.')
  }
}

const handleRejectProofAdmin = async function(sessionId: string) {
  const reason = window.prompt("Enter a reason for rejecting this proof:")
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

const confirmQuickAssign = async function() {
  if (!quickTeacherId.value || !quickStudentId.value) return
  isQuickAssigning.value = true
  try {
    const [y, m, d] = quickDate.value.split('-').map(Number)
    const [hr, min] = quickTime.value.split(':').map(Number)
    const startTime = new Date(y, m - 1, d, hr, min)
    const endTime = new Date(startTime.getTime() + 60 * 60 * 1000) // 1hr
    await scheduleStore.bookSession({
      teacherId: quickTeacherId.value,
      studentId: quickStudentId.value,
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

const handleDeleteTeacher = async function(teacher: any) {
  if (!window.confirm(`Are you sure you want to deactivate ${teacher.name}?`)) return
  try {
    await usersStore.deleteUser(teacher.id)
    toast.success('Member deactivated', `${teacher.name} has been removed from active faculty.`)
  } catch (err: any) {
    toast.error('Failed to deactivate', err.message || 'Something went wrong.')
  }
}

const handleMarkRead = async function(notifId: string) {
  await notifStore.markAsRead(notifId)
}

const handleClearAll = async function() {
  if (authStore.currentUser?.id) {
    await notifStore.markAllAsRead(authStore.currentUser.id)
  }
}

const openLiveAnalytics = function() {
  detailDate.value = new Date()
  detailSessions.value = todaySessions.value
}
</script>

<template>
  <div class="max-w-[1600px] mx-auto pb-28 space-y-4 px-4 sm:px-6">
    <!-- Page Header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-5xl font-black tracking-tight text-on-surface dark:text-on-surface mb-2">
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
        class="col-span-1 md:col-span-2 lg:col-span-3 xl:col-span-2 liquid-glass p-6 rounded-3xl border border-black/[0.04] dark:border-white/5 flex flex-col justify-between cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 transition-all group active:scale-[0.99] shadow-lg shadow-black/[0.02]"
        @click="openLiveAnalytics"
      >
        <div class="flex justify-between items-start">
          <div>
            <span class="text-[10px] font-black text-orange-500 uppercase tracking-[0.2em]"
              >Live Analytics</span
            >
            <div
              v-if="scheduleStore.isLoading"
              class="h-10 w-48 rounded bg-black/[0.04] dark:bg-white/5 animate-pulse mt-2"
            />
            <h2
              v-else
              class="text-3xl font-black mt-2 tracking-tight text-on-surface dark:text-on-surface"
            >
              {{ stats.scheduledSessions }} Active Today
            </h2>
            <p class="text-on-surface-variant dark:text-on-surface-variant text-sm mt-1">
              Real-time occupancy across departments
            </p>
          </div>
          <div class="flex gap-1 h-8 items-end">
            <div
              v-for="(h, i) in hourlyDistribution"
              :key="i"
              class="w-2 bg-primary/20 rounded-t-sm transition-all duration-1000"
              :style="{
                height: `${h}%`,
                backgroundColor: h > 70 ? 'var(--md-sys-color-primary)' : '',
              }"
            ></div>
          </div>
        </div>

        <div class="space-y-4 mt-8">
          <div
            class="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-on-surface-variant"
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
                class="w-1.5 h-1.5 rounded-full bg-primary shadow-[0_0_8px_rgba(var(--primary-rgb),0.5)]"
              ></span>
              <span class="text-[11px] font-black text-on-surface uppercase tracking-wider">{{
                inst.name
              }}</span>
              <span class="text-[10px] font-bold text-primary opacity-60">{{ inst.count }}</span>
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
        class="bg-gradient-to-br from-orange-500 to-orange-700 p-4 rounded-3xl shadow-xl shadow-orange-900/30 flex flex-col justify-between relative overflow-hidden group"
      >
        <div class="absolute -right-6 -bottom-6 opacity-20 w-40 h-40">
          <img src="/logo.png" alt="Logo" class="w-full h-full object-contain" />
        </div>
        <div class="relative z-10">
          <span class="text-[10px] font-black text-white/70 uppercase tracking-[0.2em]"
            >Retention Rate</span
          >
          <div
            v-if="scheduleStore.isLoading"
            class="h-14 w-20 rounded bg-white/20 animate-pulse mt-2"
          />
          <h2 v-else class="text-5xl font-black mt-2 tracking-tighter text-white">
            {{ stats.completionRate }}%
          </h2>
        </div>
        <p class="text-xs text-white/80 font-medium relative z-10">
          Exceeding national music academy benchmarks
        </p>
      </div>

      <!-- New Registrations -->
      <div
        class="liquid-glass p-4 rounded-3xl border border-black/[0.04] dark:border-white/5 flex flex-col justify-between"
      >
        <div>
          <span
            class="text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-[0.2em]"
            >New Registrations</span
          >
          <div
            v-if="usersStore.isLoading"
            class="h-14 w-16 rounded bg-black/[0.04] dark:bg-white/5 animate-pulse mt-2"
          />
          <h2
            v-else
            class="text-5xl font-black mt-2 tracking-tighter text-on-surface dark:text-on-surface"
          >
            {{ students.length }}
          </h2>
        </div>
        <div class="flex -space-x-3 mt-6">
          <div
            v-for="(s, i) in students.slice(0, 3)"
            :key="s.id"
            class="w-10 h-10 rounded-full border-2 border-surface-container-highest bg-surface-container-highest flex items-center justify-center text-on-surface dark:text-on-surface font-black text-xs"
            :style="{ zIndex: 3 - i }"
          >
            {{ s.name.charAt(0) }}
          </div>
          <div
            v-if="students.length > 3"
            class="w-10 h-10 rounded-full border-2 border-surface-container-highest bg-gradient-to-br from-orange-500 to-orange-700 text-white text-[10px] font-black flex items-center justify-center"
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
          <span class="text-[10px] font-black text-amber-500 uppercase tracking-[0.2em]"
            >Pending Approvals</span
          >
          <div
            v-if="scheduleStore.isLoading"
            class="h-14 w-16 rounded bg-black/[0.04] dark:bg-white/5 animate-pulse mt-2"
          />
          <h2
            v-else
            class="text-5xl font-black mt-2 tracking-tighter"
            :class="
              scheduleStore.pendingSessions.length > 0
                ? 'text-amber-400'
                : 'text-on-surface dark:text-on-surface'
            "
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
    </section>

    <!-- Main Layout -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <!-- Left: Schedule + Faculty -->
      <div class="col-span-1 md:col-span-2 lg:col-span-3 xl:col-span-2 space-y-4">
        <!-- Music Schedule -->
        <section
          class="liquid-glass rounded-3xl p-6 border border-black/[0.04] dark:border-white/5"
        >
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
            <div>
              <h3 class="text-2xl font-black tracking-tight text-on-surface dark:text-on-surface">
                Music Schedule
              </h3>
              <p class="text-on-surface-variant dark:text-on-surface-variant text-sm">
                {{ viewMode === 'daily' ? 'Managing for today' : 'Upcoming week overview' }}
              </p>
            </div>
            <div class="flex items-center gap-2">
              <!-- View Mode Toggle -->
              <div
                class="flex bg-black/5 dark:bg-white/5 p-1 rounded-2xl border border-black/5 dark:border-white/5 mr-2"
              >
                <button
                  class="px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
                  :class="
                    viewMode === 'daily'
                      ? 'bg-primary text-white shadow-md'
                      : 'text-on-surface-variant hover:text-on-surface'
                  "
                  @click="viewMode = 'daily'"
                >
                  Today
                </button>
                <button
                  class="px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
                  :class="
                    viewMode === 'weekly'
                      ? 'bg-primary text-white shadow-md'
                      : 'text-on-surface-variant hover:text-on-surface'
                  "
                  @click="viewMode = 'weekly'"
                >
                  Weekly
                </button>
              </div>

              <div v-if="viewMode === 'daily'" class="flex gap-2">
                <button
                  class="p-2 bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-xl hover:bg-black/5 dark:hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                  :disabled="!canGoPrev"
                  @click="sessionPage--"
                >
                  <span class="material-symbols-outlined text-sm">chevron_left</span>
                </button>
                <button
                  class="p-2 bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-xl hover:bg-black/5 dark:hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
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
              class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 py-2 border-b border-black/[0.04] dark:border-white/5 mb-4 px-2"
            >
              <div
                class="text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-[0.2em] col-span-1"
              >
                Time
              </div>
              <div
                class="text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-[0.2em] col-span-5"
              >
                Sessions &amp; Instructors
              </div>
            </div>

            <!-- Loading -->
            <div v-if="scheduleStore.isLoading" class="space-y-4">
              <div
                v-for="i in 3"
                :key="i"
                class="h-20 rounded-3xl bg-black/[0.04] dark:bg-white/5 animate-pulse"
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
                class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 group hover:bg-black/5 dark:hover:bg-white/5 transition-all rounded-3xl p-2 px-4 -mx-2"
              >
                <div class="col-span-1 flex flex-col justify-center">
                  <span class="text-sm font-black">{{ formatTime(session.startTime) }}</span>
                  <span
                    class="text-[10px] text-on-surface-variant dark:text-on-surface-variant uppercase font-bold tracking-widest"
                    >{{ formatAmPm(session.startTime) }}</span
                  >
                </div>
                <div
                  class="col-span-5 bg-black/[0.04] dark:bg-white/5 border-l-4 p-5 rounded-3xl flex items-center justify-between cursor-pointer hover:bg-black/[0.08] dark:hover:bg-white/10 transition-colors"
                  :class="borderColor(session.status)"
                  @click="openSessionDetail(session)"
                >
                  <div class="flex items-center gap-4">
                    <div
                      class="w-10 h-10 rounded-xl flex items-center justify-center shadow-sm border"
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
                  <div class="flex items-center gap-3">
                    <span
                      class="text-[10px] px-3 py-1 rounded-full font-black uppercase tracking-wider"
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
                  class="flex-1 min-w-[180px] bg-black/[0.02] dark:bg-white/[0.02] rounded-3xl p-4 border border-black/[0.04] dark:border-white/5 flex flex-col"
                >
                  <div class="mb-4 text-center">
                    <p class="text-[9px] font-black text-primary uppercase tracking-widest mb-1">
                      {{ day.date.toLocaleDateString('en-US', { weekday: 'short' }) }}
                    </p>
                    <p class="text-lg font-black text-on-surface">{{ day.date.getDate() }}</p>
                  </div>

                  <div class="space-y-2 flex-1">
                    <div
                      v-for="session in day.sessions"
                      :key="session.id"
                      class="bg-white dark:bg-white/5 p-3 rounded-2xl border-l-[3px] border shadow-sm hover:scale-[1.02] transition-all cursor-pointer"
                      :class="[borderColor(session.status), 'border-black/5 dark:border-white/10']"
                      @click="openSessionDetail(session)"
                    >
                      <p class="text-[8px] font-bold text-on-surface-variant uppercase mb-1">
                        {{ formatTime(session.startTime) }}
                      </p>
                      <p class="text-[10px] font-black text-on-surface truncate">
                        #{{ session.id }} {{ session.instrument?.name || 'Session' }}
                      </p>
                    </div>

                    <div
                      v-if="day.sessions.length === 0"
                      class="h-20 border border-dashed border-black/10 dark:border-white/10 rounded-2xl flex items-center justify-center opacity-30"
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
              class="col-span-5 border-2 border-dashed border-black/[0.08] dark:border-white/10 rounded-3xl p-4 flex items-center justify-center gap-2 text-on-surface-variant dark:text-on-surface-variant hover:border-orange-500/50 hover:text-orange-500 transition-all cursor-pointer bg-black/[0.02] dark:bg-white/[0.02] uppercase tracking-widest text-sm font-bold"
              @click="showAddSessionModal = true"
            >
              <span class="material-symbols-outlined">add_circle</span>
              Assign New Session
            </button>
          </div>
        </section>

        <!-- Faculty & Staff -->
        <section
          class="liquid-glass rounded-3xl p-4 border border-black/[0.04] dark:border-white/5 overflow-hidden"
        >
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <h3 class="text-2xl font-black tracking-tight text-on-surface dark:text-on-surface">
              Faculty &amp; Staff
            </h3>
            <div class="flex items-center gap-3">
              <div v-if="showTeacherSearch" class="relative">
                <input
                  v-model="teacherSearch"
                  type="text"
                  placeholder="Search faculty..."
                  class="pl-10 pr-4 py-2 bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl text-xs focus:outline-none focus:ring-1 focus:ring-orange-500/50 w-48 transition-all"
                  @keyup.esc="
                    showTeacherSearch = false;
                    teacherSearch = '';
                  "
                />
                <span
                  class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-sm text-on-surface-variant"
                  >search</span
                >
              </div>
              <button
                :class="{ 'text-orange-500 bg-orange-500/5': showTeacherSearch }"
                class="px-5 py-2.5 bg-black/[0.04] dark:bg-white/5 text-on-surface-variant dark:text-on-surface-variant text-[10px] font-black uppercase tracking-widest border border-black/[0.08] dark:border-white/10 rounded-2xl hover:bg-black/5 dark:hover:bg-white/10 transition-colors flex items-center gap-2"
                @click="showTeacherSearch = !showTeacherSearch"
              >
                <span class="material-symbols-outlined text-sm">filter_list</span>
                Filter
              </button>
              <RouterLink
                to="/admin/users?action=create"
                class="px-5 py-2.5 bg-gradient-to-br from-orange-500 to-orange-700 text-white text-[10px] font-black uppercase tracking-widest rounded-2xl hover:opacity-90 transition-opacity flex items-center gap-2 shadow-lg shadow-orange-900/30"
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
              class="h-16 rounded-2xl bg-black/[0.04] dark:bg-white/5 animate-pulse"
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
            <table class="w-full text-left">
              <thead>
                <tr
                  class="text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-[0.2em]"
                >
                  <th class="pb-6 px-2">Member</th>
                  <th class="pb-6 px-2">Department</th>
                  <th class="pb-6 px-2">Status</th>
                  <th class="pb-6 px-2">Sessions</th>
                  <th class="pb-6 px-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-black/[0.04] dark:divide-white/5">
                <tr
                  v-for="teacher in filteredTeachers"
                  :key="teacher.id"
                  class="group hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors"
                >
                  <td class="py-6 px-2">
                    <div class="flex items-center gap-4">
                      <div
                        class="w-12 h-12 rounded-[18px] bg-surface-container-highest border border-black/[0.08] dark:border-white/10 flex items-center justify-center text-on-surface dark:text-on-surface font-black text-lg"
                      >
                        {{ teacher.name.charAt(0) }}
                      </div>
                      <div>
                        <p class="text-sm font-black text-on-surface dark:text-on-surface">
                          {{ teacher.name }}
                        </p>
                        <p class="text-xs text-on-surface-variant dark:text-on-surface-variant">
                          {{ teacher.email }}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td class="py-6 px-2">
                    <span class="text-xs font-medium text-on-surface-variant">Music Faculty</span>
                  </td>
                  <td class="py-6 px-2">
                    <span
                      class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    >
                      <span
                        class="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(52,211,153,0.5)]"
                      ></span>
                      Available
                    </span>
                  </td>
                  <td class="py-6 px-2">
                    <span class="text-sm font-black text-on-surface dark:text-on-surface">
                      {{
                        scheduleStore.allSessions.filter((s) => s.teacherId === teacher.id).length
                      }}
                    </span>
                  </td>
                  <td class="py-6 px-2 text-right">
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
          class="liquid-glass rounded-3xl p-4 border border-black/[0.04] dark:border-white/5"
        >
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-lg font-black tracking-tight text-on-surface dark:text-on-surface">
              Alerts &amp; Updates
            </h3>
            <div class="flex items-center gap-2">
              <span
                v-if="notifStore.unreadCount > 0"
                class="text-[10px] font-black text-orange-500 bg-orange-500/10 px-3 py-1 rounded-full border border-orange-500/20 flex items-center gap-1"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-orange-400 animate-pulse"></span>
                {{ notifStore.unreadCount }} NEW
              </span>
              <button
                v-if="notifStore.notifications.length > 0"
                class="text-[10px] font-black text-on-surface-variant hover:text-primary transition-colors uppercase tracking-widest"
                @click="handleClearAll"
              >
                Clear
              </button>
            </div>
          </div>
          <div class="space-y-4 max-h-[400px] overflow-y-auto pr-1 custom-scrollbar">
            <!-- System Status (always show if relevant) -->
            <div
              v-if="stats.scheduledSessions > 0"
              class="bg-black/[0.04] dark:bg-white/5 p-5 rounded-3xl border-l-4 border-orange-500 hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
            >
              <div class="flex gap-4">
                <span class="material-symbols-outlined text-orange-500 text-xl">warning</span>
                <div>
                  <h4
                    class="text-[10px] font-black uppercase tracking-[0.2em] mb-1 text-orange-400"
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
              <p class="text-xs font-bold uppercase tracking-widest">No recent updates</p>
            </div>

            <div
              v-for="notif in notifStore.notifications"
              :key="notif.id"
              class="bg-black/[0.04] dark:bg-white/5 p-5 rounded-3xl border-l-4 transition-all hover:bg-black/5 dark:hover:bg-white/10 relative group"
              :class="[
                notif.isRead
                  ? 'border-zinc-500 opacity-60'
                  : 'border-primary ring-1 ring-primary/10 shadow-lg shadow-primary/5',
              ]"
            >
              <div class="flex gap-4">
                <span
                  class="material-symbols-outlined text-on-surface-variant dark:text-on-surface-variant text-xl"
                >
                  {{ notif.type === 'warning' ? 'warning' : 'info' }}
                </span>
                <div class="flex-1">
                  <h4
                    class="text-[10px] font-black uppercase tracking-[0.2em] mb-1"
                    :class="[notif.isRead ? 'text-zinc-500' : 'text-primary']"
                  >
                    {{ notif.title || 'Notification' }}
                  </h4>
                  <p class="text-xs text-on-surface dark:text-on-surface leading-relaxed">
                    {{ notif.message }}
                  </p>
                  <div class="flex items-center justify-between mt-3">
                    <p
                      class="text-[9px] text-on-surface-variant dark:text-on-surface-variant font-bold uppercase"
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
                      class="text-[9px] font-black text-primary uppercase tracking-widest hover:underline"
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
          <button
            v-if="notifStore.notifications.length > 5"
            class="w-full mt-8 py-4 text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-3xl hover:bg-black/5 dark:hover:bg-white/10 transition-all uppercase tracking-[0.2em]"
            @click="toast.info('Roadmap Item', 'The Full Activity Log is planned for Phase 3.')"
          >
            View All Activity
          </button>
        </section>

        <!-- Quick Assign -->
        <section
          class="bg-gradient-to-br from-orange-500 to-orange-700 rounded-3xl p-4 text-white shadow-xl shadow-orange-900/30 relative overflow-hidden"
        >
          <div
            class="absolute -top-10 -right-10 w-40 h-40 bg-black/[0.06] dark:bg-white/10 rounded-full blur-3xl"
          ></div>
          <div class="relative z-10">
            <h3 class="text-xl font-black mb-6 tracking-tight">Quick Assign</h3>
            <div class="space-y-5">
              <div>
                <label
                  class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60 block mb-2"
                  >Teacher</label
                >
                <select
                  v-model="quickTeacherId"
                  class="w-full bg-white/20 backdrop-blur-md rounded-2xl px-5 py-3 text-xs font-bold border border-white/20 focus:outline-none focus:ring-1 focus:ring-white/40 hover:bg-white/30 transition-all appearance-none cursor-pointer text-white"
                >
                  <option value="" class="text-on-surface">Select Faculty</option>
                  <option v-for="t in teachers" :key="t.id" :value="t.id" class="text-zinc-900">
                    {{ t.name }}
                  </option>
                </select>
              </div>
              <div>
                <label
                  class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60 block mb-2"
                  >Student</label
                >
                <select
                  v-model="quickStudentId"
                  class="w-full bg-white/20 backdrop-blur-md rounded-2xl px-5 py-3 text-xs font-bold border border-white/20 focus:outline-none focus:ring-1 focus:ring-white/40 hover:bg-white/30 transition-all appearance-none cursor-pointer text-white"
                >
                  <option value="" class="text-on-surface">Select Student</option>
                  <option v-for="s in students" :key="s.id" :value="s.id" class="text-zinc-900">
                    {{ s.name }}
                  </option>
                </select>
              </div>
              
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60 block mb-2">Date</label>
                  <input
                    v-model="quickDate"
                    type="date"
                    class="w-full bg-white/20 backdrop-blur-md rounded-2xl px-5 py-3 text-xs font-bold border border-white/20 focus:outline-none focus:ring-1 focus:ring-white/40 hover:bg-white/30 transition-all cursor-pointer text-white [color-scheme:dark]"
                  />
                </div>
                <div>
                  <label class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60 block mb-2">Time</label>
                  <input
                    v-model="quickTime"
                    type="time"
                    class="w-full bg-white/20 backdrop-blur-md rounded-2xl px-5 py-3 text-xs font-bold border border-white/20 focus:outline-none focus:ring-1 focus:ring-white/40 hover:bg-white/30 transition-all cursor-pointer text-white [color-scheme:dark]"
                  />
                </div>
              </div>
              <button
                :disabled="!quickTeacherId || !quickStudentId || isQuickAssigning"
                class="w-full bg-black/30 backdrop-blur-xl border border-white/20 text-white font-black py-4 rounded-3xl shadow-lg mt-4 active:scale-95 transition-all duration-150 uppercase text-[10px] tracking-[0.2em] disabled:opacity-50 disabled:cursor-not-allowed"
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
    :current-user-id="authStore.currentUser?.id ?? ''"
    :users="allUsers"
    @close="selectedSession = null"
  @approve-admin="(id: string) => { handleApproveAdmin(id); selectedSession = null }"
  @reject-admin="(id: string) => { handleRejectAdmin(id); selectedSession = null }"
  @complete-admin="(id: string) => { handleCompleteAdmin(id); selectedSession = null }"
  @reject-proof-admin="(id: string) => { handleRejectProofAdmin(id); selectedSession = null }"
  @approve-teacher="(id: string) => { handleApproveAdmin(id); selectedSession = null }"
  @reject-teacher="(id: string) => { handleRejectAdmin(id); selectedSession = null }"
  @counter-teacher="(s: any) => { handleApproveAdmin(s.id); selectedSession = null }"
  @approve-student="(id: string) => { handleApproveAdmin(id); selectedSession = null }"
  @counter-student="(s: any) => { handleApproveAdmin(s.id); selectedSession = null }"
    @edit-admin="() => { selectedSession = null; showAddSessionModal = true; }"
  @nudge="(id: string) => { scheduleStore.nudgeSession(id); selectedSession = null }"
  />

  <!-- Add Session Modal -->
  <ProposeSessionModal
    v-if="showAddSessionModal"
    :is-open="showAddSessionModal"
    user-role="admin"
    :current-user-id="authStore.currentUser?.id ?? ''"
    :teachers="teachers"
    :students="students"
    @close="showAddSessionModal = false"
    @submitted="onProposeSubmit"
  />
</template>

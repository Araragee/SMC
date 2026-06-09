<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { API_URL } from '@typescript/constants'
import { useRoute } from 'vue-router'
import { useScheduleStore } from '@stores/schedule'
import { useUsersStore } from '@stores/users'
import { useAuthStore } from '@stores/auth'
import { useNotificationStore } from '@stores/notification'
import { useToastStore } from '@stores/toast'
import BaseCalendar from '@components/BaseCalendar.vue'
import SessionDetailModal from '@components/SessionDetailModal.vue'
import ProposeSessionModal from '@components/ProposeSessionModal.vue'
import RecurringSessionModal from '@components/RecurringSessionModal.vue'
import type { Session } from '@types'
import { useDialog } from '@composables/useDialog'

const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()
const notifStore = useNotificationStore()
const toast = useToastStore()
const dialog = useDialog()
const route = useRoute()

const selectedDate = ref<Date | null>(null)
const selectedDaySessions = ref<Session[]>([])
const selectedSession = ref<Session | null>(null)
const showProposeModal = ref(false)
const showRecurringModal = ref(false)
const filterStatus = ref('')
const selectedSessionIds = ref<number[]>([])

const rejectModal = ref({ open: false, sessionId: 0, notes: '' })
const editModal = ref({ open: false, sessionId: 0, date: '', time: '', notes: '' })

const teachers = computed(() => usersStore.getUsersByRole('teacher'))
const students = computed(() => usersStore.getUsersByRole('student'))
const allUsers = computed(() => usersStore.users)

const pendingSessions = computed(() => scheduleStore.pendingSessions)

const filteredSessions = computed(() => {
  const all = [...scheduleStore.allSessions].sort(
    (a: any, b: any) => new Date(b.startTime).getTime() - new Date(a.startTime).getTime()
  )
  if (!filterStatus.value) return all
  return all.filter((s: any) => s.status === filterStatus.value)
})

const toggleSelectAll = () => {
  if (selectedSessionIds.value.length === filteredSessions.value.length) {
    selectedSessionIds.value = []
  } else {
    selectedSessionIds.value = filteredSessions.value.map(s => s.id)
  }
}

const handleBulkAction = async (action: 'approve' | 'cancel' | 'complete') => {
  const count = selectedSessionIds.value.length
  let message = `Are you sure you want to bulk ${action} ${count} selected session(s)?`
  
  if (action === 'cancel') {
    const completedCount = scheduleStore.allSessions.filter(
      s => selectedSessionIds.value.includes(s.id) && s.status === 'completed'
    ).length
    if (completedCount > 0) {
      message += ` Warning: ${completedCount} of these are already completed and will be reverted (credits will be refunded).`
    }
  }

  const ok = await dialog.confirm(message, {
    title: `Bulk ${action.charAt(0).toUpperCase() + action.slice(1)}`,
    destructive: action === 'cancel'
  })
  if (!ok) return
  try {
    await scheduleStore.bulkAction(selectedSessionIds.value, action)
    selectedSessionIds.value = []
    await scheduleStore.fetchAllSessions()
  } catch {
    // Error notification handled by store
  }
}

onMounted(async () => {
  await Promise.all([
    scheduleStore.fetchAllSessions(),
    usersStore.fetchUsers(),
    notifStore.fetchNotifications(authStore.currentUser?.id ?? 0),
  ])

  if (route.query.session_id) {
    const sId = Number(route.query.session_id)
    const sessionToOpen = scheduleStore.allSessions.find(s => s.id === sId)
    if (sessionToOpen) {
      selectedDate.value = new Date(sessionToOpen.startTime)
      selectedDaySessions.value = [sessionToOpen]
      
      // Clear query string gracefully so refresh doesn't pop it again
      window.history.replaceState({}, document.title, window.location.pathname)
    }
  }
})

const getUserName = function(id: number): string  {
  return usersStore.users.find((u: any) => u.id === id)?.name ?? `User #${id}`
}

const onDayClick = function({ date, sessions }: { date: Date; sessions: Session[] }) {
  selectedDate.value = date
  selectedDaySessions.value = sessions
}

const onSessionClick = function(session: Session) {
  selectedSession.value = session
}

const exportingIcs = ref(false)
const exportIcs = async function() {
  if (exportingIcs.value) return
  exportingIcs.value = true
  try {
    const res = await axios.get(`${API_URL}/sessions/export.ics`, {
      headers: { Authorization: `Bearer ${authStore.token}` },
      responseType: 'blob',
    })
    const url = URL.createObjectURL(res.data as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'smc-schedule.ics'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    toast.success('Calendar exported')
  } catch {
    toast.error('Export failed')
  } finally {
    exportingIcs.value = false
  }
}

const handleApprove = async function(sessionId: number) {
  const session = scheduleStore.allSessions.find((s: any) => s.id === sessionId)
  try {
    if (session?.status === 'pending_teacher') {
      await scheduleStore.approveAsTeacher(sessionId)
    } else if (session?.status === 'pending_student') {
      await scheduleStore.approveAsStudent(sessionId)
    } else {
      await scheduleStore.approveAsAdmin(sessionId)
    }
    toast.success('Success', `Session advanced.`)
    selectedDate.value = null
    await scheduleStore.fetchAllSessions()
  } catch {
    toast.error('Failed', 'Action could not be completed.')
  }
}

const handleCompleteAdmin = async function(sessionId: number) {
  try {
    await scheduleStore.completeSession(sessionId)
    toast.success('Session Completed', 'The session has been successfully finalized.')
    selectedDate.value = null
    await scheduleStore.fetchAllSessions()
  } catch (err: any) {
    toast.error('Failed to complete', err.message || 'Something went wrong.')
  }
}

const handleRejectProofAdmin = async function(sessionId: number) {
  const reason = await dialog.prompt('Enter a reason for rejecting this proof:', {
    title: 'Reject Proof',
    placeholder: 'e.g. Image is unclear or incorrect session'
  })
  if (!reason) return
  try {
    await scheduleStore.rejectProof(sessionId, reason)
    toast.success('Proof Rejected', 'The student has been notified to re-upload.')
    selectedDate.value = null
    await scheduleStore.fetchAllSessions()
  } catch (err: any) {
    toast.error('Failed to reject proof', err.message || 'Something went wrong.')
  }
}

const openReject = function(sessionId: number) {
  rejectModal.value = { open: true, sessionId, notes: '' }
  selectedDate.value = null
}

const confirmReject = async function() {
  const session = scheduleStore.allSessions.find((s: any) => s.id === rejectModal.value.sessionId)
  try {
    if (session?.status === 'pending_teacher') {
      await scheduleStore.rejectAsTeacher(rejectModal.value.sessionId, rejectModal.value.notes)
    } else {
      await scheduleStore.rejectAsAdmin(rejectModal.value.sessionId, rejectModal.value.notes)
    }
    toast.success('Session updated')
    rejectModal.value.open = false
    await scheduleStore.fetchAllSessions()
  } catch {
    toast.error('Failed to update session')
  }
}

const openEdit = function(session: Session) {
  const d = new Date(session.startTime)
  editModal.value = {
    open: true,
    sessionId: session.id,
    date: d.toISOString().split('T')[0],
    time: d.toTimeString().slice(0, 5),
    notes: session.notes ?? '',
  }
  selectedDate.value = null
}

const confirmEdit = async function() {
  const { sessionId, date, time, notes } = editModal.value
  try {
    const [y, m, d] = date.split('-').map(Number)
    const [hr, min] = time.split(':').map(Number)
    const startTimeDt = new Date(y, m - 1, d, hr, min)
    const startTime = startTimeDt.toISOString()
    const endTime = new Date(startTimeDt.getTime() + 3600000).toISOString()
    await scheduleStore.editSession(sessionId, { startTime, endTime, notes })
    toast.success('Session updated!')
    editModal.value.open = false
  } catch {
    toast.error('Failed to update session')
  }
}

const onProposeSubmit = async function(session: Session) {
  try {
    await scheduleStore.bookSession(session)
    toast.success('Session scheduled!', 'The session has been confirmed and parties notified.')
    showProposeModal.value = false
  } catch {
    toast.error('Failed to schedule session')
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

const statusLabel = function(status: string): string  {
  const map: Record<string, string> = {
    scheduled: 'Confirmed',
    completed: 'Completed',
    pending_teacher: 'Awaiting Teacher',
    pending_admin: 'Awaiting Admin',
    rejected: 'Rejected',
    cancelled: 'Cancelled',
  }
  return map[status] ?? status
}

const statusBarClass = function(status: string): string  {
  const map: Record<string, string> = {
    scheduled: 'bg-orange-500',
    completed: 'bg-emerald-500',
    pending_teacher: 'bg-amber-500',
    pending_admin: 'bg-blue-500',
    rejected: 'bg-red-500',
    cancelled: 'bg-zinc-500',
  }
  return map[status] ?? 'bg-zinc-700'
}

const statusBadgeClass = function(status: string): string  {
  const map: Record<string, string> = {
    scheduled: 'bg-orange-500/20 border-orange-500/30 text-orange-400',
    completed: 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400',
    pending_teacher: 'bg-amber-500/20 border-amber-500/30 text-amber-400',
    pending_admin: 'bg-blue-500/20 border-blue-500/30 text-blue-400',
    rejected: 'bg-red-500/20 border-red-500/30 text-red-400',
    cancelled: 'bg-zinc-500/20 border-zinc-500/30 text-zinc-400',
  }
  return map[status] ?? 'bg-black/5 dark:bg-white/10 border-black/10 dark:border-white/20 text-on-surface-variant dark:text-on-surface-variant'
}
</script>

<template>
  <div class="max-w-[1600px] mx-auto pb-28 space-y-4 px-4 sm:px-6">
    <!-- Page Header -->
    <div
      class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 md:gap-6"
    >
      <div>
        <h1 class="text-5xl font-black tracking-tight text-on-surface dark:text-on-surface mb-2">Schedule</h1>
        <p class="text-on-surface-variant dark:text-on-surface-variant font-medium">Manage all sessions — approve, edit, and schedule.</p>
      </div>
      <div class="shrink-0 flex items-start gap-4">
        <button
          class="px-5 py-3 bg-white/60 dark:bg-zinc-800/60 backdrop-blur text-on-surface dark:text-on-surface font-semibold rounded-3xl shadow hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2 disabled:opacity-50"
          :disabled="exportingIcs"
          @click="exportIcs"
        >
          <span class="material-symbols-outlined text-lg">calendar_month</span>
          {{ exportingIcs ? 'Exporting…' : 'Export .ics' }}
        </button>
        <button
          class="px-5 py-3 bg-white/60 dark:bg-zinc-800/60 backdrop-blur text-on-surface dark:text-on-surface font-semibold rounded-3xl shadow hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2"
          @click="showRecurringModal = true"
        >
          <span class="material-symbols-outlined text-lg">repeat</span>
          Recurring
        </button>
        <button
          class="px-6 py-3 bg-gradient-to-br from-orange-500 to-orange-700 text-white font-bold rounded-3xl shadow-lg shadow-orange-900/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2"
          @click="showProposeModal = true"
        >
          <span class="material-symbols-outlined text-lg">add_circle</span>
          Schedule Session
        </button>
      </div>
    </div>

    <!-- Pending Approvals Panel -->
    <section
      v-if="pendingSessions.length > 0"
      class="liquid-glass rounded-3xl p-6 border border-amber-500/20"
    >
      <div class="flex items-center gap-3 mb-6">
        <div class="w-10 h-10 rounded-2xl bg-amber-500/20 flex items-center justify-center">
          <span
            class="material-symbols-outlined text-amber-400"
            style="font-variation-settings: 'FILL' 1"
            >pending_actions</span
          >
        </div>
        <div>
          <h3 class="text-lg font-black text-on-surface dark:text-on-surface">Pending Approvals</h3>
          <p class="text-on-surface-variant dark:text-on-surface-variant text-sm">
            {{ pendingSessions.length }} session{{ pendingSessions.length !== 1 ? 's' : '' }}
            awaiting review
          </p>
        </div>
      </div>

      <div class="space-y-3">
        <div
          v-for="session in pendingSessions"
          :key="session.id"
          class="flex items-center gap-4 p-4 rounded-2xl border"
          :class="
            session.status === 'pending_admin'
              ? 'bg-blue-500/5 border-blue-500/20'
              : 'bg-amber-500/5 border-amber-500/20'
          "
        >
          <!-- Time & Participants -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span
                class="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border"
                :class="
                  session.status === 'pending_admin'
                    ? 'bg-blue-500/20 border-blue-500/30 text-blue-400'
                    : 'bg-amber-500/20 border-amber-500/30 text-amber-400'
                "
              >
                {{ session.status === 'pending_admin' ? 'Awaiting Admin' : 'Awaiting Teacher' }}
              </span>
            </div>
            <p class="text-on-surface dark:text-on-surface font-bold text-sm">
              {{ formatDateTime(session.startTime) }}
            </p>
            <p class="text-on-surface-variant dark:text-on-surface-variant text-xs mt-0.5">
              {{ getUserName(session.teacherId) }} &rarr; {{ getUserName(session.studentId) }}
            </p>
            <p v-if="session.notes" class="text-on-surface-variant dark:text-on-surface-variant text-xs mt-1 italic">
              {{ session.notes }}
            </p>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2 shrink-0">
            <button
              v-if="session.status === 'pending_admin'"
              class="px-4 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-xs font-bold transition-all flex items-center gap-1.5"
              @click="handleApprove(session.id)"
            >
              <span class="material-symbols-outlined text-sm">check_circle</span>
              Approve
            </button>
            <button
              v-if="session.status === 'pending_admin'"
              class="px-4 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 text-xs font-bold transition-all flex items-center gap-1.5"
              @click="openReject(session.id)"
            >
              <span class="material-symbols-outlined text-sm">cancel</span>
              Reject
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
        Weekly Overview
      </h3>
      <BaseCalendar :sessions="scheduleStore.allSessions" @day-click="onDayClick" @session-click="onSessionClick" />
    </section>

    <!-- All Sessions Table -->
    <section class="liquid-glass rounded-3xl p-4 border border-black/[0.04] dark:border-white/5">
      <div class="flex items-center justify-between mb-6">
        <h3 class="text-xl font-black text-on-surface dark:text-on-surface flex items-center gap-3">
          <span class="w-10 h-10 rounded-2xl bg-black/[0.04] dark:bg-white/5 flex items-center justify-center">
            <span class="material-symbols-outlined text-on-surface-variant dark:text-on-surface-variant">list_alt</span>
          </span>
          All Sessions
        </h3>
        <div class="flex items-center gap-3">
          <button
            v-if="filteredSessions.length > 0"
            type="button"
            class="text-xs font-black uppercase tracking-widest text-on-surface-variant hover:text-on-surface px-4 py-2 bg-black/[0.04] dark:bg-white/5 rounded-2xl border border-black/[0.08] dark:border-white/10 transition-all"
            @click="toggleSelectAll"
          >
            {{ selectedSessionIds.length === filteredSessions.length ? 'Deselect All' : 'Select All' }}
          </button>
          <select
            v-model="filterStatus"
            class="bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-4 py-2 text-on-surface dark:text-on-surface text-sm focus:outline-none focus:ring-1 focus:ring-orange-500/50"
          >
            <option value="" class="bg-surface-container">All Statuses</option>
            <option value="scheduled" class="bg-surface-container">Confirmed</option>
            <option value="pending_admin" class="bg-surface-container">Awaiting Admin</option>
            <option value="pending_teacher" class="bg-surface-container">Awaiting Teacher</option>
            <option value="completed" class="bg-surface-container">Completed</option>
            <option value="rejected" class="bg-surface-container">Rejected</option>
          </select>
        </div>
      </div>

      <div class="space-y-2">
        <div
          v-for="session in filteredSessions"
          :key="session.id"
          class="flex items-center gap-4 p-4 rounded-2xl bg-black/[0.02] dark:bg-white/[0.02] hover:bg-black/5 dark:hover:bg-white/5 border border-black/[0.04] dark:border-white/5 hover:border-black/10 dark:hover:border-white/10 transition-all"
        >
          <input
            type="checkbox"
            :value="session.id"
            v-model="selectedSessionIds"
            class="w-4 h-4 rounded border-black/20 dark:border-white/20 text-orange-500 focus:ring-orange-500/50 bg-black/10 dark:bg-white/5 cursor-pointer accent-orange-500 shrink-0"
          />
          <div class="w-1 h-10 rounded-full shrink-0" :class="statusBarClass(session.status)"></div>
          <div class="flex-1 min-w-0">
            <p class="text-on-surface dark:text-on-surface font-bold text-sm">{{ formatDateTime(session.startTime) }}</p>
            <p class="text-on-surface-variant dark:text-on-surface-variant text-xs">
              {{ getUserName(session.teacherId) }} &rarr; {{ getUserName(session.studentId) }}
            </p>
          </div>
          <span
            class="px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider border shrink-0"
            :class="statusBadgeClass(session.status)"
          >
            {{ statusLabel(session.status) }}
          </span>
          <div class="flex items-center gap-2 shrink-0">
            <button
              v-if="session.status === 'pending_admin'"
              class="p-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 transition-all"
              title="Approve"
              @click="handleApprove(session.id)"
            >
              <span class="material-symbols-outlined text-sm">check_circle</span>
            </button>
            <button
              v-if="session.status === 'pending_admin' || session.status === 'pending_teacher'"
              class="p-1.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-all"
              title="Reject"
              @click="openReject(session.id)"
            >
              <span class="material-symbols-outlined text-sm">cancel</span>
            </button>
            <button
              class="p-1.5 rounded-xl bg-black/[0.04] dark:bg-white/5 hover:bg-black/5 dark:hover:bg-white/10 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface transition-all"
              title="Edit"
              @click="openEdit(session)"
            >
              <span class="material-symbols-outlined text-sm">edit</span>
            </button>
          </div>
        </div>
        <div v-if="filteredSessions.length === 0" class="text-center py-8 text-on-surface-variant dark:text-on-surface-variant">
          No sessions found
        </div>
      </div>
    </section>

    <!-- Reject Modal (inline) -->
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
          @click.self="rejectModal.open = false"
        >
          <div
            class="absolute inset-0 bg-black/30 dark:bg-black/60 backdrop-blur-sm"
            @click="rejectModal.open = false"
          />
          <div
            class="relative w-full max-w-sm liquid-glass rounded-3xl border border-black/[0.08] dark:border-white/10 p-6 space-y-4"
          >
            <div class="flex items-center justify-between">
              <h3 class="text-lg font-black text-on-surface dark:text-on-surface">Reject Session</h3>
              <button class="w-8 h-8 rounded-xl bg-black/[0.04] dark:bg-white/5 flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-all" @click="rejectModal.open = false"><span class="material-symbols-outlined text-base">close</span></button>
            </div>
            <textarea
              v-model="rejectModal.notes"
              rows="3"
              placeholder="Reason for rejection (optional)..."
              class="w-full bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-4 py-3 text-on-surface dark:text-on-surface text-sm placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-red-500/50 resize-none"
            />
            <div class="flex gap-3">
              <button
                class="flex-1 py-3 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 font-bold rounded-2xl text-sm transition-all"
                @click="confirmReject"
              >
                Confirm Reject
              </button>
              <button
                class="px-5 py-3 bg-black/[0.04] dark:bg-white/5 hover:bg-black/5 dark:hover:bg-white/10 border border-black/[0.08] dark:border-white/10 text-on-surface-variant dark:text-on-surface-variant font-bold rounded-2xl text-sm transition-all"
                @click="rejectModal.open = false"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Edit Session Modal -->
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
          v-if="editModal.open"
          class="fixed inset-0 z-[250] flex items-center justify-center p-4"
          @click.self="editModal.open = false"
        >
          <div
            class="absolute inset-0 bg-black/30 dark:bg-black/60 backdrop-blur-sm"
            @click="editModal.open = false"
          />
          <div
            class="relative w-full max-w-md liquid-glass rounded-3xl border border-black/[0.08] dark:border-white/10 p-6 space-y-5"
          >
            <div class="flex items-center justify-between">
              <h3 class="text-lg font-black text-on-surface dark:text-on-surface">Edit Session</h3>
              <button
                class="w-8 h-8 rounded-xl bg-black/[0.04] dark:bg-white/5 flex items-center justify-center text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface"
                @click="editModal.open = false"
              >
                <span class="material-symbols-outlined text-base">close</span>
              </button>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label
                  class="block text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest mb-2"
                  >Date</label
                >
                <input
                  v-model="editModal.date"
                  type="date"
                  class="w-full bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-3 py-2.5 text-on-surface dark:text-on-surface text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50"
                />
              </div>
              <div>
                <label
                  class="block text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest mb-2"
                  >Time</label
                >
                <input
                  v-model="editModal.time"
                  type="time"
                  class="w-full bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-3 py-2.5 text-on-surface dark:text-on-surface text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50"
                />
              </div>
            </div>
            <div>
              <label
                class="block text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest mb-2"
                >Notes</label
              >
              <textarea
                v-model="editModal.notes"
                rows="2"
                class="w-full bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-4 py-3 text-on-surface dark:text-on-surface text-sm placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-orange-500/50 resize-none"
              />
            </div>
            <div class="flex gap-3">
              <button
                class="flex-1 py-3 bg-gradient-to-br from-orange-500 to-orange-700 text-white font-bold rounded-2xl text-sm"
                @click="confirmEdit"
              >
                Save Changes
              </button>
              <button
                class="px-5 py-3 bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 text-on-surface-variant dark:text-on-surface-variant font-bold rounded-2xl text-sm"
                @click="editModal.open = false"
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
      :session="selectedSession"
      user-role="admin"
      :current-user-id="authStore.currentUser?.id ?? 0"
      :users="allUsers"
      @close="selectedSession = null"
    @approve-admin="(id: number) => { handleApprove(id); selectedSession = null }"
    @reject-admin="(id: number) => { openReject(id); selectedSession = null }"
    @complete-admin="(id: number) => { handleCompleteAdmin(id); selectedSession = null }"
    @reject-proof-admin="(id: number) => { handleRejectProofAdmin(id); selectedSession = null }"
    @approve-teacher="(id: number) => { handleApprove(id); selectedSession = null }"
    @reject-teacher="(id: number) => { openReject(id); selectedSession = null }"
    @counter-teacher="(s: Session) => { handleApprove(s.id); selectedSession = null }"
    @approve-student="(id: number) => { handleApprove(id); selectedSession = null }"
    @reject-student="async (id: number) => { try { await scheduleStore.rejectAsStudent(id); await scheduleStore.fetchAllSessions() } catch { toast.error('Action failed') }; selectedSession = null }"
    @counter-student="(s: Session) => { handleApprove(s.id); selectedSession = null }"
    @edit-admin="(s: Session) => { openEdit(s); selectedSession = null }"
    @nudge="(id: number) => { scheduleStore.nudgeSession(id); selectedSession = null }"
    />

    <!-- Propose Modal -->
    <ProposeSessionModal
      v-if="showProposeModal"
      :is-open="showProposeModal"
      user-role="admin"
      :current-user-id="authStore.currentUser?.id ?? 0"
      :teachers="teachers"
      :students="students"
      :initial-date="selectedDate ?? undefined"
      @close="showProposeModal = false"
      @submitted="onProposeSubmit"
    />
    <RecurringSessionModal
      v-if="showRecurringModal"
      :is-open="showRecurringModal"
      :teachers="teachers"
      :students="students"
      @close="showRecurringModal = false"
      @created="scheduleStore.fetchAllSessions()"
    />

    <!-- Floating Bulk Action Bar -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition duration-300 ease-out transform"
        enter-from-class="translate-y-12 opacity-0"
        enter-to-class="translate-y-0 opacity-100"
        leave-active-class="transition duration-200 ease-in transform"
        leave-from-class="translate-y-0 opacity-100"
        leave-to-class="translate-y-12 opacity-0"
      >
        <div
          v-if="selectedSessionIds.length > 0"
          class="fixed bottom-6 left-1/2 -translate-x-1/2 z-[200] flex items-center gap-4 px-6 py-4 rounded-full liquid-glass border border-black/10 dark:border-white/10 shadow-2xl backdrop-blur-xl animate-bounce-subtle"
        >
          <span class="text-xs font-black uppercase tracking-widest text-on-surface dark:text-on-surface">
            {{ selectedSessionIds.length }} Selected
          </span>
          <div class="w-px h-6 bg-black/10 dark:bg-white/10"></div>
          <div class="flex items-center gap-2">
            <button
              class="px-4 py-2 rounded-full bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-xs font-bold transition-all flex items-center gap-1.5"
              @click="handleBulkAction('approve')"
            >
              <span class="material-symbols-outlined text-sm">check_circle</span>
              Approve
            </button>
            <button
              class="px-4 py-2 rounded-full bg-teal-500/20 hover:bg-teal-500/30 border border-teal-500/30 text-teal-400 text-xs font-bold transition-all flex items-center gap-1.5"
              @click="handleBulkAction('complete')"
            >
              <span class="material-symbols-outlined text-sm">done_all</span>
              Complete
            </button>
            <button
              class="px-4 py-2 rounded-full bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 text-xs font-bold transition-all flex items-center gap-1.5"
              @click="handleBulkAction('cancel')"
            >
              <span class="material-symbols-outlined text-sm">cancel</span>
              Cancel
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

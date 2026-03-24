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
const filterStatus = ref('')

const rejectModal = ref({ open: false, sessionId: '', notes: '' })
const editModal = ref({ open: false, sessionId: '', date: '', time: '', notes: '' })

const teachers = computed(() => usersStore.getUsersByRole('teacher'))
const students = computed(() => usersStore.getUsersByRole('student'))
const allUsers = computed(() => usersStore.users)

const pendingSessions = computed(() => scheduleStore.pendingSessions)

const filteredSessions = computed(() => {
  const all = [...scheduleStore.allSessions].sort(
    (a, b) => new Date(b.startTime).getTime() - new Date(a.startTime).getTime()
  )
  if (!filterStatus.value) return all
  return all.filter((s) => s.status === filterStatus.value)
})

onMounted(async () => {
  await Promise.all([
    scheduleStore.fetchAllSessions(),
    usersStore.fetchUsers(),
    notifStore.fetchNotifications(authStore.currentUser?.id ?? ''),
  ])
})

function getUserName(id: string): string {
  return usersStore.users.find((u) => u.id === id)?.name ?? `User #${id}`
}

function onDayClick({ date, sessions }: { date: Date; sessions: Session[] }) {
  selectedDate.value = date
  selectedDaySessions.value = sessions
}

async function handleApprove(sessionId: string) {
  try {
    await scheduleStore.approveAsAdmin(sessionId)
    toast.success('Session approved!', 'The session is now confirmed.')
    selectedDate.value = null
  } catch {
    toast.error('Failed to approve session')
  }
}

function openReject(sessionId: string) {
  rejectModal.value = { open: true, sessionId, notes: '' }
  selectedDate.value = null
}

async function confirmReject() {
  try {
    await scheduleStore.rejectAsAdmin(rejectModal.value.sessionId, rejectModal.value.notes)
    toast.success('Session rejected')
    rejectModal.value.open = false
  } catch {
    toast.error('Failed to reject session')
  }
}

function openEdit(session: Session) {
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

async function confirmEdit() {
  const { sessionId, date, time, notes } = editModal.value
  try {
    const startTime = new Date(`${date}T${time}:00`).toISOString()
    const endTime = new Date(new Date(`${date}T${time}:00`).getTime() + 3600000).toISOString()
    await scheduleStore.editSession(sessionId, { startTime, endTime, notes })
    toast.success('Session updated!')
    editModal.value.open = false
  } catch {
    toast.error('Failed to update session')
  }
}

async function onProposeSubmit(session: Session) {
  try {
    await scheduleStore.bookSession(session)
    toast.success('Session scheduled!', 'The session has been confirmed and parties notified.')
    showProposeModal.value = false
  } catch {
    toast.error('Failed to schedule session')
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

function statusLabel(status: string): string {
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

function statusBarClass(status: string): string {
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

function statusBadgeClass(status: string): string {
  const map: Record<string, string> = {
    scheduled: 'bg-orange-500/20 border-orange-500/30 text-orange-400',
    completed: 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400',
    pending_teacher: 'bg-amber-500/20 border-amber-500/30 text-amber-400',
    pending_admin: 'bg-blue-500/20 border-blue-500/30 text-blue-400',
    rejected: 'bg-red-500/20 border-red-500/30 text-red-400',
    cancelled: 'bg-zinc-500/20 border-zinc-500/30 text-zinc-400',
  }
  return map[status] ?? 'bg-white/10 border-white/20 text-zinc-400'
}
</script>

<template>
  <div class="w-full mx-auto pb-28 space-y-4">
    <!-- Page Header -->
    <div
      class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 md:gap-6"
    >
      <div>
        <h1 class="text-5xl font-black tracking-tight text-zinc-900 dark:text-white mb-2">Schedule</h1>
        <p class="text-zinc-600 dark:text-zinc-500 font-medium">Manage all sessions — approve, edit, and schedule.</p>
      </div>
      <div class="shrink-0 flex items-start gap-4">
        <button
          @click="showProposeModal = true"
          class="px-6 py-3 bg-gradient-to-br from-orange-500 to-orange-700 text-zinc-900 dark:text-white font-bold rounded-3xl shadow-lg shadow-orange-900/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2"
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
          <h3 class="text-lg font-black text-zinc-900 dark:text-white">Pending Approvals</h3>
          <p class="text-zinc-600 dark:text-zinc-500 text-sm">
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
            <p class="text-zinc-900 dark:text-white font-bold text-sm">
              {{ formatDateTime(session.startTime) }}
            </p>
            <p class="text-zinc-600 dark:text-zinc-500 text-xs mt-0.5">
              {{ getUserName(session.teacherId) }} &rarr; {{ getUserName(session.studentId) }}
            </p>
            <p v-if="session.notes" class="text-zinc-500 dark:text-zinc-600 text-xs mt-1 italic">
              {{ session.notes }}
            </p>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2 shrink-0">
            <button
              v-if="session.status === 'pending_admin'"
              @click="handleApprove(session.id)"
              class="px-4 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-xs font-bold transition-all flex items-center gap-1.5"
            >
              <span class="material-symbols-outlined text-sm">check_circle</span>
              Approve
            </button>
            <button
              v-if="session.status === 'pending_admin'"
              @click="openReject(session.id)"
              class="px-4 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 text-xs font-bold transition-all flex items-center gap-1.5"
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
      <div class="flex items-center justify-between mb-6">
        <h3 class="text-xl font-black text-zinc-900 dark:text-white flex items-center gap-3">
          <span
            class="w-10 h-10 rounded-2xl bg-orange-500/10 flex items-center justify-center text-orange-500"
          >
            <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
              >calendar_month</span
            >
          </span>
          Weekly Overview
        </h3>
        <!-- Legend -->
        <div class="flex items-center gap-4 text-[10px] font-bold uppercase tracking-wider">
          <span class="flex items-center gap-1.5 text-orange-400"
            ><span class="w-2 h-2 rounded-full bg-orange-400"></span>Scheduled</span
          >
          <span class="flex items-center gap-1.5 text-blue-400"
            ><span class="w-2 h-2 rounded-full bg-blue-400"></span>Pending Admin</span
          >
          <span class="flex items-center gap-1.5 text-amber-400"
            ><span class="w-2 h-2 rounded-full bg-amber-400"></span>Pending Teacher</span
          >
          <span class="flex items-center gap-1.5 text-emerald-400"
            ><span class="w-2 h-2 rounded-full bg-emerald-400"></span>Completed</span
          >
        </div>
      </div>
      <BaseCalendar :sessions="scheduleStore.allSessions" @dayClick="onDayClick" />
    </section>

    <!-- All Sessions Table -->
    <section class="liquid-glass rounded-3xl p-4 border border-black/[0.04] dark:border-white/5">
      <div class="flex items-center justify-between mb-6">
        <h3 class="text-xl font-black text-zinc-900 dark:text-white flex items-center gap-3">
          <span class="w-10 h-10 rounded-2xl bg-black/[0.04] dark:bg-white/5 flex items-center justify-center">
            <span class="material-symbols-outlined text-zinc-500 dark:text-zinc-400">list_alt</span>
          </span>
          All Sessions
        </h3>
        <div class="flex items-center gap-3">
          <select
            v-model="filterStatus"
            class="bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-4 py-2 text-zinc-300 text-sm focus:outline-none focus:ring-1 focus:ring-orange-500/50"
          >
            <option value="" class="bg-zinc-900">All Statuses</option>
            <option value="scheduled" class="bg-zinc-900">Confirmed</option>
            <option value="pending_admin" class="bg-zinc-900">Awaiting Admin</option>
            <option value="pending_teacher" class="bg-zinc-900">Awaiting Teacher</option>
            <option value="completed" class="bg-zinc-900">Completed</option>
            <option value="rejected" class="bg-zinc-900">Rejected</option>
          </select>
        </div>
      </div>

      <div class="space-y-2">
        <div
          v-for="session in filteredSessions"
          :key="session.id"
          class="flex items-center gap-4 p-4 rounded-2xl bg-black/[0.02] dark:bg-white/[0.02] hover:bg-white/5 border border-black/[0.04] dark:border-white/5 hover:border-white/10 transition-all"
        >
          <div class="w-1 h-10 rounded-full shrink-0" :class="statusBarClass(session.status)"></div>
          <div class="flex-1 min-w-0">
            <p class="text-zinc-900 dark:text-white font-bold text-sm">{{ formatDateTime(session.startTime) }}</p>
            <p class="text-zinc-600 dark:text-zinc-500 text-xs">
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
              @click="handleApprove(session.id)"
              class="p-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 transition-all"
              title="Approve"
            >
              <span class="material-symbols-outlined text-sm">check_circle</span>
            </button>
            <button
              v-if="session.status === 'pending_admin' || session.status === 'pending_teacher'"
              @click="openReject(session.id)"
              class="p-1.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-all"
              title="Reject"
            >
              <span class="material-symbols-outlined text-sm">cancel</span>
            </button>
            <button
              @click="openEdit(session)"
              class="p-1.5 rounded-xl bg-black/[0.04] dark:bg-white/5 hover:bg-white/10 text-zinc-500 dark:text-zinc-400 hover:text-white transition-all"
              title="Edit"
            >
              <span class="material-symbols-outlined text-sm">edit</span>
            </button>
          </div>
        </div>
        <div v-if="filteredSessions.length === 0" class="text-center py-8 text-zinc-500 dark:text-zinc-600">
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
            <h3 class="text-lg font-black text-zinc-900 dark:text-white">Reject Session</h3>
            <textarea
              v-model="rejectModal.notes"
              rows="3"
              placeholder="Reason for rejection (optional)..."
              class="w-full bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-4 py-3 text-zinc-900 dark:text-white text-sm placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-red-500/50 resize-none"
            />
            <div class="flex gap-3">
              <button
                @click="confirmReject"
                class="flex-1 py-3 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 font-bold rounded-2xl text-sm transition-all"
              >
                Confirm Reject
              </button>
              <button
                @click="rejectModal.open = false"
                class="px-5 py-3 bg-black/[0.04] dark:bg-white/5 hover:bg-white/10 border border-black/[0.08] dark:border-white/10 text-zinc-500 dark:text-zinc-400 font-bold rounded-2xl text-sm transition-all"
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
              <h3 class="text-lg font-black text-zinc-900 dark:text-white">Edit Session</h3>
              <button
                @click="editModal.open = false"
                class="w-8 h-8 rounded-xl bg-black/[0.04] dark:bg-white/5 flex items-center justify-center text-zinc-500 dark:text-zinc-400 hover:text-white"
              >
                <span class="material-symbols-outlined text-base">close</span>
              </button>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label
                  class="block text-[10px] font-black text-zinc-600 dark:text-zinc-500 uppercase tracking-widest mb-2"
                  >Date</label
                >
                <input
                  type="date"
                  v-model="editModal.date"
                  class="w-full bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-3 py-2.5 text-zinc-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50"
                />
              </div>
              <div>
                <label
                  class="block text-[10px] font-black text-zinc-600 dark:text-zinc-500 uppercase tracking-widest mb-2"
                  >Time</label
                >
                <input
                  type="time"
                  v-model="editModal.time"
                  class="w-full bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-3 py-2.5 text-zinc-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50"
                />
              </div>
            </div>
            <div>
              <label
                class="block text-[10px] font-black text-zinc-600 dark:text-zinc-500 uppercase tracking-widest mb-2"
                >Notes</label
              >
              <textarea
                v-model="editModal.notes"
                rows="2"
                class="w-full bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-2xl px-4 py-3 text-zinc-900 dark:text-white text-sm placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-orange-500/50 resize-none"
              />
            </div>
            <div class="flex gap-3">
              <button
                @click="confirmEdit"
                class="flex-1 py-3 bg-gradient-to-br from-orange-500 to-orange-700 text-zinc-900 dark:text-white font-bold rounded-2xl text-sm"
              >
                Save Changes
              </button>
              <button
                @click="editModal.open = false"
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
      user-role="admin"
      :current-user-id="authStore.currentUser?.id ?? ''"
      :users="allUsers"
      @close="selectedDate = null"
      @propose="((showProposeModal = true), (selectedDate = null))"
      @approve-admin="handleApprove"
      @reject-admin="openReject"
      @edit-admin="openEdit"
    />

    <!-- Propose Modal -->
    <ProposeSessionModal
      v-if="showProposeModal"
      user-role="admin"
      :current-user-id="authStore.currentUser?.id ?? ''"
      :teachers="teachers"
      :students="students"
      :initial-date="selectedDate ?? undefined"
      @close="showProposeModal = false"
      @submitted="onProposeSubmit"
    />
  </div>
</template>

<template>
  <div class="flex">
    <AdminSidebar />
    <div class="ml-64 w-full min-h-screen p-8 pt-10">

      <!-- Top header bar -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-orange-500 mb-1">Live Analytics</p>
          <h2 class="text-4xl font-black text-white tracking-tight">Admin Dashboard</h2>
          <p class="text-zinc-500 mt-1 text-sm">{{ new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) }}</p>
        </div>
        <div class="flex items-center gap-3">
          <div class="text-right mr-2">
            <p class="text-sm font-bold text-white">{{ authStore.currentUser?.name }}</p>
            <p class="text-xs text-zinc-500">Director</p>
          </div>
          <div class="w-10 h-10 rounded-full bg-gradient-to-br from-orange-500 to-orange-700 flex items-center justify-center text-white font-black text-sm">
            {{ authStore.currentUser?.name?.charAt(0) || 'A' }}
          </div>
        </div>
      </div>

      <!-- KPI Cards Row -->
      <div class="grid grid-cols-4 gap-4 mb-6">
        <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-5 hover:border-zinc-700 transition-colors">
          <p class="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">Active Sessions</p>
          <div v-if="scheduleStore.isLoading" class="h-9 w-24 rounded bg-zinc-800 animate-pulse" />
          <p v-else class="text-4xl font-black text-white">{{ stats.totalSessions }}</p>
          <p class="text-xs text-emerald-400 mt-1 font-medium">↑ {{ stats.scheduledSessions }} scheduled</p>
        </div>
        <div class="bg-gradient-to-br from-orange-600 to-orange-700 rounded-2xl p-5 shadow-xl shadow-orange-900/30">
          <p class="text-xs font-semibold text-orange-200/70 uppercase tracking-widest mb-3">Retention Rate</p>
          <div v-if="scheduleStore.isLoading" class="h-9 w-20 rounded bg-orange-500/50 animate-pulse" />
          <p v-else class="text-4xl font-black text-white">{{ stats.completionRate }}%</p>
          <p class="text-xs text-orange-200/80 mt-1 font-medium">Based on completed sessions</p>
        </div>
        <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-5 hover:border-zinc-700 transition-colors">
          <p class="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">Faculty Members</p>
          <div v-if="usersStore.isLoading" class="h-9 w-16 rounded bg-zinc-800 animate-pulse" />
          <p v-else class="text-4xl font-black text-white">{{ teachers.length }}</p>
          <div class="flex -space-x-2 mt-2">
            <div v-for="t in teachers.slice(0,4)" :key="t.id"
              class="w-6 h-6 rounded-full bg-gradient-to-br from-zinc-600 to-zinc-700 border-2 border-zinc-900 flex items-center justify-center text-[10px] text-white font-bold">
              {{ t.name.charAt(0) }}
            </div>
            <div v-if="teachers.length > 4" class="w-6 h-6 rounded-full bg-orange-600 border-2 border-zinc-900 flex items-center justify-center text-[10px] text-white font-bold">
              +{{ teachers.length - 4 }}
            </div>
          </div>
        </div>
        <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-5 hover:border-zinc-700 transition-colors">
          <p class="text-xs font-semibold text-zinc-500 uppercase tracking-widest mb-3">New Registrations</p>
          <div v-if="usersStore.isLoading" class="h-9 w-16 rounded bg-zinc-800 animate-pulse" />
          <p v-else class="text-4xl font-black text-white">{{ students.length }}</p>
          <p class="text-xs text-blue-400 mt-1 font-medium">Active student enrolments</p>
        </div>
      </div>

      <!-- Main content: Schedule + Alerts -->
      <div class="grid grid-cols-3 gap-4 mb-4">

        <!-- Music Schedule -->
        <div class="col-span-2 bg-zinc-900/60 border border-zinc-800 rounded-2xl overflow-hidden">
          <div class="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
            <div>
              <h3 class="font-black text-white text-lg">Music Schedule</h3>
              <p class="text-xs text-zinc-500">Managing for today</p>
            </div>
            <button @click="showAddSessionModal = true"
              class="flex items-center gap-2 px-4 py-2.5 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-sm font-bold transition-all active:scale-95 shadow-lg shadow-orange-900/30"
              aria-label="Assign a new session">
              <span class="material-symbols-outlined text-sm" aria-hidden="true">add_circle</span>
              Assign New
            </button>
          </div>

          <!-- Loading -->
          <div v-if="scheduleStore.isLoading" class="p-6 space-y-3">
            <div v-for="i in 3" :key="i" class="h-16 rounded-xl bg-zinc-800 animate-pulse" />
          </div>

          <!-- Empty -->
          <div v-else-if="scheduleStore.allSessions.length === 0" class="p-12 flex flex-col items-center text-center">
            <span class="material-symbols-outlined text-5xl text-zinc-700 mb-3" style="font-variation-settings:'FILL' 1" aria-hidden="true">event_busy</span>
            <p class="font-semibold text-zinc-400">No sessions scheduled</p>
            <p class="text-sm text-zinc-600 mt-1">Use "Assign New" to create your first session.</p>
          </div>

          <!-- Session rows -->
          <div v-else class="divide-y divide-zinc-800/50">
            <div v-for="session in scheduleStore.allSessions.slice(0, 8)" :key="session.id"
              class="flex items-center gap-4 px-6 py-4 hover:bg-zinc-800/30 transition-colors group">
              <!-- Time -->
              <div class="w-16 shrink-0 text-right">
                <p class="text-sm font-black text-white">{{ formatTime(session.startTime) }}</p>
                <p class="text-[10px] text-zinc-600 uppercase">{{ formatAmPm(session.startTime) }}</p>
              </div>
              <!-- Instrument dot -->
              <div class="w-10 h-10 rounded-xl bg-orange-500/20 flex items-center justify-center shrink-0">
                <span class="material-symbols-outlined text-orange-400 text-base" style="font-variation-settings:'FILL' 1" aria-hidden="true">music_note</span>
              </div>
              <!-- Session info -->
              <div class="flex-1 min-w-0">
                <p class="text-sm font-bold text-white truncate">Session #{{ session.id }}</p>
                <p class="text-xs text-zinc-500">
                  Teacher #{{ session.teacherId }} &bull; Student #{{ session.studentId }}
                </p>
              </div>
              <!-- Status badge -->
              <span class="text-xs px-3 py-1 rounded-full font-semibold capitalize shrink-0"
                :class="statusClass(session.status)">{{ session.status }}</span>
            </div>
          </div>
        </div>

        <!-- Alerts & Quick Assign -->
        <div class="flex flex-col gap-4">
          <!-- Alerts -->
          <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl overflow-hidden flex-1">
            <div class="px-5 py-4 border-b border-zinc-800 flex items-center justify-between">
              <h3 class="font-black text-white">Alerts & Updates</h3>
              <span class="text-xs px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-400 font-bold">
                {{ notifStore.notifications.length || 0 }} NEW
              </span>
            </div>
            <div class="p-4 space-y-3">
              <div class="bg-orange-500/10 border border-orange-500/20 rounded-xl p-3">
                <div class="flex items-start gap-2 mb-1">
                  <span class="material-symbols-outlined text-orange-400 text-base mt-0.5" aria-hidden="true">warning</span>
                  <div>
                    <p class="text-xs font-black text-orange-400 uppercase tracking-wider">Session Alert</p>
                    <p class="text-sm text-white font-medium mt-0.5">{{ stats.scheduledSessions }} sessions running today</p>
                    <p class="text-xs text-zinc-500 mt-1">{{ stats.completedSessions }} completed this week</p>
                  </div>
                </div>
              </div>
              <div class="bg-zinc-800/50 border border-zinc-700/50 rounded-xl p-3">
                <div class="flex items-start gap-2">
                  <span class="material-symbols-outlined text-zinc-400 text-base mt-0.5" aria-hidden="true">campaign</span>
                  <div>
                    <p class="text-xs font-black text-zinc-400 uppercase tracking-wider">System</p>
                    <p class="text-sm text-white font-medium mt-0.5">{{ teachers.length }} active faculty members</p>
                    <p class="text-xs text-zinc-500 mt-1">{{ students.length }} enrolled students</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Quick Assign -->
          <div class="bg-gradient-to-br from-orange-600 to-orange-700 rounded-2xl p-5 shadow-xl shadow-orange-900/30">
            <h3 class="font-black text-white text-base mb-4">Quick Assign</h3>
            <div class="space-y-3">
              <div>
                <p class="text-xs text-orange-200/70 uppercase tracking-widest font-semibold mb-1.5">Teacher</p>
                <select v-model="quickTeacherId"
                  class="w-full rounded-xl bg-black/20 text-white border border-white/20 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-white/30">
                  <option value="">Select Faculty</option>
                  <option v-for="t in teachers" :key="t.id" :value="t.id">{{ t.name }}</option>
                </select>
              </div>
              <div>
                <p class="text-xs text-orange-200/70 uppercase tracking-widest font-semibold mb-1.5">Student</p>
                <select v-model="quickStudentId"
                  class="w-full rounded-xl bg-black/20 text-white border border-white/20 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-white/30">
                  <option value="">Select Student</option>
                  <option v-for="s in students" :key="s.id" :value="s.id">{{ s.name }}</option>
                </select>
              </div>
              <button @click="confirmQuickAssign"
                :disabled="!quickTeacherId || !quickStudentId || isQuickAssigning"
                class="w-full py-3 bg-white text-orange-600 rounded-xl font-black text-sm hover:bg-orange-50 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed">
                {{ isQuickAssigning ? 'Scheduling...' : 'CONFIRM SCHEDULE' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Faculty & Staff Table -->
      <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl overflow-hidden">
        <div class="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
          <h3 class="font-black text-white text-lg">Faculty &amp; Staff</h3>
          <div class="flex items-center gap-2">
            <button class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-zinc-800 text-zinc-400 hover:text-white text-xs font-semibold transition-all">
              <span class="material-symbols-outlined text-sm" aria-hidden="true">filter_list</span>
              Filter
            </button>
            <button @click="showAddSessionModal = true"
              class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-orange-600 hover:bg-orange-500 text-white text-xs font-bold transition-all">
              <span class="material-symbols-outlined text-sm" aria-hidden="true">person_add</span>
              Add Member
            </button>
          </div>
        </div>

        <!-- Loading -->
        <div v-if="usersStore.isLoading" class="p-6 space-y-3">
          <div v-for="i in 3" :key="i" class="h-14 rounded-xl bg-zinc-800 animate-pulse" />
        </div>

        <!-- Empty -->
        <div v-else-if="teachers.length === 0" class="p-10 text-center">
          <span class="material-symbols-outlined text-4xl text-zinc-700 mb-2 block" aria-hidden="true">group_off</span>
          <p class="text-zinc-400 font-semibold">No faculty members yet</p>
        </div>

        <!-- Table -->
        <table v-else class="w-full text-sm">
          <thead class="bg-zinc-800/40">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Member</th>
              <th class="px-6 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Email</th>
              <th class="px-6 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Status</th>
              <th class="px-6 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Sessions</th>
              <th class="px-6 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-800/50">
            <tr v-for="teacher in teachers" :key="teacher.id" class="hover:bg-zinc-800/30 transition-colors">
              <td class="px-6 py-4">
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 rounded-full bg-gradient-to-br from-orange-500 to-orange-700 flex items-center justify-center text-white font-black text-sm shrink-0">
                    {{ teacher.name.charAt(0) }}
                  </div>
                  <div>
                    <p class="font-semibold text-white text-sm">{{ teacher.name }}</p>
                    <p class="text-xs text-zinc-500">Faculty</p>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 text-zinc-400 text-xs">{{ teacher.email }}</td>
              <td class="px-6 py-4">
                <span class="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400">● Available</span>
              </td>
              <td class="px-6 py-4 text-zinc-300 font-mono text-sm">
                {{ teacherSessionCount(teacher.id) }}
              </td>
              <td class="px-6 py-4">
                <div class="flex items-center gap-3">
                  <button class="text-xs text-zinc-400 hover:text-white transition-colors font-semibold">edit</button>
                  <button class="text-xs text-zinc-400 hover:text-red-400 transition-colors font-semibold">delete</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>
  </div>

  <!-- Add Session Modal -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showAddSessionModal"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        role="dialog" aria-modal="true" aria-labelledby="assign-modal-title"
        @click.self="showAddSessionModal = false">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="showAddSessionModal = false" />
        <div class="relative w-full max-w-md bg-zinc-900 border border-zinc-700 rounded-2xl p-6 shadow-2xl">
          <div class="flex items-center justify-between mb-6">
            <h3 id="assign-modal-title" class="text-xl font-black text-white">Assign New Session</h3>
            <button @click="showAddSessionModal = false"
              class="text-zinc-500 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-500 rounded-lg p-1"
              aria-label="Close modal">
              <span class="material-symbols-outlined" aria-hidden="true">close</span>
            </button>
          </div>
          <form @submit.prevent="createAdminSession" class="space-y-4">
            <div>
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 block" for="modal-teacher">Teacher</label>
              <select id="modal-teacher" v-model="form.teacherId" required
                class="w-full bg-zinc-800 border border-zinc-700 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50">
                <option value="">Select a teacher...</option>
                <option v-for="t in teachers" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </div>
            <div>
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 block" for="modal-student">Student</label>
              <select id="modal-student" v-model="form.studentId" required
                class="w-full bg-zinc-800 border border-zinc-700 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50">
                <option value="">Select a student...</option>
                <option v-for="s in students" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
            </div>
            <div>
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 block" for="modal-date">Date &amp; Time</label>
              <input id="modal-date" type="datetime-local" v-model="form.startTime" required
                class="w-full bg-zinc-800 border border-zinc-700 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50" />
            </div>
            <div class="flex gap-3 pt-2">
              <button type="button" @click="showAddSessionModal = false"
                class="flex-1 py-3 rounded-xl border border-zinc-700 text-zinc-400 hover:text-white text-sm font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-zinc-500/50">
                Cancel
              </button>
              <button type="submit" :disabled="scheduleStore.isLoading"
                class="flex-1 py-3 rounded-xl bg-orange-600 hover:bg-orange-500 text-white text-sm font-black transition-all active:scale-95 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-orange-500/50">
                {{ scheduleStore.isLoading ? 'Scheduling...' : 'Confirm Session' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted, computed, ref, reactive } from 'vue'
import AdminSidebar from '../../components/AdminSidebar.vue'
import { useScheduleStore } from '../../stores/schedule'
import { useUsersStore } from '../../stores/users'
import { useAuthStore } from '../../stores/auth'
import { useNotificationStore } from '../../stores/notification'
import { useToastStore } from '../../stores/toast'

const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()
const notifStore = useNotificationStore()
const toast = useToastStore()

const showAddSessionModal = ref(false)
const quickTeacherId = ref('')
const quickStudentId = ref('')
const isQuickAssigning = ref(false)

const form = reactive({ teacherId: '', studentId: '', startTime: '' })

onMounted(async () => {
  await Promise.all([
    scheduleStore.fetchAllSessions(),
    usersStore.fetchUsersByRole('teacher'),
    usersStore.fetchUsersByRole('student'),
  ])
  if (authStore.currentUser?.id) {
    notifStore.fetchNotifications(authStore.currentUser.id)
  }
})

const teachers = computed(() => usersStore.getUsersByRole('teacher'))
const students = computed(() => usersStore.getUsersByRole('student'))

const stats = computed(() => {
  const sessions = scheduleStore.allSessions
  const completed = sessions.filter(s => s.status === 'completed').length
  const rate = sessions.length ? Math.round((completed / sessions.length) * 100) : 0
  return {
    totalSessions: sessions.length,
    scheduledSessions: sessions.filter(s => s.status === 'scheduled').length,
    completedSessions: completed,
    completionRate: rate,
  }
})

const teacherSessionCount = (teacherId: string) =>
  scheduleStore.allSessions.filter(s => s.teacherId === teacherId).length

const formatTime = (dt: string | undefined) => {
  if (!dt) return '—'
  return new Date(dt).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
}
const formatAmPm = (dt: string | undefined) => {
  if (!dt) return ''
  return new Date(dt).toLocaleTimeString('en-US', { hour12: true }).slice(-2)
}

const statusClass = (status: string) => ({
  'bg-emerald-500/20 text-emerald-400': status === 'completed',
  'bg-blue-500/20 text-blue-400': status === 'scheduled',
  'bg-amber-500/20 text-amber-400': status === 'ongoing',
  'bg-red-500/20 text-red-400': status === 'cancelled',
})

async function createAdminSession() {
  if (!form.teacherId || !form.studentId || !form.startTime) return
  try {
    const start = new Date(form.startTime)
    const end = new Date(start.getTime() + 60 * 60 * 1000)
    await scheduleStore.bookSession({
      teacherId: form.teacherId,
      studentId: form.studentId,
      startTime: start.toISOString(),
      endTime: end.toISOString(),
    })
    toast.success('Session scheduled!', 'The session has been added to the calendar.')
    showAddSessionModal.value = false
    Object.assign(form, { teacherId: '', studentId: '', startTime: '' })
  } catch {
    toast.error('Failed to schedule', 'Please check the details and try again.')
  }
}

async function confirmQuickAssign() {
  if (!quickTeacherId.value || !quickStudentId.value) return
  isQuickAssigning.value = true
  try {
    const now = new Date()
    now.setMinutes(0, 0, 0)
    now.setHours(now.getHours() + 1)
    await scheduleStore.bookSession({
      teacherId: quickTeacherId.value,
      studentId: quickStudentId.value,
      startTime: now.toISOString(),
      endTime: new Date(now.getTime() + 3600000).toISOString(),
    })
    toast.success('Quick assign done!', 'Session scheduled for the next available hour.')
    quickTeacherId.value = ''
    quickStudentId.value = ''
  } catch {
    toast.error('Quick assign failed', 'Could not create the session.')
  } finally {
    isQuickAssigning.value = false
  }
}
</script>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active .relative, .modal-leave-active .relative { transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1); }
.modal-enter-from .relative { transform: scale(0.95) translateY(10px); }
.modal-leave-to .relative { transform: scale(0.95); }
</style>

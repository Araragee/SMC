<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useScheduleStore } from '../../stores/schedule'
import { useUsersStore } from '../../stores/users'
import { useAuthStore } from '../../stores/auth'
import { useNotificationStore } from '../../stores/notification'
import { useToastStore } from '../../stores/toast'
import ProposeSessionModal from '../../components/ProposeSessionModal.vue'
import type { Session } from '../../types'

const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()
const notifStore = useNotificationStore()
const toast = useToastStore()

const showAddSessionModal = ref(false)
const quickTeacherId = ref('')
const quickStudentId = ref('')
const isQuickAssigning = ref(false)

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
const students = computed(() => usersStore.getUsersByRole('student'))

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
  'bg-amber-500/20 text-amber-400': status === 'ongoing',
  'bg-red-500/20 text-red-400': status === 'cancelled',
})

const borderColor = (status: string) => ({
  'border-l-emerald-500': status === 'completed',
  'border-l-orange-500': status === 'scheduled',
  'border-l-amber-500': status === 'ongoing',
  'border-l-red-500': status === 'cancelled',
})

const iconClass = (status: string) => ({
  'bg-emerald-500/10 text-emerald-400 border-emerald-500/20': status === 'completed',
  'bg-orange-500/10 text-orange-400 border-orange-500/20': status === 'scheduled',
  'bg-amber-500/10 text-amber-400 border-amber-500/20': status === 'ongoing',
  'bg-red-500/10 text-red-400 border-red-500/20': status === 'cancelled',
})

async function onProposeSubmit(session: Session) {
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

<template>
  <div class="max-w-[80vw] mx-auto pb-28 space-y-4">
    <!-- Page Header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-5xl font-black tracking-tight text-zinc-900 dark:text-white mb-2">Admin Dashboard</h1>
        <p class="text-zinc-600 dark:text-zinc-500 font-medium">Sernan's Music Clinic — Overview</p>
      </div>
    </div>

    <!-- Bento Stats Grid -->
    <section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
      <!-- Live Analytics (col-span-1 md:col-span-2 lg:col-span-3 xl:col-span-2) -->
      <div
        class="col-span-1 md:col-span-2 lg:col-span-3 xl:col-span-2 liquid-glass p-4 rounded-3xl border border-black/[0.04] dark:border-white/5 flex flex-col justify-between"
      >
        <div>
          <span class="text-[10px] font-black text-orange-500 uppercase tracking-[0.2em]"
            >Live Analytics</span
          >
          <div
            v-if="scheduleStore.isLoading"
            class="h-10 w-48 rounded bg-black/[0.04] dark:bg-white/5 animate-pulse mt-2"
          />
          <h2 v-else class="text-3xl font-black mt-2 tracking-tight text-zinc-900 dark:text-white">
            {{ stats.totalSessions }} Active Sessions
          </h2>
          <p class="text-zinc-500 dark:text-zinc-400 text-sm mt-1">{{ stats.scheduledSessions }} scheduled today</p>
        </div>
        <div class="flex gap-2 mt-8">
          <span
            class="px-4 py-1.5 bg-orange-500/10 border border-orange-500/20 text-orange-500 text-[10px] font-black rounded-full uppercase tracking-wider"
            >Piano Masterclass</span
          >
          <span
            class="px-4 py-1.5 bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 text-zinc-300 text-[10px] font-black rounded-full uppercase tracking-wider"
            >Theory Exams</span
          >
        </div>
      </div>

      <!-- Retention Rate (orange gradient) -->
      <div
        class="bg-gradient-to-br from-orange-500 to-orange-700 p-4 rounded-3xl shadow-xl shadow-orange-900/30 flex flex-col justify-between relative overflow-hidden group"
      >
        <div class="absolute -right-6 -bottom-6 opacity-20">
          <span
            class="material-symbols-outlined text-[120px]"
            style="font-variation-settings: 'FILL' 1"
            >music_note</span
          >
        </div>
        <div class="relative z-10">
          <span class="text-[10px] font-black text-white/70 uppercase tracking-[0.2em]"
            >Retention Rate</span
          >
          <div
            v-if="scheduleStore.isLoading"
            class="h-14 w-20 rounded bg-white/20 animate-pulse mt-2"
          />
          <h2 v-else class="text-5xl font-black mt-2 tracking-tighter text-zinc-900 dark:text-white">
            {{ stats.completionRate }}%
          </h2>
        </div>
        <p class="text-xs text-white/80 font-medium relative z-10">
          Exceeding national music academy benchmarks
        </p>
      </div>

      <!-- New Registrations -->
      <div class="liquid-glass p-4 rounded-3xl border border-black/[0.04] dark:border-white/5 flex flex-col justify-between">
        <div>
          <span class="text-[10px] font-black text-zinc-600 dark:text-zinc-500 uppercase tracking-[0.2em]"
            >New Registrations</span
          >
          <div
            v-if="usersStore.isLoading"
            class="h-14 w-16 rounded bg-black/[0.04] dark:bg-white/5 animate-pulse mt-2"
          />
          <h2 v-else class="text-5xl font-black mt-2 tracking-tighter text-zinc-900 dark:text-white">
            {{ students.length }}
          </h2>
        </div>
        <div class="flex -space-x-3 mt-6">
          <div
            v-for="(s, i) in students.slice(0, 3)"
            :key="s.id"
            class="w-10 h-10 rounded-full border-2 border-zinc-900 bg-surface-container-highest flex items-center justify-center text-zinc-900 dark:text-white font-black text-xs"
            :style="{ zIndex: 3 - i }"
          >
            {{ s.name.charAt(0) }}
          </div>
          <div
            v-if="students.length > 3"
            class="w-10 h-10 rounded-full border-2 border-zinc-900 bg-gradient-to-br from-orange-500 to-orange-700 text-zinc-900 dark:text-white text-[10px] font-black flex items-center justify-center"
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
            :class="scheduleStore.pendingSessions.length > 0 ? 'text-amber-400' : 'text-white'"
          >
            {{ scheduleStore.pendingSessions.length }}
          </h2>
        </div>
        <p
          class="text-zinc-500 dark:text-zinc-600 text-xs font-bold group-hover:text-amber-500 transition-colors mt-6"
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
        <section class="liquid-glass rounded-3xl p-4 border border-black/[0.04] dark:border-white/5">
          <div class="flex items-center justify-between mb-8">
            <div>
              <h3 class="text-2xl font-black tracking-tight text-zinc-900 dark:text-white">Music Schedule</h3>
              <p class="text-zinc-600 dark:text-zinc-500 text-sm">Managing for today</p>
            </div>
            <div class="flex gap-2">
              <button
                class="p-2 bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-xl hover:bg-white/10 transition-all"
              >
                <span class="material-symbols-outlined text-sm">chevron_left</span>
              </button>
              <button
                class="p-2 bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-xl hover:bg-white/10 transition-all"
              >
                <span class="material-symbols-outlined text-sm">chevron_right</span>
              </button>
            </div>
          </div>

          <!-- Column headers -->
          <div
            class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 py-2 border-b border-black/[0.04] dark:border-white/5 mb-4"
          >
            <div class="text-[10px] font-black text-zinc-600 dark:text-zinc-500 uppercase tracking-[0.2em] col-span-1">
              Time
            </div>
            <div class="text-[10px] font-black text-zinc-600 dark:text-zinc-500 uppercase tracking-[0.2em] col-span-5">
              Sessions &amp; Instructors
            </div>
          </div>

          <!-- Loading -->
          <div v-if="scheduleStore.isLoading" class="space-y-4">
            <div v-for="i in 3" :key="i" class="h-20 rounded-3xl bg-black/[0.04] dark:bg-white/5 animate-pulse" />
          </div>

          <!-- Empty -->
          <div
            v-else-if="scheduleStore.allSessions.length === 0"
            class="py-10 flex flex-col items-center text-center"
          >
            <span class="material-symbols-outlined text-4xl text-zinc-400 dark:text-zinc-700 mb-3">event_busy</span>
            <p class="font-bold text-zinc-900 dark:text-white text-sm mb-1">No sessions scheduled</p>
            <p class="text-xs text-zinc-600 dark:text-zinc-500">Use "Assign New" to create your first session.</p>
          </div>

          <!-- Session rows -->
          <div v-else class="space-y-2">
            <div
              v-for="session in scheduleStore.allSessions.slice(0, 5)"
              :key="session.id"
              class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 group hover:bg-white/5 transition-all rounded-3xl p-2 -mx-2"
            >
              <div class="col-span-1 flex flex-col justify-center">
                <span class="text-sm font-black">{{ formatTime(session.startTime) }}</span>
                <span class="text-[10px] text-zinc-600 dark:text-zinc-500 uppercase font-bold tracking-widest">{{
                  formatAmPm(session.startTime)
                }}</span>
              </div>
              <div
                class="col-span-5 bg-black/[0.04] dark:bg-white/5 border-l-4 p-5 rounded-3xl flex items-center justify-between"
                :class="borderColor(session.status)"
              >
                <div class="flex items-center gap-4">
                  <div
                    class="w-10 h-10 rounded-xl flex items-center justify-center shadow-sm border"
                    :class="iconClass(session.status)"
                  >
                    <span class="material-symbols-outlined">music_note</span>
                  </div>
                  <div>
                    <h4 class="text-sm font-bold text-zinc-900 dark:text-white">Session #{{ session.id }}</h4>
                    <p class="text-xs text-zinc-500 dark:text-zinc-400">
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
                    class="p-2 opacity-0 group-hover:opacity-100 transition-opacity text-zinc-600 dark:text-zinc-500 hover:text-white"
                  >
                    <span class="material-symbols-outlined">more_vert</span>
                  </button>
                </div>
              </div>
            </div>

            <!-- Add slot -->
            <div
              class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 p-2 -mx-2"
            >
              <div class="col-span-1"></div>
              <button
                class="col-span-5 border-2 border-dashed border-black/[0.08] dark:border-white/10 rounded-3xl p-4 flex items-center justify-center gap-2 text-zinc-600 dark:text-zinc-500 hover:border-orange-500/50 hover:text-orange-500 transition-all cursor-pointer bg-black/[0.02] dark:bg-white/[0.02] uppercase tracking-widest text-sm font-bold"
                @click="showAddSessionModal = true"
              >
                <span class="material-symbols-outlined">add_circle</span>
                Assign New Session
              </button>
            </div>
          </div>
        </section>

        <!-- Faculty & Staff -->
        <section class="liquid-glass rounded-3xl p-4 border border-black/[0.04] dark:border-white/5 overflow-hidden">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-10">
            <h3 class="text-2xl font-black tracking-tight text-zinc-900 dark:text-white">Faculty &amp; Staff</h3>
            <div class="flex items-center gap-3">
              <button
                class="px-5 py-2.5 bg-black/[0.04] dark:bg-white/5 text-zinc-500 dark:text-zinc-400 text-[10px] font-black uppercase tracking-widest border border-black/[0.08] dark:border-white/10 rounded-2xl hover:bg-white/10 transition-colors flex items-center gap-2"
              >
                <span class="material-symbols-outlined text-sm">filter_list</span>
                Filter
              </button>
              <button
                class="px-5 py-2.5 bg-gradient-to-br from-orange-500 to-orange-700 text-zinc-900 dark:text-white text-[10px] font-black uppercase tracking-widest rounded-2xl hover:opacity-90 transition-opacity flex items-center gap-2 shadow-lg shadow-orange-900/30"
                @click="showAddSessionModal = true"
              >
                <span class="material-symbols-outlined text-sm">person_add</span>
                Add Member
              </button>
            </div>
          </div>

          <div v-if="usersStore.isLoading" class="space-y-4">
            <div v-for="i in 3" :key="i" class="h-16 rounded-2xl bg-black/[0.04] dark:bg-white/5 animate-pulse" />
          </div>

          <div v-else-if="teachers.length === 0" class="py-10 text-center">
            <span class="material-symbols-outlined text-4xl text-zinc-400 dark:text-zinc-700 mb-2 block"
              >group_off</span
            >
            <p class="text-sm font-bold text-zinc-900 dark:text-white mb-1">No faculty members yet</p>
          </div>

          <div v-else class="overflow-x-auto">
            <table class="w-full text-left">
              <thead>
                <tr class="text-[10px] font-black text-zinc-600 dark:text-zinc-500 uppercase tracking-[0.2em]">
                  <th class="pb-6 px-2">Member</th>
                  <th class="pb-6 px-2">Department</th>
                  <th class="pb-6 px-2">Status</th>
                  <th class="pb-6 px-2">Sessions</th>
                  <th class="pb-6 px-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr
                  v-for="teacher in teachers"
                  :key="teacher.id"
                  class="group hover:bg-white/[0.02] transition-colors"
                >
                  <td class="py-6 px-2">
                    <div class="flex items-center gap-4">
                      <div
                        class="w-12 h-12 rounded-[18px] bg-surface-container-highest border border-black/[0.08] dark:border-white/10 flex items-center justify-center text-zinc-900 dark:text-white font-black text-lg"
                      >
                        {{ teacher.name.charAt(0) }}
                      </div>
                      <div>
                        <p class="text-sm font-black text-zinc-900 dark:text-white">{{ teacher.name }}</p>
                        <p class="text-xs text-zinc-600 dark:text-zinc-500">{{ teacher.email }}</p>
                      </div>
                    </div>
                  </td>
                  <td class="py-6 px-2">
                    <span class="text-xs font-medium text-zinc-300">Music Faculty</span>
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
                    <span class="text-sm font-black text-zinc-900 dark:text-white">
                      {{
                        scheduleStore.allSessions.filter((s) => s.teacherId === teacher.id).length
                      }}
                    </span>
                  </td>
                  <td class="py-6 px-2 text-right">
                    <div class="flex items-center justify-end gap-1">
                      <button class="p-2 text-zinc-600 dark:text-zinc-500 hover:text-white transition-colors">
                        <span class="material-symbols-outlined text-lg">edit</span>
                      </button>
                      <button class="p-2 text-zinc-600 dark:text-zinc-500 hover:text-red-400 transition-colors">
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
        <section class="liquid-glass rounded-3xl p-4 border border-black/[0.04] dark:border-white/5">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-lg font-black tracking-tight text-zinc-900 dark:text-white">Alerts &amp; Updates</h3>
            <span
              class="text-[10px] font-black text-orange-500 bg-orange-500/10 px-3 py-1 rounded-full border border-orange-500/20 flex items-center gap-1"
            >
              <span class="w-1.5 h-1.5 rounded-full bg-orange-400 animate-pulse"></span>
              {{ notifStore.notifications.length || 0 }} NEW
            </span>
          </div>
          <div class="space-y-4">
            <div
              class="bg-black/[0.04] dark:bg-white/5 p-5 rounded-3xl border-l-4 border-orange-500 hover:bg-white/10 transition-colors"
            >
              <div class="flex gap-4">
                <span class="material-symbols-outlined text-orange-500 text-xl">warning</span>
                <div>
                  <h4
                    class="text-[10px] font-black uppercase tracking-[0.2em] mb-1 text-orange-400"
                  >
                    Session Alert
                  </h4>
                  <p class="text-xs text-zinc-300 leading-relaxed">
                    {{ stats.scheduledSessions }} sessions running today
                  </p>
                  <button
                    class="text-[10px] font-black text-orange-500 mt-3 uppercase tracking-widest hover:underline transition-all"
                  >
                    Resolve Now
                  </button>
                </div>
              </div>
            </div>
            <div
              class="bg-black/[0.04] dark:bg-white/5 p-5 rounded-3xl border-l-4 border-zinc-700 hover:bg-white/10 transition-colors"
            >
              <div class="flex gap-4">
                <span class="material-symbols-outlined text-zinc-500 dark:text-zinc-400 text-xl">campaign</span>
                <div>
                  <h4 class="text-[10px] font-black uppercase tracking-[0.2em] mb-1 text-zinc-600 dark:text-zinc-500">
                    System
                  </h4>
                  <p class="text-xs text-zinc-300 leading-relaxed">
                    {{ teachers.length }} active faculty • {{ students.length }} enrolled students
                  </p>
                  <p class="text-[10px] text-zinc-600 dark:text-zinc-500 mt-2 font-bold uppercase">Just now</p>
                </div>
              </div>
            </div>
          </div>
          <button
            class="w-full mt-8 py-4 text-[10px] font-black text-zinc-500 dark:text-zinc-400 bg-black/[0.04] dark:bg-white/5 border border-black/[0.08] dark:border-white/10 rounded-3xl hover:bg-white/10 transition-all uppercase tracking-[0.2em]"
          >
            View All Activity
          </button>
        </section>

        <!-- Quick Assign -->
        <section
          class="bg-gradient-to-br from-orange-500 to-orange-700 rounded-3xl p-4 text-zinc-900 dark:text-white shadow-xl shadow-orange-900/30 relative overflow-hidden"
        >
          <div class="absolute -top-10 -right-10 w-40 h-40 bg-black/[0.06] dark:bg-white/10 rounded-full blur-3xl"></div>
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
                  class="w-full bg-white/20 backdrop-blur-md rounded-2xl px-5 py-3 text-xs font-bold border border-black/[0.08] dark:border-white/10 focus:outline-none focus:ring-1 focus:ring-white/40 hover:bg-white/30 transition-all appearance-none cursor-pointer text-zinc-900 dark:text-white"
                >
                  <option value="" class="text-zinc-900">Select Faculty</option>
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
                  class="w-full bg-white/20 backdrop-blur-md rounded-2xl px-5 py-3 text-xs font-bold border border-black/[0.08] dark:border-white/10 focus:outline-none focus:ring-1 focus:ring-white/40 hover:bg-white/30 transition-all appearance-none cursor-pointer text-zinc-900 dark:text-white"
                >
                  <option value="" class="text-zinc-900">Select Student</option>
                  <option v-for="s in students" :key="s.id" :value="s.id" class="text-zinc-900">
                    {{ s.name }}
                  </option>
                </select>
              </div>
              <button
                :disabled="!quickTeacherId || !quickStudentId || isQuickAssigning"
                class="w-full bg-black/40 backdrop-blur-xl border border-black/[0.08] dark:border-white/10 text-zinc-900 dark:text-white font-black py-4 rounded-3xl shadow-lg mt-4 active:scale-95 transition-all duration-150 uppercase text-[10px] tracking-[0.2em] disabled:opacity-50 disabled:cursor-not-allowed"
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

  <!-- Add Session Modal -->
  <ProposeSessionModal
    v-if="showAddSessionModal"
    user-role="admin"
    :current-user-id="authStore.currentUser?.id ?? ''"
    :teachers="teachers"
    :students="students"
    @close="showAddSessionModal = false"
    @submitted="onProposeSubmit"
  />
</template>

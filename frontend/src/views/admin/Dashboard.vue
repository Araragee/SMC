<template>
  <div class="flex gap-4 overflow-x-auto h-[calc(100vh-2rem)] items-stretch snap-x snap-mandatory hide-scrollbar">
    
    <!-- COLUMN 1: Active Sessions -->
    <div class="w-48 xl:w-64 shrink-0 snap-start glass-panel bg-surface-container-low/60 rounded-[32px] p-6 xl:p-8 flex flex-col justify-start border border-white/5 hover:border-white/10 transition-colors shadow-2xl relative inner-glow-top-left overflow-hidden">
      <div class="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent opacity-0 hover:opacity-100 transition-opacity"></div>
      <p class="text-[9px] xl:text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em] mb-4 relative z-10">Active Sessions</p>
      <div v-if="scheduleStore.isLoading" class="h-12 w-24 rounded bg-surface-container-highest animate-pulse relative z-10" />
      <p v-else class="text-5xl font-black text-white tracking-tighter relative z-10">{{ stats.totalSessions }}</p>
      <p class="text-xs text-emerald-400 mt-2 font-medium relative z-10 flex items-center gap-1">
        <span class="material-symbols-outlined text-[10px] xl:text-xs">arrow_upward</span>
        {{ stats.scheduledSessions }} scheduled
      </p>
    </div>

    <!-- COLUMN 2: Retention Rate (Orange) -->
    <div class="w-48 xl:w-64 shrink-0 snap-start bg-gradient-to-br from-orange-500 to-orange-700 rounded-[32px] p-6 xl:p-8 flex flex-col justify-start shadow-xl shadow-orange-900/30 relative inner-glow-top-left overflow-hidden group">
      <div class="absolute -right-10 -top-10 w-40 h-40 bg-white/10 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-700"></div>
      <p class="text-[9px] xl:text-[10px] font-bold text-orange-200/80 uppercase tracking-[0.2em] mb-4 relative z-10">Retention Rate</p>
      <div v-if="scheduleStore.isLoading" class="h-12 w-20 rounded bg-orange-800/50 animate-pulse relative z-10" />
      <p v-else class="text-5xl font-black text-white tracking-tighter relative z-10">{{ stats.completionRate }}%</p>
      <p class="text-[9px] xl:text-[10px] text-orange-200/90 mt-2 leading-relaxed font-medium relative z-10">
        Based on<br/>completed<br/>sessions
      </p>
    </div>

    <!-- COLUMN 3: Faculty Members -->
    <div class="w-48 xl:w-64 shrink-0 snap-start glass-panel bg-surface-container-low/60 rounded-[32px] p-6 xl:p-8 flex flex-col justify-start border border-white/5 hover:border-white/10 transition-colors shadow-2xl relative inner-glow-top-left overflow-hidden">
      <p class="text-[9px] xl:text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em] mb-4 relative z-10">Faculty Members</p>
      <div v-if="usersStore.isLoading" class="h-12 w-16 rounded bg-surface-container-highest animate-pulse relative z-10" />
      <p v-else class="text-5xl font-black text-white tracking-tighter relative z-10">{{ teachers.length }}</p>
    </div>

    <!-- COLUMN 4: New Registrations -->
    <div class="w-48 xl:w-64 shrink-0 snap-start glass-panel bg-surface-container-low/60 rounded-[32px] p-6 xl:p-8 flex flex-col justify-start border border-white/5 hover:border-white/10 transition-colors shadow-2xl relative inner-glow-top-left overflow-hidden">
      <p class="text-[9px] xl:text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em] mb-4 relative z-10">New Registrations</p>
      <div v-if="usersStore.isLoading" class="h-12 w-16 rounded bg-surface-container-highest animate-pulse relative z-10" />
      <p v-else class="text-5xl font-black text-white tracking-tighter relative z-10">{{ students.length }}</p>
      <p class="text-[9px] xl:text-[10px] text-blue-400 mt-2 font-medium leading-relaxed relative z-10">
        Active student<br/>enrolments
      </p>
    </div>

    <!-- COLUMN 5: Music Schedule -->
    <div class="w-80 xl:w-96 shrink-0 snap-start glass-panel bg-surface-container-low/60 rounded-[32px] p-5 xl:p-6 flex flex-col border border-white/5 hover:border-white/10 transition-colors shadow-2xl relative inner-glow-top-left overflow-hidden">
      <div class="flex items-center justify-between mx-1 xl:mx-2 mt-2 mb-6 xl:mb-8">
        <div>
          <h3 class="font-black text-white text-base xl:text-lg tracking-tight">Music Schedule</h3>
          <p class="text-[9px] xl:text-[10px] text-zinc-500 uppercase tracking-widest mt-0.5">Managing for today</p>
        </div>
        <button class="flex items-center gap-1.5 px-3 py-2 xl:px-4 xl:py-2.5 bg-gradient-to-br from-orange-500 to-orange-700 hover:scale-[1.02] text-white rounded-xl text-[10px] xl:text-xs font-bold transition-all active:scale-95 shadow-lg shadow-orange-900/30 group" @click="showAddSessionModal = true">
          <span class="material-symbols-outlined text-[12px] xl:text-[14px] group-hover:rotate-90 transition-transform">add_circle</span>
          Assign New
        </button>
      </div>

      <div class="flex-1 overflow-y-auto pr-1 xl:pr-2 no-scrollbar space-y-2">
        <!-- Loading -->
        <div v-if="scheduleStore.isLoading" class="space-y-3">
          <div v-for="i in 3" :key="i" class="h-14 xl:h-16 rounded-2xl bg-white/5 animate-pulse" />
        </div>
        
        <!-- Empty -->
        <div v-else-if="scheduleStore.allSessions.length === 0" class="flex flex-col items-center justify-center h-full text-center p-6 mt-10">
          <div class="w-14 h-14 xl:w-16 xl:h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
            <span class="material-symbols-outlined text-2xl xl:text-3xl text-zinc-600">event_busy</span>
          </div>
          <p class="font-bold text-white text-sm mb-1">No sessions scheduled</p>
          <p class="text-[10px] xl:text-xs text-zinc-500 max-w-[180px] xl:max-w-[200px]">Use "Assign New" to create your first session.</p>
        </div>

        <!-- Session rows -->
        <div v-for="session in scheduleStore.allSessions.slice(0, 8)" v-else :key="session.id" class="flex items-center gap-3 xl:gap-4 p-2.5 xl:p-3 rounded-2xl hover:bg-white/5 transition-colors group cursor-pointer border border-transparent hover:border-white/10">
          <div class="w-12 xl:w-14 shrink-0 text-center">
            <p class="text-xs xl:text-sm font-black text-white tabular-nums">{{ formatTime(session.startTime) }}</p>
            <p class="text-[8px] xl:text-[9px] font-bold text-orange-500 uppercase tracking-widest">{{ formatAmPm(session.startTime) }}</p>
          </div>
          <div class="w-8 h-8 rounded-full bg-surface-container-highest flex flex-col items-center justify-center shrink-0 border border-white/5 shadow-inner">
            <span class="material-symbols-outlined text-[14px] text-zinc-400">music_note</span>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-[11px] xl:text-xs font-bold text-white truncate">Session #{{ session.id }}</p>
            <p class="text-[9px] xl:text-[10px] text-zinc-500 truncate mt-0.5">T:{{ session.teacherId }} • S:{{ session.studentId }}</p>
          </div>
          <span class="text-[8px] xl:text-[9px] px-2 py-1 rounded-full font-bold uppercase tracking-wider shrink-0" :class="statusClass(session.status)">{{ session.status }}</span>
        </div>
      </div>
    </div>

    <!-- COLUMN 6: Alerts & Quick Assign Stack -->
    <div class="w-64 xl:w-72 shrink-0 snap-start flex flex-col gap-4">
      <!-- Alerts -->
      <div class="flex-1 glass-panel bg-surface-container-low/60 rounded-[32px] p-5 xl:p-6 border border-white/5 shadow-2xl relative inner-glow-top-left flex flex-col overflow-hidden">
        <div class="flex items-center justify-between mb-4 xl:mb-6 mx-1">
          <h3 class="font-black text-white text-[14px] xl:text-[15px] tracking-tight leading-loose">Alerts & Updates</h3>
          <span class="text-[8px] xl:text-[9px] px-2 py-1 rounded-full bg-orange-500/20 text-orange-400 font-bold tracking-widest flex items-center gap-1">
            <span class="w-1.5 h-1.5 rounded-full bg-orange-400 animate-pulse"></span>
            {{ notifStore.notifications.length || 0 }} NEW
          </span>
        </div>
        <div class="space-y-3 flex-1 overflow-y-auto no-scrollbar pr-1">
          <div class="bg-gradient-to-br from-orange-500/10 to-orange-900/10 border border-orange-500/20 rounded-2xl p-3 xl:p-4 relative overflow-hidden group hover:border-orange-500/40 transition-colors">
            <div class="absolute inset-0 bg-orange-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div class="flex items-start gap-2 xl:gap-3 relative z-10">
              <span class="material-symbols-outlined text-orange-400 text-base xl:text-lg">warning</span>
              <div>
                <p class="text-[8px] xl:text-[9px] font-black text-orange-400 uppercase tracking-widest mb-1">Session Alert</p>
                <p class="text-[11px] xl:text-xs text-white font-bold leading-snug">{{ stats.scheduledSessions }} sessions running today</p>
                <p class="text-[9px] xl:text-[10px] text-zinc-500 mt-1">{{ stats.completedSessions }} completed this week</p>
              </div>
            </div>
          </div>
          <div class="bg-surface-container-highest/30 border border-white/5 rounded-2xl p-3 xl:p-4 hover:border-white/10 transition-colors">
            <div class="flex items-start gap-2 xl:gap-3">
              <span class="material-symbols-outlined text-zinc-400 text-base xl:text-lg">campaign</span>
              <div>
                <p class="text-[8px] xl:text-[9px] font-black text-zinc-500 uppercase tracking-widest mb-1">System</p>
                <p class="text-[11px] xl:text-xs text-white font-bold leading-snug">{{ teachers.length }} active faculty members</p>
                <p class="text-[9px] xl:text-[10px] text-zinc-500 mt-1">{{ students.length }} enrolled students</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Assign -->
      <div class="h-60 xl:h-64 bg-gradient-to-br from-orange-500 to-orange-700 rounded-[32px] p-5 xl:p-6 shadow-xl shadow-orange-900/30 relative inner-glow-top-left flex flex-col justify-between group overflow-hidden">
        <div class="absolute -bottom-12 -right-12 w-48 h-48 bg-white/10 rounded-full blur-3xl group-hover:scale-110 transition-transform duration-700"></div>
        <h3 class="font-black text-white text-[14px] xl:text-[15px] tracking-tight relative z-10">Quick Assign</h3>
        <div class="space-y-2 xl:space-y-3 relative z-10">
          <div>
            <p class="text-[8px] xl:text-[9px] text-orange-200/90 uppercase tracking-[0.2em] font-bold mb-1 ml-1 xl:mb-1.5">Teacher</p>
            <select v-model="quickTeacherId" class="w-full rounded-xl xl:rounded-2xl bg-black/20 text-white font-medium border border-white/10 px-3 py-2 xl:px-4 xl:py-3 text-[11px] xl:text-xs focus:outline-none focus:ring-1 focus:ring-white/40 hover:bg-black/30 transition-colors appearance-none cursor-pointer">
              <option value="" class="text-zinc-900">Select Faculty ▾</option>
              <option v-for="t in teachers" :key="t.id" :value="t.id" class="text-zinc-900">{{ t.name }}</option>
            </select>
          </div>
          <div>
            <p class="text-[8px] xl:text-[9px] text-orange-200/90 uppercase tracking-[0.2em] font-bold mb-1 ml-1 xl:mb-1.5">Student</p>
            <select v-model="quickStudentId" class="w-full rounded-xl xl:rounded-2xl bg-black/20 text-white font-medium border border-white/10 px-3 py-2 xl:px-4 xl:py-3 text-[11px] xl:text-xs focus:outline-none focus:ring-1 focus:ring-white/40 hover:bg-black/30 transition-colors appearance-none cursor-pointer">
              <option value="" class="text-zinc-900">Select Student ▾</option>
              <option v-for="s in students" :key="s.id" :value="s.id" class="text-zinc-900">{{ s.name }}</option>
            </select>
          </div>
        </div>
        <button :disabled="!quickTeacherId || !quickStudentId || isQuickAssigning" class="w-full py-2.5 xl:py-3.5 bg-white text-orange-600 rounded-xl xl:rounded-2xl font-black text-[9px] xl:text-[10px] hover:bg-orange-50 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-widest shadow-xl relative z-10" @click="confirmQuickAssign">
          {{ isQuickAssigning ? 'Scheduling...' : 'Confirm' }}
        </button>
      </div>
    </div>

    <!-- COLUMN 7: Faculty & Staff -->
    <div class="w-72 xl:w-80 shrink-0 snap-start glass-panel bg-surface-container-low/60 rounded-[32px] p-5 xl:p-6 flex flex-col border border-white/5 hover:border-white/10 transition-colors shadow-2xl relative inner-glow-top-left overflow-hidden">
      <div class="flex items-center justify-between mx-1 xl:mx-2 mt-2 mb-6 xl:mb-8">
        <div>
          <h3 class="font-black text-white text-base xl:text-lg tracking-tight leading-tight">Faculty & Staff</h3>
        </div>
        <div class="flex items-center gap-1.5">
          <button class="flex items-center gap-1.5 px-3 py-2 xl:px-4 xl:py-2.5 bg-gradient-to-br from-orange-500 to-orange-700 text-white text-[10px] xl:text-xs uppercase tracking-wider font-bold rounded-xl transition-all hover:scale-[1.02] active:scale-95 shadow-md" @click="showAddSessionModal = true">
            <span class="material-symbols-outlined text-[12px] xl:text-[14px]">person_add</span>
            Add
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto pr-1 xl:pr-2 no-scrollbar space-y-2">
        <!-- Loading -->
        <div v-if="usersStore.isLoading" class="space-y-3">
          <div v-for="i in 3" :key="i" class="h-14 xl:h-16 rounded-2xl bg-white/5 animate-pulse" />
        </div>

        <!-- Empty -->
        <div v-else-if="teachers.length === 0" class="flex flex-col items-center justify-center h-full text-center p-6 mt-10">
          <div class="w-14 h-14 xl:w-16 xl:h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
            <span class="material-symbols-outlined text-2xl xl:text-3xl text-zinc-600">group_off</span>
          </div>
          <p class="text-xs xl:text-sm font-bold text-white mb-1">No faculty members yet</p>
        </div>

        <!-- Faculty List (No table, just styled list items) -->
        <div v-for="teacher in teachers" v-else :key="teacher.id" class="p-2.5 xl:p-3 rounded-2xl bg-surface-container-highest/20 border border-white/5 hover:bg-white/5 hover:border-white/10 transition-all cursor-pointer group flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 xl:w-10 xl:h-10 rounded-full bg-gradient-to-br from-zinc-700 to-zinc-800 flex items-center justify-center text-white font-black text-[11px] xl:text-sm border border-zinc-600 shadow-md transform group-hover:rotate-6 transition-transform">
              {{ teacher.name.charAt(0) }}
            </div>
            <div>
              <p class="font-bold text-white text-[11px] xl:text-xs">{{ teacher.name }}</p>
              <div class="flex items-center gap-1.5 mt-0.5">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]"></span>
                <p class="text-[8px] xl:text-[9px] text-zinc-500 font-semibold uppercase tracking-widest">Available</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Right padding buffer to allow overscroll padding visually -->
    <div class="w-4 shrink-0 h-full"></div>
  </div>

  <!-- Add Session Modal -->
  <Teleport to="body">    <Transition name="modal">
      <div
v-if="showAddSessionModal"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        role="dialog" aria-modal="true" aria-labelledby="assign-modal-title"
        @click.self="showAddSessionModal = false">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="showAddSessionModal = false" />
        <div class="relative w-full max-w-md bg-zinc-900 border border-white/10 rounded-2xl p-6 shadow-2xl">
          <div class="flex items-center justify-between mb-6">
            <h3 id="assign-modal-title" class="text-xl font-black text-white">Assign New Session</h3>
            <button
class="text-zinc-500 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-500 rounded-lg p-1"
              aria-label="Close modal"
              @click="showAddSessionModal = false">
              <span class="material-symbols-outlined" aria-hidden="true">close</span>
            </button>
          </div>
          <form class="space-y-4" @submit.prevent="createAdminSession">
            <div>
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 block" for="modal-teacher">Teacher</label>
              <select
id="modal-teacher" v-model="form.teacherId" required
                class="w-full bg-surface-container-highest border border-white/10 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50">
                <option value="">Select a teacher...</option>
                <option v-for="t in teachers" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </div>
            <div>
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 block" for="modal-student">Student</label>
              <select
id="modal-student" v-model="form.studentId" required
                class="w-full bg-surface-container-highest border border-white/10 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50">
                <option value="">Select a student...</option>
                <option v-for="s in students" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
            </div>
            <div>
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 block" for="modal-date">Date &amp; Time</label>
              <input
id="modal-date" v-model="form.startTime" type="datetime-local" required
                class="w-full bg-surface-container-highest border border-white/10 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50" />
            </div>
            <div class="flex gap-3 pt-2">
              <button
type="button" class="flex-1 py-3 rounded-xl border border-white/10 text-zinc-400 hover:text-white text-sm font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-zinc-500/50"
                @click="showAddSessionModal = false">
                Cancel
              </button>
              <button
type="submit" :disabled="scheduleStore.isLoading"
                class="flex-1 py-3 rounded-xl bg-gradient-to-br from-orange-500 to-orange-700 hover:scale-[1.02] text-white text-sm font-black transition-all active:scale-95 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-orange-500/50">
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
/* Hide scrollbar for Chrome, Safari and Opera */
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
/* Hide scrollbar for IE, Edge and Firefox */
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.hide-scrollbar::-webkit-scrollbar {
  display: none;
}
.hide-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.inner-glow-top-left {
  box-shadow: inset 1px 1px 0px 0px rgba(255, 255, 255, 0.15);
}

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active .relative, .modal-leave-active .relative { transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1); }
.modal-enter-from .relative { transform: scale(0.95) translateY(10px); }
.modal-leave-to .relative { transform: scale(0.95); }
</style>

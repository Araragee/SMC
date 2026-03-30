<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useUsersStore } from '../../stores/users'
import { useScheduleStore } from '../../stores/schedule'
import { useAuthStore } from '../../stores/auth'
import { useToastStore } from '../../stores/toast'
import SessionDetailModal from '../../components/SessionDetailModal.vue'
import type { User, Session } from '../../types'

// ── click-outside directive ────────────────────────────────────────────────────
const vClickOutside = {
  mounted(el: any, binding: any) {
    el._co = (e: Event) => { if (!el.contains(e.target)) binding.value(e) }
    document.addEventListener('click', el._co)
  },
  unmounted(el: any) { document.removeEventListener('click', el._co) },
}

const usersStore    = useUsersStore()
const scheduleStore = useScheduleStore()
const authStore     = useAuthStore()
const toast         = useToastStore()

// ── list-level state ──────────────────────────────────────────────────────────
const search     = ref('')
const listFilter = ref('all')
const sortBy     = ref('name-asc')
const sortOpen   = ref(false)

// ── detail modal state ────────────────────────────────────────────────────────
const selectedStudent = ref<User | null>(null)
const activeChip      = ref<string | null>(null)
const selectedSession = ref<Session | null>(null)

onMounted(async () => {
  const myId = authStore.currentUser?.id
  await Promise.all([
    usersStore.fetchUsers(),
    myId ? scheduleStore.fetchUserSessions(myId) : Promise.resolve(),
  ])
})

// ── sessions belonging to this teacher ────────────────────────────────────────
const mySessions = computed(() => {
  const myId = authStore.currentUser?.id
  if (!myId) return []
  return scheduleStore.allSessions.filter(s => s.teacherId === myId)
})

// ── base student list (unique students from my sessions) ──────────────────────
const baseStudents = computed((): User[] => {
  const ids = [...new Set(mySessions.value.map(s => s.studentId))]
  return ids
    .map(id => usersStore.users.find(u => u.id === id))
    .filter((u): u is User => !!u)
})

// ── per-student helpers ───────────────────────────────────────────────────────
function sessionsOf(student: User) {
  return mySessions.value.filter(s => s.studentId === student.id)
}
function doneCount(student: User) {
  return sessionsOf(student).filter(s => s.status === 'completed').length
}
function hasOverdue(student: User) {
  return sessionsOf(student).some(s => ['overdue','overdue_rejected'].includes(s.status))
}
function hasAttention(student: User) {
  return sessionsOf(student).some(s =>
    ['overdue','overdue_rejected','pending_teacher','pending_student','pending_admin'].includes(s.status))
}
function hasActive(student: User) {
  return sessionsOf(student).some(s => s.status === 'scheduled')
}
function allDone(student: User) {
  const ss = sessionsOf(student)
  return ss.length > 0 && ss.every(s => ['completed','cancelled','rejected'].includes(s.status))
}

// ── list filter definitions ───────────────────────────────────────────────────
const listFilters = computed(() => {
  const bs = baseStudents.value
  return [
    { key: 'all',       label: 'All',             icon: 'group',           count: bs.length },
    { key: 'attention', label: 'Needs Attention',  icon: 'warning',         count: bs.filter(hasAttention).length },
    { key: 'overdue',   label: 'Has Overdue',      icon: 'schedule',        count: bs.filter(hasOverdue).length },
    { key: 'active',    label: 'Active',           icon: 'event_available', count: bs.filter(hasActive).length },
    { key: 'done',      label: 'All Done',         icon: 'task_alt',        count: bs.filter(allDone).length },
  ]
})

const sortOptions = [
  { key: 'name-asc',  label: 'Name A → Z',    icon: 'sort_by_alpha' },
  { key: 'name-desc', label: 'Name Z → A',    icon: 'sort_by_alpha' },
  { key: 'most-done', label: 'Most Done',     icon: 'arrow_downward' },
  { key: 'most-active', label: 'Most Active', icon: 'event_available' },
]

// ── filtered + sorted list ────────────────────────────────────────────────────
const myStudents = computed(() => {
  let list = baseStudents.value

  // text search
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(u =>
      u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
    )
  }

  // status filter
  switch (listFilter.value) {
    case 'attention': list = list.filter(hasAttention); break
    case 'overdue':   list = list.filter(hasOverdue);   break
    case 'active':    list = list.filter(hasActive);    break
    case 'done':      list = list.filter(allDone);      break
  }

  // sort
  const out = [...list]
  switch (sortBy.value) {
    case 'name-asc':    out.sort((a, b) => a.name.localeCompare(b.name)); break
    case 'name-desc':   out.sort((a, b) => b.name.localeCompare(a.name)); break
    case 'most-done':   out.sort((a, b) => doneCount(b) - doneCount(a)); break
    case 'most-active': out.sort((a, b) =>
      sessionsOf(b).filter(s => s.status === 'scheduled').length -
      sessionsOf(a).filter(s => s.status === 'scheduled').length); break
  }
  return out
})

const allUsers   = computed(() => usersStore.users)
const isFiltered = computed(() => search.value.trim() !== '' || listFilter.value !== 'all')
function clearAll() { search.value = ''; listFilter.value = 'all' }

// ── detail modal computed ─────────────────────────────────────────────────────
const studentSessions = computed(() => {
  if (!selectedStudent.value) return []
  return mySessions.value.filter(s => s.studentId === selectedStudent.value!.id)
})

const stats = computed(() => {
  const ss = studentSessions.value
  return {
    total:     ss.length,
    confirmed: ss.filter(s => s.status === 'scheduled').length,
    pending:   ss.filter(s => ['pending_teacher','pending_student','pending_admin'].includes(s.status)).length,
    completed: ss.filter(s => s.status === 'completed').length,
    overdue:   ss.filter(s => ['overdue','overdue_rejected'].includes(s.status)).length,
    review:    ss.filter(s => s.status === 'pending_verification').length,
    rejected:  ss.filter(s => ['rejected','cancelled'].includes(s.status)).length,
  }
})

const filteredSessions = computed(() => {
  const ss = studentSessions.value
  switch (activeChip.value) {
    case 'confirmed': return ss.filter(s => s.status === 'scheduled')
    case 'pending':   return ss.filter(s => ['pending_teacher','pending_student','pending_admin'].includes(s.status))
    case 'completed': return ss.filter(s => s.status === 'completed')
    case 'overdue':   return ss.filter(s => ['overdue','overdue_rejected'].includes(s.status))
    case 'review':    return ss.filter(s => s.status === 'pending_verification')
    case 'rejected':  return ss.filter(s => ['rejected','cancelled'].includes(s.status))
    default:          return ss
  }
})

const chips = computed(() => [
  { key: 'total',     label: 'All',       count: stats.value.total,     color: 'bg-zinc-500/20 border-zinc-500/30 text-zinc-400',         dot: 'bg-zinc-400' },
  { key: 'confirmed', label: 'Confirmed', count: stats.value.confirmed, color: 'bg-teal-500/20 border-teal-500/30 text-teal-400',         dot: 'bg-teal-400' },
  { key: 'pending',   label: 'Pending',   count: stats.value.pending,   color: 'bg-amber-500/20 border-amber-500/30 text-amber-400',       dot: 'bg-amber-400' },
  { key: 'completed', label: 'Done',      count: stats.value.completed, color: 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400', dot: 'bg-emerald-400' },
  { key: 'overdue',   label: 'Overdue',   count: stats.value.overdue,   color: 'bg-rose-500/20 border-rose-500/30 text-rose-400',         dot: 'bg-rose-400' },
  { key: 'review',    label: 'In Review', count: stats.value.review,    color: 'bg-violet-500/20 border-violet-500/30 text-violet-400',   dot: 'bg-violet-400' },
  { key: 'rejected',  label: 'Declined',  count: stats.value.rejected,  color: 'bg-red-500/20 border-red-500/30 text-red-400',           dot: 'bg-red-400' },
].filter(c => c.key === 'total' || c.count > 0))

function openStudent(student: User) {
  selectedStudent.value = student; activeChip.value = null; selectedSession.value = null
}
function closeStudent() {
  selectedStudent.value = null; activeChip.value = null; selectedSession.value = null
}
function selectChip(key: string) { activeChip.value = activeChip.value === key ? null : key }

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit', hour12: true,
  })
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    scheduled:            'bg-teal-500/20 border-teal-500/30 text-teal-400',
    completed:            'bg-emerald-500/20 border-emerald-500/30 text-emerald-400',
    pending_teacher:      'bg-amber-500/20 border-amber-500/30 text-amber-400',
    pending_student:      'bg-orange-500/20 border-orange-500/30 text-orange-400',
    pending_admin:        'bg-blue-500/20 border-blue-500/30 text-blue-400',
    pending_verification: 'bg-violet-500/20 border-violet-500/30 text-violet-400',
    overdue:              'bg-rose-500/20 border-rose-500/30 text-rose-400',
    overdue_rejected:     'bg-red-500/20 border-red-500/30 text-red-400',
    rejected:             'bg-red-500/20 border-red-500/30 text-red-400',
    cancelled:            'bg-zinc-500/20 border-zinc-500/30 text-zinc-400',
  }
  return map[status] ?? 'bg-zinc-500/20 border-zinc-500/30 text-zinc-400'
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    scheduled: 'Confirmed', completed: 'Done',
    pending_teacher: 'Aw. Teacher', pending_student: 'Countered',
    pending_admin: 'Aw. Admin', pending_verification: 'In Review',
    overdue: 'Overdue', overdue_rejected: 'Proof Rej.',
    rejected: 'Declined', cancelled: 'Cancelled',
  }
  return map[status] ?? status
}

// ── teacher session actions ───────────────────────────────────────────────────
async function handleApproveTeacher(sessionId: string) {
  try {
    await scheduleStore.approveAsTeacher(sessionId)
    toast.success('Session approved')
    selectedSession.value = scheduleStore.allSessions.find(s => s.id === sessionId) ?? null
  } catch { toast.error('Action failed') }
}

function handleRejectTeacher(_sessionId: string) { selectedSession.value = null }

async function handleApproveStudent(sessionId: string) {
  try {
    await scheduleStore.approveAsStudent(sessionId)
    toast.success('Approved on student behalf')
    selectedSession.value = scheduleStore.allSessions.find(s => s.id === sessionId) ?? null
  } catch { toast.error('Action failed') }
}
</script>

<template>
  <div class="w-full mx-auto pb-28 space-y-6">

    <!-- Header -->
    <div>
      <h1 class="text-5xl font-black tracking-tight text-on-surface mb-2">My Students</h1>
      <p class="text-on-surface-variant font-medium">
        <span class="text-on-surface font-bold">{{ baseStudents.length }}</span> students in your sessions
      </p>
    </div>

    <!-- Search + Filter toolbar -->
    <div class="space-y-3">

      <!-- Search bar -->
      <div class="relative group">
        <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-xl pointer-events-none transition-colors duration-200 group-focus-within:text-teal-400">search</span>
        <input
          v-model="search"
          type="text"
          placeholder="Search by name or email…"
          class="w-full pl-12 pr-11 py-4 bg-surface-container dark:bg-surface-container border border-outline-variant dark:border-outline-variant rounded-2xl text-on-surface placeholder:text-on-surface-variant text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/40 focus:border-teal-500/30 transition-all duration-200"
        />
        <Transition
          enter-active-class="transition-all duration-150"
          enter-from-class="opacity-0 scale-75"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition-all duration-150"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-75"
        >
          <button
            v-if="search"
            class="absolute right-3 top-1/2 -translate-y-1/2 w-7 h-7 rounded-xl bg-black/[0.06] dark:bg-white/[0.06] hover:bg-black/10 dark:hover:bg-white/10 flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-all"
            @click="search = ''"
          >
            <span class="material-symbols-outlined text-base">close</span>
          </button>
        </Transition>
      </div>

      <!-- Filter pills + Sort -->
      <div class="flex items-center gap-2">
        <!-- Scrollable pills -->
        <div class="flex-1 flex items-center gap-1.5 overflow-x-auto scrollbar-hide pb-0.5 min-w-0">
          <button
            v-for="f in listFilters"
            :key="f.key"
            class="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-bold transition-all duration-200"
            :class="listFilter === f.key
              ? 'bg-teal-500 border-teal-500 text-white shadow-md shadow-teal-500/30'
              : 'bg-black/[0.04] dark:bg-white/[0.04] border-black/[0.06] dark:border-white/[0.06] text-on-surface-variant hover:text-on-surface hover:bg-black/[0.08] dark:hover:bg-white/[0.08]'"
            @click="listFilter = listFilter === f.key && f.key !== 'all' ? 'all' : f.key"
          >
            <span class="material-symbols-outlined" style="font-size:14px">{{ f.icon }}</span>
            {{ f.label }}
            <span class="font-black" :class="listFilter === f.key ? 'opacity-80' : 'opacity-50'">{{ f.count }}</span>
          </button>
        </div>

        <!-- Sort dropdown -->
        <div class="relative shrink-0">
          <button
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-2xl border text-xs font-bold transition-all duration-200 whitespace-nowrap"
            :class="sortOpen
              ? 'bg-black/[0.08] dark:bg-white/[0.08] border-black/10 dark:border-white/10 text-on-surface'
              : 'bg-black/[0.04] dark:bg-white/[0.04] border-black/[0.06] dark:border-white/[0.06] text-on-surface-variant hover:text-on-surface hover:bg-black/[0.07]'"
            @click.stop="sortOpen = !sortOpen"
          >
            <span class="material-symbols-outlined" style="font-size:14px">swap_vert</span>
            {{ sortOptions.find(o => o.key === sortBy)?.label }}
            <span class="material-symbols-outlined transition-transform duration-200" style="font-size:14px" :class="sortOpen ? 'rotate-180' : ''">expand_more</span>
          </button>
          <Transition
            enter-active-class="transition-all duration-150 ease-out"
            enter-from-class="opacity-0 translate-y-1 scale-95"
            enter-to-class="opacity-100 translate-y-0 scale-100"
            leave-active-class="transition-all duration-100 ease-in"
            leave-from-class="opacity-100 translate-y-0 scale-100"
            leave-to-class="opacity-0 translate-y-1 scale-95"
          >
            <div
              v-if="sortOpen"
              v-click-outside="() => sortOpen = false"
              class="absolute right-0 top-full mt-2 w-48 glass-heavy rounded-2xl shadow-xl overflow-hidden z-30"
            >
              <button
                v-for="opt in sortOptions"
                :key="opt.key"
                class="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-bold text-left transition-colors hover:bg-black/[0.04] dark:hover:bg-white/[0.04]"
                :class="sortBy === opt.key ? 'text-teal-400' : 'text-on-surface-variant hover:text-on-surface'"
                @click="sortBy = opt.key; sortOpen = false"
              >
                <span class="material-symbols-outlined" style="font-size:14px">{{ opt.icon }}</span>
                {{ opt.label }}
                <span v-if="sortBy === opt.key" class="material-symbols-outlined ml-auto" style="font-size:14px">check</span>
              </button>
            </div>
          </Transition>
        </div>
      </div>

      <!-- Active filter summary + clear -->
      <Transition
        enter-active-class="transition-all duration-200"
        enter-from-class="opacity-0 -translate-y-1"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition-all duration-150"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 -translate-y-1"
      >
        <div v-if="isFiltered" class="flex items-center gap-2 text-xs text-on-surface-variant">
          <span>
            Showing <strong class="text-on-surface">{{ myStudents.length }}</strong>
            result{{ myStudents.length !== 1 ? 's' : '' }}
          </span>
          <button
            class="ml-auto inline-flex items-center gap-1 font-bold text-rose-400 hover:text-rose-300 transition-colors"
            @click="clearAll"
          >
            <span class="material-symbols-outlined" style="font-size:14px">filter_list_off</span>
            Clear filters
          </button>
        </div>
      </Transition>
    </div>

    <!-- Student List -->
    <section class="liquid-glass rounded-3xl border border-black/[0.04] dark:border-white/5 overflow-hidden">
      <div v-if="usersStore.isLoading || scheduleStore.isLoading" class="p-12 text-center text-on-surface-variant">
        <span class="material-symbols-outlined text-4xl block mb-3 animate-spin">progress_activity</span>
        Loading students…
      </div>
      <div v-else-if="baseStudents.length === 0" class="p-12 text-center text-on-surface-variant">
        <span class="material-symbols-outlined text-4xl block mb-3">group</span>
        <p class="font-bold mb-1">No students yet</p>
        <p class="text-sm">Students appear here once you have sessions scheduled.</p>
      </div>
      <div v-else-if="myStudents.length === 0" class="p-12 text-center text-on-surface-variant">
        <span class="material-symbols-outlined text-4xl block mb-3">search_off</span>
        <p class="font-bold mb-1">No students match</p>
        <button class="text-sm text-teal-400 hover:text-teal-300 font-bold mt-2 transition-colors" @click="clearAll">Clear filters</button>
      </div>
      <div v-else class="divide-y divide-black/[0.04] dark:divide-white/5">
        <button
          v-for="student in myStudents"
          :key="student.id"
          class="w-full flex items-center gap-4 px-6 py-4 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors text-left group"
          @click="openStudent(student)"
        >
          <!-- Avatar -->
          <div class="w-11 h-11 rounded-2xl bg-teal-500/20 border border-teal-500/20 flex items-center justify-center text-teal-400 font-black text-base shrink-0 overflow-hidden">
            <img v-if="student.avatarUrl" :src="student.avatarUrl" class="w-full h-full object-cover" />
            <span v-else>{{ student.name.charAt(0).toUpperCase() }}</span>
          </div>
          <!-- Info -->
          <div class="flex-1 min-w-0">
            <p class="font-bold text-on-surface text-sm truncate">{{ student.name }}</p>
            <p class="text-on-surface-variant text-xs truncate">{{ student.email }}</p>
          </div>
          <!-- Status + done count -->
          <div class="flex items-center gap-2 shrink-0">
            <span
              v-if="hasOverdue(student)"
              class="text-[9px] font-black px-2 py-0.5 rounded-full bg-rose-500/15 border border-rose-500/25 text-rose-400"
            >Overdue</span>
            <span
              v-else-if="hasAttention(student)"
              class="text-[9px] font-black px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/25 text-amber-400"
            >Pending</span>
            <span class="text-[10px] font-black px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              {{ doneCount(student) }} done
            </span>
          </div>
          <span class="material-symbols-outlined text-on-surface-variant/40 group-hover:text-on-surface-variant group-hover:translate-x-1 transition-all">arrow_forward_ios</span>
        </button>
      </div>
    </section>

    <!-- ── Student Detail Modal ────────────────────────────────────────────── -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="opacity-0 translate-x-8"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition-all duration-150 ease-in"
        leave-from-class="opacity-100 translate-x-0"
        leave-to-class="opacity-0 translate-x-8"
      >
        <div v-if="selectedStudent" class="fixed inset-0 z-[200] flex items-center justify-center p-4" @click.self="closeStudent">
          <div class="absolute inset-0 bg-black/40 dark:bg-black/70 backdrop-blur-sm" @click="closeStudent" />

          <div class="relative w-full max-w-xl glass-heavy rounded-3xl shadow-2xl flex flex-col max-h-[90vh]">
            <!-- Header -->
            <div class="flex items-center gap-4 p-6 border-b border-black/5 dark:border-white/5">
              <div class="w-14 h-14 rounded-2xl bg-teal-500/20 border border-teal-500/20 flex items-center justify-center text-teal-400 font-black text-xl overflow-hidden shrink-0">
                <img v-if="selectedStudent.avatarUrl" :src="selectedStudent.avatarUrl" class="w-full h-full object-cover" />
                <span v-else>{{ selectedStudent.name.charAt(0).toUpperCase() }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <h2 class="font-black text-xl text-on-surface truncate">{{ selectedStudent.name }}</h2>
                <p class="text-on-surface-variant text-sm">{{ selectedStudent.email }}</p>
              </div>
              <button
                class="w-10 h-10 rounded-2xl bg-black/[0.06] dark:bg-white/[0.06] hover:bg-black/10 dark:hover:bg-white/10 flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-all"
                @click="closeStudent"
              >
                <span class="material-symbols-outlined text-lg">close</span>
              </button>
            </div>

            <!-- Body -->
            <div class="overflow-y-auto flex-1 p-6 space-y-5 custom-scrollbar">
              <!-- Info grid -->
              <div class="grid grid-cols-2 gap-3">
                <div v-if="selectedStudent.school" class="bg-black/[0.04] dark:bg-white/[0.04] rounded-2xl p-3">
                  <p class="text-[9px] font-black text-on-surface-variant uppercase tracking-widest mb-1">School</p>
                  <p class="text-sm font-bold text-on-surface">{{ selectedStudent.school }}</p>
                </div>
                <div v-if="selectedStudent.contactNumber" class="bg-black/[0.04] dark:bg-white/[0.04] rounded-2xl p-3">
                  <p class="text-[9px] font-black text-on-surface-variant uppercase tracking-widest mb-1">Contact</p>
                  <p class="text-sm font-bold text-on-surface">{{ selectedStudent.contactNumber }}</p>
                </div>
                <div v-if="selectedStudent.parentName" class="bg-black/[0.04] dark:bg-white/[0.04] rounded-2xl p-3">
                  <p class="text-[9px] font-black text-on-surface-variant uppercase tracking-widest mb-1">Parent</p>
                  <p class="text-sm font-bold text-on-surface">{{ selectedStudent.parentName }}</p>
                </div>
                <div class="bg-teal-500/10 border border-teal-500/20 rounded-2xl p-3">
                  <p class="text-[9px] font-black text-teal-400 uppercase tracking-widest mb-1">Sessions Done</p>
                  <p class="text-2xl font-black text-teal-400">{{ stats.completed }}</p>
                </div>
              </div>

              <!-- Stat chips -->
              <div>
                <p class="text-[9px] font-black text-on-surface-variant uppercase tracking-widest mb-3">Session Breakdown</p>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="chip in chips"
                    :key="chip.key"
                    class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-[10px] font-black uppercase tracking-wider transition-all"
                    :class="[chip.color, activeChip === chip.key ? 'ring-2 ring-offset-1 ring-offset-transparent scale-105' : 'opacity-80 hover:opacity-100']"
                    @click="selectChip(chip.key)"
                  >
                    <span class="w-1.5 h-1.5 rounded-full" :class="chip.dot"></span>
                    {{ chip.label }}
                    <span class="font-black ml-0.5">{{ chip.count }}</span>
                  </button>
                </div>
              </div>

              <!-- Session list -->
              <div v-if="filteredSessions.length > 0" class="space-y-2">
                <p class="text-[9px] font-black text-on-surface-variant uppercase tracking-widest">
                  {{ activeChip ? chips.find(c => c.key === activeChip)?.label : 'All' }} Sessions
                </p>
                <button
                  v-for="session in filteredSessions"
                  :key="session.id"
                  class="w-full flex items-center gap-3 p-3 rounded-2xl bg-black/[0.03] dark:bg-white/[0.03] border border-black/[0.05] dark:border-white/5 hover:bg-black/[0.06] dark:hover:bg-white/[0.06] transition-all text-left group"
                  @click="selectedSession = session"
                >
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-bold text-on-surface">{{ formatTime(session.startTime) }}</p>
                    <p class="text-xs text-on-surface-variant">{{ statusLabel(session.status) }}</p>
                  </div>
                  <span class="text-[9px] font-black px-2 py-1 rounded-full border" :class="statusBadge(session.status)">
                    {{ statusLabel(session.status) }}
                  </span>
                  <span class="material-symbols-outlined text-sm text-on-surface-variant/40 group-hover:text-on-surface-variant transition-colors">chevron_right</span>
                </button>
              </div>
              <div v-else-if="activeChip" class="text-center py-6 text-on-surface-variant text-sm">No sessions in this category.</div>
              <div v-else-if="studentSessions.length === 0" class="text-center py-6 text-on-surface-variant text-sm">No sessions with this student yet.</div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Session Detail Modal -->
    <SessionDetailModal
      :session="selectedSession"
      user-role="teacher"
      :current-user-id="authStore.currentUser?.id ?? ''"
      :users="allUsers"
      @close="selectedSession = null"
      @approve-teacher="(id) => handleApproveTeacher(id)"
      @reject-teacher="(id) => handleRejectTeacher(id)"
      @approve-student="(id) => handleApproveStudent(id)"
    />
  </div>
</template>

<style scoped>
.scrollbar-hide::-webkit-scrollbar { display: none; }
.scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
</style>

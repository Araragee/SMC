<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useUsersStore } from '@stores/users'
import { useScheduleStore } from '@stores/schedule'
import { useAuthStore } from '@stores/auth'
import { useToastStore } from '@stores/toast'
import SessionDetailModal from '@components/SessionDetailModal.vue'
import type { User, Session } from '@types'
import { useDialog } from '@composables/useDialog'

// ── click-outside directive ────────────────────────────────────────────────────
const vClickOutside = {
  mounted(el: any, binding: any) {
    el._co = (e: Event) => { if (!el.contains(e.target)) binding.value(e) }
    document.addEventListener('click', el._co)
  },
  unmounted(el: any) { document.removeEventListener('click', el._co) },
}

const usersStore  = useUsersStore()
const scheduleStore = useScheduleStore()
const authStore   = useAuthStore()
const toast       = useToastStore()
const dialog      = useDialog()

// ── list-level state ──────────────────────────────────────────────────────────
const search       = ref('')
const listFilter   = ref('all')
const sortBy       = ref('name-asc')
const sortOpen     = ref(false)

// ── detail modal state ────────────────────────────────────────────────────────
const selectedStudent  = ref<User | null>(null)
const activeChip       = ref<string | null>(null)
const selectedSession  = ref<Session | null>(null)

onMounted(async () => {
  await Promise.all([usersStore.fetchUsers(), scheduleStore.fetchAllSessions()])
})

// ── helpers for per-student session counts ────────────────────────────────────
function sessionsOf(student: User) {
  return scheduleStore.allSessions.filter(s => s.studentId === student.id)
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

// ── list filter definitions ───────────────────────────────────────────────────
const baseStudents = computed(() => usersStore.getUsersByRole('student'))

const listFilters = computed(() => {
  const bs = baseStudents.value
  return [
    { key: 'all',        label: 'All',             icon: 'group',            count: bs.length },
    { key: 'attention',  label: 'Needs Attention',  icon: 'warning',          count: bs.filter(hasAttention).length },
    { key: 'overdue',    label: 'Has Overdue',      icon: 'schedule',         count: bs.filter(hasOverdue).length },
    { key: 'active',     label: 'Active',           icon: 'event_available',  count: bs.filter(hasActive).length },
    { key: 'low',        label: 'Low Sessions',     icon: 'hourglass_bottom', count: bs.filter(s => (s.sessionsLeft ?? 0) > 0 && (s.sessionsLeft ?? 0) <= 2).length },
    { key: 'none',       label: 'No Sessions Left', icon: 'block',            count: bs.filter(s => (s.sessionsLeft ?? 0) === 0).length },
  ]
})

const sortOptions = [
  { key: 'name-asc',      label: 'Name A → Z',      icon: 'sort_by_alpha' },
  { key: 'name-desc',     label: 'Name Z → A',      icon: 'sort_by_alpha' },
  { key: 'sessions-high', label: 'Sessions Left ↓',  icon: 'arrow_downward' },
  { key: 'sessions-low',  label: 'Sessions Left ↑',  icon: 'arrow_upward' },
]

// ── main list (search + filter + sort) ───────────────────────────────────────
const allStudents = computed(() => {
  let list = baseStudents.value

  // text search
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(s =>
      s.name.toLowerCase().includes(q) || s.email.toLowerCase().includes(q)
    )
  }

  // list filter
  switch (listFilter.value) {
    case 'attention': list = list.filter(hasAttention); break
    case 'overdue':   list = list.filter(hasOverdue);   break
    case 'active':    list = list.filter(hasActive);    break
    case 'low':       list = list.filter(s => (s.sessionsLeft ?? 0) > 0 && (s.sessionsLeft ?? 0) <= 2); break
    case 'none':      list = list.filter(s => (s.sessionsLeft ?? 0) === 0); break
  }

  // sort
  const out = [...list]
  switch (sortBy.value) {
    case 'name-asc':      out.sort((a: any, b: any) => a.name.localeCompare(b.name)); break
    case 'name-desc':     out.sort((a: any, b: any) => b.name.localeCompare(a.name)); break
    case 'sessions-high': out.sort((a: any, b: any) => (b.sessionsLeft ?? 0) - (a.sessionsLeft ?? 0)); break
    case 'sessions-low':  out.sort((a: any, b: any) => (a.sessionsLeft ?? 0) - (b.sessionsLeft ?? 0)); break
  }
  return out
})

const isFiltered = computed(() => search.value.trim() !== '' || listFilter.value !== 'all')

function clearAll() { search.value = ''; listFilter.value = 'all' }

// ── detail modal helpers ──────────────────────────────────────────────────────
const allUsers = computed(() => usersStore.users)

const studentSessions = computed(() => {
  if (!selectedStudent.value) return []
  return scheduleStore.allSessions.filter(s => s.studentId === selectedStudent.value!.id)
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
function selectChip(key: string) {
  activeChip.value = activeChip.value === key ? null : key
}

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

function getTeacherName(id: number) {
  return usersStore.users.find(u => u.id === id)?.name ?? `Teacher #${id}`
}

// ── admin session actions ─────────────────────────────────────────────────────
async function handleApprove(sessionId: number) {
  const session = scheduleStore.allSessions.find(s => s.id === sessionId)
  try {
    if (session?.status === 'pending_teacher') await scheduleStore.approveAsTeacher(sessionId)
    else if (session?.status === 'pending_student') await scheduleStore.approveAsStudent(sessionId)
    else await scheduleStore.approveAsAdmin(sessionId)
    toast.success('Session advanced')
    selectedSession.value = null
    await scheduleStore.fetchAllSessions()
  } catch { toast.error('Action failed') }
}

async function handleComplete(sessionId: number) {
  try {
    await scheduleStore.completeSession(sessionId)
    toast.success('Session completed')
    selectedSession.value = null
    await scheduleStore.fetchAllSessions()
  } catch (e: any) { toast.error('Failed', e.message) }
}

async function handleRejectProof(sessionId: number) {
  const reason = await dialog.prompt('Enter a reason for rejecting this proof:', {
    title: 'Reject Proof',
    placeholder: 'e.g. Image is unclear or incorrect session'
  })
  if (!reason) return
  try {
    await scheduleStore.rejectProof(sessionId, reason)
    toast.success('Proof rejected')
    selectedSession.value = null
    await scheduleStore.fetchAllSessions()
  } catch (e: any) { toast.error('Failed', e.message) }
}
</script>

<template>
  <div class="page">

    <!-- Header -->
    <div>
      <h1 class="text-5xl font-semibold tracking-tight text-on-surface mb-2">Students</h1>
      <p class="text-on-surface-variant font-medium">
        <span class="text-on-surface font-bold">{{ baseStudents.length }}</span> enrolled students
      </p>
    </div>

    <!-- Search + Filter toolbar -->
    <div class="space-y-3">

      <!-- Search bar -->
      <div class="relative group">
        <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-xl pointer-events-none transition-colors group-focus-within:text-teal-400">search</span>
        <input
          v-model="search"
          type="text"
          placeholder="Search by name or email…"
          class="input pl-12 pr-11"
        />
        <Transition
          enter-active-class="transition-all"
          enter-from-class="opacity-0 scale-75"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition-all"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-75"
        >
          <button
            v-if="search"
            class="absolute right-3 top-1/2 -translate-y-1/2 size-7 rounded-xl bg-black/[0.06] dark:bg-white/[0.06] hover:bg-black/10 dark:hover:bg-white/10 flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-all"
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
            class="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-bold transition-all"
            :class="listFilter === f.key ? 'bg-teal-500 border-teal-500 text-white shadow-md shadow-teal-500/30' : 'bg-black/[0.04] dark:bg-white/[0.04] border-black/[0.06] dark:border-white/[0.06] text-on-surface-variant hover:text-on-surface hover:bg-black/[0.08] dark:hover:bg-white/[0.08]'"
            @click="listFilter = listFilter === f.key && f.key !== 'all' ? 'all' : f.key"
          >
            <span class="material-symbols-outlined text-sm" style="font-size:14px">{{ f.icon }}</span>
            {{ f.label }}
            <span class="font-semibold" :class="listFilter === f.key ? 'opacity-80' : 'opacity-50'">{{ f.count }}</span>
          </button>
        </div>

        <!-- Sort dropdown -->
        <div class="relative shrink-0">
          <button
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-2xl border text-xs font-bold transition-all whitespace-nowrap"
            :class="sortOpen ? 'bg-black/[0.08] dark:bg-white/[0.08] border-black/10 dark:border-white/10 text-on-surface' : 'bg-black/[0.04] dark:bg-white/[0.04] border-black/[0.06] dark:border-white/[0.06] text-on-surface-variant hover:text-on-surface hover:bg-black/[0.07]'"
            @click.stop="sortOpen = !sortOpen"
          >
            <span class="material-symbols-outlined text-sm" style="font-size:14px">swap_vert</span>
            {{ sortOptions.find(o => o.key === sortBy)?.label }}
            <span
              class="material-symbols-outlined text-sm transition-transform"
              style="font-size:14px"
              :class="sortOpen ? 'rotate-180' : ''"
            >expand_more</span>
          </button>
          <Transition
            enter-active-class="transition-all ease-out"
            enter-from-class="opacity-0 translate-y-1 scale-95"
            enter-to-class="opacity-100 translate-y-0 scale-100"
            leave-active-class="transition-all ease-in"
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
                class="w-full flex items-center gap-2 px-4 py-2 text-xs font-bold text-left transition-colors hover:bg-black/[0.04] dark:hover:bg-white/[0.04]"
                :class="sortBy === opt.key ? 'text-teal-400' : 'text-on-surface-variant hover:text-on-surface'"
                @click="sortBy = opt.key; sortOpen = false"
              >
                <span class="material-symbols-outlined text-sm" style="font-size:14px">{{ opt.icon }}</span>
                {{ opt.label }}
                <span v-if="sortBy === opt.key" class="material-symbols-outlined text-sm ml-auto" style="font-size:14px">check</span>
              </button>
            </div>
          </Transition>
        </div>
      </div>

      <!-- Active filter summary + clear -->
      <Transition
        enter-active-class="transition-all"
        enter-from-class="opacity-0 -translate-y-1"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition-all"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 -translate-y-1"
      >
        <div v-if="isFiltered" class="flex items-center gap-2 text-xs text-on-surface-variant">
          <span>
            Showing
            <strong class="text-on-surface">{{ allStudents.length }}</strong>
            result{{ allStudents.length !== 1 ? 's' : '' }}
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
      <div v-if="usersStore.isLoading" class="p-12 text-center text-on-surface-variant">
        <span class="material-symbols-outlined text-4xl block mb-3 animate-spin">progress_activity</span>
        Loading students…
      </div>
      <div v-else-if="allStudents.length === 0" class="p-12 text-center text-on-surface-variant">
        <span class="material-symbols-outlined text-4xl block mb-3">{{ isFiltered ? 'search_off' : 'school' }}</span>
        <p class="font-bold mb-1">{{ isFiltered ? 'No students match' : 'No students found' }}</p>
        <button v-if="isFiltered" class="text-sm text-teal-400 hover:text-teal-300 font-bold mt-2 transition-colors" @click="clearAll">Clear filters</button>
      </div>
      <div v-else class="divide-y divide-black/[0.04] dark:divide-white/5">
        <button
          v-for="student in allStudents"
          :key="student.id"
          class="w-full flex items-center gap-4 px-6 py-4 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors text-left group"
          @click="openStudent(student)"
        >
          <!-- Avatar -->
          <div class="size-11 rounded-2xl bg-teal-500/20 border border-teal-500/20 flex items-center justify-center text-teal-400 font-semibold text-base shrink-0 overflow-hidden">
            <img v-if="student.avatarUrl" :src="student.avatarUrl" class="w-full h-full object-cover" />
            <span v-else>{{ student.name.charAt(0).toUpperCase() }}</span>
          </div>
          <!-- Info -->
          <div class="flex-1 min-w-0">
            <p class="font-bold text-on-surface text-sm truncate">{{ student.name }}</p>
            <p class="text-on-surface-variant text-xs truncate">{{ student.email }}</p>
          </div>
          <!-- Status indicators -->
          <div class="flex items-center gap-2 shrink-0">
            <span
              v-if="hasOverdue(student)"
              class="text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-500/15 border border-rose-500/25 text-rose-400"
            >Overdue</span>
            <span
              v-else-if="hasAttention(student)"
              class="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/25 text-amber-400"
            >Pending</span>
            <span
              class="text-xs font-semibold px-2 py-1 rounded-full shrink-0"
              :class="(student.sessionsLeft ?? 0) === 0 ? 'bg-zinc-500/10 border border-zinc-500/20 text-zinc-500' : (student.sessionsLeft ?? 0) <= 2 ? 'bg-rose-500/10 border border-rose-500/20 text-rose-400' : 'bg-teal-500/10 border border-teal-500/20 text-teal-400'"
            >
              {{ student.sessionsLeft ?? 0 }} left
            </span>
          </div>
          <span class="material-symbols-outlined text-on-surface-variant/40 group-hover:text-on-surface-variant group-hover:translate-x-1 transition-all">arrow_forward_ios</span>
        </button>
      </div>
    </section>

    <!-- ── Student Detail Modal ────────────────────────────────────────────── -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition-all ease-out"
        enter-from-class="opacity-0 translate-x-8"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition-all ease-in"
        leave-from-class="opacity-100 translate-x-0"
        leave-to-class="opacity-0 translate-x-8"
      >
        <div v-if="selectedStudent" class="fixed inset-0 z-[200] flex items-center justify-center p-4" @click.self="closeStudent">
          <div class="absolute inset-0 bg-black/40 dark:bg-black/70 backdrop-blur-sm" @click="closeStudent" />

          <div class="relative w-full max-w-xl glass-heavy rounded-3xl shadow-2xl flex flex-col max-h-[90vh]">
            <!-- Header -->
            <div class="flex items-center gap-4 p-6 border-b border-black/5 dark:border-white/5">
              <div class="size-14 rounded-2xl bg-teal-500/20 border border-teal-500/20 flex items-center justify-center text-teal-400 font-semibold text-xl overflow-hidden shrink-0">
                <img v-if="selectedStudent.avatarUrl" :src="selectedStudent.avatarUrl" class="w-full h-full object-cover" />
                <span v-else>{{ selectedStudent.name.charAt(0).toUpperCase() }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <h2 class="font-semibold text-xl text-on-surface truncate">{{ selectedStudent.name }}</h2>
                <p class="text-on-surface-variant text-sm">{{ selectedStudent.email }}</p>
              </div>
              <button
                class="icon-btn"
                @click="closeStudent"
              >
                <span class="material-symbols-outlined text-lg">close</span>
              </button>
            </div>

            <!-- Body -->
            <div class="overflow-y-auto flex-1 p-6 space-y-4 custom-scrollbar">
              <!-- Info grid -->
              <div class="grid grid-cols-2 gap-3">
                <div v-if="selectedStudent.school" class="bg-black/[0.04] dark:bg-white/[0.04] rounded-2xl p-3">
                  <p class="text-xs font-semibold text-on-surface-variant uppercase mb-1">School</p>
                  <p class="text-sm font-bold text-on-surface">{{ selectedStudent.school }}</p>
                </div>
                <div v-if="selectedStudent.contactNumber" class="bg-black/[0.04] dark:bg-white/[0.04] rounded-2xl p-3">
                  <p class="text-xs font-semibold text-on-surface-variant uppercase mb-1">Contact</p>
                  <p class="text-sm font-bold text-on-surface">{{ selectedStudent.contactNumber }}</p>
                </div>
                <div v-if="selectedStudent.parentName" class="bg-black/[0.04] dark:bg-white/[0.04] rounded-2xl p-3">
                  <p class="text-xs font-semibold text-on-surface-variant uppercase mb-1">Parent</p>
                  <p class="text-sm font-bold text-on-surface">{{ selectedStudent.parentName }}</p>
                </div>
                <div class="bg-teal-500/10 border border-teal-500/20 rounded-2xl p-3">
                  <p class="text-xs font-semibold text-teal-400 uppercase mb-1">Sessions Left</p>
                  <p class="text-2xl font-semibold text-teal-400">{{ selectedStudent.sessionsLeft ?? 0 }}</p>
                </div>
              </div>

              <!-- Stat chips -->
              <div>
                <p class="text-xs font-semibold text-on-surface-variant uppercase mb-3">Session Breakdown</p>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="chip in chips"
                    :key="chip.key"
                    class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-semibold uppercase transition-all"
                    :class="[chip.color, activeChip === chip.key ? 'ring-2 ring-offset-1 ring-offset-transparent scale-105' : 'opacity-80 hover:opacity-100']"
                    @click="selectChip(chip.key)"
                  >
                    <span class="size-1.5 rounded-full" :class="chip.dot"></span>
                    {{ chip.label }}
                    <span class="font-semibold ml-0.5">{{ chip.count }}</span>
                  </button>
                </div>
              </div>

              <!-- Session list -->
              <div v-if="filteredSessions.length > 0" class="space-y-2">
                <p class="text-xs font-semibold text-on-surface-variant uppercase">
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
                    <p class="text-xs text-on-surface-variant">with {{ getTeacherName(session.teacherId) }}</p>
                  </div>
                  <span class="text-xs font-semibold px-2 py-1 rounded-full border" :class="statusBadge(session.status)">
                    {{ statusLabel(session.status) }}
                  </span>
                  <span class="material-symbols-outlined text-sm text-on-surface-variant/40 group-hover:text-on-surface-variant transition-colors">chevron_right</span>
                </button>
              </div>
              <div v-else-if="activeChip" class="text-center py-6 text-on-surface-variant text-sm">No sessions in this category.</div>
              <div v-else-if="studentSessions.length === 0" class="text-center py-6 text-on-surface-variant text-sm">No sessions yet for this student.</div>
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
      @approve-admin="(id) => handleApprove(id)"
      @reject-admin="() => { selectedSession = null }"
      @complete-admin="(id) => handleComplete(id)"
      @reject-proof-admin="(id) => handleRejectProof(id)"
      @approve-teacher="(id) => handleApprove(id)"
      @reject-teacher="() => { selectedSession = null }"
      @approve-student="(id) => handleApprove(id)"
      @reject-student="async (id) => { try { await scheduleStore.rejectAsStudent(id); toast.success('Session declined'); selectedSession = null; await scheduleStore.fetchAllSessions() } catch { toast.error('Action failed') } }"
      @edit-admin="() => { selectedSession = null }"
    />
  </div>
</template>

<style scoped>
.scrollbar-hide::-webkit-scrollbar { display: none; }
.scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
</style>

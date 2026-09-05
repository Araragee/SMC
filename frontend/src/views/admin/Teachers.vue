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
    el._co = (e: Event) => {
      if (!el.contains(e.target)) binding.value(e)
    }
    document.addEventListener('click', el._co)
  },
  unmounted(el: any) {
    document.removeEventListener('click', el._co)
  },
}

const usersStore = useUsersStore()
const scheduleStore = useScheduleStore()
const authStore = useAuthStore()
const toast = useToastStore()
const dialog = useDialog()

// ── list-level state ──────────────────────────────────────────────────────────
const search = ref('')
const instrumentFilter = ref('all')
const sortBy = ref('name-asc')
const sortOpen = ref(false)

// ── detail modal state ────────────────────────────────────────────────────────
const selectedTeacher = ref<User | null>(null)
const activeChip = ref<string | null>(null)
const selectedSession = ref<Session | null>(null)

onMounted(async () => {
  await Promise.all([usersStore.fetchUsers(), scheduleStore.fetchAllSessions()])
})

// ── helpers ───────────────────────────────────────────────────────────────────
const baseTeachers = computed(() => usersStore.getUsersByRole('teacher'))

function completedCount(teacher: User) {
  return scheduleStore.allSessions.filter(
    (s) => s.teacherId === teacher.id && s.status === 'completed'
  ).length
}
function studentCount(teacher: User) {
  return new Set(
    scheduleStore.allSessions.filter((s) => s.teacherId === teacher.id).map((s) => s.studentId)
  ).size
}
function getInstrumentsLabel(teacher: User) {
  return teacher.instruments?.length ? teacher.instruments.map((i) => i.name).join(',') : null
}

// ── filter & sort ─────────────────────────────────────────────────────────────
// Collect unique instruments across all teachers (for filter pills)
const availableInstruments = computed(() => {
  const seen = new Set<string>()
  const result: string[] = []
  baseTeachers.value.forEach((t) => {
    t.instruments?.forEach((i) => {
      if (!seen.has(i.name)) {
        seen.add(i.name)
        result.push(i.name)
      }
    })
  })
  return result.sort()
})

const listFilters = computed(() => {
  const pills = [{ key: 'all', label: 'All', count: baseTeachers.value.length }]
  availableInstruments.value.forEach((name) => {
    pills.push({
      key: name,
      label: name,
      count: baseTeachers.value.filter((t) => t.instruments?.some((i) => i.name === name)).length,
    })
  })
  return pills
})

const sortOptions = [
  { key: 'name-asc', label: 'Name A → Z', icon: 'sort_by_alpha' },
  { key: 'name-desc', label: 'Name Z → A', icon: 'sort_by_alpha' },
  { key: 'most-taught', label: 'Most Sessions', icon: 'arrow_downward' },
  { key: 'most-students', label: 'Most Students', icon: 'group' },
]

const allTeachers = computed(() => {
  let list = baseTeachers.value

  // text search
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.email.toLowerCase().includes(q) ||
        (getInstrumentsLabel(t) ?? '').toLowerCase().includes(q)
    )
  }

  // instrument filter
  if (instrumentFilter.value !== 'all') {
    list = list.filter((t) => t.instruments?.some((i) => i.name === instrumentFilter.value))
  }

  // sort
  const out = [...list]
  switch (sortBy.value) {
    case 'name-asc':
      out.sort((a: any, b: any) => a.name.localeCompare(b.name))
      break
    case 'name-desc':
      out.sort((a: any, b: any) => b.name.localeCompare(a.name))
      break
    case 'most-taught':
      out.sort((a: any, b: any) => completedCount(b) - completedCount(a))
      break
    case 'most-students':
      out.sort((a: any, b: any) => studentCount(b) - studentCount(a))
      break
  }
  return out
})

const isFiltered = computed(() => search.value.trim() !== '' || instrumentFilter.value !== 'all')
function clearAll() {
  search.value = ''
  instrumentFilter.value = 'all'
}

// ── detail modal computed ─────────────────────────────────────────────────────
const allUsers = computed(() => usersStore.users)

const teacherSessions = computed(() => {
  if (!selectedTeacher.value) return []
  return scheduleStore.allSessions.filter((s) => s.teacherId === selectedTeacher.value!.id)
})

const uniqueStudentCount = computed(() => {
  if (!selectedTeacher.value) return 0
  return new Set(teacherSessions.value.map((s) => s.studentId)).size
})

const stats = computed(() => {
  const ss = teacherSessions.value
  return {
    total: ss.length,
    confirmed: ss.filter((s) => s.status === 'scheduled').length,
    pending: ss.filter((s) =>
      ['pending_teacher', 'pending_student', 'pending_admin'].includes(s.status)
    ).length,
    completed: ss.filter((s) => s.status === 'completed').length,
    overdue: ss.filter((s) => ['overdue', 'overdue_rejected'].includes(s.status)).length,
    review: ss.filter((s) => s.status === 'pending_verification').length,
    rejected: ss.filter((s) => ['rejected', 'cancelled'].includes(s.status)).length,
  }
})

const filteredSessions = computed(() => {
  const ss = teacherSessions.value
  switch (activeChip.value) {
    case 'confirmed':
      return ss.filter((s) => s.status === 'scheduled')
    case 'pending':
      return ss.filter((s) =>
        ['pending_teacher', 'pending_student', 'pending_admin'].includes(s.status)
      )
    case 'completed':
      return ss.filter((s) => s.status === 'completed')
    case 'overdue':
      return ss.filter((s) => ['overdue', 'overdue_rejected'].includes(s.status))
    case 'review':
      return ss.filter((s) => s.status === 'pending_verification')
    case 'rejected':
      return ss.filter((s) => ['rejected', 'cancelled'].includes(s.status))
    default:
      return ss
  }
})

const chips = computed(() =>
  [
    {
      key: 'total',
      label: 'All',
      count: stats.value.total,
      color: 'bg-surface-container-high/20 border-outline-variant/30 text-on-surface-variant',
      dot: 'bg-surface-container-high',
    },
    {
      key: 'confirmed',
      label: 'Confirmed',
      count: stats.value.confirmed,
      color: 'bg-success/20 border-success/30 text-success',
      dot: 'bg-success',
    },
    {
      key: 'pending',
      label: 'Pending',
      count: stats.value.pending,
      color: 'bg-warning/20 border-warning/30 text-warning',
      dot: 'bg-warning',
    },
    {
      key: 'completed',
      label: 'Done',
      count: stats.value.completed,
      color: 'bg-success/20 border-success/30 text-success',
      dot: 'bg-success',
    },
    {
      key: 'overdue',
      label: 'Overdue',
      count: stats.value.overdue,
      color: 'bg-error/20 border-error/30 text-error',
      dot: 'bg-error',
    },
    {
      key: 'review',
      label: 'In Review',
      count: stats.value.review,
      color: 'bg-tertiary/20 border-tertiary/30 text-tertiary',
      dot: 'bg-tertiary',
    },
    {
      key: 'rejected',
      label: 'Declined',
      count: stats.value.rejected,
      color: 'bg-error/20 border-error/30 text-error',
      dot: 'bg-error',
    },
  ].filter((c) => c.key === 'total' || c.count > 0)
)

function openTeacher(teacher: User) {
  selectedTeacher.value = teacher
  activeChip.value = null
  selectedSession.value = null
}
function closeTeacher() {
  selectedTeacher.value = null
  activeChip.value = null
  selectedSession.value = null
}
function selectChip(key: string) {
  activeChip.value = activeChip.value === key ? null : key
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    scheduled: 'bg-success/20 border-success/30 text-success',
    completed: 'bg-success/20 border-success/30 text-success',
    pending_teacher: 'bg-warning/20 border-warning/30 text-warning',
    pending_student: 'bg-primary/20 border-primary/30 text-primary',
    pending_admin: 'bg-tertiary/20 border-tertiary/30 text-tertiary',
    pending_verification: 'bg-tertiary/20 border-tertiary/30 text-tertiary',
    overdue: 'bg-error/20 border-error/30 text-error',
    overdue_rejected: 'bg-error/20 border-error/30 text-error',
    rejected: 'bg-error/20 border-error/30 text-error',
    cancelled: 'bg-surface-container-high/20 border-outline-variant/30 text-on-surface-variant',
  }
  return (
    map[status] ?? 'bg-surface-container-high/20 border-outline-variant/30 text-on-surface-variant'
  )
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    scheduled: 'Confirmed',
    completed: 'Done',
    pending_teacher: 'Aw. Teacher',
    pending_student: 'Countered',
    pending_admin: 'Aw. Admin',
    pending_verification: 'In Review',
    overdue: 'Overdue',
    overdue_rejected: 'Proof Rej.',
    rejected: 'Declined',
    cancelled: 'Cancelled',
  }
  return map[status] ?? status
}

function getStudentName(id: number) {
  return usersStore.users.find((u) => u.id === id)?.name ?? `Student #${id}`
}

// ── admin session actions ─────────────────────────────────────────────────────
async function handleApprove(sessionId: number) {
  const session = scheduleStore.allSessions.find((s) => s.id === sessionId)
  try {
    if (session?.status === 'pending_teacher') await scheduleStore.approveAsTeacher(sessionId)
    else if (session?.status === 'pending_student') await scheduleStore.approveAsStudent(sessionId)
    else await scheduleStore.approveAsAdmin(sessionId)
    toast.success('Session advanced')
    selectedSession.value = null
    await scheduleStore.fetchAllSessions()
  } catch {
    toast.error('Action failed')
  }
}

async function handleComplete(sessionId: number) {
  try {
    await scheduleStore.completeSession(sessionId)
    toast.success('Session completed')
    selectedSession.value = null
    await scheduleStore.fetchAllSessions()
  } catch (e: any) {
    toast.error('Failed', e.message)
  }
}

async function handleRejectProof(sessionId: number) {
  const reason = await dialog.prompt('Enter a reason for rejecting this proof:', {
    title: 'Reject Proof',
    placeholder: 'e.g. Image is unclear or incorrect session',
  })
  if (!reason) return
  try {
    await scheduleStore.rejectProof(sessionId, reason)
    toast.success('Proof rejected')
    selectedSession.value = null
    await scheduleStore.fetchAllSessions()
  } catch (e: any) {
    toast.error('Failed', e.message)
  }
}
</script>

<template>
  <div class="page">
    <!-- Header -->
    <div>
      <h1 class="text-5xl font-semibold tracking-tight text-on-surface mb-2">Teachers</h1>
      <p class="text-on-surface-variant font-medium">
        <span class="text-on-surface font-bold">{{ baseTeachers.length }}</span> registered
        instructors
      </p>
    </div>

    <!-- Search + Filter toolbar -->
    <div class="space-y-3">
      <!-- Search bar -->
      <div class="relative group">
        <span
          class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-xl pointer-events-none transition-colors group-focus-within:text-primary"
          >search</span
        >
        <input
          v-model="search"
          type="text"
          placeholder="Search by name, email, or instrument…"
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
            class="absolute right-3 top-1/2 -translate-y-1/2 size-7 rounded-xl bg-on-surface/[0.06] dark:bg-on-surface/[0.06] hover:bg-on-surface/10 dark:hover:bg-on-surface/10 flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-all"
            @click="search = ''"
          >
            <span class="material-symbols-outlined text-base">close</span>
          </button>
        </Transition>
      </div>

      <!-- Filter pills + Sort -->
      <div class="flex items-center gap-2">
        <!-- Instrument pills (scrollable) -->
        <div class="flex-1 flex items-center gap-1.5 overflow-x-auto scrollbar-hide pb-0.5 min-w-0">
          <button
            v-for="f in listFilters"
            :key="f.key"
            class="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-bold transition-all"
            :class="
              instrumentFilter === f.key
                ? 'bg-primary border-primary text-on-primary shadow-md'
                : 'bg-on-surface/[0.04] dark:bg-on-surface/[0.04] border-on-surface/[0.06] dark:border-on-surface/[0.06] text-on-surface-variant hover:text-on-surface hover:bg-on-surface/[0.08] dark:hover:bg-on-surface/[0.08]'
            "
            @click="instrumentFilter = instrumentFilter === f.key && f.key !== 'all' ? 'all' : f.key"
          >
            <span v-if="f.key === 'all'" class="material-symbols-outlined" style="font-size: 14px"
              >person_book</span
            >
            <span v-else class="material-symbols-outlined" style="font-size: 14px">piano</span>
            {{ f.label }}
            <span
              class="font-semibold"
              :class="instrumentFilter === f.key ? 'opacity-80' : 'opacity-50'"
              >{{ f.count }}</span
            >
          </button>
        </div>

        <!-- Sort dropdown -->
        <div class="relative shrink-0">
          <button
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-2xl border text-xs font-bold transition-all whitespace-nowrap"
            :class="
              sortOpen
                ? 'bg-on-surface/[0.08] dark:bg-on-surface/[0.08] border-on-surface/10 text-on-surface'
                : 'bg-on-surface/[0.04] dark:bg-on-surface/[0.04] border-on-surface/[0.06] dark:border-on-surface/[0.06] text-on-surface-variant hover:text-on-surface hover:bg-on-surface/[0.07]'
            "
            @click.stop="sortOpen = !sortOpen"
          >
            <span class="material-symbols-outlined" style="font-size: 14px">swap_vert</span>
            {{ sortOptions.find((o) => o.key === sortBy)?.label }}
            <span
              class="material-symbols-outlined transition-transform"
              style="font-size: 14px"
              :class="sortOpen ? 'rotate-180' : ''"
              >expand_more</span
            >
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
              v-click-outside="() => (sortOpen = false)"
              class="absolute right-0 top-full mt-2 w-48 glass-heavy rounded-2xl shadow-xl overflow-hidden z-30"
            >
              <button
                v-for="opt in sortOptions"
                :key="opt.key"
                class="w-full flex items-center gap-2 px-4 py-2 text-xs font-bold text-left transition-colors hover:bg-on-surface/[0.04] dark:hover:bg-on-surface/[0.04]"
                :class="
                  sortBy === opt.key
                    ? 'text-primary'
                    : 'text-on-surface-variant hover:text-on-surface'
                "
                @click="sortBy = opt.key; sortOpen = false"
              >
                <span class="material-symbols-outlined" style="font-size: 14px">{{
                  opt.icon
                }}</span>
                {{ opt.label }}
                <span
                  v-if="sortBy === opt.key"
                  class="material-symbols-outlined ml-auto"
                  style="font-size: 14px"
                  >check</span
                >
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
            Showing <strong class="text-on-surface">{{ allTeachers.length }}</strong> result{{
              allTeachers.length !== 1 ? 's' : ''
            }}
          </span>
          <button
            class="ml-auto inline-flex items-center gap-1 font-bold text-error hover:text-error transition-colors"
            @click="clearAll"
          >
            <span class="material-symbols-outlined" style="font-size: 14px">filter_list_off</span>
            Clear filters
          </button>
        </div>
      </Transition>
    </div>

    <!-- Teacher List -->
    <section
      class="liquid-glass rounded-3xl border border-on-surface/[0.04] dark:border-on-surface/5 overflow-hidden"
    >
      <div v-if="usersStore.isLoading" class="p-12 text-center text-on-surface-variant">
        <span class="material-symbols-outlined text-4xl block mb-3 animate-spin"
          >progress_activity</span
        >
        Loading teachers…
      </div>
      <div v-else-if="allTeachers.length === 0" class="p-12 text-center text-on-surface-variant">
        <span class="material-symbols-outlined text-4xl block mb-3">{{
          isFiltered ? 'search_off' : 'person_book'
        }}</span>
        <p class="font-bold mb-1">{{ isFiltered ? 'No teachers match' : 'No teachers found' }}</p>
        <button
          v-if="isFiltered"
          class="text-sm text-primary hover:text-primary font-bold mt-2 transition-colors"
          @click="clearAll"
        >
          Clear filters
        </button>
      </div>
      <div v-else class="divide-y divide-on-surface/[0.04] dark:divide-on-surface/5">
        <button
          v-for="teacher in allTeachers"
          :key="teacher.id"
          class="w-full flex items-center gap-4 px-6 py-4 hover:bg-on-surface/[0.02] dark:hover:bg-on-surface/[0.02] transition-colors text-left group"
          @click="openTeacher(teacher)"
        >
          <!-- Avatar -->
          <div
            class="size-11 rounded-2xl bg-primary/20 border border-primary/20 flex items-center justify-center text-primary font-semibold text-base shrink-0 overflow-hidden"
          >
            <img
              v-if="teacher.avatarUrl"
              :src="teacher.avatarUrl"
              class="w-full h-full object-cover"
            />
            <span v-else>{{ teacher.name.charAt(0).toUpperCase() }}</span>
          </div>
          <!-- Info -->
          <div class="flex-1 min-w-0">
            <p class="font-bold text-on-surface text-sm truncate">{{ teacher.name }}</p>
            <p class="text-on-surface-variant text-xs truncate">
              {{ getInstrumentsLabel(teacher) ?? teacher.email }}
            </p>
          </div>
          <!-- Stats -->
          <div class="flex items-center gap-2 shrink-0">
            <span
              class="text-xs font-semibold px-2 py-1 rounded-full bg-success/10 border border-success/20 text-success"
            >
              {{ completedCount(teacher) }} taught
            </span>
            <span
              class="text-xs font-semibold px-2 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary"
            >
              {{ studentCount(teacher) }} students
            </span>
          </div>
          <span
            class="material-symbols-outlined text-on-surface-variant/40 group-hover:text-on-surface-variant group-hover:translate-x-1 transition-all"
            >arrow_forward_ios</span
          >
        </button>
      </div>
    </section>

    <!-- ── Teacher Detail Modal ────────────────────────────────────────────── -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition-all ease-out"
        enter-from-class="opacity-0 translate-x-8"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition-all ease-in"
        leave-from-class="opacity-100 translate-x-0"
        leave-to-class="opacity-0 translate-x-8"
      >
        <div
          v-if="selectedTeacher"
          class="fixed inset-0 z-[200] flex items-center justify-center p-4"
          @click.self="closeTeacher"
        >
          <div class="absolute inset-0 bg-black/40 dark:bg-black/70" @click="closeTeacher" />

          <div
            class="relative w-full max-w-xl glass-heavy rounded-3xl shadow-2xl flex flex-col max-h-[90vh]"
          >
            <!-- Header -->
            <div class="flex items-center gap-4 p-6 border-b border-on-surface/5">
              <div
                class="size-14 rounded-2xl bg-primary/20 border border-primary/20 flex items-center justify-center text-primary font-semibold text-xl overflow-hidden shrink-0"
              >
                <img
                  v-if="selectedTeacher.avatarUrl"
                  :src="selectedTeacher.avatarUrl"
                  class="w-full h-full object-cover"
                />
                <span v-else>{{ selectedTeacher.name.charAt(0).toUpperCase() }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <h2 class="font-semibold text-xl text-on-surface truncate">
                  {{ selectedTeacher.name }}
                </h2>
                <p class="text-on-surface-variant text-sm">{{ selectedTeacher.email }}</p>
              </div>
              <button class="icon-btn" @click="closeTeacher">
                <span class="material-symbols-outlined text-lg">close</span>
              </button>
            </div>

            <!-- Body -->
            <div class="overflow-y-auto flex-1 p-6 space-y-4 custom-scrollbar">
              <!-- Info grid -->
              <div class="grid grid-cols-2 gap-3">
                <div
                  v-if="getInstrumentsLabel(selectedTeacher)"
                  class="col-span-2 bg-on-surface/[0.04] dark:bg-on-surface/[0.04] rounded-2xl p-3"
                >
                  <p class="text-xs font-semibold text-on-surface-variant uppercase mb-1">
                    Instruments
                  </p>
                  <p class="text-sm font-bold text-on-surface">
                    {{ getInstrumentsLabel(selectedTeacher) }}
                  </p>
                </div>
                <div
                  v-if="selectedTeacher.contactNumber"
                  class="bg-on-surface/[0.04] dark:bg-on-surface/[0.04] rounded-2xl p-3"
                >
                  <p class="text-xs font-semibold text-on-surface-variant uppercase mb-1">
                    Contact
                  </p>
                  <p class="text-sm font-bold text-on-surface">
                    {{ selectedTeacher.contactNumber }}
                  </p>
                </div>
                <div class="bg-primary/10 border border-primary/20 rounded-2xl p-3">
                  <p class="text-xs font-semibold text-primary uppercase mb-1">Students Taught</p>
                  <p class="text-2xl font-semibold text-primary">{{ uniqueStudentCount }}</p>
                </div>
                <div class="alert-success">
                  <p class="text-xs font-semibold text-success uppercase mb-1">Sessions Done</p>
                  <p class="text-2xl font-semibold text-success">{{ stats.completed }}</p>
                </div>
              </div>

              <!-- Stat chips -->
              <div>
                <p class="text-xs font-semibold text-on-surface-variant uppercase mb-3">
                  Session Breakdown
                </p>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="chip in chips"
                    :key="chip.key"
                    class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-semibold uppercase transition-all"
                    :class="[
                      chip.color,
                      activeChip === chip.key
                        ? 'ring-2 ring-offset-1 ring-offset-transparent scale-105'
                        : 'opacity-80 hover:opacity-100',
                    ]"
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
                  {{ activeChip ? chips.find((c) => c.key === activeChip)?.label : 'All' }} Sessions
                </p>
                <button
                  v-for="session in filteredSessions"
                  :key="session.id"
                  class="w-full flex items-center gap-3 p-3 rounded-2xl bg-on-surface/[0.03] dark:bg-on-surface/[0.03] border border-on-surface/[0.05] dark:border-on-surface/5 hover:bg-on-surface/[0.06] dark:hover:bg-on-surface/[0.06] transition-all text-left group"
                  @click="selectedSession = session"
                >
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-bold text-on-surface">
                      {{ formatTime(session.startTime) }}
                    </p>
                    <p class="text-xs text-on-surface-variant">
                      with {{ getStudentName(session.studentId) }}
                    </p>
                  </div>
                  <span
                    class="text-xs font-semibold px-2 py-1 rounded-full border"
                    :class="statusBadge(session.status)"
                  >
                    {{ statusLabel(session.status) }}
                  </span>
                  <span
                    class="material-symbols-outlined text-sm text-on-surface-variant/40 group-hover:text-on-surface-variant transition-colors"
                    >chevron_right</span
                  >
                </button>
              </div>
              <div v-else-if="activeChip" class="text-center py-6 text-on-surface-variant text-sm">
                No sessions in this category.
              </div>
              <div
                v-else-if="teacherSessions.length === 0"
                class="text-center py-6 text-on-surface-variant text-sm"
              >
                No sessions yet for this teacher.
              </div>
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
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>

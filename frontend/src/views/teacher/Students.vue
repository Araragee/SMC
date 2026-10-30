<script setup lang="ts">
import StudentDetailModal from '@components/StudentDetailModal.vue'
import { ref, computed, onMounted } from 'vue'
import { useUsersStore } from '@stores/users'
import { useScheduleStore } from '@stores/schedule'
import { useAuthStore } from '@stores/auth'
import { useToastStore } from '@stores/toast'
import SessionDetailModal from '@components/SessionDetailModal.vue'
import type { User, Session } from '@types'

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

// ── list-level state ──────────────────────────────────────────────────────────
const search = ref('')
const listFilter = ref('all')
const sortBy = ref('name-asc')
const sortOpen = ref(false)

// Two statements, so not inline: Prettier splits a multi-statement handler
// across lines and drops the separator, leaving markup Vue cannot parse.
function applySort(key: typeof sortBy.value) {
  sortBy.value = key
  sortOpen.value = false
}

// ── detail modal state ────────────────────────────────────────────────────────
const selectedStudent = ref<User | null>(null)
const activeChip = ref<string | null>(null)
const selectedSession = ref<Session | null>(null)

onMounted(async () => {
  const myId = authStore.currentUser?.id
  await Promise.all([
    usersStore.fetchUsersByRole('student'),
    usersStore.fetchUsersByRole('teacher'),
    myId ? scheduleStore.fetchUserSessions(myId) : Promise.resolve(),
  ])
})

// ── sessions belonging to this teacher ────────────────────────────────────────
const mySessions = computed(() => {
  const myId = authStore.currentUser?.id
  if (!myId) return []
  return scheduleStore.allSessions.filter((s) => s.teacherId === myId)
})

// ── base student list (unique students from my sessions) ──────────────────────
const baseStudents = computed((): User[] => {
  const ids = [...new Set(mySessions.value.map((s) => s.studentId))]
  return ids.map((id) => usersStore.users.find((u) => u.id === id)).filter((u): u is User => !!u)
})

// ── per-student helpers ───────────────────────────────────────────────────────
function sessionsOf(student: User) {
  return mySessions.value.filter((s) => s.studentId === student.id)
}
function doneCount(student: User) {
  return sessionsOf(student).filter((s) => s.status === 'completed').length
}
function hasOverdue(student: User) {
  return sessionsOf(student).some((s) => ['overdue', 'overdue_rejected'].includes(s.status))
}
function hasAttention(student: User) {
  return sessionsOf(student).some((s) =>
    ['overdue', 'overdue_rejected', 'pending_teacher', 'pending_student', 'pending_admin'].includes(
      s.status
    )
  )
}
function hasActive(student: User) {
  return sessionsOf(student).some((s) => s.status === 'scheduled')
}
function allDone(student: User) {
  const ss = sessionsOf(student)
  return ss.length > 0 && ss.every((s) => ['completed', 'cancelled', 'rejected'].includes(s.status))
}

// ── list filter definitions ───────────────────────────────────────────────────
const listFilters = computed(() => {
  const bs = baseStudents.value
  return [
    { key: 'all', label: 'All', icon: 'group', count: bs.length },
    {
      key: 'attention',
      label: 'Needs Attention',
      icon: 'warning',
      count: bs.filter(hasAttention).length,
    },
    { key: 'overdue', label: 'Has Overdue', icon: 'schedule', count: bs.filter(hasOverdue).length },
    { key: 'active', label: 'Active', icon: 'event_available', count: bs.filter(hasActive).length },
    { key: 'done', label: 'All Done', icon: 'task_alt', count: bs.filter(allDone).length },
  ]
})

const sortOptions = [
  { key: 'name-asc', label: 'Name A → Z', icon: 'sort_by_alpha' },
  { key: 'name-desc', label: 'Name Z → A', icon: 'sort_by_alpha' },
  { key: 'most-done', label: 'Most Done', icon: 'arrow_downward' },
  { key: 'most-active', label: 'Most Active', icon: 'event_available' },
]

// ── filtered + sorted list ────────────────────────────────────────────────────
const myStudents = computed(() => {
  let list = baseStudents.value

  // text search
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter((u) => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q))
  }

  // status filter
  switch (listFilter.value) {
    case 'attention':
      list = list.filter(hasAttention)
      break
    case 'overdue':
      list = list.filter(hasOverdue)
      break
    case 'active':
      list = list.filter(hasActive)
      break
    case 'done':
      list = list.filter(allDone)
      break
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
    case 'most-done':
      out.sort((a: any, b: any) => doneCount(b) - doneCount(a))
      break
    case 'most-active':
      out.sort(
        (a: any, b: any) =>
          sessionsOf(b).filter((s) => s.status === 'scheduled').length -
          sessionsOf(a).filter((s) => s.status === 'scheduled').length
      )
      break
  }
  return out
})

const allUsers = computed(() => usersStore.users)
const isFiltered = computed(() => search.value.trim() !== '' || listFilter.value !== 'all')
function clearAll() {
  search.value = ''
  listFilter.value = 'all'
}

// ── detail modal computed ─────────────────────────────────────────────────────
const studentSessions = computed(() => {
  if (!selectedStudent.value) return []
  return mySessions.value.filter((s) => s.studentId === selectedStudent.value!.id)
})

const stats = computed(() => {
  const ss = studentSessions.value
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

function openStudent(student: User) {
  selectedStudent.value = student
  activeChip.value = null
  selectedSession.value = null
}
function closeStudent() {
  selectedStudent.value = null
  activeChip.value = null
  selectedSession.value = null
}
// ── teacher session actions ───────────────────────────────────────────────────
async function handleApproveTeacher(sessionId: number) {
  try {
    await scheduleStore.approveAsTeacher(sessionId)
    toast.success('Session approved')
    selectedSession.value = scheduleStore.allSessions.find((s) => s.id === sessionId) ?? null
  } catch {
    toast.error('Action failed')
  }
}

function handleRejectTeacher(_sessionId: number) {
  selectedSession.value = null
}

async function handleApproveStudent(sessionId: number) {
  try {
    await scheduleStore.approveAsStudent(sessionId)
    toast.success('Approved on student behalf')
    selectedSession.value = scheduleStore.allSessions.find((s) => s.id === sessionId) ?? null
  } catch {
    toast.error('Action failed')
  }
}

async function handleRejectStudent(sessionId: number) {
  try {
    await scheduleStore.rejectAsStudent(sessionId)
    toast.success('Session declined on student behalf')
    selectedSession.value = null
  } catch {
    toast.error('Action failed')
  }
}
</script>

<template>
  <div class="w-full mx-auto pb-28 space-y-6">
    <div>
      <h1 class="text-5xl font-semibold tracking-tight text-on-surface mb-2">My Students</h1>
      <p class="text-on-surface-variant font-medium">
        <span class="text-on-surface font-bold">{{ baseStudents.length }}</span> students in your
        sessions
      </p>
    </div>

    <!-- Search + Filter toolbar -->
    <div class="space-y-3">
      <div class="relative group">
        <span
          class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant text-xl pointer-events-none transition-colors group-focus-within:text-success"
          >search</span
        >
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
            class="absolute right-3 top-1/2 -translate-y-1/2 size-7 rounded-xl bg-on-surface/[0.06] dark:bg-on-surface/[0.06] hover:bg-on-surface/10 dark:hover:bg-on-surface/10 flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-all"
            @click="search = ''"
          >
            <span class="material-symbols-outlined text-base">close</span>
          </button>
        </Transition>
      </div>

      <!-- Filter pills + Sort -->
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div
          class="w-full sm:flex-1 flex items-center gap-1.5 overflow-x-auto scrollbar-hide pb-0.5 min-w-0"
        >
          <button
            v-for="f in listFilters"
            :key="f.key"
            class="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-bold transition-all"
            :class="
              listFilter === f.key
                ? 'bg-success border-success text-on-success shadow-md shadow-success/30'
                : 'bg-on-surface/[0.04] dark:bg-on-surface/[0.04] border-on-surface/[0.06] dark:border-on-surface/[0.06] text-on-surface-variant hover:text-on-surface hover:bg-on-surface/[0.08] dark:hover:bg-on-surface/[0.08]'
            "
            @click="listFilter = listFilter === f.key && f.key !== 'all' ? 'all' : f.key"
          >
            <span class="material-symbols-outlined text-sm">{{ f.icon }}</span>
            {{ f.label }}
            <span
              class="font-semibold"
              :class="listFilter === f.key ? 'opacity-80' : 'opacity-50'"
              >{{ f.count }}</span
            >
          </button>
        </div>

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
            <span class="material-symbols-outlined text-sm">swap_vert</span>
            {{ sortOptions.find((o) => o.key === sortBy)?.label }}
            <span
              class="material-symbols-outlined transition-transform text-sm"
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
                    ? 'text-success'
                    : 'text-on-surface-variant hover:text-on-surface'
                "
                @click="applySort(opt.key)"
              >
                <span class="material-symbols-outlined text-sm">{{ opt.icon }}</span>
                {{ opt.label }}
                <span v-if="sortBy === opt.key" class="material-symbols-outlined ml-auto text-sm"
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
            Showing <strong class="text-on-surface">{{ myStudents.length }}</strong> result{{
              myStudents.length !== 1 ? 's' : ''
            }}
          </span>
          <button
            class="ml-auto inline-flex items-center gap-1 font-bold text-error hover:text-error transition-colors"
            @click="clearAll"
          >
            <span class="material-symbols-outlined text-sm">filter_list_off</span>
            Clear filters
          </button>
        </div>
      </Transition>
    </div>

    <section
      class="liquid-glass rounded-3xl border border-on-surface/[0.04] dark:border-on-surface/5 overflow-hidden"
    >
      <div
        v-if="usersStore.isLoading || scheduleStore.isLoading"
        class="p-12 text-center text-on-surface-variant"
      >
        <span class="material-symbols-outlined text-4xl block mb-3 animate-spin"
          >progress_activity</span
        >
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
        <button
          class="text-sm text-success hover:text-success font-bold mt-2 transition-colors"
          @click="clearAll"
        >
          Clear filters
        </button>
      </div>
      <div v-else class="divide-y divide-on-surface/[0.04] dark:divide-on-surface/5">
        <button
          v-for="student in myStudents"
          :key="student.id"
          class="w-full flex flex-wrap items-center gap-x-4 gap-y-2 px-4 sm:px-6 py-4 hover:bg-on-surface/[0.02] dark:hover:bg-on-surface/[0.02] transition-colors text-left group"
          @click="openStudent(student)"
        >
          <div
            class="size-11 rounded-2xl bg-success/20 border border-success/20 flex items-center justify-center text-success font-semibold text-base shrink-0 overflow-hidden"
          >
            <img
              v-if="student.avatarUrl"
              :src="student.avatarUrl"
              class="w-full h-full object-cover"
            />
            <span v-else>{{ student.name.charAt(0).toUpperCase() }}</span>
          </div>
          <div class="flex-1 min-w-0">
            <p class="font-bold text-on-surface text-sm truncate">{{ student.name }}</p>
            <p class="text-on-surface-variant text-xs truncate">{{ student.email }}</p>
          </div>
          <!-- Status + done count -->
          <div
            class="order-last w-full flex items-center gap-2 sm:order-none sm:w-auto sm:shrink-0"
          >
            <span
              v-if="hasOverdue(student)"
              class="text-xs font-semibold px-2 py-0.5 rounded-full bg-error/15 border border-error/25 text-error"
              >Overdue</span
            >
            <span
              v-else-if="hasAttention(student)"
              class="text-xs font-semibold px-2 py-0.5 rounded-full bg-warning/15 border border-warning/25 text-warning"
              >Pending</span
            >
            <span
              class="text-xs font-semibold px-2 py-1 rounded-full bg-success/10 border border-success/20 text-success"
            >
              {{ doneCount(student) }} done
            </span>
          </div>
          <span
            class="material-symbols-outlined text-on-surface-variant/40 group-hover:text-on-surface-variant group-hover:translate-x-1 transition-all"
            >arrow_forward_ios</span
          >
        </button>
      </div>
    </section>

    <!-- ── Student Detail Modal ────────────────────────────────────────────── -->
    <StudentDetailModal
      :student="selectedStudent"
      :sessions="studentSessions"
      stat-label="Sessions Done"
      :stat-value="stats.completed"
      empty-text="No sessions with this student yet."
      @close="closeStudent"
      @select-session="selectedSession = $event"
    />

    <SessionDetailModal
      :session="selectedSession"
      user-role="teacher"
      :current-user-id="authStore.currentUser?.id ?? 0"
      :users="allUsers"
      @close="selectedSession = null"
      @approve-teacher="(id) => handleApproveTeacher(id)"
      @reject-teacher="(id) => handleRejectTeacher(id)"
      @approve-student="(id) => handleApproveStudent(id)"
      @reject-student="(id) => handleRejectStudent(id)"
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

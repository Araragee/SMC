<script setup lang="ts">
import StudentDetailModal from '@components/StudentDetailModal.vue'
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
  await Promise.all([usersStore.fetchUsers(), scheduleStore.fetchAllSessions()])
})

// ── helpers for per-student session counts ────────────────────────────────────
function sessionsOf(student: User) {
  return scheduleStore.allSessions.filter((s) => s.studentId === student.id)
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

// ── list filter definitions ───────────────────────────────────────────────────
const baseStudents = computed(() => usersStore.getUsersByRole('student'))

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
    {
      key: 'low',
      label: 'Low Sessions',
      icon: 'hourglass_bottom',
      count: bs.filter((s) => (s.sessionsLeft ?? 0) > 0 && (s.sessionsLeft ?? 0) <= 2).length,
    },
    {
      key: 'none',
      label: 'No Sessions Left',
      icon: 'block',
      count: bs.filter((s) => (s.sessionsLeft ?? 0) === 0).length,
    },
  ]
})

const sortOptions = [
  { key: 'name-asc', label: 'Name A → Z', icon: 'sort_by_alpha' },
  { key: 'name-desc', label: 'Name Z → A', icon: 'sort_by_alpha' },
  { key: 'sessions-high', label: 'Sessions Left ↓', icon: 'arrow_downward' },
  { key: 'sessions-low', label: 'Sessions Left ↑', icon: 'arrow_upward' },
]

// ── main list (search + filter + sort) ───────────────────────────────────────
const allStudents = computed(() => {
  let list = baseStudents.value

  // text search
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter((s) => s.name.toLowerCase().includes(q) || s.email.toLowerCase().includes(q))
  }

  // list filter
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
    case 'low':
      list = list.filter((s) => (s.sessionsLeft ?? 0) > 0 && (s.sessionsLeft ?? 0) <= 2)
      break
    case 'none':
      list = list.filter((s) => (s.sessionsLeft ?? 0) === 0)
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
    case 'sessions-high':
      out.sort((a: any, b: any) => (b.sessionsLeft ?? 0) - (a.sessionsLeft ?? 0))
      break
    case 'sessions-low':
      out.sort((a: any, b: any) => (a.sessionsLeft ?? 0) - (b.sessionsLeft ?? 0))
      break
  }
  return out
})

const isFiltered = computed(() => search.value.trim() !== '' || listFilter.value !== 'all')

function clearAll() {
  search.value = ''
  listFilter.value = 'all'
}

// ── detail modal helpers ──────────────────────────────────────────────────────
const allUsers = computed(() => usersStore.users)

const studentSessions = computed(() => {
  if (!selectedStudent.value) return []
  return scheduleStore.allSessions.filter((s) => s.studentId === selectedStudent.value!.id)
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
function getTeacherName(id: number) {
  return usersStore.users.find((u) => u.id === id)?.name ?? `Teacher #${id}`
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
    <div>
      <h1 class="text-5xl font-semibold tracking-tight text-on-surface mb-2">Students</h1>
      <p class="text-on-surface-variant font-medium">
        <span class="text-on-surface font-bold">{{ baseStudents.length }}</span> enrolled students
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
      <div class="flex items-center gap-2">
        <div class="flex-1 flex items-center gap-1.5 overflow-x-auto scrollbar-hide pb-0.5 min-w-0">
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
              class="material-symbols-outlined text-sm transition-transform"
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
                <span v-if="sortBy === opt.key" class="material-symbols-outlined text-sm ml-auto"
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
            Showing
            <strong class="text-on-surface">{{ allStudents.length }}</strong>
            result{{ allStudents.length !== 1 ? 's' : '' }}
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
      <div v-if="usersStore.isLoading" class="p-12 text-center text-on-surface-variant">
        <span class="material-symbols-outlined text-4xl block mb-3 animate-spin"
          >progress_activity</span
        >
        Loading students…
      </div>
      <div v-else-if="allStudents.length === 0" class="p-12 text-center text-on-surface-variant">
        <span class="material-symbols-outlined text-4xl block mb-3">{{
          isFiltered ? 'search_off' : 'school'
        }}</span>
        <p class="font-bold mb-1">{{ isFiltered ? 'No students match' : 'No students found' }}</p>
        <button
          v-if="isFiltered"
          class="text-sm text-success hover:text-success font-bold mt-2 transition-colors"
          @click="clearAll"
        >
          Clear filters
        </button>
      </div>
      <div v-else class="divide-y divide-on-surface/[0.04] dark:divide-on-surface/5">
        <button
          v-for="student in allStudents"
          :key="student.id"
          class="w-full flex items-center gap-4 px-6 py-4 hover:bg-on-surface/[0.02] dark:hover:bg-on-surface/[0.02] transition-colors text-left group"
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
          <div class="flex items-center gap-2 shrink-0">
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
              class="text-xs font-semibold px-2 py-1 rounded-full shrink-0"
              :class="
                (student.sessionsLeft ?? 0) === 0
                  ? 'bg-surface-container-high/10 border border-outline-variant/20 text-on-surface-variant'
                  : (student.sessionsLeft ?? 0) <= 2
                    ? 'bg-error/10 border border-error/20 text-error'
                    : 'bg-success/10 border border-success/20 text-success'
              "
            >
              {{ student.sessionsLeft ?? 0 }} left
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
      stat-label="Sessions Left"
      :stat-value="selectedStudent?.sessionsLeft ?? 0"
      @close="closeStudent"
      @select-session="selectedSession = $event"
    >
      <template #session-subtitle="{ session }">
        with {{ getTeacherName(session.teacherId) }}
      </template>
    </StudentDetailModal>

    <SessionDetailModal
      :session="selectedSession"
      user-role="admin"
      :current-user-id="authStore.currentUser?.id ?? 0"
      :users="allUsers"
      @close="selectedSession = null"
      @approve-admin="(id) => handleApprove(id)"
      @reject-admin="
        () => {
          selectedSession = null
        }
      "
      @complete-admin="(id) => handleComplete(id)"
      @reject-proof-admin="(id) => handleRejectProof(id)"
      @approve-teacher="(id) => handleApprove(id)"
      @reject-teacher="
        () => {
          selectedSession = null
        }
      "
      @approve-student="(id) => handleApprove(id)"
      @reject-student="
        async (id) => {
          try {
            await scheduleStore.rejectAsStudent(id)
            toast.success('Session declined')
            selectedSession = null
            await scheduleStore.fetchAllSessions()
          } catch {
            toast.error('Action failed')
          }
        }
      "
      @edit-admin="
        () => {
          selectedSession = null
        }
      "
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

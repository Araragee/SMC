<script setup lang="ts">
/**
 * The teacher's homework desk.
 *
 * The organising idea is the review queue: the default tab is work that has
 * been handed in and is waiting on the teacher, because that is the only
 * status where someone else is blocked. Assigning is available from here too,
 * but it is the secondary action — a teacher opens this page to respond to
 * submissions far more often than to create one.
 */
import { computed, onMounted, ref } from 'vue'
import { useHomeworkStore } from '@stores/homework'
import { useScheduleStore } from '@stores/schedule'
import { useUsersStore } from '@stores/users'
import { useAuthStore } from '@stores/auth'
import { useToastStore } from '@stores/toast'
import { useDialog } from '@composables/useDialog'
import type { Homework, HomeworkStatus } from '@types'
import BaseButton from '@components/BaseButton.vue'
import BaseInput from '@components/BaseInput.vue'

const homeworkStore = useHomeworkStore()
const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()
const toast = useToastStore()
const { confirm } = useDialog()

type Tab = HomeworkStatus | 'all'

const activeTab = ref<Tab>('submitted')
const studentFilter = ref<number | 'all'>('all')

// Assign form
const showAssignForm = ref(false)
const assignSessionId = ref<number | null>(null)
const assignDescription = ref('')
const assignDueDate = ref('')

// Review form — keyed by row so two rows cannot share one draft.
const reviewingId = ref<number | null>(null)
const reviewGrade = ref('')
const reviewFeedback = ref('')

// Edit form
const editingId = ref<number | null>(null)
const editDescription = ref('')
const editDueDate = ref('')

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: 'submitted', label: 'To review', icon: 'rate_review' },
  { key: 'assigned', label: 'Outstanding', icon: 'pending_actions' },
  { key: 'overdue', label: 'Overdue', icon: 'schedule' },
  { key: 'reviewed', label: 'Reviewed', icon: 'task_alt' },
  { key: 'all', label: 'All', icon: 'list' },
]

const STATUS_STYLES: Record<HomeworkStatus, { label: string; classes: string }> = {
  assigned: { label: 'Outstanding', classes: 'bg-tertiary/10 text-tertiary border-tertiary/20' },
  overdue: { label: 'Overdue', classes: 'bg-error/10 text-error border-error/20' },
  submitted: { label: 'Awaiting review', classes: 'bg-primary/10 text-primary border-primary/20' },
  reviewed: { label: 'Reviewed', classes: 'bg-secondary/10 text-secondary border-secondary/20' },
}

onMounted(async () => {
  // The whole list, filtered client-side: a teacher's assignment count is in
  // the dozens, and holding it locally makes the tab counts honest and the
  // tab switches instant. The server filter exists for when that stops being
  // true, and `fetchAssigned` already accepts it.
  await homeworkStore.fetchAssigned().catch(() => {})
  if (!scheduleStore.allSessions.length && authStore.currentUser?.id) {
    await scheduleStore.fetchUserSessions(authStore.currentUser.id).catch(() => {})
  }
  // Sessions carry a studentId, not a name; the assign dropdown has to say who
  // the lesson is with or it is a list of indistinguishable timestamps.
  if (!usersStore.myStudents.length) {
    await usersStore.fetchMyStudents().catch(() => {})
  }
})

const studentNameById = computed(() => {
  const names = new Map<number, string>()
  for (const s of usersStore.myStudents) names.set(Number(s.id), s.name)
  // Assignments already name their student, so they fill any gap the roster
  // call left (a student who has since been unenrolled, say).
  for (const h of homeworkStore.assigned) {
    if (h.studentId && h.studentName && !names.has(h.studentId)) names.set(h.studentId, h.studentName)
  }
  return names
})

const counts = computed(() => homeworkStore.countsByStatus)

const visibleHomework = computed(() => {
  let rows: Homework[] = homeworkStore.assigned
  if (activeTab.value !== 'all') rows = rows.filter((h) => h.status === activeTab.value)
  if (studentFilter.value !== 'all') rows = rows.filter((h) => h.studentId === studentFilter.value)
  return rows
})

/** Students the teacher actually has assignments for — the filter should not
 * offer a name that would produce an empty list. */
const studentsWithHomework = computed(() => {
  const seen = new Map<number, string>()
  for (const h of homeworkStore.assigned) {
    if (h.studentId && !seen.has(h.studentId)) seen.set(h.studentId, h.studentName || 'Student')
  }
  return [...seen.entries()].map(([id, name]) => ({ id, name }))
})

/** Sessions this teacher can assign against, most recent first. */
const assignableSessions = computed(() =>
  [...scheduleStore.allSessions]
    .filter((s) => s.status !== 'cancelled' && s.status !== 'rejected')
    .sort((a, b) => new Date(b.startTime).getTime() - new Date(a.startTime).getTime())
    .slice(0, 50)
)

const formatDate = (value?: string | null) => {
  if (!value) return null
  return new Date(value).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

const dueLabel = (item: Homework) => {
  if (!item.dueDate) return 'No deadline'
  const prefix = item.status === 'overdue' ? 'Was due' : 'Due'
  return `${prefix} ${formatDate(item.dueDate)}`
}

const resetAssignForm = () => {
  showAssignForm.value = false
  assignSessionId.value = null
  assignDescription.value = ''
  assignDueDate.value = ''
}

const submitAssign = async () => {
  if (!assignSessionId.value) {
    toast.error('Pick a lesson', 'Homework is attached to the lesson it follows.')
    return
  }
  if (!assignDescription.value.trim()) {
    toast.error('Describe the work', 'The student sees this text and nothing else.')
    return
  }
  try {
    await homeworkStore.assign(
      assignSessionId.value,
      assignDescription.value.trim(),
      assignDueDate.value ? new Date(assignDueDate.value).toISOString() : null
    )
    resetAssignForm()
  } catch {
    // The store has already reported it with the server's own message.
  }
}

const startReview = (item: Homework) => {
  reviewingId.value = item.id
  // Pre-fill from any previous review so re-grading is an edit, not a retype.
  reviewGrade.value = item.grade ?? ''
  reviewFeedback.value = item.feedback ?? ''
}

const submitReview = async (item: Homework) => {
  try {
    await homeworkStore.review(item.id, reviewGrade.value.trim(), reviewFeedback.value.trim())
    reviewingId.value = null
  } catch {
    /* reported by the store */
  }
}

const startEdit = (item: Homework) => {
  editingId.value = item.id
  editDescription.value = item.description
  // datetime-local wants `YYYY-MM-DDTHH:mm` in local time, not an ISO string.
  editDueDate.value = item.dueDate ? toLocalInput(item.dueDate) : ''
}

function toLocalInput(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const submitEdit = async (item: Homework) => {
  if (!editDescription.value.trim()) {
    toast.error('Describe the work', 'The description cannot be empty.')
    return
  }
  try {
    await homeworkStore.edit(item.id, {
      description: editDescription.value.trim(),
      dueDate: editDueDate.value ? new Date(editDueDate.value).toISOString() : null,
      // An emptied field means "remove the deadline", which the API needs told
      // explicitly — a null due_date alone is indistinguishable from omitting it.
      clearDueDate: !editDueDate.value && !!item.dueDate,
    })
    editingId.value = null
  } catch {
    /* reported by the store */
  }
}

const withdraw = async (item: Homework) => {
  const ok = await confirm(
    `Withdraw this homework for ${item.studentName || 'this student'}? Anything they submitted is removed with it.`,
    { title: 'Withdraw homework', destructive: true }
  )
  if (!ok) return
  await homeworkStore.remove(item.id).catch(() => {})
}
</script>

<template>
  <div class="max-w-[1200px] mx-auto pb-28 space-y-8 px-4 sm:px-6">
    <header class="pt-8">
      <div class="flex items-center gap-3 mb-3">
        <div
          class="size-10 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center"
        >
          <span class="material-symbols-outlined text-primary text-2xl">assignment</span>
        </div>
        <p class="text-xs font-semibold text-primary uppercase">Teaching</p>
      </div>
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 class="text-3xl font-bold text-on-surface">Homework</h1>
          <p class="text-sm text-on-surface/60 mt-1">
            Assign practice, then review what comes back.
          </p>
        </div>
        <BaseButton @click="showAssignForm = !showAssignForm">
          <span class="material-symbols-outlined text-base mr-1 align-middle">
            {{ showAssignForm ? 'close' : 'add' }}
          </span>
          {{ showAssignForm ? 'Cancel' : 'Assign homework' }}
        </BaseButton>
      </div>
    </header>

    <!-- Assign -->
    <section v-if="showAssignForm" class="glass rounded-3xl p-5 sm:p-6 space-y-4">
      <h2 class="font-semibold text-on-surface">New assignment</h2>

      <div>
        <label class="block text-xs font-semibold text-on-surface/60 mb-1.5" for="hw-session">
          Lesson
        </label>
        <select
          id="hw-session"
          v-model.number="assignSessionId"
          class="w-full rounded-2xl bg-surface border border-outline/30 px-4 py-2.5 text-sm text-on-surface"
        >
          <option :value="null" disabled>Choose the lesson this follows…</option>
          <option v-for="s in assignableSessions" :key="s.id" :value="s.id">
            {{ studentNameById.get(s.studentId) || 'Student' }} — {{ formatDate(s.startTime) }}
          </option>
        </select>
        <p v-if="!assignableSessions.length" class="text-xs text-on-surface/50 mt-1.5">
          You have no lessons yet. Homework is attached to the lesson it follows.
        </p>
      </div>

      <div>
        <label class="block text-xs font-semibold text-on-surface/60 mb-1.5" for="hw-desc">
          What should they practise?
        </label>
        <textarea
          id="hw-desc"
          v-model="assignDescription"
          rows="3"
          maxlength="2000"
          placeholder="e.g. G major scale, two octaves, hands together at 60 bpm"
          class="w-full rounded-2xl bg-surface border border-outline/30 px-4 py-2.5 text-sm text-on-surface"
        />
      </div>

      <BaseInput v-model="assignDueDate" label="Due (optional)" type="datetime-local" />

      <div class="flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
        <BaseButton variant="tertiary" @click="resetAssignForm">Cancel</BaseButton>
        <BaseButton :disabled="homeworkStore.isSaving" @click="submitAssign">
          {{ homeworkStore.isSaving ? 'Assigning…' : 'Assign' }}
        </BaseButton>
      </div>
    </section>

    <!-- Filters -->
    <div class="flex flex-wrap items-center gap-2">
      <button
        v-for="tab in TABS"
        :key="tab.key"
        class="px-3.5 py-2 rounded-2xl text-xs font-semibold border transition-colors flex items-center gap-1.5"
        :class="
          activeTab === tab.key
            ? 'bg-primary/10 text-primary border-primary/20'
            : 'bg-surface text-on-surface/60 border-outline/20 hover:text-on-surface'
        "
        @click="activeTab = tab.key"
      >
        <span class="material-symbols-outlined text-sm">{{ tab.icon }}</span>
        {{ tab.label }}
        <span v-if="tab.key !== 'all'" class="opacity-70">({{ counts[tab.key] }})</span>
      </button>

      <select
        v-if="studentsWithHomework.length > 1"
        v-model="studentFilter"
        class="ml-auto rounded-2xl bg-surface border border-outline/30 px-3 py-2 text-xs text-on-surface"
        aria-label="Filter by student"
      >
        <option value="all">All students</option>
        <option v-for="s in studentsWithHomework" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
    </div>

    <!-- List -->
    <section class="space-y-3">
      <p v-if="homeworkStore.isLoading" class="text-sm text-on-surface/60 py-8 text-center">
        Loading homework…
      </p>

      <div
        v-else-if="!visibleHomework.length"
        class="glass rounded-3xl p-10 text-center space-y-2"
      >
        <span class="material-symbols-outlined text-4xl text-on-surface/30">assignment_turned_in</span>
        <p class="text-sm text-on-surface/60">
          {{
            activeTab === 'submitted'
              ? 'Nothing waiting on you right now.'
              : 'No homework here yet.'
          }}
        </p>
      </div>

      <article
        v-for="item in visibleHomework"
        :key="item.id"
        class="glass rounded-3xl p-5 space-y-3"
      >
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="font-semibold text-on-surface truncate">
              {{ item.studentName || 'Student' }}
            </p>
            <p class="text-xs text-on-surface/50 mt-0.5">
              Lesson {{ formatDate(item.sessionStartTime) || '—' }} · {{ dueLabel(item) }}
            </p>
          </div>
          <span
            class="shrink-0 px-2.5 py-1 rounded-xl text-[11px] font-semibold border"
            :class="STATUS_STYLES[item.status].classes"
          >
            {{ STATUS_STYLES[item.status].label }}
          </span>
        </div>

        <!-- Description, or the edit form in its place -->
        <div v-if="editingId === item.id" class="space-y-3 pt-1">
          <textarea
            v-model="editDescription"
            rows="3"
            maxlength="2000"
            class="w-full rounded-2xl bg-surface border border-outline/30 px-4 py-2.5 text-sm text-on-surface"
          />
          <BaseInput v-model="editDueDate" label="Due (leave blank for none)" type="datetime-local" />
          <div class="flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
            <BaseButton variant="tertiary" size="sm" @click="editingId = null">Cancel</BaseButton>
            <BaseButton size="sm" :disabled="homeworkStore.isSaving" @click="submitEdit(item)">
              Save changes
            </BaseButton>
          </div>
        </div>
        <p v-else class="text-sm text-on-surface/80 whitespace-pre-line">{{ item.description }}</p>

        <!-- What the student handed in -->
        <div v-if="item.fileUrl" class="flex items-center gap-2 text-xs">
          <span class="material-symbols-outlined text-sm text-on-surface/50">attach_file</span>
          <a
            :href="item.fileUrl"
            target="_blank"
            rel="noopener noreferrer"
            class="text-primary font-semibold hover:underline"
          >
            View submission
          </a>
          <span v-if="item.completedAt" class="text-on-surface/40">
            · submitted {{ formatDate(item.completedAt) }}
          </span>
        </div>

        <!-- Existing review -->
        <div
          v-if="item.status === 'reviewed' && reviewingId !== item.id"
          class="rounded-2xl bg-secondary/5 border border-secondary/15 px-4 py-3 space-y-1"
        >
          <p v-if="item.grade" class="text-sm font-semibold text-on-surface">
            Grade: {{ item.grade }}
          </p>
          <p v-if="item.feedback" class="text-sm text-on-surface/70 whitespace-pre-line">
            {{ item.feedback }}
          </p>
          <p v-if="!item.grade && !item.feedback" class="text-sm text-on-surface/50">
            Marked as reviewed with no remarks.
          </p>
        </div>

        <!-- Review form -->
        <div v-if="reviewingId === item.id" class="space-y-3 pt-1">
          <BaseInput
            v-model="reviewGrade"
            label="Grade (optional)"
            placeholder="A-, 92%, Needs work…"
          />
          <textarea
            v-model="reviewFeedback"
            rows="3"
            maxlength="2000"
            placeholder="What went well, what to work on next."
            class="w-full rounded-2xl bg-surface border border-outline/30 px-4 py-2.5 text-sm text-on-surface"
          />
          <div class="flex flex-col-reverse sm:flex-row sm:justify-end gap-2">
            <BaseButton variant="tertiary" size="sm" @click="reviewingId = null">Cancel</BaseButton>
            <BaseButton size="sm" :disabled="homeworkStore.isSaving" @click="submitReview(item)">
              {{ homeworkStore.isSaving ? 'Saving…' : 'Save review' }}
            </BaseButton>
          </div>
        </div>

        <!-- Actions -->
        <div
          v-if="reviewingId !== item.id && editingId !== item.id"
          class="flex flex-wrap items-center gap-2 pt-1"
        >
          <BaseButton
            v-if="item.status === 'submitted' || item.status === 'reviewed'"
            size="sm"
            @click="startReview(item)"
          >
            {{ item.status === 'reviewed' ? 'Edit review' : 'Review' }}
          </BaseButton>
          <BaseButton variant="tertiary" size="sm" @click="startEdit(item)">Edit</BaseButton>
          <button
            class="text-xs font-semibold text-error/80 hover:text-error px-2 py-1.5 rounded-xl"
            @click="withdraw(item)"
          >
            Withdraw
          </button>
        </div>
      </article>
    </section>
  </div>
</template>

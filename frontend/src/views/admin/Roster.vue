<script setup lang="ts">
import BaseDropdown from '@/components/BaseDropdown.vue';
import { computed, onMounted, reactive, ref } from 'vue'
import { useUsersStore } from '@stores/users'
import { useRosterStore, type BulkResult } from '@stores/roster'
import { useToastStore } from '@stores/toast'
import { useDialog } from '@composables/useDialog'
import StudentPickerModal from '@components/StudentPickerModal.vue'
import type { Enrollment } from '@types'

type Tab = 'enrollments' | 'requests'

const usersStore = useUsersStore()
const rosterStore = useRosterStore()
const toast = useToastStore()
const dialog = useDialog()

const activeTab = ref<Tab>('enrollments')
const selectedTeacherId = ref<number | null>(null)
const search = ref('')
const showPicker = ref(false)
const isSubmitting = ref(false)

const approvingId = ref<number | null>(null)
const approveHours = ref<number>(8)

const approveRequest = async function(enrollment: Enrollment) {
  isSubmitting.value = true
  try {
    await rosterStore.approveEnrollment(enrollment.id, approveHours.value)
    toast.success('Enrollment approved', `${userName(enrollment.studentId)} now has ${approveHours.value} hours.`)
    approvingId.value = null
  } catch (err: any) {
    toast.error('Approve failed', err?.response?.data?.detail ?? err?.message)
  } finally {
    isSubmitting.value = false
  }
}

const rejectRequest = async function(enrollment: Enrollment) {
  const ok = await dialog.confirm(
    `Reject ${userName(enrollment.studentId)}'s request to enrol with ${userName(enrollment.teacherId)}?`,
  )
  if (!ok) return
  try {
    await rosterStore.rejectEnrollment(enrollment.id)
    toast.success('Request rejected')
  } catch (err: any) {
    toast.error('Reject failed', err?.response?.data?.detail ?? err?.message)
  }
}

const editing = ref<Enrollment | null>(null)
const editForm = reactive({ teacherId: 0, sessionsPurchased: 0, isActive: true })

const teachers = computed(() => usersStore.getUsersByRole('teacher'))
const students = computed(() => usersStore.getUsersByRole('student'))

const userName = (id: number) => usersStore.users.find((u) => u.id === id)?.name ?? `#${id}`


const enrollmentRows = computed(() => {
  const term = search.value.trim().toLowerCase()
  return rosterStore.enrollments.filter(
    (e) =>
      !term ||
      userName(e.studentId).toLowerCase().includes(term) ||
      userName(e.teacherId).toLowerCase().includes(term),
  )
})

/** Students not already enrolled with the selected teacher. */
const pickerCandidates = computed(() => {
  if (!selectedTeacherId.value) return students.value
  const taken = rosterStore.assignedStudentIds(selectedTeacherId.value)
  return students.value.filter((s) => !taken.has(s.id))
})

const reportBulk = (result: BulkResult, verb: string) => {
  if (result.ok) toast.success(`${result.ok} ${result.ok === 1 ? 'student' : 'students'} ${verb}`)
  for (const failure of result.failed) {
    toast.error(`Skipped ${userName(failure.studentId)}`, failure.reason)
  }
}

const openPicker = () => {
  if (!selectedTeacherId.value) {
    toast.error('Pick a teacher first', 'Choose who these students are enrolling with.')
    return
  }
  showPicker.value = true
}

const handlePicked = async (studentIds: number[], sessions: number) => {
  const teacherId = selectedTeacherId.value
  if (!teacherId || studentIds.length === 0) return
  isSubmitting.value = true
  try {
    const result = await rosterStore.bulkEnroll(teacherId, studentIds, sessions)
    reportBulk(result, 'enrolled')
    showPicker.value = false
  } finally {
    isSubmitting.value = false
  }
}


const openEdit = (enrollment: Enrollment) => {
  editing.value = enrollment
  editForm.teacherId = enrollment.teacherId
  editForm.sessionsPurchased = enrollment.sessionsPurchased
  editForm.isActive = enrollment.isActive ?? true
}

const saveEdit = async () => {
  if (!editing.value) return
  isSubmitting.value = true
  try {
    await rosterStore.updateEnrollment(editing.value.id, { ...editForm })
    toast.success('Enrollment updated')
    editing.value = null
  } catch (err: any) {
    toast.error('Update failed', err?.response?.data?.detail || err.message)
  } finally {
    isSubmitting.value = false
  }
}

const handleDeleteEnrollment = async (enrollment: Enrollment) => {
  const label = `${userName(enrollment.studentId)} · ${userName(enrollment.teacherId)}`
  const ok = await dialog.confirm(`Delete the enrollment for ${label}? Unused credits are rolled back.`, {
    title: 'Delete enrollment',
  })
  if (!ok) return
  try {
    await rosterStore.deleteEnrollment(enrollment.id)
    toast.success('Enrollment deleted')
  } catch (err: any) {
    // 409 = the enrollment has usage history; offer the soft-delete path instead.
    if (err?.response?.status === 409) {
      const force = await dialog.confirm(
        'This enrollment already has completed sessions. Archive it instead? History is kept.',
        { title: 'Archive enrollment' },
      )
      if (!force) return
      await rosterStore.deleteEnrollment(enrollment.id, true)
      toast.success('Enrollment archived')
      return
    }
    toast.error('Delete failed', err?.response?.data?.detail || err.message)
  }
}

onMounted(async () => {
  await usersStore.fetchUsers()
  try {
    await rosterStore.fetchAll()
  } catch (err: any) {
    toast.error('Could not load roster', err?.response?.data?.detail || err.message)
  }
  if (!selectedTeacherId.value && teachers.value.length) {
    selectedTeacherId.value = teachers.value[0].id
  }
})
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div class="space-y-2">
        <p class="page-eyebrow">Administration</p>
        <h1 class="page-title">Roster</h1>
        <p class="page-subtitle">
          Place existing students on a teacher's roster, manage their enrollments, and fix credit
          counts without recreating accounts.
        </p>
      </div>
      <div class="flex flex-wrap gap-3">
        <button class="btn-primary" @click="openPicker()">
          <span class="material-symbols-outlined text-lg" aria-hidden="true">library_add</span>
          Bulk enroll
        </button>
      </div>
    </header>

    <!-- Controls: teacher scope + search + tabs -->
    <section class="card card-pad space-y-6">
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="field">
          <label for="roster-teacher" class="field-label">Teacher</label>
          <div class="relative">
            <BaseDropdown :options="[...teachers.map(teacher => ({ value: teacher.id, label: teacher.name }))]" />
            <span
              class="material-symbols-outlined pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-lg text-on-surface-variant"
              aria-hidden="true"
            >expand_more</span>
          </div>
          <p class="field-hint">Adds and bulk enrollments apply to this teacher.</p>
        </div>
        <div class="field">
          <label for="roster-search" class="field-label">Search</label>
          <input id="roster-search" v-model="search" type="search" class="input" placeholder="Filter by name" />
        </div>
      </div>

      <div class="flex gap-2 border-b border-outline-variant/20" role="tablist">
        <button
          v-for="tab in (['enrollments', 'requests'] as Tab[])"
          :key="tab"
          role="tab"
          :aria-selected="activeTab === tab"
          class="-mb-px border-b-2 px-4 py-3 text-sm font-semibold capitalize transition-colors"
          :class="activeTab === tab ? 'border-primary text-primary' : 'border-transparent text-on-surface-variant hover:text-on-surface'"
          @click="activeTab = tab"
        >
          {{ tab === 'enrollments' ? 'Enrollments' : 'Requests' }}
          <span
            v-if="tab === 'requests' && rosterStore.pendingEnrollments.length"
            class="ml-1.5 rounded-full bg-primary px-1.5 py-0.5 text-xs text-on-primary"
          >{{ rosterStore.pendingEnrollments.length }}</span>
        </button>
      </div>

      <!-- Enrollments -->
      <!-- Pending student requests -->
      <div v-if="activeTab === 'requests'">
        <div v-if="!rosterStore.pendingEnrollments.length" class="empty-state">
          <span class="material-symbols-outlined text-4xl text-on-surface-variant" aria-hidden="true">inbox</span>
          <p class="section-title">No pending requests</p>
          <p class="section-caption">Student enrollment requests will appear here for approval.</p>
        </div>
        <div v-else class="overflow-x-auto">
          <table class="data-table">
            <thead>
              <tr>
                <th scope="col">Student</th>
                <th scope="col">Teacher</th>
                <th scope="col">Requested</th>
                <th scope="col" class="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="req in rosterStore.pendingEnrollments" :key="req.id">
                <td class="cell-strong">{{ userName(req.studentId) }}</td>
                <td>{{ userName(req.teacherId) }}</td>
                <td class="cell-muted">{{ new Date(req.createdAt).toLocaleDateString() }}</td>
                <td class="text-right">
                  <!-- Hours are set at approval because they follow payment;
                       the request itself carries none. -->
                  <div v-if="approvingId === req.id" class="flex items-center justify-end gap-2">
                    <input
                      v-model.number="approveHours"
                      type="number"
                      min="1"
                      class="input w-24 py-1.5 text-sm"
                      aria-label="Hours to grant"
                    />
                    <button class="btn-primary btn-sm" :disabled="isSubmitting || approveHours < 1" @click="approveRequest(req)">
                      Grant
                    </button>
                    <button class="btn-ghost btn-sm" @click="approvingId = null">Cancel</button>
                  </div>
                  <div v-else class="flex items-center justify-end gap-2">
                    <button class="btn-primary btn-sm" @click="approvingId = req.id; approveHours = 8">Approve</button>
                    <button class="btn-subtle btn-sm" @click="rejectRequest(req)">Reject</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-else-if="activeTab === 'enrollments'">
        <div v-if="rosterStore.isLoading && !enrollmentRows.length" class="space-y-3">
          <div v-for="i in 4" :key="i" class="skeleton-row" />
        </div>
        <div v-else-if="!enrollmentRows.length" class="empty-state">
          <span class="material-symbols-outlined text-4xl text-on-surface-variant" aria-hidden="true">receipt_long</span>
          <p class="section-title">No enrollments yet</p>
          <p class="section-caption">Enroll students in bulk to grant session credits.</p>
          <button class="btn-primary btn-sm" @click="openPicker()">Bulk enroll</button>
        </div>
        <div v-else class="overflow-x-auto">
          <table class="data-table">
            <thead>
              <tr>
                <th scope="col">Student</th>
                <th scope="col">Teacher</th>
                <th scope="col">Purchased</th>
                <th scope="col">Used</th>
                <th scope="col">Left</th>
                <th scope="col">Status</th>
                <th scope="col" class="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="enrollment in enrollmentRows" :key="enrollment.id">
                <td class="cell-strong">{{ userName(enrollment.studentId) }}</td>
                <td class="cell-muted">{{ userName(enrollment.teacherId) }}</td>
                <td class="num">{{ enrollment.sessionsPurchased }}</td>
                <td class="num">{{ enrollment.sessionsUsed }}</td>
                <td class="num cell-strong">{{ enrollment.sessionsLeft }}</td>
                <td>
                  <span
                    class="badge"
                    :class="enrollment.isActive === false ? 'border-outline-variant/40 text-on-surface-variant' : 'border-emerald-500/30 text-emerald-600 dark:text-emerald-400'"
                  >
                    {{ enrollment.isActive === false ? 'Archived' : 'Active' }}
                  </span>
                </td>
                <td>
                  <div class="flex justify-end gap-2">
                    <button
                      class="icon-btn"
                      :aria-label="`Edit enrollment for ${userName(enrollment.studentId)}`"
                      @click="openEdit(enrollment)"
                    >
                      <span class="material-symbols-outlined text-lg" aria-hidden="true">edit</span>
                    </button>
                    <button
                      class="icon-btn-danger"
                      :aria-label="`Delete enrollment for ${userName(enrollment.studentId)}`"
                      @click="handleDeleteEnrollment(enrollment)"
                    >
                      <span class="material-symbols-outlined text-lg" aria-hidden="true">delete</span>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <StudentPickerModal
      :is-open="showPicker"
      :students="pickerCandidates"
      :is-submitting="isSubmitting"
      :teacher-name="teachers.find((t) => t.id === selectedTeacherId)?.name ?? ''"
      @close="showPicker = false"
      @confirm="handlePicked"
    />

    <!-- Edit enrollment -->
    <Teleport to="body">
      <div
        v-if="editing"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-enrollment-title"
      >
        <div class="absolute inset-0 bg-black/40 dark:bg-black/70" @click="editing = null" />
        <div class="card relative w-full max-w-md bg-surface-container p-6 shadow-xl">
          <div class="mb-6 flex items-start justify-between gap-4">
            <div class="space-y-1">
              <h2 id="edit-enrollment-title" class="section-title">Edit enrollment</h2>
              <p class="section-caption">{{ userName(editing.studentId) }}</p>
            </div>
            <button class="icon-btn" aria-label="Close" @click="editing = null">
              <span class="material-symbols-outlined text-lg" aria-hidden="true">close</span>
            </button>
          </div>

          <form class="space-y-4" @submit.prevent="saveEdit">
            <div class="field">
              <label for="edit-teacher" class="field-label">Teacher</label>
              <BaseDropdown :options="[...teachers.map(teacher => ({ value: teacher.id, label: teacher.name }))]" />
            </div>
            <div class="field">
              <label for="edit-purchased" class="field-label">Sessions purchased</label>
              <input
                id="edit-purchased"
                v-model.number="editForm.sessionsPurchased"
                type="number"
                :min="editing.sessionsUsed"
                class="input num"
              />
              <p class="field-hint">
                {{ editing.sessionsUsed }} already used — the student's credit balance moves by the
                difference.
              </p>
            </div>
            <label class="flex items-center gap-3 text-sm text-on-surface">
              <input v-model="editForm.isActive" type="checkbox" class="size-4 accent-primary" />
              Active
            </label>
            <div class="flex justify-end gap-3 pt-2">
              <button type="button" class="btn-ghost" @click="editing = null">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="isSubmitting">
                {{ isSubmitting ? 'Saving…' : 'Save changes' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

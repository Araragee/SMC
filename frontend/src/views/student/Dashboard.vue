<script setup lang="ts">
import { useRouter } from 'vue-router'
import { onMounted, computed, ref, reactive } from 'vue'
import { useScheduleStore } from '@stores/schedule'
import { useUsersStore } from '@stores/users'
import { useAuthStore } from '@stores/auth'
import { useToastStore } from '@stores/toast'
import { useInteractionsStore } from '@stores/interactions'
import type { Session } from '@types'

const router = useRouter()
const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()
const toast = useToastStore()
const interactionsStore = useInteractionsStore()

const showRequestModal = ref(false)
const requestForm = reactive({ teacherId: null as number | null, startTime: '' })

// ID of the selected session — we store the ID so `selectedSession` always reflects latest store data
const selectedSessionId = ref<number | null>(null)
// Always derive the live session object from the store (so status changes reflect immediately)
const selectedSession = computed(() =>
  selectedSessionId.value
    ? (scheduleStore.allSessions.find((s: any) => s.id === selectedSessionId.value) ?? null)
    : null
)
const showProofViewer = ref(false)

const stagedProofFile = ref<File | null>(null)
const stagedProofUrl = ref<string | null>(null)

const proofPreviewUrl = ref<string | null>(null)
const proofPreviewFile = ref<File | null>(null)

onMounted(async () => {
  if (authStore.currentUser?.id) {
    await Promise.all([
      scheduleStore.fetchUserSessions(authStore.currentUser.id),
      usersStore.fetchUsersByRole('teacher'),
      interactionsStore.fetchStudentEnrollments(authStore.currentUser.id),
    ])
  }
})

const myId = computed(() => authStore.currentUser?.id ?? 0)

const mySessions = computed(() =>
  scheduleStore.allSessions.filter((s: any) => s.studentId === myId.value)
)

const nextSession = computed(
  () =>
    mySessions.value
      .filter((s: any) => s.status === 'scheduled' && s.startTime)
      .sort((a: any, b: any) => new Date(a.startTime!).getTime() - new Date(b.startTime!).getTime())[0] ??
    null
)

const nextSessionCountdown = computed(() => {
  if (!nextSession.value?.startTime) return 'no upcoming sessions'
  const diff = new Date(nextSession.value.startTime).getTime() - Date.now()
  if (diff <= 0) return 'now'
  const hours = Math.floor(diff / 3600000)
  if (hours < 24) return `${hours} hours`
  return `${Math.floor(hours / 24)} days`
})

const overdueSessions = computed(() =>
  mySessions.value.filter((s: any) => ['overdue', 'overdue_rejected'].includes(s.status))
)

const pendingHomework = computed(
  () => mySessions.value.find((s: any) => s.homeworkAssigned && !s.homeworkCompleted) ?? null
)

const sessionProgress = computed(() => {
  const totalSessions = interactionsStore.enrollments.reduce(
    (sum, e) => sum + (e.sessionsPurchased || 0), 0
  )
  if (!totalSessions) return 0
  const used = mySessions.value.filter((s: any) => s.status === 'completed').length
  return Math.min((used / totalSessions) * 100, 100)
})

const allTeachers = computed(() => usersStore.getUsersByRole('teacher'))

const formatTime = (dt: string | undefined) => {
  if (!dt) return '—'
  return new Date(dt).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  })
}
const formatDay = (dt: string | undefined) => {
  if (!dt) return '—'
  return new Date(dt).getDate().toString()
}
const formatMonth = (dt: string | undefined) => {
  if (!dt) return ''
  return new Date(dt).toLocaleString('en-US', { month: 'short' }).toUpperCase()
}

const submitRequest = async function() {
  if (!requestForm.teacherId || !requestForm.startTime) return
  try {
    const start = new Date(requestForm.startTime)
    const end = new Date(start.getTime() + 60 * 60 * 1000)
    await scheduleStore.proposeSessionAsStudent({
      teacherId: requestForm.teacherId,
      studentId: myId.value,
      startTime: start.toISOString(),
      endTime: end.toISOString(),
    })
    toast.success(
      'Session requested!',
      'Your teacher will review and forward to admin for approval.'
    )
    showRequestModal.value = false
    Object.assign(requestForm, { teacherId: null, startTime: '' })
  } catch {
    toast.error('Request failed', 'Please try again or contact your teacher.')
  }
}

const markHomeworkDone = async function(sessionId: number) {
  await interactionsStore.completeHomework(sessionId)
  toast.success('Homework submitted!', 'Great work — keep it up.')
}

const handleStagedProofUpload = function(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.[0]) return
  stagedProofFile.value = input.files[0]
  stagedProofUrl.value = window.URL.createObjectURL(stagedProofFile.value)
}

const saveStagedProof = async function() {
  if (!selectedSession.value || !stagedProofFile.value) return
  try {
    await interactionsStore.uploadImageProof(selectedSession.value.id, stagedProofFile.value)
    toast.success('Proof saved!', 'Your proof is uploaded. You can now request approval.')

    // selectedSession is now a computed, it will auto-update from store - just clear staged state
    stagedProofFile.value = null
    stagedProofUrl.value = null
  } catch {
    // error already toasted in the store
  }
}

const closeSessionModal = function() {
  selectedSessionId.value = null
  stagedProofFile.value = null
  stagedProofUrl.value = null
  approvalJustification.value = ''
  isCountering.value = false
}

const approvalJustification = ref('')

const submitApprovalRequest = async function(sessionId: number) {
  try {
    await scheduleStore.requestApproval(sessionId, approvalJustification.value)
    toast.success('Approval Requested', 'Your proof has been submitted for review.')
    approvalJustification.value = ''
    // The computed selectedSession will update automatically since the store was updated
    // Close modal only after status update is reflected
    selectedSessionId.value = null
  } catch (err: any) {
    toast.error('Failed to submit', err.message || 'Something went wrong.')
  }
}

const handleGenericProofSelection = function(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.[0]) return
  proofPreviewFile.value = input.files[0]
  proofPreviewUrl.value = window.URL.createObjectURL(proofPreviewFile.value)
}

const handleGenericProofUpload = async function() {
  const firstScheduled = mySessions.value.find((s: any) => s.status === 'scheduled')
  if (!firstScheduled) {
    toast.warning('No session to attach to', 'You need an active scheduled session.')
    return
  }
  if (!proofPreviewFile.value) return

  await interactionsStore.uploadImageProof(firstScheduled.id, proofPreviewFile.value)
  toast.success('Proof uploaded!', 'Your session proof has been saved.')

  proofPreviewFile.value = null
  proofPreviewUrl.value = null
}

const isCountering = ref(false)
const counterForm = reactive({ startTime: '', endTime: '', notes: '' })

const startCountering = function(session: Session) {
  isCountering.value = true
  counterForm.startTime = session.startTime.slice(0, 16)
  counterForm.endTime = session.endTime?.slice(0, 16) || ''
  counterForm.notes = 'Refining my schedule'
}

const submitStudentCounter = async function() {
  if (!selectedSession.value) return
  try {
    const startTime = new Date(counterForm.startTime).toISOString();
    let endTime = '';
    if (counterForm.endTime) {
        endTime = new Date(counterForm.endTime).toISOString();
    } else {
        endTime = new Date(new Date(startTime).getTime() + 60 * 60 * 1000).toISOString();
    }

    await scheduleStore.counterAsStudent(selectedSession.value.id, {
      startTime,
      endTime,
      notes: counterForm.notes
    })
    toast.success('Counter proposal sent!', 'Wait for teacher review.')
    isCountering.value = false
    // Don't close: let the computed session update to show new status (pending_teacher)
    // Re-fetch to get any extra server-side updates
    await scheduleStore.fetchUserSessions(authStore.currentUser?.id ?? 0);
  } catch {
    toast.error('Failed to send counter')
  }
}

const approveCounter = async function() {
  if (!selectedSession.value) return
  try {
    await scheduleStore.approveAsStudent(selectedSession.value.id)
    toast.success('Proposal accepted!', 'Forwarded to admin for final confirmation.')
    // Don't close immediately: let selectedSession computed reactively show new status (pending_admin)
    await scheduleStore.fetchUserSessions(authStore.currentUser?.id ?? 0);
  } catch {
    toast.error('Failed to accept proposal')
  }
}

const openRequestModal = () => {
  showRequestModal.value = true
}

const closeRequestModal = () => {
  showRequestModal.value = false
}

const resolveOverdue = () => {
  if (overdueSessions.value.length > 0) {
    selectedSessionId.value = overdueSessions.value[0].id
  }
}

const selectSession = (id: number) => {
  selectedSessionId.value = id
}

const stopCountering = () => {
  isCountering.value = false
}
</script>

<template>
  <div class="w-full mx-auto pb-10">
    <!-- Hero Welcome -->
    <div class="flex items-start justify-between gap-4 mb-6">
      <div>
        <h2 class="text-5xl font-black tracking-tighter text-on-surface dark:text-on-surface mb-3">
          Morning, {{ authStore.currentUser?.name?.split(' ')[0] || 'Student' }}.
        </h2>
        <p class="text-on-surface-variant dark:text-on-surface-variant font-medium mb-6">
          Your next recital rehearsal is in
          <span class="text-primary font-bold">{{ nextSessionCountdown }}</span
          >.
        </p>
        <div class="flex gap-4">
          <RouterLink
            to="/student/schedule"
            class="px-6 py-3 bg-on-surface/[0.04] dark:bg-on-surface/5 hover:bg-on-surface/5 dark:hover:bg-on-surface/10 text-on-surface dark:text-on-surface font-bold rounded-3xl border border-on-surface/[0.08] dark:border-on-surface/10 active:scale-95 transition-all flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-lg">calendar_today</span>
            Schedule
          </RouterLink>
          <button
            class="px-6 py-3 bg-primary text-on-primary font-bold rounded-3xl shadow-lg active:scale-95 hover:scale-[1.02] transition-all flex items-center gap-2"
            @click="openRequestModal"
          >
            <span class="material-symbols-outlined text-lg">add_circle</span>
            Request Session
          </button>
        </div>
      </div>
    </div>

    <!-- Overdue Warning -->
    <div v-if="overdueSessions.length > 0" class="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-start gap-4 text-red-700 dark:text-red-400">
      <span class="material-symbols-outlined shrink-0 text-red-500" style="font-variation-settings: 'FILL' 1">warning</span>
      <div>
        <h4 class="font-bold mb-1">Action Required: Overdue Sessions</h4>
        <p class="text-sm">You have {{ overdueSessions.length }} session(s) that are past their scheduled time. Please upload your session proofs so they can be marked complete.</p>
        <button class="mt-2 text-sm font-semibold underline text-red-600 dark:text-red-300" @click="resolveOverdue">Resolve Now</button>
      </div>
    </div>

    <!-- Main Grid -->
    <div class="grid grid-cols-1 md:grid-cols-8 lg:grid-cols-12 gap-4">
      <!-- Left Column -->
      <div class="col-span-1 md:col-span-8 space-y-4">
        <!-- My Sessions -->
        <section class="liquid-glass rounded-3xl p-4 border border-on-surface/[0.04] dark:border-on-surface/5">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-xl font-bold text-on-surface dark:text-on-surface flex items-center gap-3">
              <span
                class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary"
              >
                <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
                  >event_note</span
                >
              </span>
              My Sessions
            </h3>
            <div class="flex gap-2">
              <button
                class="p-2 bg-on-surface/[0.04] dark:bg-on-surface/5 hover:bg-on-surface/5 dark:hover:bg-on-surface/10 rounded-full border border-on-surface/[0.04] dark:border-on-surface/5 transition-colors"
              >
                <span class="material-symbols-outlined text-sm">chevron_left</span>
              </button>
              <button
                class="p-2 bg-on-surface/[0.04] dark:bg-on-surface/5 hover:bg-on-surface/5 dark:hover:bg-on-surface/10 rounded-full border border-on-surface/[0.04] dark:border-on-surface/5 transition-colors"
              >
                <span class="material-symbols-outlined text-sm">chevron_right</span>
              </button>
            </div>
          </div>

          <!-- Loading -->
          <div v-if="scheduleStore.isLoading" class="space-y-4">
            <div v-for="i in 3" :key="i" class="h-24 rounded-3xl bg-on-surface/[0.04] dark:bg-on-surface/5 animate-pulse" />
          </div>

          <!-- Empty -->
          <div
            v-else-if="mySessions.length === 0"
            class="py-12 flex flex-col items-center text-center"
          >
            <span
              class="material-symbols-outlined text-5xl text-on-surface-variant/50 dark:text-on-surface-variant/40 mb-3"
              style="font-variation-settings: 'FILL' 1"
              >music_off</span
            >
            <p class="font-semibold text-on-surface-variant dark:text-on-surface-variant">No sessions yet</p>
            <p class="text-sm text-on-surface-variant dark:text-on-surface-variant mt-1">
              Request a session with your teacher to get started!
            </p>
            <button
              class="mt-4 px-5 py-2.5 bg-primary text-on-primary rounded-2xl font-bold text-sm transition-all hover:scale-[1.02] active:scale-95"
              @click="openRequestModal"
            >
              Request a Session
            </button>
          </div>

          <!-- Session list -->
          <div v-else class="space-y-4">
            <div
              v-for="session in mySessions"
              :key="session.id"
              class="bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.04] dark:border-on-surface/5 p-5 rounded-3xl flex items-center gap-6 hover:bg-on-surface/5 dark:hover:bg-on-surface/10 hover:translate-x-1 transition-all cursor-pointer group"
              @click="selectSession(session.id)"
            >
              <!-- Date badge -->
              <div
                class="flex flex-col items-center justify-center w-16 h-16 rounded-3xl shadow-lg shrink-0"
                :class="
                  session.status === 'completed'
                    ? 'bg-surface-container-high text-on-surface-variant'
                    : session.status === 'pending_teacher'
                      ? 'bg-amber-500/10 border border-amber-500/20 text-amber-400'
                      : session.status === 'pending_student'
                        ? 'bg-primary/20 border border-primary/40 text-primary'
                      : session.status === 'pending_admin'
                        ? 'bg-blue-500/20 border border-blue-500/40 text-blue-400'
                        : session.status === 'rejected'
                          ? 'bg-red-900 text-red-300'
                          : 'bg-primary text-on-surface'
                "
              >
                <span class="text-[10px] uppercase font-black">{{
                  formatMonth(session.startTime)
                }}</span>
                <span class="text-2xl font-black">{{ formatDay(session.startTime) }}</span>
              </div>

              <!-- Info -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1 flex-wrap">
                  <span
                    class="px-2 py-0.5 text-[10px] font-bold rounded-full uppercase border"
                    :class="
                      session.status === 'pending_teacher'
                        ? 'bg-amber-500/20 border-amber-500/30 text-amber-400'
                        : session.status === 'pending_admin'
                          ? 'bg-blue-500/20 border-blue-500/30 text-blue-400'
                          : session.status === 'rejected'
                            ? 'bg-red-500/20 border-red-500/30 text-red-400'
                            : session.status === 'completed'
                              ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400'
                              : 'bg-primary/20 border-primary/30 text-primary'
                    "
                  >
                    {{
                      session.status === 'pending_teacher'
                        ? 'Awaiting Teacher'
                        : session.status === 'pending_student'
                          ? 'Countered by Teacher'
                        : session.status === 'pending_admin'
                          ? 'Awaiting Admin'
                          : session.status === 'rejected'
                            ? 'Declined'
                            : session.status === 'completed'
                              ? 'Completed'
                              : 'Confirmed'
                    }}
                  </span>
                  <span class="text-on-surface-variant dark:text-on-surface-variant text-xs">{{ formatTime(session.startTime) }}</span>
                </div>
                <h4 class="font-bold text-lg text-on-surface dark:text-on-surface">Session #{{ session.id }}</h4>
                <p class="text-on-surface-variant dark:text-on-surface-variant text-sm">Teacher #{{ session.teacherId }}</p>
                <p v-if="session.notes" class="text-on-surface-variant dark:text-on-surface-variant text-xs mt-0.5 italic">
                  {{ session.notes }}
                </p>
              </div>

              <!-- Right actions -->
              <div class="flex items-center gap-3 shrink-0">
                <span
                  v-if="session.homeworkAssigned && !session.homeworkCompleted"
                  class="text-xs px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-400 font-semibold"
                  >HW Pending</span
                >
                <span
                  v-else-if="session.homeworkCompleted"
                  class="text-xs px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold"
                  >HW Done ✓</span
                >
                <span
                  class="material-symbols-outlined text-on-surface-variant dark:text-on-surface-variant group-hover:text-primary transition-colors"
                  >arrow_forward</span
                >
              </div>
            </div>
          </div>
        </section>

        <!-- Session Proofs & Homework -->
        <section class="liquid-glass rounded-3xl p-4 border border-on-surface/[0.04] dark:border-on-surface/5">
          <h3 class="text-xl font-bold text-on-surface dark:text-on-surface flex items-center gap-3 mb-8">
            <span
              class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary"
            >
              <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
                >cloud_upload</span
              >
            </span>
            Session Proofs &amp; Homework
          </h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <!-- Upload area -->
            <label
              class="relative overflow-hidden border-2 border-dashed border-on-surface/[0.08] dark:border-on-surface/10 bg-on-surface/[0.02] dark:bg-on-surface/[0.02] rounded-3xl p-4 flex flex-col items-center justify-center text-center transition-all cursor-pointer group min-h-[160px]"
              :class="
                proofPreviewUrl
                  ? 'border-primary/50'
                  : 'hover:bg-on-surface/5 dark:hover:bg-on-surface/5 hover:border-primary/50'
              "
            >
              <template v-if="!proofPreviewUrl">
                <div
                  class="w-14 h-14 bg-primary/10 text-primary rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform"
                >
                  <span
                    class="material-symbols-outlined text-3xl"
                    style="font-variation-settings: 'FILL' 1"
                    >add_a_photo</span
                  >
                </div>
                <p class="font-bold text-on-surface dark:text-on-surface">Select Session Photo...</p>
                <p class="text-xs text-on-surface-variant dark:text-on-surface-variant mt-2">Verification for completed credits</p>
              </template>

              <template v-else>
                <img
                  :src="proofPreviewUrl"
                  alt="Proof preview"
                  class="absolute inset-0 w-full h-full object-cover opacity-60 mix-blend-screen"
                />
                <div
                  class="relative z-10 w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-500 flex items-center justify-center mb-3"
                >
                  <span
                    class="material-symbols-outlined absolute"
                    style="font-variation-settings: 'FILL' 1"
                    >check_circle</span
                  >
                </div>
                <p
                  class="relative z-10 font-black text-on-surface dark:text-on-surface text-sm bg-on-surface/40 px-3 py-1 rounded-full"
                >
                  Image Selected
                </p>
              </template>

              <input
                type="file"
                accept="image/*"
                class="hidden"
                aria-label="Upload session photo proof"
                @change="handleGenericProofSelection"
              />
            </label>
            <div v-if="proofPreviewUrl" class="col-span-1 sm:col-span-2 flex justify-end -mt-2">
              <button
                class="px-6 py-2.5 bg-primary text-on-primary text-sm font-black rounded-xl shadow-lg hover:scale-105 active:scale-95 transition-all w-full sm:w-auto"
                @click="handleGenericProofUpload"
              >
                Submit Proof
              </button>
            </div>

            <!-- Pending homework -->
            <div
              v-if="pendingHomework"
              class="bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.04] dark:border-on-surface/5 p-6 rounded-3xl flex items-center gap-4 hover:bg-on-surface/5 dark:hover:bg-on-surface/10 transition-all"
            >
              <div
                class="w-12 h-12 bg-surface-container-high text-on-surface-variant dark:text-on-surface-variant rounded-2xl flex items-center justify-center shrink-0"
              >
                <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
                  >description</span
                >
              </div>
              <div>
                <p class="font-bold text-sm text-on-surface dark:text-on-surface">{{ pendingHomework.homeworkAssigned }}</p>
                <p class="text-xs text-on-surface-variant dark:text-on-surface-variant mt-0.5">Due for next session</p>
                <button
                  class="mt-2 text-primary font-bold text-xs flex items-center gap-1 hover:brightness-125 transition-all focus:outline-none"
                  @click="markHomeworkDone(pendingHomework.id)"
                >
                  Submit Work
                  <span class="material-symbols-outlined text-xs">north_east</span>
                </button>
              </div>
            </div>
            <div
              v-else
              class="bg-on-surface/[0.04] dark:bg-on-surface/5 border border-dashed border-on-surface/[0.08] dark:border-on-surface/10 rounded-3xl p-6 flex items-center justify-center"
            >
              <p class="text-sm text-on-surface-variant dark:text-on-surface-variant">No homework pending ✓</p>
            </div>
          </div>
        </section>
      </div>

      <!-- Right Column -->
      <div class="col-span-1 md:col-span-4 space-y-4">
        <!-- Enrollment Status -->
        <section
          class="liquid-glass rounded-3xl p-4 border border-on-surface/[0.04] dark:border-on-surface/5 relative overflow-hidden group"
        >
          <div class="relative z-10">
            <h3 class="text-xl font-bold text-on-surface dark:text-on-surface mb-8">Enrollment Status</h3>
            <div class="flex items-center justify-center mb-10 relative">
              <svg
                class="w-48 h-48 -rotate-90 drop-shadow-[0_0_15px_rgba(249,115,22,0.3)]"
                viewBox="0 0 192 192"
                aria-hidden="true"
              >
                <circle
                  cx="96"
                  cy="96"
                  r="84"
                  fill="none"
                  stroke="currentColor"
                  class="text-on-surface/[0.06] dark:text-on-surface/5"
                  stroke-width="10"
                />
                <circle
                  cx="96"
                  cy="96"
                  r="84"
                  fill="none"
                  stroke="var(--primary)"
                  stroke-width="10"
                  stroke-linecap="round"
                  :stroke-dasharray="`${(sessionProgress * 527.8) / 100} 527.8`"
                  style="transition: stroke-dasharray 0.8s ease"
                />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-4xl font-black text-on-surface dark:text-on-surface">
                  {{ mySessions.filter((s: any) => s.status === 'completed').length }} /
                  {{ authStore.currentUser?.sessionsLeft ?? 0 }}
                </span>
                <span class="text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest mt-1"
                  >Sessions Used</span
                >
              </div>
            </div>
            <div class="space-y-4 mb-8">
              <div
                class="flex justify-between items-center p-3 rounded-2xl bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.04] dark:border-on-surface/5"
              >
                <span class="text-xs text-on-surface-variant dark:text-on-surface-variant">Package</span>
                <span class="text-xs font-bold text-on-surface dark:text-on-surface">Term B - Intensive</span>
              </div>
              <div
                class="flex justify-between items-center p-3 rounded-2xl bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.04] dark:border-on-surface/5"
              >
                <span class="text-xs text-on-surface-variant dark:text-on-surface-variant">Valid Until</span>
                <span class="text-xs font-bold text-on-surface dark:text-on-surface">Dec 15, 2026</span>
              </div>
            </div>
            <button
              class="w-full py-3 bg-on-surface/[0.06] dark:bg-on-surface/10 hover:bg-on-surface/8 dark:hover:bg-on-surface/20 text-on-surface dark:text-on-surface font-bold rounded-3xl border border-on-surface/[0.08] dark:border-on-surface/10 transition-all active:scale-95"
              @click="router.push('/student/payments')"
            >
              Manage Subscription
            </button>
          </div>
          <div
            class="absolute -right-20 -bottom-20 w-48 h-48 bg-primary/10 rounded-full blur-[80px] group-hover:bg-primary/20 transition-all "
          ></div>
        </section>

        <!-- Notice Board -->
        <section class="liquid-glass rounded-3xl p-4 border border-on-surface/[0.04] dark:border-on-surface/5">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-xl font-bold text-on-surface dark:text-on-surface flex items-center gap-3">
              <span
                class="material-symbols-outlined text-primary"
                style="font-variation-settings: 'FILL' 1"
                >campaign</span
              >
              Notice Board
            </h3>
            <button
              class="text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface transition-colors"
              aria-label="More options"
            >
              <span class="material-symbols-outlined">more_horiz</span>
            </button>
          </div>
          <div class="space-y-4">
            <div
              class="bg-primary-container text-on-primary-container rounded-3xl p-6 relative overflow-hidden group/promo cursor-pointer"
            >
              <div class="relative z-10">
                <span
                  class="inline-block px-2 py-1 bg-on-surface/20 rounded-lg text-[9px] font-black uppercase tracking-widest mb-3"
                  >Limited Offer</span
                >
                <h4 class="font-bold text-lg leading-tight mb-2">Summer Masterclass Series</h4>
                <p class="text-xs text-on-surface/80 mb-4 font-medium">
                  Get 20% off if you book before Friday evening.
                </p>
                <button
                  class="bg-surface-container-lowest text-primary px-4 py-2 rounded-2xl text-[10px] font-black uppercase tracking-wider hover:scale-105 active:scale-95 transition-all"
                >
                  Learn More
                </button>
              </div>
              <span
                class="material-symbols-outlined absolute -right-6 -bottom-6 text-8xl opacity-10 group-hover/promo:scale-110 transition-transform "
                style="font-variation-settings: 'FILL' 1"
                >music_note</span
              >
            </div>
            <div class="bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.04] dark:border-on-surface/5 p-4 rounded-3xl flex items-start gap-4">
              <div
                class="w-10 h-10 bg-surface-container-highest rounded-2xl flex items-center justify-center shrink-0"
              >
                <span
                  class="material-symbols-outlined text-primary text-xl"
                  style="font-variation-settings: 'FILL' 1"
                  >lightbulb</span
                >
              </div>
              <div>
                <p class="text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest mb-1">
                  Academy Tip
                </p>
                <p class="text-sm font-medium text-on-surface dark:text-on-surface leading-snug">
                  Don't forget to book Studio A for next week's exam recording session.
                </p>
              </div>
            </div>
          </div>
        </section>

        <!-- Stats -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="liquid-glass rounded-3xl p-6 text-center border border-on-surface/[0.04] dark:border-on-surface/5">
            <p class="text-3xl font-black text-primary">{{ mySessions.length * 60 }}</p>
            <p class="text-[9px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest mt-1">
              Practice Hours
            </p>
          </div>
          <div class="liquid-glass rounded-3xl p-6 text-center border border-on-surface/[0.04] dark:border-on-surface/5">
            <p class="text-3xl font-black text-on-surface dark:text-on-surface">A+</p>
            <p class="text-[9px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest mt-1">
              Avg Grade
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Session Detail Modal -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition opacity-200 ease-out "
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition opacity-200 ease-in "
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="selectedSession"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="session-modal-title"
        @click.self="closeSessionModal"
      >
        <div class="absolute inset-0 bg-on-surface/30 dark:bg-on-surface/70" @click="closeSessionModal" />
        <div
          class="relative w-full max-w-md bg-surface-container-high dark:bg-surface-container-high border border-outline-variant dark:border-outline-variant rounded-2xl p-6 shadow-2xl flex flex-col gap-6"
        >
          <!-- Header -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div
                class="flex flex-col items-center justify-center w-14 h-14 rounded-2xl shadow-lg shrink-0"
                :class="
                  selectedSession.status === 'completed'
                    ? 'bg-surface-container-high text-on-surface-variant'
                    : selectedSession.status === 'pending_teacher'
                      ? 'bg-amber-500/20 border border-amber-500/40 text-amber-400'
                      : selectedSession.status === 'pending_admin'
                        ? 'bg-blue-500/20 border border-blue-500/40 text-blue-400'
                        : selectedSession.status === 'rejected'
                          ? 'bg-red-900 text-red-300'
                          : 'bg-primary text-on-surface'
                "
              >
                <span class="text-[9px] uppercase font-black">{{
                  formatMonth(selectedSession.startTime)
                }}</span>
                <span class="text-xl font-black">{{ formatDay(selectedSession.startTime) }}</span>
              </div>
              <div>
                <h3 id="session-modal-title" class="text-xl font-black text-on-surface dark:text-on-surface">
                  Session #{{ selectedSession.id }}
                </h3>
                <span
                  class="px-2 py-0.5 text-[10px] font-bold rounded-full uppercase border inline-block mt-1"
                  :class="
                    selectedSession.status === 'pending_teacher'
                      ? 'bg-amber-500/20 border-amber-500/30 text-amber-400'
                      : selectedSession.status === 'pending_admin'
                        ? 'bg-blue-500/20 border-blue-500/30 text-blue-400'
                        : selectedSession.status === 'rejected'
                          ? 'bg-red-500/20 border-red-500/30 text-red-400'
                          : selectedSession.status === 'completed'
                            ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400'
                            : 'bg-primary/20 border-primary/30 text-primary'
                  "
                >
                  {{
                    selectedSession.status === 'pending_teacher'
                      ? 'Awaiting Teacher'
                      : selectedSession.status === 'pending_admin'
                        ? 'Awaiting Admin'
                        : selectedSession.status === 'rejected'
                          ? 'Declined'
                          : selectedSession.status === 'completed'
                            ? 'Completed'
                            : 'Confirmed'
                  }}
                </span>
              </div>
            </div>
            <button
              class="text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-500 rounded-lg p-1 self-start"
              aria-label="Close modal"
              @click="closeSessionModal"
            >
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <!-- Info rows -->
          <div class="space-y-4">
            <div class="flex justify-between items-center py-2 border-b border-on-surface/[0.04] dark:border-on-surface/5">
              <span class="text-xs text-on-surface-variant dark:text-on-surface-variant">Teacher</span>
              <span class="text-sm font-bold text-on-surface dark:text-on-surface"
                >Teacher #{{ selectedSession.teacherId }}</span
              >
            </div>
            <div class="flex justify-between items-center py-2 border-b border-on-surface/[0.04] dark:border-on-surface/5">
              <span class="text-xs text-on-surface-variant dark:text-on-surface-variant">Time</span>
              <span class="text-sm font-bold text-on-surface dark:text-on-surface">{{
                formatTime(selectedSession.startTime)
              }}</span>
            </div>
            <div class="flex justify-between items-center py-2 border-b border-on-surface/[0.04] dark:border-on-surface/5">
              <span class="text-xs text-on-surface-variant dark:text-on-surface-variant">Homework</span>
              <span
                class="text-sm font-bold"
                :class="
                  selectedSession.homeworkCompleted
                    ? 'text-emerald-400'
                    : selectedSession.homeworkAssigned
                      ? 'text-amber-400'
                      : 'text-on-surface-variant'
                "
              >
                {{
                  selectedSession.homeworkCompleted
                    ? 'Completed ✓'
                    : selectedSession.homeworkAssigned
                      ? 'Pending'
                      : 'None'
                }}
              </span>
            </div>
            <div v-if="selectedSession.notes" class="py-2">
              <span class="text-xs text-on-surface-variant dark:text-on-surface-variant block mb-1">Notes</span>
              <p class="text-sm text-on-surface-variant italic">{{ selectedSession.notes }}</p>
            </div>
          </div>

          <!-- Proof Section -->
          <div
            v-if="['scheduled', 'overdue', 'completed', 'pending_verification', 'overdue_rejected'].includes(selectedSession.status)"
            class="bg-on-surface/[0.04] dark:bg-on-surface/5 rounded-xl p-4 border border-on-surface/[0.04] dark:border-on-surface/5"
          >
            <h4 class="text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest mb-3">
              Session Proofs
            </h4>

            <div v-if="selectedSession.status === 'overdue_rejected'" class="mb-4 bg-red-500/10 border border-red-500/20 rounded-xl p-3">
              <p class="text-[10px] font-black uppercase text-red-500 tracking-wider mb-1">Proof Rejected</p>
              <p class="text-xs text-red-400 font-bold mb-1">{{ selectedSession.rejectionReason }}</p>
              <p class="text-xs text-on-surface-variant">Please upload a valid proof and provide justification below.</p>
            </div>

            <div class="space-y-3 mb-4">
              <div class="flex items-center justify-between">
                <span class="text-sm text-on-surface-variant">Your Proof</span>
                <span class="text-sm font-bold" :class="selectedSession.proofs?.some(p => p.uploaderRole === 'student') ? 'text-emerald-500' : 'text-amber-500'">
                  {{ selectedSession.proofs?.some(p => p.uploaderRole === 'student') ? 'Uploaded ✓' : 'Pending' }}
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm text-on-surface-variant">Teacher's Proof</span>
                <span class="text-sm font-bold" :class="selectedSession.proofs?.some(p => p.uploaderRole === 'teacher') ? 'text-emerald-500' : 'text-amber-500'">
                  {{ selectedSession.proofs?.some(p => p.uploaderRole === 'teacher') ? 'Uploaded ✓' : 'Pending' }}
                </span>
              </div>
            </div>

            <div v-if="selectedSession.proofs?.some(p => p.uploaderRole === 'student')" class="flex flex-col gap-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div class="w-12 h-12 rounded-lg overflow-hidden bg-surface-container-high border border-outline-variant dark:border-outline-variant shrink-0">
                    <img :src="selectedSession.proofs?.find(p => p.uploaderRole === 'student')?.imageUrl" class="w-full h-full object-cover" />
                  </div>
                  <div>
                    <p class="text-sm font-bold text-on-surface dark:text-on-surface">Your Proof</p>
                    <p class="text-xs text-emerald-400">Recorded ✓</p>
                  </div>
                </div>
                <button
                  class="px-4 py-2 bg-on-surface/[0.06] dark:bg-on-surface/10 hover:bg-on-surface/8 dark:hover:bg-on-surface/20 text-on-surface dark:text-on-surface text-xs font-bold rounded-lg transition-all border border-on-surface/[0.08] dark:border-on-surface/10"
                  @click="showProofViewer = true; proofPreviewUrl = selectedSession.proofs?.find(p => p.uploaderRole === 'student')?.imageUrl || null"
                >
                  View
                </button>
              </div>

              <div v-if="['overdue', 'overdue_rejected'].includes(selectedSession.status)" class="mt-2 pt-3 border-t border-outline/[0.04] dark:border-on-surface/5 space-y-3">
                <label class="block text-xs text-on-surface-variant mb-1 font-bold">Add a note for the Admin (Optional)</label>
                <textarea v-model="approvalJustification" rows="2" class="w-full bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.08] dark:border-on-surface/10 rounded-xl px-3 py-2 text-xs text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none placeholder:text-on-surface-variant/50" placeholder="E.g. Class was conducted successfully..."></textarea>
                <button class="w-full py-2.5 bg-primary hover:scale-[1.02] active:scale-95 text-on-primary font-bold rounded-xl transition-all text-sm shadow-md" @click="submitApprovalRequest(selectedSession.id)">
                  Submit Request for Approval
                </button>
              </div>
            </div>

            <div v-else-if="selectedSession.status === 'pending_verification'" class="mt-4 bg-emerald-500/10 border border-emerald-500/20 p-3 rounded-xl text-center">
              <p class="text-xs font-bold text-emerald-500">Approval Request Pending</p>
              <p class="text-[10px] text-emerald-400 mt-1">An admin or teacher is reviewing your proof.</p>
            </div>

            <div v-else-if="selectedSession.status === 'pending_student'" class="space-y-4">
              <div class="bg-primary/10 p-4 rounded-2xl border border-primary/20">
                <p class="text-sm font-bold text-primary mb-2">Teacher proposed a new time</p>
                <div v-if="!isCountering" class="flex gap-3">
                  <button
                    class="flex-1 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-1.5"
                    @click="approveCounter"
                  >
                    <span class="material-symbols-outlined text-sm">check_circle</span>
                    Approve Time
                  </button>
                  <button
                    class="flex-1 py-2 bg-primary/20 hover:bg-primary/30 border border-primary/30 text-primary text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-1.5"
                    @click="startCountering(selectedSession)"
                  >
                    <span class="material-symbols-outlined text-sm">edit_calendar</span>
                    Suggest Other
                  </button>
                </div>
                <div v-else class="space-y-3 mt-2   ">
                  <input
                    v-model="counterForm.startTime"
                    type="datetime-local"
                    class="w-full bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.08] dark:border-on-surface/10 rounded-xl px-3 py-2 text-xs text-on-surface dark:text-on-surface [color-scheme:dark]"
                  />
                  <input
                    v-model="counterForm.endTime"
                    type="datetime-local"
                    class="w-full bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.08] dark:border-on-surface/10 rounded-xl px-3 py-2 text-xs text-on-surface dark:text-on-surface [color-scheme:dark]"
                  />
                  <div class="flex gap-2">
                    <button
                      class="flex-1 py-2 bg-primary text-on-surface text-xs font-bold rounded-xl"
                      @click="submitStudentCounter"
                    >
                      Send Proposal
                    </button>
                    <button
                      class="px-4 py-2 bg-on-surface/5 dark:bg-on-surface/5 text-xs font-bold rounded-xl"
                      @click="stopCountering"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="stagedProofUrl" class="flex flex-col gap-3">
              <div class="flex items-center gap-3">
                <div
                  class="w-12 h-12 rounded-lg overflow-hidden bg-surface-container-high border border-outline-variant dark:border-outline-variant shrink-0"
                >
                  <img :src="stagedProofUrl" class="w-full h-full object-cover" />
                </div>
                <div>
                  <p class="text-sm font-bold text-on-surface dark:text-on-surface">Ready to save</p>
                  <label class="text-xs text-primary cursor-pointer hover:underline">
                    Replace
                    <input
                      type="file"
                      accept="image/*"
                      class="hidden"
                      @change="handleStagedProofUpload"
                    />
                  </label>
                </div>
              </div>
              <button
                class="w-full py-2 bg-primary hover:scale-[1.02] text-on-primary text-xs font-black rounded-lg transition-all active:scale-95"
                @click="saveStagedProof"
              >
                Save Proof
              </button>
            </div>

            <div v-else-if="['scheduled', 'overdue', 'overdue_rejected'].includes(selectedSession.status)">
              <label
                class="flex flex-col items-center justify-center p-4 border-2 border-dashed border-on-surface/[0.08] dark:border-on-surface/10 rounded-xl hover:bg-on-surface/5 dark:hover:bg-on-surface/5 hover:border-primary/50 transition-all cursor-pointer group text-center"
              >
                <span
                  class="material-symbols-outlined text-on-surface-variant dark:text-on-surface-variant group-hover:text-primary text-2xl mb-1"
                  >upload</span
                >
                <span
                  class="text-sm font-bold text-on-surface dark:text-on-surface group-hover:text-primary transition-colors"
                  >Select Image</span
                >
                <span class="text-xs text-on-surface-variant dark:text-on-surface-variant mt-1">PNG, JPG, or WEBP</span>
                <input
                  type="file"
                  accept="image/*"
                  class="hidden"
                  @change="handleStagedProofUpload"
                />
              </label>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Proof Viewer Lightbox -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition opacity-200 ease-out "
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition opacity-200 ease-in "
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="showProofViewer && selectedSession?.imageProofUrl"
        class="fixed inset-0 z-[300] flex items-center justify-center bg-on-surface/90 p-4"
        @click.self="showProofViewer = false"
      >
        <button
          class="absolute top-6 right-6 text-on-surface/50 hover:text-on-surface dark:hover:text-on-surface transition-colors bg-on-surface/10 dark:bg-on-surface/50 p-2 rounded-full border border-on-surface/[0.08] dark:border-on-surface/10"
          @click="showProofViewer = false"
        >
          <span class="material-symbols-outlined text-2xl">close</span>
        </button>
        <img
          :src="selectedSession.imageProofUrl"
          class="max-w-full max-h-[85vh] object-contain rounded-2xl shadow-2xl border border-on-surface/[0.08] dark:border-on-surface/10"
        />
      </div>
    </Transition>
  </Teleport>

  <!-- Request Session Modal -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition opacity-200 ease-out "
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition opacity-200 ease-in "
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="showRequestModal"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="request-modal-title"
        @click.self="closeRequestModal"
      >
        <div
          class="absolute inset-0 bg-on-surface/30 dark:bg-on-surface/70"
          @click="closeRequestModal"
        />
        <div
          class="relative w-full max-w-md bg-surface-container-high dark:bg-surface-container-high border border-outline-variant dark:border-outline-variant rounded-2xl p-6 shadow-2xl"
        >
          <div class="flex items-center justify-between mb-6">
            <h3 id="request-modal-title" class="text-xl font-black text-on-surface dark:text-on-surface">
              Request a Session
            </h3>
            <button
              class="text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-500 rounded-lg p-1"
              aria-label="Close modal"
              @click="closeRequestModal"
            >
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <form class="space-y-4" @submit.prevent="submitRequest">
            <div>
              <label
                class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase tracking-wider mb-1.5 block"
                for="req-teacher"
                >Preferred Teacher</label
              >
              <select
                id="req-teacher"
                v-model="requestForm.teacherId"
                required
                class="w-full bg-surface-container-highest border border-on-surface/[0.08] dark:border-on-surface/10 text-on-surface dark:text-on-surface rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option :value="null">Select a teacher...</option>
                <option v-for="t in allTeachers" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </div>
            <div>
              <label
                class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase tracking-wider mb-1.5 block"
                for="req-date"
                >Preferred Date &amp; Time</label
              >
              <input
                id="req-date"
                v-model="requestForm.startTime"
                type="datetime-local"
                required
                class="w-full bg-surface-container-highest border border-on-surface/[0.08] dark:border-on-surface/10 text-on-surface dark:text-on-surface rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
            <div class="flex gap-3 pt-2">
              <button
                type="button"
                class="flex-1 py-3 rounded-xl border border-on-surface/[0.08] dark:border-on-surface/10 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface text-sm font-semibold transition-all"
                @click="closeRequestModal"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="scheduleStore.isLoading"
                class="flex-1 py-3 rounded-xl bg-primary hover:scale-[1.02] text-on-primary text-sm font-black transition-all active:scale-95 disabled:opacity-50"
              >
                {{ scheduleStore.isLoading ? 'Submitting...' : 'Request Session' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

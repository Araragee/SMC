<script setup lang="ts">
import { onMounted, computed, ref, reactive } from 'vue'
import { useScheduleStore } from '../../stores/schedule'
import { useUsersStore } from '../../stores/users'
import { useAuthStore } from '../../stores/auth'
import { useToastStore } from '../../stores/toast'
import { useInteractionsStore } from '../../stores/interactions'
import type { Session } from '../../types'

const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()
const toast = useToastStore()
const interactionsStore = useInteractionsStore()

const showRequestModal = ref(false)
const requestForm = reactive({ teacherId: '', startTime: '' })

const selectedSession = ref<Session | null>(null)
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

const myId = computed(() => authStore.currentUser?.id ?? '')

const mySessions = computed(() =>
  scheduleStore.allSessions.filter((s) => s.studentId === myId.value)
)

const nextSession = computed(
  () =>
    mySessions.value
      .filter((s) => s.status === 'scheduled' && s.startTime)
      .sort((a, b) => new Date(a.startTime!).getTime() - new Date(b.startTime!).getTime())[0] ??
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

const pendingHomework = computed(
  () => mySessions.value.find((s) => s.homeworkAssigned && !s.homeworkCompleted) ?? null
)

const sessionProgress = computed(() => {
  const totalSessions = interactionsStore.enrollments[0]?.sessionsPurchased || 10
  const used = mySessions.value.filter((s) => s.status === 'completed').length
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

async function submitRequest() {
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
    Object.assign(requestForm, { teacherId: '', startTime: '' })
  } catch {
    toast.error('Request failed', 'Please try again or contact your teacher.')
  }
}

async function markHomeworkDone(sessionId: string) {
  await interactionsStore.completeHomework(sessionId)
  toast.success('Homework submitted!', 'Great work — keep it up.')
}

function handleStagedProofUpload(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.[0]) return
  stagedProofFile.value = input.files[0]
  stagedProofUrl.value = window.URL.createObjectURL(stagedProofFile.value)
}

async function saveStagedProof() {
  if (!selectedSession.value || !stagedProofFile.value) return
  await interactionsStore.uploadImageProof(selectedSession.value.id, stagedProofFile.value)
  toast.success('Proof uploaded!', 'Your session proof has been saved.')

  // Update the local state to show "View Proof" instead of the staged file
  stagedProofFile.value = null
  stagedProofUrl.value = null
}

function closeSessionModal() {
  selectedSession.value = null
  stagedProofFile.value = null
  stagedProofUrl.value = null
}

function handleGenericProofSelection(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.[0]) return
  proofPreviewFile.value = input.files[0]
  proofPreviewUrl.value = URL.createObjectURL(proofPreviewFile.value)
}

async function handleGenericProofUpload() {
  const firstScheduled = mySessions.value.find((s) => s.status === 'scheduled')
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
</script>

<template>
  <div class="w-full mx-auto pb-10">
    <!-- Hero Welcome -->
    <div class="flex items-start justify-between gap-4 mb-6">
      <div>
        <h2 class="text-5xl font-black tracking-tighter text-white mb-3">
          Morning, {{ authStore.currentUser?.name?.split(' ')[0] || 'Student' }}.
        </h2>
        <p class="text-zinc-400 font-medium mb-6">
          Your next recital rehearsal is in
          <span class="text-orange-500 font-bold">{{ nextSessionCountdown }}</span
          >.
        </p>
        <div class="flex gap-4">
          <RouterLink
            to="/student/schedule"
            class="px-6 py-3 bg-white/5 hover:bg-white/10 text-white font-bold rounded-3xl border border-white/10 active:scale-95 transition-all flex items-center gap-2"
          >
            <span class="material-symbols-outlined text-lg">calendar_today</span>
            Schedule
          </RouterLink>
          <button
            class="px-6 py-3 bg-gradient-to-br from-orange-500 to-orange-700 text-white font-bold rounded-3xl shadow-lg shadow-orange-900/20 active:scale-95 hover:scale-[1.02] transition-all flex items-center gap-2"
            @click="showRequestModal = true"
          >
            <span class="material-symbols-outlined text-lg">add_circle</span>
            Request Session
          </button>
        </div>
      </div>
    </div>

    <!-- Main Grid -->
    <div class="grid grid-cols-1 md:grid-cols-8 lg:grid-cols-12 gap-4">
      <!-- Left Column -->
      <div class="col-span-1 md:col-span-8 space-y-4">
        <!-- My Sessions -->
        <section class="liquid-glass rounded-3xl p-4 border border-white/5">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-xl font-bold text-white flex items-center gap-3">
              <span
                class="w-10 h-10 rounded-xl bg-orange-500/10 flex items-center justify-center text-orange-500"
              >
                <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
                  >event_note</span
                >
              </span>
              My Sessions
            </h3>
            <div class="flex gap-2">
              <button
                class="p-2 bg-white/5 hover:bg-white/10 rounded-full border border-white/5 transition-colors"
              >
                <span class="material-symbols-outlined text-sm">chevron_left</span>
              </button>
              <button
                class="p-2 bg-white/5 hover:bg-white/10 rounded-full border border-white/5 transition-colors"
              >
                <span class="material-symbols-outlined text-sm">chevron_right</span>
              </button>
            </div>
          </div>

          <!-- Loading -->
          <div v-if="scheduleStore.isLoading" class="space-y-4">
            <div v-for="i in 3" :key="i" class="h-24 rounded-3xl bg-white/5 animate-pulse" />
          </div>

          <!-- Empty -->
          <div
            v-else-if="mySessions.length === 0"
            class="py-12 flex flex-col items-center text-center"
          >
            <span
              class="material-symbols-outlined text-5xl text-zinc-700 mb-3"
              style="font-variation-settings: 'FILL' 1"
              >music_off</span
            >
            <p class="font-semibold text-zinc-400">No sessions yet</p>
            <p class="text-sm text-zinc-600 mt-1">
              Request a session with your teacher to get started!
            </p>
            <button
              class="mt-4 px-5 py-2.5 bg-gradient-to-br from-orange-500 to-orange-700 text-white rounded-2xl font-bold text-sm transition-all hover:scale-[1.02] active:scale-95"
              @click="showRequestModal = true"
            >
              Request a Session
            </button>
          </div>

          <!-- Session list -->
          <div v-else class="space-y-4">
            <div
              v-for="session in mySessions"
              :key="session.id"
              class="bg-white/5 border border-white/5 p-5 rounded-3xl flex items-center gap-6 hover:bg-white/10 hover:translate-x-1 transition-all cursor-pointer group"
              @click="selectedSession = session"
            >
              <!-- Date badge -->
              <div
                class="flex flex-col items-center justify-center w-16 h-16 rounded-3xl shadow-lg shrink-0"
                :class="
                  session.status === 'completed'
                    ? 'bg-zinc-800 text-zinc-400'
                    : session.status === 'pending_teacher'
                      ? 'bg-amber-500/20 border border-amber-500/40 text-amber-400'
                      : session.status === 'pending_admin'
                        ? 'bg-blue-500/20 border border-blue-500/40 text-blue-400'
                        : session.status === 'rejected'
                          ? 'bg-red-900 text-red-300'
                          : 'bg-orange-500 text-white shadow-orange-900/30'
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
                              : 'bg-orange-500/20 border-orange-500/30 text-orange-400'
                    "
                  >
                    {{
                      session.status === 'pending_teacher'
                        ? 'Awaiting Teacher'
                        : session.status === 'pending_admin'
                          ? 'Awaiting Admin'
                          : session.status === 'rejected'
                            ? 'Declined'
                            : session.status === 'completed'
                              ? 'Completed'
                              : 'Confirmed'
                    }}
                  </span>
                  <span class="text-zinc-500 text-xs">{{ formatTime(session.startTime) }}</span>
                </div>
                <h4 class="font-bold text-lg text-white">Session #{{ session.id }}</h4>
                <p class="text-zinc-500 text-sm">Teacher #{{ session.teacherId }}</p>
                <p v-if="session.notes" class="text-zinc-600 text-xs mt-0.5 italic">
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
                  class="material-symbols-outlined text-zinc-600 group-hover:text-orange-500 transition-colors"
                  >arrow_forward</span
                >
              </div>
            </div>
          </div>
        </section>

        <!-- Session Proofs & Homework -->
        <section class="liquid-glass rounded-3xl p-4 border border-white/5">
          <h3 class="text-xl font-bold text-white flex items-center gap-3 mb-8">
            <span
              class="w-10 h-10 rounded-xl bg-orange-500/10 flex items-center justify-center text-orange-500"
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
              class="relative overflow-hidden border-2 border-dashed border-white/10 bg-white/[0.02] rounded-3xl p-4 flex flex-col items-center justify-center text-center transition-all cursor-pointer group min-h-[160px]"
              :class="
                proofPreviewUrl
                  ? 'border-orange-500/50'
                  : 'hover:bg-white/5 hover:border-orange-500/50'
              "
            >
              <template v-if="!proofPreviewUrl">
                <div
                  class="w-14 h-14 bg-orange-500/10 text-orange-500 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform"
                >
                  <span
                    class="material-symbols-outlined text-3xl"
                    style="font-variation-settings: 'FILL' 1"
                    >add_a_photo</span
                  >
                </div>
                <p class="font-bold text-white">Select Session Photo...</p>
                <p class="text-xs text-zinc-500 mt-2">Verification for completed credits</p>
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
                  class="relative z-10 font-black text-white text-sm bg-black/40 px-3 py-1 rounded-full backdrop-blur-md"
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
                @click="handleGenericProofUpload"
                class="px-6 py-2.5 bg-gradient-to-br from-orange-500 to-orange-700 text-white text-sm font-black rounded-xl shadow-lg hover:scale-105 active:scale-95 transition-all w-full sm:w-auto"
              >
                Submit Proof
              </button>
            </div>

            <!-- Pending homework -->
            <div
              v-if="pendingHomework"
              class="bg-white/5 border border-white/5 p-6 rounded-3xl flex items-center gap-4 hover:bg-white/10 transition-all"
            >
              <div
                class="w-12 h-12 bg-zinc-800 text-zinc-400 rounded-2xl flex items-center justify-center shrink-0"
              >
                <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1"
                  >description</span
                >
              </div>
              <div>
                <p class="font-bold text-sm text-white">{{ pendingHomework.homeworkAssigned }}</p>
                <p class="text-xs text-zinc-500 mt-0.5">Due for next session</p>
                <button
                  class="mt-2 text-orange-500 font-bold text-xs flex items-center gap-1 hover:brightness-125 transition-all focus:outline-none"
                  @click="markHomeworkDone(pendingHomework.id)"
                >
                  Submit Work
                  <span class="material-symbols-outlined text-xs">north_east</span>
                </button>
              </div>
            </div>
            <div
              v-else
              class="bg-white/5 border border-dashed border-white/10 rounded-3xl p-6 flex items-center justify-center"
            >
              <p class="text-sm text-zinc-600">No homework pending ✓</p>
            </div>
          </div>
        </section>
      </div>

      <!-- Right Column -->
      <div class="col-span-1 md:col-span-4 space-y-4">
        <!-- Enrollment Status -->
        <section
          class="liquid-glass rounded-3xl p-4 border border-white/5 relative overflow-hidden group"
        >
          <div class="relative z-10">
            <h3 class="text-xl font-bold text-white mb-8">Enrollment Status</h3>
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
                  stroke="rgba(255,255,255,0.05)"
                  stroke-width="10"
                />
                <circle
                  cx="96"
                  cy="96"
                  r="84"
                  fill="none"
                  stroke="#f97316"
                  stroke-width="10"
                  stroke-linecap="round"
                  :stroke-dasharray="`${(sessionProgress * 527.8) / 100} 527.8`"
                  style="transition: stroke-dasharray 0.8s ease"
                />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-4xl font-black text-white">
                  {{ mySessions.filter((s) => s.status === 'completed').length }} /
                  {{ authStore.currentUser?.sessionsLeft || 10 }}
                </span>
                <span class="text-[10px] font-black text-zinc-500 uppercase tracking-widest mt-1"
                  >Sessions Used</span
                >
              </div>
            </div>
            <div class="space-y-4 mb-8">
              <div
                class="flex justify-between items-center p-3 rounded-2xl bg-white/5 border border-white/5"
              >
                <span class="text-xs text-zinc-400">Package</span>
                <span class="text-xs font-bold text-white">Term B - Intensive</span>
              </div>
              <div
                class="flex justify-between items-center p-3 rounded-2xl bg-white/5 border border-white/5"
              >
                <span class="text-xs text-zinc-400">Valid Until</span>
                <span class="text-xs font-bold text-white">Dec 15, 2026</span>
              </div>
            </div>
            <button
              class="w-full py-3 bg-white/10 hover:bg-white/20 text-white font-bold rounded-3xl border border-white/10 transition-all active:scale-95"
            >
              Manage Subscription
            </button>
          </div>
          <div
            class="absolute -right-20 -bottom-20 w-48 h-48 bg-orange-500/10 rounded-full blur-[80px] group-hover:bg-orange-500/20 transition-all duration-700"
          ></div>
        </section>

        <!-- Notice Board -->
        <section class="liquid-glass rounded-3xl p-4 border border-white/5">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-xl font-bold text-white flex items-center gap-3">
              <span
                class="material-symbols-outlined text-orange-500"
                style="font-variation-settings: 'FILL' 1"
                >campaign</span
              >
              Notice Board
            </h3>
            <button
              class="text-zinc-500 hover:text-white transition-colors"
              aria-label="More options"
            >
              <span class="material-symbols-outlined">more_horiz</span>
            </button>
          </div>
          <div class="space-y-4">
            <div
              class="bg-gradient-to-br from-orange-500 to-orange-700 rounded-3xl p-6 text-white relative overflow-hidden group/promo cursor-pointer"
            >
              <div class="relative z-10">
                <span
                  class="inline-block px-2 py-1 bg-white/20 backdrop-blur-lg rounded-lg text-[9px] font-black uppercase tracking-widest mb-3"
                  >Limited Offer</span
                >
                <h4 class="font-bold text-lg leading-tight mb-2">Summer Masterclass Series</h4>
                <p class="text-xs text-white/80 mb-4 font-medium">
                  Get 20% off if you book before Friday evening.
                </p>
                <button
                  class="bg-white text-orange-600 px-4 py-2 rounded-2xl text-[10px] font-black uppercase tracking-wider hover:scale-105 active:scale-95 transition-all"
                >
                  Learn More
                </button>
              </div>
              <span
                class="material-symbols-outlined absolute -right-6 -bottom-6 text-8xl opacity-10 group-hover/promo:scale-110 transition-transform duration-500"
                style="font-variation-settings: 'FILL' 1"
                >music_note</span
              >
            </div>
            <div class="bg-white/5 border border-white/5 p-4 rounded-3xl flex items-start gap-4">
              <div
                class="w-10 h-10 bg-surface-container-highest rounded-2xl flex items-center justify-center shrink-0"
              >
                <span
                  class="material-symbols-outlined text-orange-500 text-xl"
                  style="font-variation-settings: 'FILL' 1"
                  >lightbulb</span
                >
              </div>
              <div>
                <p class="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-1">
                  Academy Tip
                </p>
                <p class="text-sm font-medium text-white/90 leading-snug">
                  Don't forget to book Studio A for next week's exam recording session.
                </p>
              </div>
            </div>
          </div>
        </section>

        <!-- Stats -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="liquid-glass rounded-3xl p-6 text-center border border-white/5">
            <p class="text-3xl font-black text-orange-500">{{ mySessions.length * 60 }}</p>
            <p class="text-[9px] font-black text-zinc-500 uppercase tracking-widest mt-1">
              Practice Hours
            </p>
          </div>
          <div class="liquid-glass rounded-3xl p-6 text-center border border-white/5">
            <p class="text-3xl font-black text-white">A+</p>
            <p class="text-[9px] font-black text-zinc-500 uppercase tracking-widest mt-1">
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
      enter-active-class="transition opacity-200 ease-out duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition opacity-200 ease-in duration-200"
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
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="closeSessionModal" />
        <div
          class="relative w-full max-w-md bg-zinc-900 border border-white/10 rounded-2xl p-6 shadow-2xl flex flex-col gap-6"
        >
          <!-- Header -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div
                class="flex flex-col items-center justify-center w-14 h-14 rounded-2xl shadow-lg shrink-0"
                :class="
                  selectedSession.status === 'completed'
                    ? 'bg-zinc-800 text-zinc-400'
                    : selectedSession.status === 'pending_teacher'
                      ? 'bg-amber-500/20 border border-amber-500/40 text-amber-400'
                      : selectedSession.status === 'pending_admin'
                        ? 'bg-blue-500/20 border border-blue-500/40 text-blue-400'
                        : selectedSession.status === 'rejected'
                          ? 'bg-red-900 text-red-300'
                          : 'bg-orange-500 text-white shadow-orange-900/30'
                "
              >
                <span class="text-[9px] uppercase font-black">{{
                  formatMonth(selectedSession.startTime)
                }}</span>
                <span class="text-xl font-black">{{ formatDay(selectedSession.startTime) }}</span>
              </div>
              <div>
                <h3 id="session-modal-title" class="text-xl font-black text-white">
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
                            : 'bg-orange-500/20 border-orange-500/30 text-orange-400'
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
              class="text-zinc-500 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-500 rounded-lg p-1 self-start"
              aria-label="Close modal"
              @click="closeSessionModal"
            >
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <!-- Info rows -->
          <div class="space-y-4">
            <div class="flex justify-between items-center py-2 border-b border-white/5">
              <span class="text-xs text-zinc-400">Teacher</span>
              <span class="text-sm font-bold text-white"
                >Teacher #{{ selectedSession.teacherId }}</span
              >
            </div>
            <div class="flex justify-between items-center py-2 border-b border-white/5">
              <span class="text-xs text-zinc-400">Time</span>
              <span class="text-sm font-bold text-white">{{
                formatTime(selectedSession.startTime)
              }}</span>
            </div>
            <div class="flex justify-between items-center py-2 border-b border-white/5">
              <span class="text-xs text-zinc-400">Homework</span>
              <span
                class="text-sm font-bold"
                :class="
                  selectedSession.homeworkCompleted
                    ? 'text-emerald-400'
                    : selectedSession.homeworkAssigned
                      ? 'text-amber-400'
                      : 'text-zinc-500'
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
              <span class="text-xs text-zinc-400 block mb-1">Notes</span>
              <p class="text-sm text-zinc-300 italic">{{ selectedSession.notes }}</p>
            </div>
          </div>

          <!-- Proof Section -->
          <div
            v-if="selectedSession.status !== 'cancelled'"
            class="bg-black/40 rounded-xl p-4 border border-white/5"
          >
            <h4 class="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-3">
              Session Proof
            </h4>

            <div v-if="selectedSession.imageProofUrl" class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div
                  class="w-12 h-12 rounded-lg overflow-hidden bg-zinc-800 border border-white/10 shrink-0"
                >
                  <img :src="selectedSession.imageProofUrl" class="w-full h-full object-cover" />
                </div>
                <div>
                  <p class="text-sm font-bold text-white">Proof Uploaded</p>
                  <p class="text-xs text-emerald-400">Verified ✓</p>
                </div>
              </div>
              <button
                class="px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-xs font-bold rounded-lg transition-all border border-white/10"
                @click="showProofViewer = true"
              >
                View Proof
              </button>
            </div>

            <div v-else-if="stagedProofUrl" class="flex flex-col gap-3">
              <div class="flex items-center gap-3">
                <div
                  class="w-12 h-12 rounded-lg overflow-hidden bg-zinc-800 border border-white/10 shrink-0"
                >
                  <img :src="stagedProofUrl" class="w-full h-full object-cover" />
                </div>
                <div>
                  <p class="text-sm font-bold text-white">Ready to save</p>
                  <label class="text-xs text-orange-500 cursor-pointer hover:underline">
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
                class="w-full py-2 bg-gradient-to-br from-orange-500 to-orange-700 hover:scale-[1.02] text-white text-xs font-black rounded-lg transition-all active:scale-95"
                @click="saveStagedProof"
              >
                Save Proof
              </button>
            </div>

            <div v-else>
              <label
                class="flex flex-col items-center justify-center p-4 border-2 border-dashed border-white/10 rounded-xl hover:bg-white/5 hover:border-orange-500/50 transition-all cursor-pointer group text-center"
              >
                <span
                  class="material-symbols-outlined text-zinc-500 group-hover:text-orange-500 text-2xl mb-1"
                  >upload</span
                >
                <span
                  class="text-sm font-bold text-white group-hover:text-orange-400 transition-colors"
                  >Select Image</span
                >
                <span class="text-xs text-zinc-500 mt-1">PNG, JPG, or WEBP</span>
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
      enter-active-class="transition opacity-200 ease-out duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition opacity-200 ease-in duration-300"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="showProofViewer && selectedSession?.imageProofUrl"
        class="fixed inset-0 z-[300] flex items-center justify-center bg-black/90 backdrop-blur-md p-4"
        @click.self="showProofViewer = false"
      >
        <button
          class="absolute top-6 right-6 text-white/50 hover:text-white transition-colors bg-black/50 p-2 rounded-full backdrop-blur-md border border-white/10"
          @click="showProofViewer = false"
        >
          <span class="material-symbols-outlined text-2xl">close</span>
        </button>
        <img
          :src="selectedSession.imageProofUrl"
          class="max-w-full max-h-[85vh] object-contain rounded-2xl shadow-2xl border border-white/10"
        />
      </div>
    </Transition>
  </Teleport>

  <!-- Request Session Modal -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition opacity-200 ease-out duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition opacity-200 ease-in duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="showRequestModal"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="request-modal-title"
        @click.self="showRequestModal = false"
      >
        <div
          class="absolute inset-0 bg-black/70 backdrop-blur-sm"
          @click="showRequestModal = false"
        />
        <div
          class="relative w-full max-w-md bg-zinc-900 border border-white/10 rounded-2xl p-6 shadow-2xl"
        >
          <div class="flex items-center justify-between mb-6">
            <h3 id="request-modal-title" class="text-xl font-black text-white">
              Request a Session
            </h3>
            <button
              class="text-zinc-500 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-500 rounded-lg p-1"
              aria-label="Close modal"
              @click="showRequestModal = false"
            >
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <form class="space-y-4" @submit.prevent="submitRequest">
            <div>
              <label
                class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 block"
                for="req-teacher"
                >Preferred Teacher</label
              >
              <select
                id="req-teacher"
                v-model="requestForm.teacherId"
                required
                class="w-full bg-surface-container-highest border border-white/10 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50"
              >
                <option value="">Select a teacher...</option>
                <option v-for="t in allTeachers" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </div>
            <div>
              <label
                class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 block"
                for="req-date"
                >Preferred Date &amp; Time</label
              >
              <input
                id="req-date"
                v-model="requestForm.startTime"
                type="datetime-local"
                required
                class="w-full bg-surface-container-highest border border-white/10 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50"
              />
            </div>
            <div class="flex gap-3 pt-2">
              <button
                type="button"
                class="flex-1 py-3 rounded-xl border border-white/10 text-zinc-400 hover:text-white text-sm font-semibold transition-all"
                @click="showRequestModal = false"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="scheduleStore.isLoading"
                class="flex-1 py-3 rounded-xl bg-gradient-to-br from-orange-500 to-orange-700 hover:scale-[1.02] text-white text-sm font-black transition-all active:scale-95 disabled:opacity-50"
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

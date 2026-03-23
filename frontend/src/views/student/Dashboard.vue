<template>
  <div class="flex">
    <StudentSidebar />
    <div class="ml-64 w-full min-h-screen p-8 pt-10">

      <!-- Header -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <p class="text-xs font-bold uppercase tracking-[0.2em] text-orange-500 mb-1">Student Portal</p>
          <h2 class="text-4xl font-black text-white tracking-tight">My Schedule</h2>
          <p class="text-zinc-500 mt-1 text-sm">
            Your next recital rehearsal is in
            <span class="text-orange-500 font-bold">{{ nextSessionCountdown }}</span>.
          </p>
        </div>
        <button @click="showRequestModal = true"
          class="flex items-center gap-2 px-5 py-3 bg-orange-600 hover:bg-orange-500 text-white rounded-2xl font-black text-sm transition-all active:scale-95 shadow-lg shadow-orange-900/30 focus:outline-none focus:ring-2 focus:ring-orange-500/50"
          aria-label="Request a new session">
          <span class="material-symbols-outlined text-sm" aria-hidden="true">add</span>
          Request Session
        </button>
      </div>

      <div class="grid grid-cols-3 gap-4">
        <!-- Left: Sessions list -->
        <div class="col-span-2 space-y-4">

          <!-- Upcoming Sessions -->
          <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl overflow-hidden">
            <div class="px-6 py-4 border-b border-zinc-800 flex items-center gap-2">
              <span class="material-symbols-outlined text-orange-400" style="font-variation-settings:'FILL' 1" aria-hidden="true">calendar_month</span>
              <h3 class="font-black text-white">My Sessions</h3>
            </div>

            <!-- Loading -->
            <div v-if="scheduleStore.isLoading" class="p-6 space-y-3">
              <div v-for="i in 3" :key="i" class="h-20 rounded-xl bg-zinc-800 animate-pulse" />
            </div>

            <!-- Empty -->
            <div v-else-if="mySessions.length === 0" class="p-12 flex flex-col items-center text-center">
              <span class="material-symbols-outlined text-5xl text-zinc-700 mb-3" style="font-variation-settings:'FILL' 1" aria-hidden="true">music_off</span>
              <p class="font-semibold text-zinc-400">No sessions yet</p>
              <p class="text-sm text-zinc-600 mt-1">Request a session with your teacher to get started!</p>
              <button @click="showRequestModal = true"
                class="mt-4 px-5 py-2.5 bg-orange-600 hover:bg-orange-500 text-white rounded-xl font-bold text-sm transition-all active:scale-95">
                Request a Session
              </button>
            </div>

            <!-- Session rows -->
            <div v-else class="divide-y divide-zinc-800/50">
              <div v-for="session in mySessions" :key="session.id"
                class="flex items-center gap-4 px-6 py-4 hover:bg-zinc-800/20 transition-colors">
                <!-- Date badge -->
                <div class="w-14 shrink-0 text-center">
                  <div class="w-12 h-12 rounded-xl mx-auto flex flex-col items-center justify-center"
                    :class="session.status === 'completed' ? 'bg-zinc-800' : 'bg-orange-600'">
                    <p class="text-[10px] font-bold uppercase"
                      :class="session.status === 'completed' ? 'text-zinc-500' : 'text-orange-200'">
                      {{ formatMonth(session.startTime) }}
                    </p>
                    <p class="text-lg font-black leading-none"
                      :class="session.status === 'completed' ? 'text-zinc-400' : 'text-white'">
                      {{ formatDay(session.startTime) }}
                    </p>
                  </div>
                </div>

                <!-- Session info -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-0.5">
                    <span class="text-xs px-2 py-0.5 rounded-full font-bold bg-blue-500/20 text-blue-400 uppercase tracking-wider">
                      1-on-1 Session
                    </span>
                    <span class="text-xs text-zinc-500">{{ formatTime(session.startTime) }}</span>
                  </div>
                  <p class="text-sm font-bold text-white">Session #{{ session.id }}</p>
                  <p class="text-xs text-zinc-500 mt-0.5">Teacher #{{ session.teacherId }}</p>
                </div>

                <!-- Right actions -->
                <div class="flex items-center gap-2 shrink-0">
                  <!-- Homework badge -->
                  <span v-if="session.homeworkAssigned && !session.homeworkCompleted"
                    class="text-xs px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-400 font-semibold">
                    HW Pending
                  </span>
                  <span v-else-if="session.homeworkCompleted"
                    class="text-xs px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold">
                    HW Done ✓
                  </span>

                  <!-- Upload proof -->
                  <label v-if="session.status !== 'cancelled'"
                    class="cursor-pointer text-xs px-3 py-1.5 rounded-lg border transition-all focus-within:ring-2 focus-within:ring-orange-500/50"
                    :class="session.imageProofUrl
                      ? 'border-emerald-500/40 text-emerald-400'
                      : 'border-zinc-700 text-zinc-500 hover:border-orange-500/50 hover:text-orange-400'">
                    <span class="material-symbols-outlined text-xs mr-1 align-middle" aria-hidden="true">
                      {{ session.imageProofUrl ? 'check_circle' : 'upload' }}
                    </span>
                    {{ session.imageProofUrl ? 'Proof ✓' : 'Upload Proof' }}
                    <input type="file" accept="image/*" class="hidden"
                      @change="handleProofUpload(session.id, $event)"
                      :aria-label="`Upload session proof for session ${session.id}`" />
                  </label>

                  <!-- Arrow -->
                  <button class="text-zinc-700 hover:text-white transition-colors" aria-label="View session details">
                    <span class="material-symbols-outlined text-lg" aria-hidden="true">chevron_right</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Session Proofs & Homework -->
          <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl overflow-hidden">
            <div class="px-6 py-4 border-b border-zinc-800 flex items-center gap-2">
              <span class="material-symbols-outlined text-orange-400" style="font-variation-settings:'FILL' 1" aria-hidden="true">cloud_upload</span>
              <h3 class="font-black text-white">Session Proofs &amp; Homework</h3>
            </div>
            <div class="p-4 grid grid-cols-2 gap-3">
              <!-- Upload area -->
              <label class="border-2 border-dashed border-zinc-700 rounded-xl p-6 flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-orange-500/50 transition-colors text-center group">
                <span class="material-symbols-outlined text-3xl text-zinc-600 group-hover:text-orange-500 transition-colors" style="font-variation-settings:'FILL' 1" aria-hidden="true">photo_camera_add</span>
                <p class="text-sm font-bold text-zinc-400 group-hover:text-white transition-colors">Upload Session Photo</p>
                <p class="text-xs text-zinc-600">Verification for completed credits</p>
                <input type="file" accept="image/*" class="hidden" @change="handleGenericProofUpload" aria-label="Upload session photo proof" />
              </label>

              <!-- Pending homework -->
              <div v-if="pendingHomework" class="bg-zinc-800/50 border border-zinc-700/50 rounded-xl p-4">
                <div class="flex items-start gap-3">
                  <span class="material-symbols-outlined text-orange-400 mt-0.5" style="font-variation-settings:'FILL' 1" aria-hidden="true">assignment</span>
                  <div>
                    <p class="text-sm font-bold text-white">{{ pendingHomework.homeworkAssigned }}</p>
                    <p class="text-xs text-zinc-500 mt-1">Due for next session</p>
                    <button @click="markHomeworkDone(pendingHomework.id)"
                      class="mt-2 text-xs text-orange-500 hover:text-orange-400 font-bold flex items-center gap-1 transition-colors focus:outline-none focus:underline">
                      Submit Work
                      <span class="material-symbols-outlined text-xs" aria-hidden="true">north_east</span>
                    </button>
                  </div>
                </div>
              </div>

              <div v-else class="bg-zinc-800/30 border border-dashed border-zinc-700/50 rounded-xl p-4 flex items-center justify-center">
                <p class="text-sm text-zinc-600">No homework pending ✓</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Right column: Sessions meter + Notice board -->
        <div class="space-y-4">
          <!-- Sessions used meter -->
          <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-5">
            <p class="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-4">Sessions Used</p>
            <!-- Circular progress -->
            <div class="relative flex items-center justify-center mb-4">
              <svg class="w-32 h-32 -rotate-90" viewBox="0 0 100 100" aria-hidden="true">
                <circle cx="50" cy="50" r="40" fill="none" stroke="#27272a" stroke-width="8" />
                <circle cx="50" cy="50" r="40" fill="none" stroke="#f97316" stroke-width="8"
                  :stroke-dasharray="`${sessionProgress * 251.2 / 100} 251.2`"
                  stroke-linecap="round" style="transition: stroke-dasharray 0.8s ease" />
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <p class="text-2xl font-black text-white">{{ mySessions.filter(s => s.status === 'completed').length }}</p>
                <p class="text-[10px] text-zinc-500 font-semibold">of {{ interactionsStore.enrollments[0]?.sessionsPurchased || 10 }}</p>
              </div>
            </div>
            <div class="text-center">
              <span class="text-xs px-3 py-1 rounded-full bg-orange-500/20 text-orange-400 font-bold">
                Term B - Intensive
              </span>
              <div class="mt-3 flex justify-between text-xs text-zinc-500">
                <span>Valid Until</span>
                <span class="text-zinc-300 font-semibold">Dec 15, 2026</span>
              </div>
            </div>
            <button class="w-full mt-4 py-2.5 rounded-xl border border-zinc-700 text-zinc-400 hover:text-white hover:border-zinc-600 text-xs font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-zinc-500/50">
              Manage Subscription
            </button>
          </div>

          <!-- Stats -->
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-4 text-center">
              <p class="text-3xl font-black text-orange-500">{{ mySessions.length * 60 }}</p>
              <p class="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mt-1">Practice</p>
              <p class="text-[10px] text-zinc-600">Hours</p>
            </div>
            <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-4 text-center">
              <p class="text-3xl font-black text-emerald-400">A+</p>
              <p class="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mt-1">Avg Grade</p>
              <p class="text-[10px] text-zinc-600">This term</p>
            </div>
          </div>

          <!-- Notice Board -->
          <div class="bg-zinc-900/60 border border-zinc-800 rounded-2xl overflow-hidden">
            <div class="px-5 py-4 border-b border-zinc-800 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-orange-400 text-base" style="font-variation-settings:'FILL' 1" aria-hidden="true">campaign</span>
                <h3 class="font-black text-white text-sm">Notice Board</h3>
              </div>
              <button class="text-zinc-600 hover:text-white transition-colors" aria-label="More notice board options">
                <span class="material-symbols-outlined text-base" aria-hidden="true">more_horiz</span>
              </button>
            </div>
            <div class="p-4 space-y-3">
              <div class="bg-orange-600 rounded-xl p-3">
                <span class="text-[10px] px-2 py-0.5 rounded-full bg-white/20 text-white font-bold uppercase tracking-wider">Limited Offer</span>
                <p class="text-sm font-black text-white mt-2">Summer Masterclass Series</p>
                <p class="text-xs text-orange-200/80 mt-1">Get 20% off if you book before Friday evening.</p>
                <button class="mt-2 text-[10px] font-black bg-white text-orange-600 px-3 py-1 rounded-lg hover:bg-orange-50 transition-colors">
                  LEARN MORE
                </button>
              </div>
              <div class="bg-zinc-800/50 rounded-xl p-3">
                <div class="flex items-start gap-2">
                  <span class="material-symbols-outlined text-zinc-500 text-base mt-0.5" style="font-variation-settings:'FILL' 1" aria-hidden="true">tips_and_updates</span>
                  <div>
                    <p class="text-[10px] text-zinc-500 uppercase tracking-wider font-bold">Academy Tip</p>
                    <p class="text-xs text-zinc-300 mt-0.5 leading-relaxed">Don't forget to book Studio A for next week's exam recording session.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Request Session Modal -->
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="showRequestModal"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        role="dialog" aria-modal="true" aria-labelledby="request-modal-title"
        @click.self="showRequestModal = false">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="showRequestModal = false" />
        <div class="relative w-full max-w-md bg-zinc-900 border border-zinc-700 rounded-2xl p-6 shadow-2xl">
          <div class="flex items-center justify-between mb-6">
            <h3 id="request-modal-title" class="text-xl font-black text-white">Request a Session</h3>
            <button @click="showRequestModal = false"
              class="text-zinc-500 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-500 rounded-lg p-1"
              aria-label="Close modal">
              <span class="material-symbols-outlined" aria-hidden="true">close</span>
            </button>
          </div>
          <form @submit.prevent="submitRequest" class="space-y-4">
            <div>
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 block" for="req-teacher">Preferred Teacher</label>
              <select id="req-teacher" v-model="requestForm.teacherId" required
                class="w-full bg-zinc-800 border border-zinc-700 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50">
                <option value="">Select a teacher...</option>
                <option v-for="t in allTeachers" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </div>
            <div>
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1.5 block" for="req-date">Preferred Date &amp; Time</label>
              <input id="req-date" type="datetime-local" v-model="requestForm.startTime" required
                class="w-full bg-zinc-800 border border-zinc-700 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50" />
            </div>
            <div class="flex gap-3 pt-2">
              <button type="button" @click="showRequestModal = false"
                class="flex-1 py-3 rounded-xl border border-zinc-700 text-zinc-400 hover:text-white text-sm font-semibold transition-all focus:outline-none focus:ring-2 focus:ring-zinc-500/50">
                Cancel
              </button>
              <button type="submit" :disabled="scheduleStore.isLoading"
                class="flex-1 py-3 rounded-xl bg-orange-600 hover:bg-orange-500 text-white text-sm font-black transition-all active:scale-95 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-orange-500/50">
                {{ scheduleStore.isLoading ? 'Submitting...' : 'Request Session' }}
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
import StudentSidebar from '../../components/StudentSidebar.vue'
import { useScheduleStore } from '../../stores/schedule'
import { useUsersStore } from '../../stores/users'
import { useAuthStore } from '../../stores/auth'
import { useToastStore } from '../../stores/toast'
import { useInteractionsStore } from '../../stores/interactions'

const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()
const authStore = useAuthStore()
const toast = useToastStore()
const interactionsStore = useInteractionsStore()

const showRequestModal = ref(false)
const requestForm = reactive({ teacherId: '', startTime: '' })

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
  scheduleStore.allSessions.filter(s => s.studentId === myId.value)
)

const nextSession = computed(() =>
  mySessions.value
    .filter(s => s.status === 'scheduled' && s.startTime)
    .sort((a, b) => new Date(a.startTime!).getTime() - new Date(b.startTime!).getTime())[0] ?? null
)

const nextSessionCountdown = computed(() => {
  if (!nextSession.value?.startTime) return 'no upcoming sessions'
  const diff = new Date(nextSession.value.startTime).getTime() - Date.now()
  if (diff <= 0) return 'now'
  const hours = Math.floor(diff / 3600000)
  if (hours < 24) return `${hours} hours`
  return `${Math.floor(hours / 24)} days`
})

const pendingHomework = computed(() =>
  mySessions.value.find(s => s.homeworkAssigned && !s.homeworkCompleted) ?? null
)

const sessionProgress = computed(() => {
  const totalSessions = interactionsStore.enrollments[0]?.sessionsPurchased || 10
  const used = mySessions.value.filter(s => s.status === 'completed').length
  return Math.min((used / totalSessions) * 100, 100)
})

const allTeachers = computed(() => usersStore.getUsersByRole('teacher'))

const formatTime = (dt: string | undefined) => {
  if (!dt) return '—'
  return new Date(dt).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
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
    await scheduleStore.bookSession({
      teacherId: requestForm.teacherId,
      studentId: myId.value,
      startTime: start.toISOString(),
      endTime: end.toISOString(),
    })
    toast.success('Session requested!', 'Your teacher will confirm shortly.')
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

async function handleProofUpload(sessionId: string, event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.[0]) return
  await interactionsStore.uploadImageProof(sessionId, input.files[0])
}

async function handleGenericProofUpload(event: Event) {
  const firstScheduled = mySessions.value.find(s => s.status === 'scheduled')
  if (!firstScheduled) {
    toast.warning('No session to attach to', 'Upload a proof for a specific session below.')
    return
  }
  await handleProofUpload(firstScheduled.id, event)
}
</script>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>

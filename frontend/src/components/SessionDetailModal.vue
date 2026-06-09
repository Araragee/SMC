<script setup lang="ts">
import { NUDGE_COOLDOWN_MS, API_URL } from '@typescript/constants'
import { ref, computed } from 'vue'
import { useToastStore } from '@stores/toast'
import { useScheduleStore } from '@stores/schedule'
import { useDialog } from '@composables/useDialog'
import type { User, Session } from '@types'

const props = defineProps<{
  session: Session | null
  userRole: 'admin' | 'teacher' | 'student'
  currentUserId: number
  users: User[]
}>()

const emit = defineEmits<{
  close: []
  'approve-teacher': [sessionId: number]
  'reject-teacher': [sessionId: number]
  'counter-teacher': [session: Session]
  'approve-student': [sessionId: number]
  'reject-student': [sessionId: number]
  'counter-student': [session: Session]
  'approve-admin': [sessionId: number]
  'reject-admin': [sessionId: number]
  'edit-admin': [session: Session]
  'complete-admin': [sessionId: number]
  'reject-proof-admin': [sessionId: number]
  'cancel-session': [sessionId: number, notes?: string]
  'upload-proof': [sessionId: number, file: File]
}>()

import { watch, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '@stores/auth'

const toast = useToastStore()
const scheduleStore = useScheduleStore()
const authStore = useAuthStore()
const dialog = useDialog()
const fileInput = ref<HTMLInputElement | null>(null)

// Tabs
const activeTab = ref<'overview' | 'history'>('overview')
const historyLogs = ref<any[] | null>(null)
const isLoadingHistory = ref(false)

const authHeaders = () => {
  return authStore.token ? { Authorization: `Bearer ${authStore.token}` } : {}
}

const fetchHistory = async () => {
  if (!props.session?.id) return
  isLoadingHistory.value = true
  try {
    const res = await axios.get(`${API_URL}/activity-log/session/${props.session.id}`, {
      headers: authHeaders()
    })
    historyLogs.value = res.data
  } catch (err: any) {
    console.error('Failed to fetch session history:', err)
  } finally {
    isLoadingHistory.value = false
  }
}

watch(activeTab, (tab) => {
  if (tab === 'history' && !historyLogs.value) {
    fetchHistory()
  }
})

watch(() => props.session?.id, () => {
  activeTab.value = 'overview'
  historyLogs.value = null
})

// Proof Lightbox navigation
const proofUrls = computed(() => {
  if (!props.session?.proofs) return []
  return props.session.proofs.map((p: any) => p.imageUrl?.startsWith('http') ? p.imageUrl : `${API_URL}${p.imageUrl}`)
})

const currentProofIndex = ref<number>(-1)
const showProofViewer = computed({
  get: () => currentProofIndex.value >= 0 ? proofUrls.value[currentProofIndex.value] : null,
  set: (val: string | null) => {
    if (val === null) {
      currentProofIndex.value = -1
    } else {
      currentProofIndex.value = proofUrls.value.indexOf(val)
    }
  }
})

const prevProof = () => {
  if (proofUrls.value.length === 0) return
  currentProofIndex.value = (currentProofIndex.value - 1 + proofUrls.value.length) % proofUrls.value.length
}
const nextProof = () => {
  if (proofUrls.value.length === 0) return
  currentProofIndex.value = (currentProofIndex.value + 1) % proofUrls.value.length
}

const handleKeydown = (e: KeyboardEvent) => {
  if (currentProofIndex.value < 0) return
  if (e.key === 'ArrowLeft') {
    prevProof()
  } else if (e.key === 'ArrowRight') {
    nextProof()
  } else if (e.key === 'Escape') {
    currentProofIndex.value = -1
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

// Copy session link
const copySessionLink = () => {
  if (!props.session) return
  const rolePath = props.userRole === 'admin' ? '/admin/schedule' : props.userRole === 'teacher' ? '/teacher/schedule' : '/student/schedule'
  const link = `${window.location.origin}${rolePath}?session_id=${props.session.id}`
  navigator.clipboard.writeText(link)
  toast.success('Session link copied to clipboard!')
}

// Countdown to Force Complete
const forceCompleteCountdown = ref('')
let countdownInterval: any = null

const updateCountdown = () => {
  if (!props.session) return
  const end = new Date(props.session.endTime).getTime()
  const target = end + (24 * 60 * 60 * 1000)
  const now = new Date().getTime()
  const diff = target - now
  if (diff <= 0) {
    forceCompleteCountdown.value = ''
  } else {
    const hours = Math.floor(diff / (60 * 60 * 1000))
    const minutes = Math.floor((diff % (60 * 60 * 1000)) / (60 * 1000))
    const seconds = Math.floor((diff % (60 * 1000)) / 1000)
    forceCompleteCountdown.value = `${hours}h ${minutes}m ${seconds}s remaining`
  }
}

watch(() => props.session, () => {
  if (countdownInterval) clearInterval(countdownInterval)
  updateCountdown()
  countdownInterval = setInterval(updateCountdown, 1000)
}, { immediate: true })

onUnmounted(() => {
  if (countdownInterval) clearInterval(countdownInterval)
})

const CANCEL_CUTOFF_HOURS = 24
const isWithinCutoff = computed(() => {
  if (!props.session) return false
  const start = new Date(props.session.startTime).getTime()
  const now = new Date().getTime()
  return (start - now) < (CANCEL_CUTOFF_HOURS * 60 * 60 * 1000)
})

const canCancel = computed(() => {
  if (!props.session) return false
  const is_admin = props.userRole === 'admin'
  if (is_admin) return true
  return !isWithinCutoff.value
})

const showCancelButton = computed(() => {
  if (!props.session) return false
  const allowedStatuses = ['scheduled', 'pending_teacher', 'pending_student', 'pending_admin', 'overdue', 'overdue_rejected']
  if (!allowedStatuses.includes(props.session.status)) return false
  const is_admin = props.userRole === 'admin'
  const is_party = props.currentUserId === props.session.teacherId || props.currentUserId === props.session.studentId
  return is_admin || is_party
})

const showUploadProofButton = computed(() => {
  if (!props.session) return false
  const allowedStatuses = ['scheduled', 'overdue', 'overdue_rejected', 'pending_verification']
  if (!allowedStatuses.includes(props.session.status)) return false
  const is_party = props.currentUserId === props.session.teacherId || props.currentUserId === props.session.studentId
  if (!is_party) return false
  const role = props.userRole
  const hasUploaded = props.session.proofs?.some(p => p.uploaderRole === role)
  return !hasUploaded
})

async function clickCancel() {
  if (!props.session) return
  const reason = await dialog.prompt('Enter cancellation reason (optional):', {
    title: 'Cancel Session',
    placeholder: 'Why are you cancelling?'
  })
  if (reason !== null) {
    try {
      await scheduleStore.cancelSession(props.session.id, reason)
      emit('close')
    } catch (err) {
      console.error(err)
    }
  }
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0] && props.session) {
    try {
      await scheduleStore.uploadSessionProof(props.session.id, target.files[0])
      emit('close')
    } catch (err) {
      console.error(err)
    }
  }
}

// ── Nudge cooldown (1 hour per session, persisted in localStorage) ─────────

function getNudgeKey(sessionId: number) {
  return `nudge_last_${sessionId}`
}

function getNudgeCooldownLeft(sessionId: number): number {
  const last = localStorage.getItem(getNudgeKey(sessionId))
  if (!last) return 0
  const elapsed = Date.now() - Number(last)
  return Math.max(0, NUDGE_COOLDOWN_MS - elapsed)
}

function nudgeCooldownLabel(sessionId: number): string {
  const ms = getNudgeCooldownLeft(sessionId)
  if (ms <= 0) return ''
  const mins = Math.ceil(ms / 60000)
  if (mins >= 60) return `${Math.ceil(mins / 60)}h cooldown`
  return `${mins}m cooldown`
}

function isNudgeOnCooldown(sessionId: number): boolean {
  return getNudgeCooldownLeft(sessionId) > 0
}

async function sendNudge(sessionId: number) {
  if (isNudgeOnCooldown(sessionId)) return
  try {
    await scheduleStore.nudgeSession(sessionId)
    localStorage.setItem(getNudgeKey(sessionId), String(Date.now()))
    toast.info('Nudge sent!', 'The other participant has been notified. You can nudge again in 1 hour.')
    emit('close')
  } catch {
    toast.error('Nudge failed', 'Could not send the nudge. Please try again.')
  }
}

const getUser = function(id: number): string  {
  return props.users.find((u: any) => u.id === id)?.name ?? `User #${id}`
}

const formatTime = function(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

const formatDateLong = function(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
}

const statusConfig = computed(() => {
  const s = props.session?.status ?? ''
  const map: Record<string, { label: string; icon: string; badge: string; dot: string; cardBg: string; headerBg: string }> = {
    scheduled:           { label: 'Confirmed',           icon: 'check_circle',    badge: 'bg-teal-500/20 border-teal-500/40 text-teal-400',   dot: 'bg-teal-400',   cardBg: 'bg-teal-500/5 border-teal-500/20',       headerBg: 'from-teal-500/10 to-transparent' },
    completed:           { label: 'Completed',           icon: 'verified',        badge: 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400', dot: 'bg-emerald-400', cardBg: 'bg-emerald-500/5 border-emerald-500/20', headerBg: 'from-emerald-500/10 to-transparent' },
    pending_teacher:     { label: 'Awaiting Teacher',    icon: 'pending',         badge: 'bg-amber-500/20 border-amber-500/40 text-amber-400',  dot: 'bg-amber-400',  cardBg: 'bg-amber-500/5 border-amber-500/20',     headerBg: 'from-amber-500/10 to-transparent' },
    pending_student:     { label: 'Awaiting Student',    icon: 'swap_horiz',      badge: 'bg-orange-500/20 border-orange-500/40 text-orange-400', dot: 'bg-orange-400', cardBg: 'bg-orange-500/5 border-orange-500/20', headerBg: 'from-orange-500/10 to-transparent' },
    pending_admin:       { label: 'Awaiting Admin',      icon: 'admin_panel_settings', badge: 'bg-blue-500/20 border-blue-500/40 text-blue-400', dot: 'bg-blue-400', cardBg: 'bg-blue-500/5 border-blue-500/20',       headerBg: 'from-blue-500/10 to-transparent' },
    pending_verification:{ label: 'Proof Under Review',  icon: 'fact_check',      badge: 'bg-violet-500/20 border-violet-500/40 text-violet-400', dot: 'bg-violet-400', cardBg: 'bg-violet-500/5 border-violet-500/20', headerBg: 'from-violet-500/10 to-transparent' },
    overdue:             { label: 'Overdue',             icon: 'schedule_send',   badge: 'bg-rose-500/20 border-rose-500/40 text-rose-400',     dot: 'bg-rose-400',   cardBg: 'bg-rose-500/5 border-rose-500/30',       headerBg: 'from-rose-500/10 to-transparent' },
    overdue_rejected:    { label: 'Proof Rejected',      icon: 'cancel',          badge: 'bg-red-500/20 border-red-500/40 text-red-400',        dot: 'bg-red-500',    cardBg: 'bg-red-500/5 border-red-500/30',         headerBg: 'from-red-500/10 to-transparent' },
    rejected:            { label: 'Declined',            icon: 'block',           badge: 'bg-red-500/20 border-red-500/30 text-red-400',        dot: 'bg-red-400',    cardBg: 'bg-red-500/5 border-red-500/20',         headerBg: 'from-red-500/10 to-transparent' },
    cancelled:           { label: 'Cancelled',           icon: 'do_not_disturb',  badge: 'bg-zinc-500/20 border-zinc-500/40 text-zinc-400',     dot: 'bg-zinc-400',   cardBg: 'bg-zinc-500/5 border-zinc-500/20',       headerBg: 'from-zinc-500/10 to-transparent' },
  }
  return map[s] ?? { label: s, icon: 'info', badge: 'bg-zinc-500/20 border-zinc-500/40 text-zinc-400', dot: 'bg-zinc-400', cardBg: 'bg-black/5', headerBg: 'from-zinc-500/10 to-transparent' }
})

const canForceComplete = function(session: Session) {
  return new Date().getTime() >= new Date(session.endTime).getTime() + 24 * 60 * 60 * 1000
}

// Contextual "what is happening" message per status + role
const statusContext = computed(() => {
  if (!props.session) return null
  const { status }  = props.session
  const role = props.userRole
  if (status === 'scheduled') {
    return { icon: 'event_available', color: 'text-teal-400', text: 'This session is confirmed and scheduled.' }
  }
  if (status === 'completed') {
    return { icon: 'verified', color: 'text-emerald-400', text: 'This session has been completed and finalized.' }
  }
  if (status === 'pending_teacher') {
    return role === 'teacher'
      ? { icon: 'pending_actions', color: 'text-amber-400', text: 'A student is requesting this session. Review and approve, counter, or decline.' }
      : { icon: 'hourglass_top', color: 'text-amber-400', text: 'Waiting for the teacher to review this request.' }
  }
  if (status === 'pending_student') {
    return role === 'student'
      ? { icon: 'swap_horiz', color: 'text-orange-400', text: 'Your teacher has proposed a different time. Accept or suggest another.' }
      : { icon: 'hourglass_top', color: 'text-orange-400', text: 'Waiting for the student to respond to the counter-proposal.' }
  }
  if (status === 'pending_admin') {
    return role === 'admin'
      ? { icon: 'admin_panel_settings', color: 'text-blue-400', text: 'This session is awaiting your final approval.' }
      : { icon: 'hourglass_top', color: 'text-blue-400', text: 'Waiting for admin to give final approval.' }
  }
  if (status === 'pending_verification') {
    return role === 'admin'
      ? { icon: 'fact_check', color: 'text-violet-400', text: 'Student submitted a proof. Review and approve or reject it.' }
      : { icon: 'hourglass_top', color: 'text-violet-400', text: 'Your proof is under review by the admin.' }
  }
  if (status === 'overdue') {
    return { icon: 'assignment_late', color: 'text-rose-400', text: 'This session is overdue. Upload proof to request completion.' }
  }
  if (status === 'overdue_rejected') {
    return { icon: 'cancel', color: 'text-red-400', text: 'Your proof was rejected. Please re-upload with a valid image and justification.' }
  }
  if (status === 'rejected') {
    return { icon: 'block', color: 'text-red-400', text: 'This request was declined.' }
  }
  if (status === 'cancelled') {
    return { icon: 'do_not_disturb', color: 'text-zinc-400', text: 'This session was cancelled.' }
  }
  return null
})
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 scale-95 translate-y-4 blur-[4px]"
      enter-to-class="opacity-100 scale-100 translate-y-0 blur-0"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100 scale-100 translate-y-0 blur-0"
      leave-to-class="opacity-0 scale-95 translate-y-4 blur-[4px]"
    >
      <div
        v-if="session"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        @click.self="$emit('close')"
      >
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/40 dark:bg-black/70 backdrop-blur-sm"
          @click="$emit('close')"
        />

        <!-- Modal -->
        <div class="relative w-full max-w-md glass-heavy rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
          <!-- Coloured header stripe -->
          <div :class="`bg-gradient-to-b ${statusConfig.headerBg} p-5 pb-4 border-b border-black/5 dark:border-white/5`">
            <div class="flex items-start justify-between gap-3">
              <div class="flex-1 min-w-0">
                <span
                  class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider border mb-2"
                  :class="statusConfig.badge"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="statusConfig.dot"></span>
                  {{ statusConfig.label }}
                </span>
                <p class="text-on-surface dark:text-on-surface font-black text-lg leading-tight">
                  {{ formatDateLong(session.startTime) }}
                </p>
                <p class="text-on-surface-variant dark:text-on-surface-variant text-sm mt-0.5 font-medium">
                  {{ formatTime(session.startTime) }} – {{ formatTime(session.endTime) }}
                </p>
              </div>
              <!-- Status icon + copy + close -->
              <div class="flex items-center gap-2 shrink-0">
                <div class="w-10 h-10 rounded-2xl flex items-center justify-center" :class="statusConfig.badge">
                  <span class="material-symbols-outlined text-lg" style="font-variation-settings:'FILL' 1">{{ statusConfig.icon }}</span>
                </div>
                <!-- Copy link button -->
                <button
                  class="w-10 h-10 rounded-2xl flex items-center justify-center bg-black/[0.06] dark:bg-white/[0.06] hover:bg-black/10 dark:hover:bg-white/10 text-on-surface-variant hover:text-on-surface transition-all"
                  title="Copy session link"
                  @click="copySessionLink"
                >
                  <span class="material-symbols-outlined text-lg">link</span>
                </button>
                <!-- Universal close button -->
                <button
                  class="w-10 h-10 rounded-2xl flex items-center justify-center bg-black/[0.06] dark:bg-white/[0.06] hover:bg-black/10 dark:hover:bg-white/10 text-on-surface-variant hover:text-on-surface transition-all"
                  @click="emit('close')"
                >
                  <span class="material-symbols-outlined text-lg">close</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Scrollable body -->
          <div class="overflow-y-auto flex-1 p-5 space-y-4 custom-scrollbar">

            <!-- Tabs -->
            <div class="flex bg-black/[0.04] dark:bg-white/5 p-1 rounded-2xl border border-black/[0.06] dark:border-white/10">
              <button
                class="flex-1 py-1.5 rounded-xl text-xs font-black uppercase tracking-wider transition-all"
                :class="activeTab === 'overview' ? 'bg-orange-500 text-white shadow-md' : 'text-on-surface-variant hover:text-on-surface'"
                @click="activeTab = 'overview'"
              >
                Overview
              </button>
              <button
                class="flex-1 py-1.5 rounded-xl text-xs font-black uppercase tracking-wider transition-all"
                :class="activeTab === 'history' ? 'bg-orange-500 text-white shadow-md' : 'text-on-surface-variant hover:text-on-surface'"
                @click="activeTab = 'history'"
              >
                History
              </button>
            </div>

            <div v-if="activeTab === 'overview'" class="space-y-4">
              <!-- Context message -->
              <div
                v-if="statusContext"
                class="flex items-start gap-2.5 p-3 rounded-2xl bg-black/[0.03] dark:bg-white/[0.04] border border-black/[0.04] dark:border-white/5"
              >
                <span class="material-symbols-outlined text-lg mt-0.5 shrink-0" :class="statusContext.color">{{ statusContext.icon }}</span>
                <p class="text-sm text-on-surface-variant dark:text-on-surface-variant">{{ statusContext.text }}</p>
              </div>

              <!-- Participants -->
              <div class="grid grid-cols-2 gap-2">
                <div class="bg-black/[0.04] dark:bg-white/5 rounded-2xl p-3">
                  <p class="text-[9px] text-on-surface-variant uppercase font-black tracking-widest mb-1">Teacher</p>
                  <p class="text-on-surface dark:text-on-surface text-sm font-bold truncate">{{ getUser(session.teacherId) }}</p>
                </div>
                <div class="bg-black/[0.04] dark:bg-white/5 rounded-2xl p-3">
                  <p class="text-[9px] text-on-surface-variant uppercase font-black tracking-widest mb-1">Student</p>
                  <p class="text-on-surface dark:text-on-surface text-sm font-bold truncate">{{ getUser(session.studentId) }}</p>
                </div>
              </div>

              <!-- Notes -->
              <div v-if="session.notes" class="bg-black/[0.04] dark:bg-white/5 rounded-2xl p-3">
                <p class="text-[9px] text-on-surface-variant uppercase font-black tracking-widest mb-1">Notes</p>
                <p class="text-sm text-on-surface-variant italic">{{ session.notes }}</p>
              </div>

              <!-- ────────────────────────────────────────────────
                   STATUS SECTIONS
                   ──────────────────────────────────────────────── -->

              <!-- COMPLETED: proof thumbnails -->
              <div v-if="session.status === 'completed'" class="space-y-3">
                <p class="text-[9px] text-on-surface-variant uppercase font-black tracking-widest">Session Proofs</p>
                <div v-if="session.proofs && session.proofs.length > 0" class="flex gap-3">
                  <button
                    v-for="proof in session.proofs"
                    :key="proof.id"
                    class="w-16 h-16 rounded-2xl overflow-hidden border border-black/[0.08] dark:border-white/10 hover:brightness-110 transition-all relative shrink-0"
                    @click="showProofViewer = proof.imageUrl?.startsWith('http') ? proof.imageUrl : `${API_URL}${proof.imageUrl}`"
                  >
                    <img :src="proof.imageUrl?.startsWith('http') ? proof.imageUrl : `${API_URL}${proof.imageUrl}`" class="w-full h-full object-cover" />
                    <div class="absolute bottom-0 inset-x-0 bg-black/50 text-[8px] text-white font-bold text-center py-0.5">
                      {{ proof.uploaderRole === 'teacher' ? 'Teacher' : 'Student' }}
                    </div>
                  </button>
                </div>
                <p v-else class="text-xs text-on-surface-variant">No proofs attached</p>
              </div>

              <!-- OVERDUE / OVERDUE_REJECTED / PENDING_VERIFICATION: proof status -->
              <div v-if="['overdue', 'overdue_rejected', 'pending_verification'].includes(session.status)" class="space-y-4">
                <!-- Proof status table -->
                <div class="bg-black/[0.04] dark:bg-white/5 rounded-2xl p-4 space-y-3">
                  <p class="text-[9px] text-on-surface-variant uppercase font-black tracking-widest">Proof Status</p>
                  <div class="flex items-center justify-between text-sm">
                    <span class="text-on-surface-variant">Teacher</span>
                    <div class="flex items-center gap-2">
                      <span class="font-bold" :class="session.proofs?.some(p => p.uploaderRole === 'teacher') ? 'text-emerald-500' : 'text-amber-500'">
                        {{ session.proofs?.some(p => p.uploaderRole === 'teacher') ? 'Uploaded ✓' : (session.isForceCompleted ? 'Force completed' : 'Pending') }}
                      </span>
                      <button
                        v-if="!session.proofs?.some(p => p.uploaderRole === 'teacher') && !session.isForceCompleted"
                        v-tooltip="isNudgeOnCooldown(session.id) ? `Cooldown: ${nudgeCooldownLabel(session.id)}` : 'Nudge Teacher to upload proof'"
                        class="p-1 rounded-lg transition-colors"
                        :class="isNudgeOnCooldown(session.id) ? 'text-zinc-400 cursor-not-allowed' : 'text-amber-500 hover:bg-black/5 dark:hover:bg-white/5 hover:text-amber-400'"
                        :disabled="isNudgeOnCooldown(session.id)"
                        @click="sendNudge(session.id)"
                      >
                        <span class="material-symbols-outlined text-[16px]">notifications_active</span>
                      </button>
                    </div>
                  </div>
                  <div class="flex items-center justify-between text-sm">
                    <span class="text-on-surface-variant">Student</span>
                    <div class="flex items-center gap-2">
                      <span class="font-bold" :class="session.proofs?.some(p => p.uploaderRole === 'student') ? 'text-emerald-500' : 'text-amber-500'">
                        {{ session.proofs?.some(p => p.uploaderRole === 'student') ? 'Uploaded ✓' : (session.isForceCompleted ? 'Force completed' : 'Pending') }}
                      </span>
                      <button
                        v-if="!session.proofs?.some(p => p.uploaderRole === 'student') && !session.isForceCompleted"
                        v-tooltip="isNudgeOnCooldown(session.id) ? `Cooldown: ${nudgeCooldownLabel(session.id)}` : 'Nudge Student to upload proof'"
                        class="p-1 rounded-lg transition-colors"
                        :class="isNudgeOnCooldown(session.id) ? 'text-zinc-400 cursor-not-allowed' : 'text-amber-500 hover:bg-black/5 dark:hover:bg-white/5 hover:text-amber-400'"
                        :disabled="isNudgeOnCooldown(session.id)"
                        @click="sendNudge(session.id)"
                      >
                        <span class="material-symbols-outlined text-[16px]">notifications_active</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Verif status pill -->
              <div v-if="session.status === 'pending_verification'" class="flex items-center gap-2 p-3 bg-violet-500/10 border border-violet-500/20 rounded-xl">
                <span class="material-symbols-outlined text-violet-400 text-lg">hourglass_top</span>
                <div>
                  <p class="text-xs font-bold text-violet-400">Awaiting Admin Review</p>
                  <p class="text-[10px] text-violet-300/70">Your proof has been submitted successfully.</p>
                </div>
              </div>
            </div>

            <!-- History Tab -->
            <div v-else class="space-y-3">
              <p class="text-[9px] text-on-surface-variant uppercase font-black tracking-widest">Activity History</p>
              <div v-if="isLoadingHistory" class="text-center py-4 text-xs text-on-surface-variant">
                Loading history...
              </div>
              <div v-else-if="!historyLogs || historyLogs.length === 0" class="text-center py-4 text-xs text-on-surface-variant">
                No activity logged yet.
              </div>
              <div v-else class="space-y-2.5">
                <div
                  v-for="log in historyLogs"
                  :key="log.id"
                  class="bg-black/[0.03] dark:bg-white/[0.03] border border-black/[0.04] dark:border-white/5 rounded-2xl p-3 flex flex-col space-y-1"
                >
                  <div class="flex items-center justify-between text-[10px] text-on-surface-variant font-bold">
                    <span>{{ log.actorName || 'System' }}</span>
                    <span>{{ formatDateLong(log.createdAt) }}</span>
                  </div>
                  <p class="text-xs text-on-surface">{{ log.description }}</p>
                </div>
              </div>
            </div>

            <!-- ────────────────────────────────────────────────
                 ACTION BUTTONS
                 ──────────────────────────────────────────────── -->
            <div class="flex flex-col gap-2 pt-1">

              <!-- Teacher: approve / counter / decline student proposal -->
              <template
                v-if="
                  (userRole === 'teacher' && session.status === 'pending_teacher' && session.teacherId === currentUserId) ||
                  (userRole === 'admin' && session.status === 'pending_teacher')
                "
              >
                <div class="flex gap-2">
                  <button class="flex-1 py-2.5 rounded-2xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-sm font-bold transition-all flex items-center justify-center gap-1.5" @click="$emit('approve-teacher', session.id)">
                    <span class="material-symbols-outlined text-base">check_circle</span> Approve
                  </button>
                  <button class="flex-1 py-2.5 rounded-2xl bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/30 text-orange-400 text-sm font-bold transition-all flex items-center justify-center gap-1.5" @click="$emit('counter-teacher', session)">
                    <span class="material-symbols-outlined text-base">swap_horiz</span> Counter
                  </button>
                  <button class="flex-1 py-2.5 rounded-2xl bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 text-sm font-bold transition-all flex items-center justify-center gap-1.5" @click="$emit('reject-teacher', session.id)">
                    <span class="material-symbols-outlined text-base">cancel</span> Decline
                  </button>
                </div>
              </template>

              <!-- Student: approve time / suggest other / decline -->
              <template
                v-if="
                  (userRole === 'student' && session.status === 'pending_student' && session.studentId === currentUserId) ||
                  (userRole === 'admin' && session.status === 'pending_student')
                "
              >
                <div class="flex gap-2">
                  <button class="flex-1 py-2.5 rounded-2xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-sm font-bold transition-all flex items-center justify-center gap-1.5" @click="$emit('approve-student', session.id)">
                    <span class="material-symbols-outlined text-base">check_circle</span> Accept Time
                  </button>
                  <button class="flex-1 py-2.5 rounded-2xl bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/30 text-orange-400 text-sm font-bold transition-all flex items-center justify-center gap-1.5" @click="$emit('counter-student', session)">
                    <span class="material-symbols-outlined text-base">edit_calendar</span> Suggest Other
                  </button>
                  <button class="flex-1 py-2.5 rounded-2xl bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 text-sm font-bold transition-all flex items-center justify-center gap-1.5" @click="$emit('reject-student', session.id)">
                    <span class="material-symbols-outlined text-base">cancel</span> Decline
                  </button>
                </div>
              </template>

              <!-- Admin: approve / reject pending_admin -->
              <template v-if="userRole === 'admin' && session.status === 'pending_admin'">
                <div class="flex gap-2">
                  <button class="flex-1 py-2.5 rounded-2xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-sm font-bold transition-all flex items-center justify-center gap-1.5" @click="$emit('approve-admin', session.id)">
                    <span class="material-symbols-outlined text-base">check_circle</span> Approve
                  </button>
                  <button class="flex-1 py-2.5 rounded-2xl bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 text-sm font-bold transition-all flex items-center justify-center gap-1.5" @click="$emit('reject-admin', session.id)">
                    <span class="material-symbols-outlined text-base">cancel</span> Reject
                  </button>
                </div>
              </template>

              <!-- Admin: approve proof / reject proof for pending_verification -->
              <template v-if="userRole === 'admin' && session.status === 'pending_verification'">
                <div class="flex gap-2">
                  <button class="flex-1 py-2.5 rounded-2xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-sm font-bold transition-all flex items-center justify-center gap-1.5" @click="$emit('complete-admin', session.id)">
                    <span class="material-symbols-outlined text-base">verified</span> Approve Proof
                  </button>
                  <button class="flex-1 py-2.5 rounded-2xl bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 text-sm font-bold transition-all flex items-center justify-center gap-1.5" @click="$emit('reject-proof-admin', session.id)">
                    <span class="material-symbols-outlined text-base">cancel</span> Reject Proof
                  </button>
                </div>
              </template>

              <!-- Admin: force complete (overdue/overdue_rejected/scheduled) -->
              <template v-if="userRole === 'admin' && ['scheduled', 'overdue', 'overdue_rejected'].includes(session.status)">
                <button
                  class="w-full py-2.5 rounded-2xl bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/30 text-orange-400 text-sm font-bold transition-all flex items-center justify-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
                  :title="canForceComplete(session) ? 'Overrides proof requirements and finalizes session' : 'Only available 24h after session end time'"
                  :disabled="!canForceComplete(session)"
                  @click="$emit('complete-admin', session.id)"
                >
                  <span class="material-symbols-outlined text-base">workspace_premium</span>
                  {{ canForceComplete(session) ? 'Force Complete' : 'Force Complete (' + (forceCompleteCountdown || 'available in 24h') + ')' }}
                </button>
              </template>

              <!-- Admin edit button (always visible for admin) -->
              <button
                v-if="userRole === 'admin' && !['completed', 'cancelled', 'rejected'].includes(session.status)"
                class="w-full py-2.5 rounded-2xl bg-black/[0.04] dark:bg-white/5 hover:bg-black/5 dark:hover:bg-white/10 border border-black/[0.06] dark:border-white/10 text-on-surface-variant text-sm font-bold transition-all flex items-center justify-center gap-1.5"
                @click="$emit('edit-admin', session)"
              >
                <span class="material-symbols-outlined text-base">edit</span> Edit Session
              </button>

              <!-- Upload Proof Button (visible to participant who hasn't uploaded) -->
              <button
                v-if="showUploadProofButton"
                class="w-full py-2.5 rounded-2xl bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/30 text-indigo-400 text-sm font-bold transition-all flex items-center justify-center gap-1.5"
                @click="triggerUpload"
              >
                <span class="material-symbols-outlined text-base">upload</span> Upload My Proof
              </button>
              <input
                ref="fileInput"
                type="file"
                class="hidden"
                accept="image/*"
                @change="handleFileChange"
              />

              <!-- Cancel Session Button (visible to admin or participant) -->
              <button
                v-if="showCancelButton"
                class="w-full py-2.5 rounded-2xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 text-sm font-bold transition-all flex items-center justify-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
                :disabled="!canCancel"
                :title="!canCancel ? 'Non-admins cannot cancel sessions starting in less than 24 hours.' : 'Cancel this session'"
                @click="clickCancel"
              >
                <span class="material-symbols-outlined text-base">cancel</span> Cancel Session
              </button>

              <div v-if="session.counterCount && session.counterCount > 0" class="text-xs text-on-surface-variant text-center my-1">
                Counter proposals used: {{ session.counterCount }} / 3
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Proof Lightbox -->
    <Transition
      enter-active-class="transition-all duration-150 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="showProofViewer"
        class="fixed inset-0 z-[300] flex items-center justify-center bg-black/90 backdrop-blur-md p-4"
        @click="showProofViewer = null"
      >
        <button
          class="absolute top-5 right-5 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 border border-white/10 flex items-center justify-center text-white transition-all"
          @click="showProofViewer = null"
        >
          <span class="material-symbols-outlined">close</span>
        </button>

        <!-- Prev Button -->
        <button
          v-if="proofUrls.length > 1"
          class="absolute left-5 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 border border-white/10 flex items-center justify-center text-white transition-all select-none"
          @click.stop="prevProof"
        >
          <span class="material-symbols-outlined">chevron_left</span>
        </button>

        <img
          :src="showProofViewer"
          class="max-w-full max-h-[85vh] object-contain rounded-2xl shadow-2xl border border-white/10"
        />

        <!-- Next Button -->
        <button
          v-if="proofUrls.length > 1"
          class="absolute right-5 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 border border-white/10 flex items-center justify-center text-white transition-all select-none"
          @click.stop="nextProof"
        >
          <span class="material-symbols-outlined">chevron_right</span>
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

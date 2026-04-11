<script setup lang="ts">
import { NUDGE_COOLDOWN_MS } from '@typscript/constants'
import { ref, computed } from 'vue'
import { useToastStore } from '@stores/toast'
import type { User, Session } from '@types'

const props = defineProps<{
  session: Session | null
  userRole: 'admin' | 'teacher' | 'student'
  currentUserId: string
  users: User[]
}>()

const emit = defineEmits<{
  close: []
  'approve-teacher': [sessionId: string]
  'reject-teacher': [sessionId: string]
  'counter-teacher': [session: Session]
  'approve-student': [sessionId: string]
  'counter-student': [session: Session]
  'approve-admin': [sessionId: string]
  'reject-admin': [sessionId: string]
  'edit-admin': [session: Session]
  'complete-admin': [sessionId: string]
  'reject-proof-admin': [sessionId: string]
}>()

const toast = useToastStore()
const showProofViewer = ref<string | null>(null)

// ── Nudge cooldown (1 hour per session, persisted in localStorage) ─────────

function getNudgeKey(sessionId: string) {
  return `nudge_last_${sessionId}`
}

function getNudgeCooldownLeft(sessionId: string): number {
  const last = localStorage.getItem(getNudgeKey(sessionId))
  if (!last) return 0
  const elapsed = Date.now() - Number(last)
  return Math.max(0, NUDGE_COOLDOWN_MS - elapsed)
}

function nudgeCooldownLabel(sessionId: string): string {
  const ms = getNudgeCooldownLeft(sessionId)
  if (ms <= 0) return ''
  const mins = Math.ceil(ms / 60000)
  if (mins >= 60) return `${Math.ceil(mins / 60)}h cooldown`
  return `${mins}m cooldown`
}

function isNudgeOnCooldown(sessionId: string): boolean {
  return getNudgeCooldownLeft(sessionId) > 0
}

function sendNudge(sessionId: string) {
  if (isNudgeOnCooldown(sessionId)) return
  localStorage.setItem(getNudgeKey(sessionId), String(Date.now()))
  const remaining = '1 hour'
  toast.info('Nudge sent!', `The other participant has been notified. You can nudge again in ${remaining}.`)
  emit('close')
}

const getUser = function(id: string): string  {
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
              <!-- Status icon + close -->
              <div class="flex items-center gap-2 shrink-0">
                <div class="w-10 h-10 rounded-2xl flex items-center justify-center" :class="statusConfig.badge">
                  <span class="material-symbols-outlined text-lg" style="font-variation-settings:'FILL' 1">{{ statusConfig.icon }}</span>
                </div>
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
                  class="flex-1 aspect-video rounded-xl overflow-hidden border border-black/[0.08] dark:border-white/10 hover:brightness-110 transition-all relative group"
                  @click="showProofViewer = proof.imageUrl"
                >
                  <img :src="proof.imageUrl" class="w-full h-full object-cover" />
                  <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <span class="material-symbols-outlined text-white text-2xl">zoom_in</span>
                  </div>
                  <span class="absolute bottom-1.5 left-2 text-[9px] font-black uppercase text-white/80 bg-black/40 rounded px-1.5 py-0.5 backdrop-blur-sm">
                    {{ proof.uploaderRole === 'teacher' ? 'Teacher' : 'Student' }}
                  </span>
                </button>
              </div>
              <div v-else-if="session.isForceCompleted" class="p-3 bg-orange-500/10 border border-orange-500/20 rounded-xl text-center">
                <p class="text-xs font-bold text-orange-400">Force completed by admin</p>
                <p class="text-[10px] text-orange-300/70 mt-0.5">Proofs were not required for this completion.</p>
              </div>
              <div v-else class="p-3 bg-black/[0.04] dark:bg-white/5 rounded-xl text-center">
                <p class="text-xs text-on-surface-variant">No proofs attached</p>
              </div>
            </div>

            <!-- PENDING status group: show who's still needed -->
            <div
              v-if="['pending_teacher', 'pending_student', 'pending_admin'].includes(session.status)"
              class="rounded-2xl p-4 border space-y-2"
              :class="statusConfig.cardBg"
            >
              <p class="text-[9px] font-black uppercase tracking-widest text-on-surface-variant mb-2">Approval Status</p>
              <div class="flex items-center justify-between text-sm">
                <span class="text-on-surface-variant">Teacher</span>
                <span class="font-bold" :class="session.status === 'pending_teacher' ? 'text-amber-400' : 'text-emerald-400'">
                  {{ session.status === 'pending_teacher' ? 'Reviewing…' : '✓ Responded' }}
                </span>
              </div>
              <div class="flex items-center justify-between text-sm">
                <span class="text-on-surface-variant">Student</span>
                <span class="font-bold" :class="session.status === 'pending_student' ? 'text-orange-400' : 'text-emerald-400'">
                  {{ session.status === 'pending_student' ? 'Countering…' : '✓ Responded' }}
                </span>
              </div>
              <div class="flex items-center justify-between text-sm">
                <span class="text-on-surface-variant">Admin</span>
                <span class="font-bold" :class="session.status === 'pending_admin' ? 'text-blue-400' : 'text-emerald-400'">
                  {{ session.status === 'pending_admin' ? 'Reviewing…' : (session.status === 'scheduled' ? '✓ Approved' : '—') }}
                </span>
              </div>
            </div>

            <!-- OVERDUE / OVERDUE_REJECTED: proof status -->
            <div v-if="['overdue', 'overdue_rejected', 'pending_verification', 'scheduled'].includes(session.status)" class="space-y-3">
              <!-- Rejection notice -->
              <div v-if="session.status === 'overdue_rejected'" class="p-3 bg-red-500/10 border border-red-500/20 rounded-2xl">
                <p class="text-[9px] font-black uppercase text-red-500 tracking-wider mb-1">Proof Rejected</p>
                <p class="text-xs text-red-400 font-bold">{{ session.rejectionReason }}</p>
              </div>

              <!-- Proof status row -->
              <div class="bg-black/[0.04] dark:bg-white/5 rounded-2xl p-3.5 border border-black/[0.04] dark:border-white/5">
                <p class="text-[9px] text-on-surface-variant uppercase font-black tracking-widest mb-3">Session Proofs</p>
                <div class="space-y-2">
                  <div class="flex items-center justify-between text-sm">
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
                <!-- Proof thumbnails (if any) -->
                <div v-if="session.proofs && session.proofs.length > 0" class="flex gap-2 mt-3 pt-3 border-t border-black/[0.04] dark:border-white/5">
                  <button
                    v-for="proof in session.proofs"
                    :key="proof.id"
                    class="w-12 h-12 rounded-lg overflow-hidden border border-black/[0.08] dark:border-white/10 hover:brightness-110 transition-all relative shrink-0"
                    @click="showProofViewer = proof.imageUrl"
                  >
                    <img :src="proof.imageUrl" class="w-full h-full object-cover" />
                    <div class="absolute bottom-0 inset-x-0 bg-black/50 text-[7px] text-white font-bold text-center py-0.5">
                      {{ proof.uploaderRole === 'teacher' ? 'T' : 'S' }}
                    </div>
                  </button>
                </div>
                <!-- Justification note -->
                <div v-if="session.proofJustification" class="mt-3 pt-3 border-t border-black/[0.04] dark:border-white/5">
                  <p class="text-[9px] text-on-surface-variant uppercase font-black tracking-wider mb-1">Student's Note</p>
                  <p class="text-xs text-on-surface italic">"{{ session.proofJustification }}"</p>
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

              <!-- Student: approve time / suggest other -->
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
                  {{ canForceComplete(session) ? 'Force Complete' : 'Force Complete (available in 24h)' }}
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
        <img
          :src="showProofViewer"
          class="max-w-full max-h-[85vh] object-contain rounded-2xl shadow-2xl border border-white/10"
        />
      </div>
    </Transition>
  </Teleport>
</template>

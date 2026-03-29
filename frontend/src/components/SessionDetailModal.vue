<script setup lang="ts">
import { computed } from 'vue'
import type { Session, User } from '../types'

const props = defineProps<{
  date: Date | null
  sessions: Session[]
  userRole: 'admin' | 'teacher' | 'student'
  currentUserId: string
  users: User[]
}>()

defineEmits<{
  close: []
  propose: []
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

const formattedDate = computed(() => {
  if (!props.date) return ''
  return props.date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
})

function getTeacherName(teacherId: string): string {
  return props.users.find((u) => u.id === teacherId)?.name ?? `Teacher #${teacherId}`
}

function getStudentName(studentId: string): string {
  return props.users.find((u) => u.id === studentId)?.name ?? `Student #${studentId}`
}

function formatTime(iso: string) {
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    scheduled: 'Confirmed',
    completed: 'Completed',
    pending_teacher: 'Awaiting Teacher',
    pending_student: 'Countered by Teacher',
    pending_admin: 'Awaiting Admin',
    rejected: 'Declined',
    cancelled: 'Cancelled',
    overdue: 'Overdue',
  }
  return map[status] ?? status
}

function sessionCardBg(status: string): string {
  const map: Record<string, string> = {
    scheduled: 'bg-orange-500/5 border-orange-500/20',
    completed: 'bg-emerald-500/5 border-emerald-500/20',
    pending_teacher: 'bg-amber-500/5 border-amber-500/20',
    pending_student: 'bg-orange-500/5 border-orange-500/20',
    pending_admin: 'bg-blue-500/5 border-blue-500/20',
    rejected: 'bg-red-500/5 border-red-500/20',
    cancelled: 'bg-zinc-500/5 border-zinc-500/20',
    overdue: 'bg-red-500/5 border-red-500/40',
  }
  return map[status] ?? 'bg-black/5 dark:bg-white/5 border-black/10 dark:border-white/10'
}

function statusBadgeClass(status: string): string {
  const map: Record<string, string> = {
    scheduled: 'bg-orange-500/20 border-orange-500/40 text-orange-400',
    completed: 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400',
    pending_teacher: 'bg-amber-500/20 border-amber-500/40 text-amber-400',
    pending_student: 'bg-orange-500/20 border-orange-500/40 text-orange-400',
    pending_admin: 'bg-blue-500/20 border-blue-500/40 text-blue-400',
    rejected: 'bg-red-500/20 border-red-500/40 text-red-400',
    cancelled: 'bg-zinc-500/20 border-zinc-500/40 text-zinc-400',
    overdue: 'bg-red-500/20 border-red-500/40 text-red-400',
  }
  return (
    map[status] ??
    'bg-black/5 dark:bg-white/10 border-black/10 dark:border-white/20 text-on-surface-variant dark:text-on-surface-variant'
  )
}

function statusDotClass(status: string): string {
  const map: Record<string, string> = {
    scheduled: 'bg-orange-400',
    completed: 'bg-emerald-400',
    pending_teacher: 'bg-amber-400',
    pending_student: 'bg-orange-400',
    pending_admin: 'bg-blue-400',
    rejected: 'bg-red-400',
    cancelled: 'bg-zinc-400',
    overdue: 'bg-red-400',
  }
  return map[status] ?? 'bg-zinc-400'
}

function canForceComplete(session: Session) {
  const end = new Date(session.endTime).getTime()
  const now = new Date().getTime()
  return now >= end + 24 * 60 * 60 * 1000
}
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
        v-if="date"
        class="fixed inset-0 z-[200] flex items-center justify-center p-4"
        @click.self="$emit('close')"
      >
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/30 dark:bg-black/60 backdrop-blur-sm"
          @click="$emit('close')"
        />

        <!-- Modal -->
        <div class="relative w-full max-w-lg glass-heavy rounded-3xl shadow-2xl overflow-hidden">
          <!-- Header -->
          <div
            class="flex items-center justify-between p-6 border-b border-black/5 dark:border-white/5"
          >
            <div>
              <p class="text-[10px] font-black text-orange-500 uppercase tracking-widest mb-1">
                Session Details
              </p>
              <h3 class="text-xl font-black text-on-surface dark:text-on-surface">
                {{ formattedDate }}
              </h3>
              <p class="text-on-surface-variant dark:text-on-surface-variant text-sm mt-0.5">
                {{ sessions.length }} session{{ sessions.length !== 1 ? 's' : '' }} scheduled
              </p>
            </div>
            <button
              class="w-10 h-10 rounded-2xl bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 border border-black/8 dark:border-white/10 flex items-center justify-center text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-all"
              @click="$emit('close')"
            >
              <span class="material-symbols-outlined text-lg">close</span>
            </button>
          </div>

          <!-- Session List -->
          <div class="p-6 space-y-4 max-h-[400px] overflow-y-auto">
            <!-- No sessions state -->
            <div v-if="sessions.length === 0" class="text-center py-8">
              <span
                class="material-symbols-outlined text-4xl text-on-surface-variant/60 dark:text-on-surface-variant/40 mb-3 block"
                >calendar_today</span
              >
              <p class="text-on-surface-variant dark:text-on-surface-variant font-medium">
                No sessions on this day
              </p>
              <p class="text-on-surface-variant dark:text-on-surface-variant text-sm mt-1">
                Click "Propose Session" to schedule one
              </p>
            </div>

            <!-- Session Cards -->
            <div
              v-for="session in sessions"
              :key="session.id"
              class="rounded-2xl p-4 border space-y-3"
              :class="sessionCardBg(session.status)"
            >
              <!-- Time & Status -->
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-on-surface dark:text-on-surface font-bold text-sm">
                    {{ formatTime(session.startTime) }} – {{ formatTime(session.endTime) }}
                  </p>
                  <div class="flex items-center gap-2 mt-1">
                    <span
                      class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border"
                      :class="statusBadgeClass(session.status)"
                    >
                      <span
                        class="w-1.5 h-1.5 rounded-full"
                        :class="statusDotClass(session.status)"
                      ></span>
                      {{ statusLabel(session.status) }}
                    </span>
                  </div>
                </div>
                <!-- Admin edit button -->
                <button
                  v-if="userRole === 'admin'"
                  class="p-1.5 rounded-xl bg-black/[0.04] dark:bg-white/5 hover:bg-black/5 dark:hover:bg-white/10 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-all"
                  title="Edit session"
                  @click="$emit('edit-admin', session)"
                >
                  <span class="material-symbols-outlined text-base">edit</span>
                </button>
              </div>

              <!-- Participants -->
              <div class="grid grid-cols-2 gap-2">
                <div class="bg-black/[0.04] dark:bg-white/5 rounded-xl py-2.5 px-4">
                  <p
                    class="text-[9px] text-on-surface-variant dark:text-on-surface-variant uppercase font-bold tracking-wider mb-1"
                  >
                    Teacher
                  </p>
                  <p class="text-on-surface dark:text-on-surface text-xs font-bold truncate">
                    {{ getTeacherName(session.teacherId) }}
                  </p>
                </div>
                <div class="bg-black/[0.04] dark:bg-white/5 rounded-xl py-2.5 px-4">
                  <p
                    class="text-[9px] text-on-surface-variant dark:text-on-surface-variant uppercase font-bold tracking-wider mb-1"
                  >
                    Student
                  </p>
                  <p class="text-on-surface dark:text-on-surface text-xs font-bold truncate">
                    {{ getStudentName(session.studentId) }}
                  </p>
                </div>
              </div>

              <!-- Notes -->
              <div
                v-if="session.notes"
                class="bg-black/[0.04] dark:bg-white/5 rounded-xl py-2.5 px-4"
              >
                <p
                  class="text-[9px] text-on-surface-variant dark:text-on-surface-variant uppercase font-bold tracking-wider mb-1"
                >
                  Notes
                </p>
                <p class="text-on-surface-variant text-xs">{{ session.notes }}</p>
              </div>

              <!-- Proof Status -->
              <div v-if="['scheduled', 'overdue', 'completed', 'pending_verification', 'overdue_rejected'].includes(session.status)" class="bg-black/[0.04] dark:bg-white/5 rounded-xl py-2.5 px-4 mt-2 border border-black/[0.04] dark:border-white/5">
                <p class="text-[9px] text-on-surface-variant dark:text-on-surface-variant uppercase font-bold tracking-wider mb-2">
                  Session Proofs
                </p>
                <div class="space-y-1">
                  <div class="flex items-center justify-between text-xs">
                    <span class="text-on-surface-variant">Teacher:</span>
                    <span class="font-bold" :class="session.proofs?.some(p => p.uploaderRole === 'teacher') ? 'text-emerald-500' : 'text-amber-500'">
                      {{ session.proofs?.some(p => p.uploaderRole === 'teacher') ? 'Uploaded ✓' : (session.isForceCompleted ? '(force completed by admin)' : 'Pending') }}
                    </span>
                  </div>
                  <div class="flex items-center justify-between text-xs">
                    <span class="text-on-surface-variant">Student:</span>
                    <span class="font-bold" :class="session.proofs?.some(p => p.uploaderRole === 'student') ? 'text-emerald-500' : 'text-amber-500'">
                      {{ session.proofs?.some(p => p.uploaderRole === 'student') ? 'Uploaded ✓' : (session.isForceCompleted ? '(force completed by admin)' : 'Pending') }}
                    </span>
                  </div>
                </div>
                <div v-if="session.proofJustification" class="mt-2 pt-2 border-t border-black/5 dark:border-white/5">
                  <p class="text-[9px] text-on-surface-variant uppercase font-bold tracking-wider mb-1">Student's Note</p>
                  <p class="text-xs text-on-surface italic">"{{ session.proofJustification }}"</p>
                </div>
                <div v-if="session.rejectionReason && session.status === 'overdue_rejected'" class="mt-2 pt-2 border-t border-red-500/20">
                  <p class="text-[9px] text-red-500 uppercase font-bold tracking-wider mb-1">Admin Rejection Reason</p>
                  <p class="text-xs text-red-400 font-bold">"{{ session.rejectionReason }}"</p>
                </div>
              </div>

              <!-- Action Buttons -->
              <div class="flex gap-2 pt-1">
                <!-- Teacher actions: approve/reject student proposals -->
                <template
                  v-if="
                    (userRole === 'teacher' &&
                      session.status === 'pending_teacher' &&
                      session.teacherId === currentUserId) ||
                    (userRole === 'admin' && session.status === 'pending_teacher')
                  "
                >
                  <button
                    class="flex-1 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-xs font-bold transition-all flex items-center justify-center gap-1"
                    @click="$emit('approve-teacher', session.id)"
                  >
                    <span class="material-symbols-outlined text-sm">check_circle</span>
                    Approve
                  </button>
                  <button
                    class="flex-1 py-2 rounded-xl bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/30 text-orange-400 text-xs font-bold transition-all flex items-center justify-center gap-1"
                    @click="$emit('counter-teacher', session)"
                  >
                    <span class="material-symbols-outlined text-sm">swap_horiz</span>
                    Counter
                  </button>
                  <button
                    class="flex-1 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 text-xs font-bold transition-all flex items-center justify-center gap-1"
                    @click="$emit('reject-teacher', session.id)"
                  >
                    <span class="material-symbols-outlined text-sm">cancel</span>
                    Decline
                  </button>
                </template>

                <!-- Student actions: approve/counter proposals -->
                <template
                  v-if="
                    (userRole === 'student' &&
                      session.status === 'pending_student' &&
                      session.studentId === currentUserId) ||
                    (userRole === 'admin' && session.status === 'pending_student')
                  "
                >
                  <button
                    class="flex-1 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-xs font-bold transition-all flex items-center justify-center gap-1"
                    @click="$emit('approve-student', session.id)"
                  >
                    <span class="material-symbols-outlined text-sm">check_circle</span>
                    Approve New Time
                  </button>
                  <button
                    class="flex-1 py-2 rounded-xl bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/30 text-orange-400 text-xs font-bold transition-all flex items-center justify-center gap-1"
                    @click="$emit('counter-student', session)"
                  >
                    <span class="material-symbols-outlined text-sm">swap_horiz</span>
                    Suggest Other
                  </button>
                </template>

                <!-- Admin actions: approve/reject pending_admin sessions -->
                <template v-if="userRole === 'admin' && session.status === 'pending_admin'">
                  <button
                    class="flex-1 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-xs font-bold transition-all flex items-center justify-center gap-1"
                    @click="$emit('approve-admin', session.id)"
                  >
                    <span class="material-symbols-outlined text-sm">check_circle</span>
                    Approve
                  </button>
                  <button
                    class="flex-1 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 text-xs font-bold transition-all flex items-center justify-center gap-1"
                    @click="$emit('reject-admin', session.id)"
                  >
                    <span class="material-symbols-outlined text-sm">cancel</span>
                    Reject
                  </button>
                </template>

                <!-- Admin actions: approve/reject pending_verification (proofs submitted) -->
                <template v-if="userRole === 'admin' && session.status === 'pending_verification'">
                  <button
                    class="flex-1 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/30 text-emerald-400 text-xs font-bold transition-all flex items-center justify-center gap-1"
                    title="Approves proof and finalizes session"
                    @click="$emit('complete-admin', session.id)"
                  >
                    <span class="material-symbols-outlined text-sm">verified</span>
                    Approve Proof
                  </button>
                  <button
                    class="flex-1 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 text-xs font-bold transition-all flex items-center justify-center gap-1"
                    title="Rejects proof with a reason"
                    @click="$emit('reject-proof-admin', session.id)"
                  >
                    <span class="material-symbols-outlined text-sm">cancel</span>
                    Reject Proof
                  </button>
                </template>

                <!-- Admin actions: complete session manually -->
                <template v-if="userRole === 'admin' && ['scheduled', 'overdue', 'overdue_rejected'].includes(session.status)">
                  <button
                    class="flex-1 py-2 rounded-xl bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/30 text-orange-400 text-xs font-bold transition-all flex items-center justify-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                    :title="canForceComplete(session) ? 'Overrides proof requirements and finalizes session' : 'Cannot force complete a session until 24 hours after its end time'"
                    :disabled="!canForceComplete(session)"
                    @click="$emit('complete-admin', session.id)"
                  >
                    <span class="material-symbols-outlined text-sm">workspace_premium</span>
                    Force Complete
                  </button>
                </template>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="p-4 border-t border-black/5 dark:border-white/5 flex gap-3">
            <button
              v-if="userRole !== 'admin' && !sessions.some(s => ['overdue', 'overdue_rejected', 'pending_verification'].includes(s.status))"
              class="flex-1 py-3 bg-gradient-to-br from-orange-500 to-orange-700 text-white font-bold rounded-2xl shadow-lg shadow-orange-900/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-2 text-sm"
              @click="$emit('propose')"
            >
              <span class="material-symbols-outlined text-base">add_circle</span>
              Propose New Schedule
            </button>
            <button
              v-if="userRole === 'admin' && !sessions.some(s => ['overdue', 'overdue_rejected', 'pending_verification'].includes(s.status))"
              class="flex-1 py-3 bg-gradient-to-br from-orange-500 to-orange-700 text-white font-bold rounded-2xl shadow-lg shadow-orange-900/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-2 text-sm"
              @click="$emit('propose')"
            >
              <span class="material-symbols-outlined text-base">add_circle</span>
              Schedule New Session
            </button>
            <button
              class="px-5 py-3 bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 border border-black/8 dark:border-white/10 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface font-bold rounded-2xl transition-all text-sm"
              @click="$emit('close')"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

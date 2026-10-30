<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import BaseModal from '@components/BaseModal.vue'
import type { Session, User } from '@types'

const props = withDefaults(
  defineProps<{
    student: User | null
    /** The student's sessions. The admin view passes every session, the
     *  teacher view only their own — which is the whole difference between
     *  the two screens' data. */
    sessions: Session[]
    /** The highlighted tile: credits remaining for admins, lessons taught
     *  for teachers. */
    statLabel: string
    statValue: number
    emptyText?: string
  }>(),
  { emptyText: 'No sessions yet for this student.' }
)

const emit = defineEmits<{
  close: []
  'select-session': [Session]
}>()

const activeChip = ref<string | null>(null)

const stats = computed(() => {
  const ss = props.sessions
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

const chips = computed(() =>
  [
    {
      key: 'total',
      label: 'All',
      count: stats.value.total,
      color: 'bg-surface-container-high/20 border-outline-variant/30 text-on-surface-variant',
      dot: 'bg-surface-container-high',
    },
    {
      key: 'confirmed',
      label: 'Confirmed',
      count: stats.value.confirmed,
      color: 'bg-success/20 border-success/30 text-success',
      dot: 'bg-success',
    },
    {
      key: 'pending',
      label: 'Pending',
      count: stats.value.pending,
      color: 'bg-warning/20 border-warning/30 text-warning',
      dot: 'bg-warning',
    },
    {
      key: 'completed',
      label: 'Done',
      count: stats.value.completed,
      color: 'bg-success/20 border-success/30 text-success',
      dot: 'bg-success',
    },
    {
      key: 'overdue',
      label: 'Overdue',
      count: stats.value.overdue,
      color: 'bg-error/20 border-error/30 text-error',
      dot: 'bg-error',
    },
    {
      key: 'review',
      label: 'In Review',
      count: stats.value.review,
      color: 'bg-tertiary/20 border-tertiary/30 text-tertiary',
      dot: 'bg-tertiary',
    },
    {
      key: 'rejected',
      label: 'Declined',
      count: stats.value.rejected,
      color: 'bg-error/20 border-error/30 text-error',
      dot: 'bg-error',
    },
  ].filter((chip) => chip.count > 0)
)

const filteredSessions = computed(() => {
  const ss = props.sessions
  switch (activeChip.value) {
    case 'confirmed':
      return ss.filter((s) => s.status === 'scheduled')
    case 'pending':
      return ss.filter((s) =>
        ['pending_teacher', 'pending_student', 'pending_admin'].includes(s.status)
      )
    case 'completed':
      return ss.filter((s) => s.status === 'completed')
    case 'overdue':
      return ss.filter((s) => ['overdue', 'overdue_rejected'].includes(s.status))
    case 'review':
      return ss.filter((s) => s.status === 'pending_verification')
    case 'rejected':
      return ss.filter((s) => ['rejected', 'cancelled'].includes(s.status))
    default:
      return ss
  }
})

const activeChipLabel = computed(
  () => chips.value.find((c) => c.key === activeChip.value)?.label ?? 'All'
)

function selectChip(key: string) {
  activeChip.value = activeChip.value === key ? null : key
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    scheduled: 'bg-success/20 border-success/30 text-success',
    completed: 'bg-success/20 border-success/30 text-success',
    pending_teacher: 'bg-warning/20 border-warning/30 text-warning',
    pending_student: 'bg-primary/20 border-primary/30 text-primary',
    pending_admin: 'bg-tertiary/20 border-tertiary/30 text-tertiary',
    pending_verification: 'bg-tertiary/20 border-tertiary/30 text-tertiary',
    overdue: 'bg-error/20 border-error/30 text-error',
    overdue_rejected: 'bg-error/20 border-error/30 text-error',
    rejected: 'bg-error/20 border-error/30 text-error',
    cancelled: 'bg-surface-container-high/20 border-outline-variant/30 text-on-surface-variant',
  }
  return (
    map[status] ?? 'bg-surface-container-high/20 border-outline-variant/30 text-on-surface-variant'
  )
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    scheduled: 'Confirmed',
    completed: 'Done',
    pending_teacher: 'Aw. Teacher',
    pending_student: 'Countered',
    pending_admin: 'Aw. Admin',
    pending_verification: 'In Review',
    overdue: 'Overdue',
    overdue_rejected: 'Proof Rej.',
    rejected: 'Declined',
    cancelled: 'Cancelled',
  }
  return map[status] ?? status
}

// A filter chosen for one student means nothing for the next one.
watch(
  () => props.student?.id,
  () => {
    activeChip.value = null
  }
)
</script>

<template>
  <BaseModal
    :is-open="!!student"
    size="xl"
    close-label="Close student details"
    @close="emit('close')"
  >
    <template v-if="student" #header>
      <div class="flex items-center gap-4 p-6 border-b border-on-surface/5">
        <div
          class="size-14 rounded-2xl bg-success/20 border border-success/20 flex items-center justify-center text-success font-semibold text-xl overflow-hidden shrink-0"
        >
          <img
            v-if="student.avatarUrl"
            :src="student.avatarUrl"
            alt=""
            class="w-full h-full object-cover"
          />
          <span v-else>{{ student.name.charAt(0).toUpperCase() }}</span>
        </div>
        <div class="flex-1 min-w-0">
          <h2 class="font-semibold text-xl text-on-surface truncate">{{ student.name }}</h2>
          <p class="text-on-surface-variant text-sm">{{ student.email }}</p>
        </div>
        <button class="icon-btn" aria-label="Close student details" @click="emit('close')">
          <span class="material-symbols-outlined text-lg">close</span>
        </button>
      </div>
    </template>

    <template v-if="student">
      <div class="grid grid-cols-2 gap-3">
        <div v-if="student.school" class="bg-on-surface/[0.04] rounded-2xl p-3">
          <p class="text-xs font-semibold text-on-surface-variant uppercase mb-1">School</p>
          <p class="text-sm font-bold text-on-surface">{{ student.school }}</p>
        </div>
        <div v-if="student.contactNumber" class="bg-on-surface/[0.04] rounded-2xl p-3">
          <p class="text-xs font-semibold text-on-surface-variant uppercase mb-1">Contact</p>
          <p class="text-sm font-bold text-on-surface">{{ student.contactNumber }}</p>
        </div>
        <div v-if="student.parentName" class="bg-on-surface/[0.04] rounded-2xl p-3">
          <p class="text-xs font-semibold text-on-surface-variant uppercase mb-1">Parent</p>
          <p class="text-sm font-bold text-on-surface">{{ student.parentName }}</p>
        </div>
        <div class="bg-success/10 border border-success/20 rounded-2xl p-3">
          <p class="text-xs font-semibold text-success uppercase mb-1">{{ statLabel }}</p>
          <p class="text-2xl font-semibold text-success">{{ statValue }}</p>
        </div>
      </div>

      <div class="mt-4">
        <p class="text-xs font-semibold text-on-surface-variant uppercase mb-3">
          Session Breakdown
        </p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="chip in chips"
            :key="chip.key"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-semibold uppercase transition-all"
            :class="[
              chip.color,
              activeChip === chip.key
                ? 'ring-2 ring-offset-1 ring-offset-transparent scale-105'
                : 'opacity-80 hover:opacity-100',
            ]"
            :aria-pressed="activeChip === chip.key"
            @click="selectChip(chip.key)"
          >
            <span class="size-1.5 rounded-full" :class="chip.dot"></span>
            {{ chip.label }}
            <span class="font-semibold ml-0.5">{{ chip.count }}</span>
          </button>
        </div>
      </div>

      <div v-if="filteredSessions.length > 0" class="space-y-2 mt-4">
        <p class="text-xs font-semibold text-on-surface-variant uppercase">
          {{ activeChipLabel }} Sessions
        </p>
        <button
          v-for="session in filteredSessions"
          :key="session.id"
          class="w-full flex items-center gap-3 p-3 rounded-2xl bg-on-surface/[0.03] border border-on-surface/[0.05] hover:bg-on-surface/[0.06] transition-all text-left group"
          @click="emit('select-session', session)"
        >
          <div class="flex-1 min-w-0">
            <p class="text-sm font-bold text-on-surface">{{ formatTime(session.startTime) }}</p>
            <p class="text-xs text-on-surface-variant">
              <slot name="session-subtitle" :session="session">
                {{ statusLabel(session.status) }}
              </slot>
            </p>
          </div>
          <span
            class="text-xs font-semibold px-2 py-1 rounded-full border"
            :class="statusBadge(session.status)"
          >
            {{ statusLabel(session.status) }}
          </span>
          <span
            class="material-symbols-outlined text-sm text-on-surface-variant/40 group-hover:text-on-surface-variant transition-colors"
            >chevron_right</span
          >
        </button>
      </div>
      <div v-else-if="activeChip" class="text-center py-6 text-on-surface-variant text-sm mt-4">
        No sessions in this category.
      </div>
      <div v-else class="text-center py-6 text-on-surface-variant text-sm mt-4">
        {{ emptyText }}
      </div>
    </template>
  </BaseModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Session } from '@types'
import BaseDropdown from '@/components/BaseDropdown.vue'

interface DayData {
  label: string
  dateNum: number
  iso: string
  date: Date
  isToday: boolean
  isWeekend: boolean
  sessions: Session[]
}

const props = defineProps<{
  sessions: Session[]
  isAdmin?: boolean
}>()

const emit = defineEmits<{
  dayClick: [{ date: Date; sessions: Session[] }]
  sessionClick: [session: Session]
  reschedule: [{ session: Session; newStart: Date; newEnd: Date }]
}>()

const activeView = ref<'week' | 'month' | 'day'>(
  (localStorage.getItem('smc_calendar_view') as 'week' | 'month' | 'day') || 'week'
)

const offset = ref(0)
const currentDate = ref(new Date())

watch(activeView, () => {
  localStorage.setItem('smc_calendar_view', activeView.value)
  offset.value = 0 // Reset when changing view
})

const baseDate = computed(() => {
  const d = new Date(currentDate.value)
  d.setHours(0, 0, 0, 0)
  if (activeView.value === 'day') {
    d.setDate(d.getDate() + offset.value)
  } else if (activeView.value === 'week') {
    d.setDate(d.getDate() + offset.value * 7)
  } else if (activeView.value === 'month') {
    d.setMonth(d.getMonth() + offset.value)
  }
  return d
})

const displayMonthYear = computed(() => {
  const d = baseDate.value
  if (activeView.value === 'day') {
    return d.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    })
  } else {
    return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  }
})

const calendarDays = computed<DayData[]>(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  if (activeView.value === 'day') {
    const date = new Date(baseDate.value)
    const iso = date.toDateString()
    const isToday = iso === today.toDateString()
    const isWeekend = date.getDay() === 0 || date.getDay() === 6
    const dayLabels = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    const label = dayLabels[date.getDay()]

    const daySessions = props.sessions
      .filter((s: any) => new Date(s.startTime).toDateString() === iso)
      .sort((a: any, b: any) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime())

    return [
      { label, dateNum: date.getDate(), iso, date, isToday, isWeekend, sessions: daySessions },
    ]
  }

  if (activeView.value === 'week') {
    const d = baseDate.value
    const dayOfWeek = d.getDay() || 7
    const monday = new Date(d)
    monday.setDate(d.getDate() - dayOfWeek + 1)

    const dayLabels = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    return dayLabels.map((label, i) => {
      const date = new Date(monday)
      date.setDate(monday.getDate() + i)

      const iso = date.toDateString()
      const isToday = iso === today.toDateString()
      const isWeekend = i >= 5

      const daySessions = props.sessions
        .filter((s: any) => new Date(s.startTime).toDateString() === iso)
        .sort((a: any, b: any) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime())

      return {
        label,
        dateNum: date.getDate(),
        iso,
        date,
        isToday,
        isWeekend,
        sessions: daySessions,
      }
    })
  }

  // Month View
  const d = baseDate.value
  const year = d.getFullYear()
  const month = d.getMonth()

  const firstDay = new Date(year, month, 1)
  const startDayOfWeek = firstDay.getDay() || 7

  const gridStart = new Date(firstDay)
  gridStart.setDate(firstDay.getDate() - startDayOfWeek + 1)

  const lastDay = new Date(year, month + 1, 0)
  const endDayOfWeek = lastDay.getDay() || 7

  const gridEnd = new Date(lastDay)
  gridEnd.setDate(lastDay.getDate() + (7 - endDayOfWeek))

  const days: DayData[] = []
  const current = new Date(gridStart)
  const dayLabels = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']

  while (current <= gridEnd) {
    const date = new Date(current)
    const iso = date.toDateString()
    const isToday = iso === today.toDateString()
    const dow = date.getDay()
    const isWeekend = dow === 0 || dow === 6
    const label = dayLabels[(dow || 7) - 1]

    const daySessions = props.sessions
      .filter((s: any) => new Date(s.startTime).toDateString() === iso)
      .sort((a: any, b: any) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime())

    days.push({
      label,
      dateNum: date.getDate(),
      iso,
      date,
      isToday,
      isWeekend,
      sessions: daySessions,
    })
    current.setDate(current.getDate() + 1)
  }
  return days
})

const formatTime = function (iso: string) {
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

const themeStatusStyles = (status: string) => {
  const map: Record<string, string> = {
    scheduled:
      'bg-success-container/60 border-success text-on-success-container dark:bg-success/10 dark:border-success/30 dark:text-success',
    completed:
      'bg-success-container/60 border-success text-on-success-container dark:bg-success/10 dark:border-success/30 dark:text-success',
    pending_teacher:
      'bg-warning-container/60 border-warning text-on-warning-container dark:bg-warning/10 dark:border-warning/30 dark:text-warning',
    pending_student:
      'bg-primary-container/60 border-primary text-primary dark:bg-primary/10 dark:border-primary/30',
    pending_admin:
      'bg-tertiary-container/60 border-tertiary text-on-tertiary-container dark:bg-tertiary/10 dark:border-tertiary/30 dark:text-tertiary',
    pending_verification:
      'bg-tertiary-container/60 border-tertiary text-on-tertiary-container dark:bg-tertiary/10 dark:border-tertiary/30 dark:text-tertiary',
    overdue:
      'bg-error-container/60 border-error text-on-error-container dark:bg-error/15 dark:border-error/40 dark:text-error',
    overdue_rejected:
      'bg-error-container/60 border-error text-on-error-container dark:bg-error/15 dark:border-error/40 dark:text-error',
    rejected:
      'bg-error-container/50 border-error text-on-error-container dark:bg-error/10 dark:border-error/25 dark:text-error',
    cancelled:
      'bg-surface-container/50 border-outline-variant text-on-surface-variant dark:bg-surface-container-high/10 dark:border-outline-variant/20',
  }
  return map[status] ?? 'bg-surface-container-low border-outline-variant text-on-surface-variant'
}

const statusLabel = function (status: string): string {
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

const statusDotColor = function (status: string): string {
  const map: Record<string, string> = {
    scheduled: 'bg-success',
    completed: 'bg-success',
    pending_teacher: 'bg-warning',
    pending_student: 'bg-primary',
    pending_admin: 'bg-tertiary',
    pending_verification: 'bg-tertiary',
    overdue: 'bg-error',
    overdue_rejected: 'bg-error',
    rejected: 'bg-error',
    cancelled: 'bg-surface-container-high',
  }
  return map[status] ?? 'bg-surface-container-high'
}

const previous = function () {
  offset.value--
}
const next = function () {
  offset.value++
}
const resetToToday = function () {
  currentDate.value = new Date()
  offset.value = 0
}

// Drag & Drop
const onDragStart = (event: DragEvent, session: Session) => {
  if (!props.isAdmin) return
  event.dataTransfer?.setData('application/json', JSON.stringify(session))
  event.dataTransfer!.effectAllowed = 'move'
}

const onDrop = (event: DragEvent, targetDate: Date) => {
  if (!props.isAdmin) return
  const rawData = event.dataTransfer?.getData('application/json')
  if (!rawData) return
  const session = JSON.parse(rawData) as Session

  const oldStart = new Date(session.startTime)
  const oldEnd = new Date(session.endTime)
  const durationMs = oldEnd.getTime() - oldStart.getTime()

  const newStart = new Date(targetDate)
  newStart.setHours(oldStart.getHours(), oldStart.getMinutes(), 0, 0)

  const newEnd = new Date(newStart.getTime() + durationMs)

  emit('reschedule', { session, newStart, newEnd })
}

// Session Overflow Popover
const overflowOpenDay = ref<string | null>(null)
const overflowSessions = ref<Session[]>([])
const toggleOverflow = (dayIso: string, sessions: Session[]) => {
  if (overflowOpenDay.value === dayIso) {
    overflowOpenDay.value = null
  } else {
    overflowOpenDay.value = dayIso
    overflowSessions.value = sessions
  }
}

// Get sessions up to limit depending on view
const limitForView = computed(() => {
  if (activeView.value === 'month') return 3
  return 4
})

// Legend lives behind a button rather than as a wrapping row: on a phone the
// eight entries wrapped to three lines and pushed the grid off screen.
const legendOpen = ref(false)
const legendItems = [
  { dot: 'bg-success', text: 'text-success', label: 'Confirmed' },
  { dot: 'bg-success', text: 'text-success', label: 'Done' },
  { dot: 'bg-warning', text: 'text-warning', label: 'Aw. Teacher' },
  { dot: 'bg-primary', text: 'text-primary', label: 'Countered' },
  { dot: 'bg-tertiary', text: 'text-tertiary', label: 'Aw. Admin' },
  { dot: 'bg-tertiary', text: 'text-tertiary', label: 'In Review' },
  { dot: 'bg-error', text: 'text-error', label: 'Overdue' },
  { dot: 'bg-error', text: 'text-error', label: 'Proof Rej.' },
]

const viewOptions = [
  { value: 'day', label: 'Day' },
  { value: 'week', label: 'Week' },
  { value: 'month', label: 'Month' },
]
</script>

<template>
  <div
    class="bg-surface-container-lowest liquid-glass rounded-3xl p-4 sm:p-6 border border-outline-variant shadow-xl transition-colors duration-300 flex flex-col h-full space-y-4 sm:space-y-6"
  >
    <!-- Calendar Controls -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex items-center gap-3">
        <h3 class="text-lg sm:text-2xl font-semibold text-on-surface tracking-tight">
          {{ displayMonthYear }}
        </h3>
        <button
          v-if="offset !== 0"
          class="px-3 py-1.5 rounded-full bg-primary-container dark:bg-primary/10 text-primary text-xs font-semibold uppercase hover:bg-primary-container dark:hover:bg-primary/20 transition-colors"
          @click="resetToToday"
        >
          Today
        </button>
      </div>

      <!-- View Toggle & Navigation -->
      <div class="flex items-center gap-2 sm:gap-3">
        <!-- Phone: the three views collapse into the shared dropdown. -->
        <div class="sm:hidden flex-1">
          <BaseDropdown v-model="activeView" size="sm" :options="viewOptions" />
        </div>

        <!-- Tablet and up: segmented control. rounded-full on the track so it
             matches the pill it contains — a rounded-2xl track left visible
             corner gaps around the selected pill. -->
        <div
          class="hidden sm:flex bg-surface-container-high p-1 rounded-full border border-outline-variant"
        >
          <button
            v-for="view in ['day', 'week', 'month'] as const"
            :key="view"
            class="px-4 py-1.5 rounded-full text-xs font-semibold uppercase transition-all"
            :class="
              activeView === view
                ? 'bg-primary text-on-primary shadow-md'
                : 'text-on-surface-variant hover:text-on-surface'
            "
            @click="activeView = view"
          >
            {{ view }}
          </button>
        </div>

        <!-- Pagination sits as two standalone buttons rather than sharing one
             bordered track with each other. -->
        <button class="icon-btn rounded-full border border-outline-variant" @click="previous">
          <span class="material-symbols-outlined text-lg">chevron_left</span>
        </button>
        <button class="icon-btn rounded-full border border-outline-variant" @click="next">
          <span class="material-symbols-outlined text-lg">chevron_right</span>
        </button>

        <!-- Legend, on demand -->
        <div class="relative">
          <button
            class="icon-btn rounded-full border border-outline-variant"
            aria-label="Show status legend"
            @click="legendOpen = !legendOpen"
          >
            <span class="material-symbols-outlined text-lg">palette</span>
          </button>
          <div
            v-if="legendOpen"
            class="absolute right-0 top-full z-30 mt-2 w-52 rounded-2xl border border-outline-variant bg-surface-container p-3 shadow-2xl"
          >
            <div
              class="mb-2 flex items-center justify-between border-b border-outline-variant pb-1.5"
            >
              <span class="text-xs font-semibold uppercase text-on-surface">Legend</span>
              <button
                class="text-on-surface-variant hover:text-on-surface"
                @click="legendOpen = false"
              >
                <span class="material-symbols-outlined text-sm">close</span>
              </button>
            </div>
            <div class="grid grid-cols-1 gap-1.5">
              <span
                v-for="item in legendItems"
                :key="item.label"
                class="flex items-center gap-2 text-xs font-bold"
                :class="item.text"
              >
                <span class="size-2 shrink-0 rounded-full" :class="item.dot"></span>{{ item.label }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Calendar Grid -->
    <div
      class="grid flex-1 gap-2 sm:gap-3"
      :class="{
        'grid-cols-1': activeView === 'day',
        'grid-cols-1 sm:grid-cols-7': activeView === 'week' || activeView === 'month',
      }"
    >
      <div
        v-for="day in calendarDays"
        :key="day.iso"
        class="flex h-full flex-row sm:flex-col bg-surface-container border border-outline-variant rounded-2xl overflow-hidden hover:border-outline dark:hover:border-outline transition-colors group relative"
        :class="{ 'ring-2 ring-success border-transparent': day.isToday }"
        @dragover.prevent
        @drop="onDrop($event, day.date)"
        @click="emit('dayClick', { date: day.date, sessions: day.sessions })"
      >
        <!-- Day Header -->
        <div
          class="flex w-16 shrink-0 flex-col items-center justify-center border-r p-2 text-center border-outline-variant sm:w-auto sm:border-b sm:border-r-0"
          :class="day.isToday ? 'bg-success/10' : 'bg-surface-container-high'"
        >
          <p
            class="text-xs font-semibold uppercase mb-1"
            :class="
              day.isToday
                ? 'text-success'
                : day.isWeekend
                  ? 'text-on-surface-variant/50 dark:text-on-surface-variant/40'
                  : 'text-on-surface-variant'
            "
          >
            {{ day.label }}
          </p>
          <div
            class="size-8 rounded-full flex items-center justify-center mx-auto text-sm font-semibold transition-all"
            :class="day.isToday ? 'bg-primary text-on-primary shadow-e1' : 'text-on-surface'"
          >
            {{ day.dateNum }}
          </div>
        </div>

        <!-- Session List -->
        <div
          class="relative flex-1 space-y-1.5 p-1.5 min-h-[64px]"
          :class="activeView === 'month' ? 'sm:min-h-[90px]' : 'sm:min-h-[120px]'"
        >
          <div
            v-for="session in day.sessions.slice(0, limitForView)"
            :key="session.id"
            :draggable="isAdmin ? 'true' : 'false'"
            class="px-2 py-1.5 rounded-lg border-l-[3px] shadow-sm cursor-pointer hover:brightness-95 dark:hover:brightness-125 active:scale-95 transition-all select-none"
            :class="themeStatusStyles(session.status)"
            @dragstart="onDragStart($event, session)"
            @click.stop="emit('sessionClick', session)"
          >
            <div class="flex items-center gap-1 mb-0.5">
              <span
                class="size-1.5 rounded-full shrink-0"
                :class="statusDotColor(session.status)"
              ></span>
              <span class="font-semibold text-xs truncate">{{
                formatTime(session.startTime)
              }}</span>
            </div>
            <p class="text-xs font-bold uppercase opacity-75 truncate">
              {{ statusLabel(session.status) }}
            </p>
          </div>

          <!-- Session Overflow Chip -->
          <div v-if="day.sessions.length > limitForView" class="mt-1">
            <button
              class="w-full text-center py-1 text-xs font-semibold uppercase text-primary bg-primary/10 hover:bg-primary/20 rounded-md transition-colors"
              @click.stop="toggleOverflow(day.iso, day.sessions)"
            >
              +{{ day.sessions.length - limitForView }} more
            </button>
          </div>

          <!-- Empty state hover hint -->
          <div
            v-if="day.sessions.length === 0"
            class="absolute inset-x-0 bottom-2 flex justify-center opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <span
              class="size-7 rounded-full bg-surface-container-high shadow flex items-center justify-center text-on-surface-variant"
            >
              <span class="material-symbols-outlined text-sm">add</span>
            </span>
          </div>
        </div>

        <!-- Overflow Popover -->
        <div
          v-if="overflowOpenDay === day.iso"
          class="absolute z-10 bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 bg-surface-container-lowest border border-outline-variant rounded-2xl p-3 shadow-2xl space-y-2 max-h-60 overflow-y-auto"
          @click.stop
        >
          <div class="flex items-center justify-between border-b border-outline-variant pb-1.5">
            <span class="text-xs font-semibold uppercase text-on-surface">All Sessions</span>
            <button
              class="text-on-surface-variant hover:text-on-surface"
              @click="overflowOpenDay = null"
            >
              <span class="material-symbols-outlined text-sm">close</span>
            </button>
          </div>
          <div
            v-for="session in day.sessions"
            :key="session.id"
            class="px-2 py-1.5 rounded-lg border-l-[3px] shadow-sm cursor-pointer hover:brightness-95 dark:hover:brightness-125 transition-all"
            :class="themeStatusStyles(session.status)"
            @click.stop="emit('sessionClick', session); overflowOpenDay = null"
          >
            <div class="flex items-center gap-1 mb-0.5">
              <span
                class="size-1.5 rounded-full shrink-0"
                :class="statusDotColor(session.status)"
              ></span>
              <span class="font-semibold text-xs">{{ formatTime(session.startTime) }}</span>
            </div>
            <p class="text-xs font-bold uppercase opacity-75">
              {{ statusLabel(session.status) }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

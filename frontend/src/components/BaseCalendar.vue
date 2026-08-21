<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Session } from '@types'

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
    return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
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

    return [{ label, dateNum: date.getDate(), iso, date, isToday, isWeekend, sessions: daySessions }]
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

      return { label, dateNum: date.getDate(), iso, date, isToday, isWeekend, sessions: daySessions }
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
      
    days.push({ label, dateNum: date.getDate(), iso, date, isToday, isWeekend, sessions: daySessions })
    current.setDate(current.getDate() + 1)
  }
  return days
})

const formatTime = function(iso: string) {
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

const themeStatusStyles = (status: string) => {
  const map: Record<string, string> = {
    scheduled:
      'bg-teal-100/60 border-teal-300 text-teal-800 dark:bg-teal-500/10 dark:border-teal-500/30 dark:text-teal-300',
    completed:
      'bg-emerald-100/60 border-emerald-300 text-emerald-800 dark:bg-emerald-500/10 dark:border-emerald-500/30 dark:text-emerald-300',
    pending_teacher:
      'bg-amber-100/60 border-amber-300 text-amber-800 dark:bg-amber-500/10 dark:border-amber-500/30 dark:text-amber-300',
    pending_student:
      'bg-primary-container/60 border-primary text-primary dark:bg-primary/10 dark:border-primary/30 dark:text-primary',
    pending_admin:
      'bg-blue-100/60 border-blue-300 text-blue-800 dark:bg-blue-500/10 dark:border-blue-500/30 dark:text-blue-300',
    pending_verification:
      'bg-violet-100/60 border-violet-300 text-violet-800 dark:bg-violet-500/10 dark:border-violet-500/30 dark:text-violet-300',
    overdue:
      'bg-rose-100/60 border-rose-300 text-rose-800 dark:bg-rose-500/15 dark:border-rose-500/40 dark:text-rose-300',
    overdue_rejected:
      'bg-red-100/60 border-red-400 text-red-800 dark:bg-red-500/15 dark:border-red-500/40 dark:text-red-300',
    rejected:
      'bg-red-100/50 border-red-300 text-red-800 dark:bg-red-500/10 dark:border-red-500/25 dark:text-red-400',
    cancelled:
      'bg-zinc-100/50 border-zinc-300 text-zinc-600 dark:bg-zinc-500/10 dark:border-zinc-500/20 dark:text-zinc-400',
  }
  return (
    map[status] ??
    'bg-surface-container-low border-outline-variant text-on-surface-variant dark:bg-surface-container-low dark:border-outline-variant dark:text-on-surface-variant'
  )
}

const statusLabel = function(status: string): string  {
  const map: Record<string, string> = {
    scheduled:            'Confirmed',
    completed:            'Done',
    pending_teacher:      'Aw. Teacher',
    pending_student:      'Countered',
    pending_admin:        'Aw. Admin',
    pending_verification: 'In Review',
    overdue:              'Overdue',
    overdue_rejected:     'Proof Rej.',
    rejected:             'Declined',
    cancelled:            'Cancelled',
  }
  return map[status] ?? status
}

const statusDotColor = function(status: string): string  {
  const map: Record<string, string> = {
    scheduled:            'bg-teal-400',
    completed:            'bg-emerald-400',
    pending_teacher:      'bg-amber-400',
    pending_student:      'bg-primary',
    pending_admin:        'bg-blue-400',
    pending_verification: 'bg-violet-400',
    overdue:              'bg-rose-400',
    overdue_rejected:     'bg-red-500',
    rejected:             'bg-red-400',
    cancelled:            'bg-zinc-400',
  }
  return map[status] ?? 'bg-zinc-400'
}

const previous = function() { offset.value-- }
const next = function() { offset.value++ }
const resetToToday = function() { currentDate.value = new Date(); offset.value = 0 }

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
</script>

<template>
  <div
    class="bg-surface-container-lowest dark:bg-surface-container-lowest liquid-glass rounded-3xl p-6 border border-outline-variant dark:border-outline-variant shadow-xl transition-colors duration-300 flex flex-col h-full space-y-6 overflow-x-auto custom-scrollbar"
  >
    <!-- Calendar Controls -->
    <div class="flex items-center justify-between min-w-[700px]">
      <div class="flex items-center gap-4">
        <h3 class="text-2xl font-black text-on-surface dark:text-on-surface tracking-tight min-w-[200px]">
          {{ displayMonthYear }}
        </h3>
        <button
          v-if="offset !== 0"
          class="px-3 py-1.5 rounded-full bg-primary-container dark:bg-primary/10 text-primary dark:text-primary text-[10px] font-black uppercase tracking-wider hover:bg-primary-container dark:hover:bg-primary/20 transition-colors"
          @click="resetToToday"
        >
          Today
        </button>
      </div>

      <!-- View Toggle & Navigation -->
      <div class="flex items-center gap-4">
        <!-- View Toggle Buttons -->
        <div class="flex bg-surface-container-high dark:bg-surface-container-high p-1 rounded-2xl border border-outline-variant dark:border-outline-variant">
          <button
            v-for="view in (['day', 'week', 'month'] as const)"
            :key="view"
            class="px-4 py-1.5 rounded-xl text-xs font-black uppercase tracking-wider transition-all"
            :class="activeView === view 
              ? 'bg-primary text-on-surface shadow-md' 
              : 'text-on-surface-variant hover:text-on-surface'"
            @click="activeView = view"
          >
            {{ view }}
          </button>
        </div>

        <div
          class="flex items-center gap-2 bg-surface-container-high dark:bg-surface-container-high p-1 rounded-2xl border border-outline-variant dark:border-outline-variant"
        >
          <button
            class="w-10 h-10 rounded-xl flex items-center justify-center text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-surface-container-high dark:hover:bg-on-surface/10 shadow-sm dark:shadow-none transition-all"
            @click="previous"
          >
            <span class="material-symbols-outlined text-lg">chevron_left</span>
          </button>
          <button
            class="w-10 h-10 rounded-xl flex items-center justify-center text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-surface-container-high dark:hover:bg-on-surface/10 shadow-sm dark:shadow-none transition-all"
            @click="next"
          >
            <span class="material-symbols-outlined text-lg">chevron_right</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Calendar Grid -->
    <div 
      class="grid gap-3 min-w-[700px] flex-1"
      :class="{
        'grid-cols-1': activeView === 'day',
        'grid-cols-7': activeView === 'week' || activeView === 'month'
      }"
    >
      <div
        v-for="day in calendarDays"
        :key="day.iso"
        class="flex flex-col h-full bg-surface-container dark:bg-surface-container border border-outline-variant dark:border-outline-variant rounded-2xl overflow-hidden hover:border-outline dark:hover:border-outline transition-colors group relative"
        :class="{ 'ring-2 ring-teal-400 border-transparent': day.isToday }"
        @dragover.prevent
        @drop="onDrop($event, day.date)"
        @click="emit('dayClick', { date: day.date, sessions: day.sessions })"
      >
        <!-- Day Header -->
        <div
          class="p-2.5 text-center border-b border-outline-variant dark:border-outline-variant"
          :class="
            day.isToday
              ? 'bg-teal-500/10 dark:bg-teal-500/10'
              : 'bg-surface-container-high dark:bg-surface-container-high'
          "
        >
          <p
            class="text-[9px] font-black uppercase tracking-widest mb-1"
            :class="
              day.isToday
                ? 'text-teal-600 dark:text-teal-400'
                : day.isWeekend
                  ? 'text-on-surface-variant/50 dark:text-on-surface-variant/40'
                  : 'text-on-surface-variant dark:text-on-surface-variant'
            "
          >
            {{ day.label }}
          </p>
          <div
            class="w-8 h-8 rounded-full flex items-center justify-center mx-auto text-sm font-black transition-all"
            :class="
              day.isToday
                ? 'bg-primary text-on-primary shadow-e1'
                : 'text-on-surface dark:text-on-surface'
            "
          >
            {{ day.dateNum }}
          </div>
        </div>

        <!-- Session List -->
        <div class="p-1.5 space-y-1.5 flex-1 relative" :class="activeView === 'month' ? 'min-h-[90px]' : 'min-h-[120px]'">
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
              <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="statusDotColor(session.status)"></span>
              <span class="font-black text-[10px] truncate">{{ formatTime(session.startTime) }}</span>
            </div>
            <p class="text-[9px] font-bold uppercase tracking-wider opacity-75 truncate">
              {{ statusLabel(session.status) }}
            </p>
          </div>

          <!-- Session Overflow Chip -->
          <div 
            v-if="day.sessions.length > limitForView" 
            class="mt-1"
          >
            <button
              class="w-full text-center py-1 text-[9px] font-black uppercase tracking-wider text-primary dark:text-primary bg-primary/10 hover:bg-primary/20 rounded-md transition-colors"
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
              class="w-7 h-7 rounded-full bg-surface-container-high dark:bg-surface-container-high shadow flex items-center justify-center text-on-surface-variant dark:text-on-surface-variant"
            >
              <span class="material-symbols-outlined text-sm">add</span>
            </span>
          </div>
        </div>

        <!-- Overflow Popover -->
        <div
          v-if="overflowOpenDay === day.iso"
          class="absolute z-10 bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-64 bg-surface-container-lowest dark:bg-surface-container-lowest border border-outline-variant dark:border-outline-variant rounded-2xl p-3 shadow-2xl space-y-2 max-h-60 overflow-y-auto"
          @click.stop
        >
          <div class="flex items-center justify-between border-b border-outline-variant pb-1.5">
            <span class="text-xs font-black uppercase tracking-wider text-on-surface">All Sessions</span>
            <button class="text-on-surface-variant hover:text-on-surface" @click="overflowOpenDay = null">
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
              <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="statusDotColor(session.status)"></span>
              <span class="font-black text-[10px]">{{ formatTime(session.startTime) }}</span>
            </div>
            <p class="text-[9px] font-bold uppercase tracking-wider opacity-75">
              {{ statusLabel(session.status) }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Legend -->
    <div class="flex flex-wrap items-center gap-x-4 gap-y-1.5 pt-3 border-t border-outline-variant dark:border-outline-variant min-w-[700px]">
      <span class="text-[9px] font-black uppercase tracking-widest text-on-surface-variant mr-1">Legend</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-teal-600 dark:text-teal-400"><span class="w-2 h-2 rounded-full bg-teal-400 shrink-0"></span>Confirmed</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-emerald-600 dark:text-emerald-400"><span class="w-2 h-2 rounded-full bg-emerald-400 shrink-0"></span>Done</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-amber-600 dark:text-amber-400"><span class="w-2 h-2 rounded-full bg-amber-400 shrink-0"></span>Aw. Teacher</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-primary dark:text-primary"><span class="w-2 h-2 rounded-full bg-primary shrink-0"></span>Countered</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-blue-600 dark:text-blue-400"><span class="w-2 h-2 rounded-full bg-blue-400 shrink-0"></span>Aw. Admin</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-violet-600 dark:text-violet-400"><span class="w-2 h-2 rounded-full bg-violet-400 shrink-0"></span>In Review</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-rose-600 dark:text-rose-400"><span class="w-2 h-2 rounded-full bg-rose-400 shrink-0"></span>Overdue</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-red-600 dark:text-red-400"><span class="w-2 h-2 rounded-full bg-red-500 shrink-0"></span>Proof Rej.</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Session } from '../types'

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
}>()

const emit = defineEmits<{
  dayClick: [{ date: Date; sessions: Session[] }]
  sessionClick: [session: Session]
}>()

const weekOffset = ref(0)
const currentDate = ref(new Date())

const displayMonthYear = computed(() => {
  const d = new Date(currentDate.value)
  d.setDate(d.getDate() + weekOffset.value * 7)
  return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
})

const weekDays = computed<DayData[]>(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const baseDate = new Date(currentDate.value)
  baseDate.setHours(0, 0, 0, 0)

  const dayOfWeek = baseDate.getDay() || 7
  const monday = new Date(baseDate)
  monday.setDate(baseDate.getDate() - dayOfWeek + 1 + weekOffset.value * 7)

  const dayLabels = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']

  return dayLabels.map((label, i) => {
    const date = new Date(monday)
    date.setDate(monday.getDate() + i)

    const iso = date.toDateString()
    const isToday = iso === today.toDateString()
    const isWeekend = i >= 5

    const daySessions = props.sessions
      .filter((s) => new Date(s.startTime).toDateString() === iso)
      .sort((a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime())

    return { label, dateNum: date.getDate(), iso, date, isToday, isWeekend, sessions: daySessions }
  })
})

function formatTime(iso: string) {
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
      'bg-orange-100/60 border-orange-300 text-orange-800 dark:bg-orange-500/10 dark:border-orange-500/30 dark:text-orange-300',
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

function statusLabel(status: string): string {
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

function statusDotColor(status: string): string {
  const map: Record<string, string> = {
    scheduled:            'bg-teal-400',
    completed:            'bg-emerald-400',
    pending_teacher:      'bg-amber-400',
    pending_student:      'bg-orange-400',
    pending_admin:        'bg-blue-400',
    pending_verification: 'bg-violet-400',
    overdue:              'bg-rose-400',
    overdue_rejected:     'bg-red-500',
    rejected:             'bg-red-400',
    cancelled:            'bg-zinc-400',
  }
  return map[status] ?? 'bg-zinc-400'
}

function previousWeek() { weekOffset.value-- }
function nextWeek() { weekOffset.value++ }
function resetToToday() { currentDate.value = new Date(); weekOffset.value = 0 }
</script>

<template>
  <div
    class="bg-surface-container-lowest dark:bg-surface-container-lowest liquid-glass rounded-3xl p-6 border border-outline-variant dark:border-outline-variant shadow-xl transition-colors duration-300 flex flex-col h-full space-y-6 overflow-x-auto custom-scrollbar"
  >
    <!-- Calendar Controls -->
    <div class="flex items-center justify-between min-w-[700px]">
      <div class="flex items-center gap-4">
        <h3 class="text-2xl font-black text-on-surface dark:text-on-surface tracking-tight">
          {{ displayMonthYear }}
        </h3>
        <button
          v-if="weekOffset !== 0"
          class="px-3 py-1.5 rounded-full bg-orange-100 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400 text-[10px] font-black uppercase tracking-wider hover:bg-orange-200 dark:hover:bg-orange-500/20 transition-colors"
          @click="resetToToday"
        >
          Today
        </button>
      </div>

      <div
        class="flex items-center gap-2 bg-surface-container-high dark:bg-surface-container-high p-1 rounded-2xl border border-outline-variant dark:border-outline-variant"
      >
        <button
          class="w-10 h-10 rounded-xl flex items-center justify-center text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-surface-container-high dark:hover:bg-white/10 shadow-sm dark:shadow-none transition-all"
          @click="previousWeek"
        >
          <span class="material-symbols-outlined text-lg">chevron_left</span>
        </button>
        <button
          class="w-10 h-10 rounded-xl flex items-center justify-center text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface hover:bg-surface-container-high dark:hover:bg-white/10 shadow-sm dark:shadow-none transition-all"
          @click="nextWeek"
        >
          <span class="material-symbols-outlined text-lg">chevron_right</span>
        </button>
      </div>
    </div>

    <!-- Calendar Grid -->
    <div class="grid grid-cols-7 gap-3 min-w-[700px] flex-1">
      <div
        v-for="day in weekDays"
        :key="day.iso"
        class="flex flex-col h-full bg-surface-container dark:bg-surface-container border border-outline-variant dark:border-outline-variant rounded-2xl overflow-hidden hover:border-outline dark:hover:border-outline transition-colors group"
        :class="{ 'ring-2 ring-teal-400 border-transparent': day.isToday }"
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
                ? 'bg-gradient-to-br from-teal-500 to-teal-600 text-white shadow-md shadow-teal-500/20'
                : 'text-on-surface dark:text-on-surface'
            "
          >
            {{ day.dateNum }}
          </div>
        </div>

        <!-- Session List -->
        <div class="p-1.5 space-y-1.5 flex-1 relative min-h-[120px]">
          <div
            v-for="session in day.sessions"
            :key="session.id"
            class="px-2 py-1.5 rounded-lg border-l-[3px] shadow-sm cursor-pointer hover:brightness-95 dark:hover:brightness-125 active:scale-95 transition-all select-none"
            :class="themeStatusStyles(session.status)"
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
      </div>
    </div>

    <!-- Legend -->
    <div class="flex flex-wrap items-center gap-x-4 gap-y-1.5 pt-3 border-t border-outline-variant dark:border-outline-variant min-w-[700px]">
      <span class="text-[9px] font-black uppercase tracking-widest text-on-surface-variant mr-1">Legend</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-teal-600 dark:text-teal-400"><span class="w-2 h-2 rounded-full bg-teal-400 shrink-0"></span>Confirmed</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-emerald-600 dark:text-emerald-400"><span class="w-2 h-2 rounded-full bg-emerald-400 shrink-0"></span>Done</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-amber-600 dark:text-amber-400"><span class="w-2 h-2 rounded-full bg-amber-400 shrink-0"></span>Aw. Teacher</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-orange-600 dark:text-orange-400"><span class="w-2 h-2 rounded-full bg-orange-400 shrink-0"></span>Countered</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-blue-600 dark:text-blue-400"><span class="w-2 h-2 rounded-full bg-blue-400 shrink-0"></span>Aw. Admin</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-violet-600 dark:text-violet-400"><span class="w-2 h-2 rounded-full bg-violet-400 shrink-0"></span>In Review</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-rose-600 dark:text-rose-400"><span class="w-2 h-2 rounded-full bg-rose-400 shrink-0"></span>Overdue</span>
      <span class="flex items-center gap-1 text-[9px] font-bold text-red-600 dark:text-red-400"><span class="w-2 h-2 rounded-full bg-red-500 shrink-0"></span>Proof Rej.</span>
    </div>
  </div>
</template>

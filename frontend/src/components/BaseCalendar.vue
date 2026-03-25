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

  const dayOfWeek = baseDate.getDay() || 7 // Sunday = 7
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
      .filter((s) => {
        return new Date(s.startTime).toDateString() === iso
      })
      .sort((a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime())

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
})

function formatTime(iso: string) {
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

const themeStatusStyles = (status: string) => {
  const map: Record<string, string> = {
    scheduled:
      'bg-orange-100/50 border-orange-200 text-orange-800 dark:bg-orange-500/10 dark:border-orange-500/20 dark:text-orange-300',
    completed:
      'bg-emerald-100/50 border-emerald-200 text-emerald-800 dark:bg-emerald-500/10 dark:border-emerald-500/20 dark:text-emerald-300',
    pending_teacher:
      'bg-amber-100/50 border-amber-200 text-amber-800 dark:bg-amber-500/10 dark:border-amber-500/20 dark:text-amber-300',
    pending_admin:
      'bg-blue-100/50 border-blue-200 text-blue-800 dark:bg-blue-500/10 dark:border-blue-500/20 dark:text-blue-300',
    rejected:
      'bg-red-100/50 border-red-200 text-red-800 dark:bg-red-500/10 dark:border-red-500/20 dark:text-red-300',
    cancelled:
      'bg-zinc-100/50 border-zinc-200 text-zinc-600 dark:bg-zinc-500/10 dark:border-zinc-500/20 dark:text-zinc-400',
  }
  return (
    map[status] ??
    'bg-zinc-50 border-zinc-200 text-zinc-500 dark:bg-white/5 dark:border-white/10 dark:text-zinc-400'
  )
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    scheduled: 'Confirmed',
    completed: 'Done',
    pending_teacher: 'Aw. Teacher',
    pending_admin: 'Aw. Admin',
    rejected: 'Declined',
    cancelled: 'Cancelled',
  }
  return map[status] ?? status
}

function previousWeek() {
  weekOffset.value--
}

function nextWeek() {
  weekOffset.value++
}

function resetToToday() {
  currentDate.value = new Date()
  weekOffset.value = 0
}
</script>

<template>
  <div
    class="bg-white dark:bg-black/20 liquid-glass rounded-3xl p-6 border border-zinc-200 dark:border-white/5 shadow-xl transition-colors duration-300 flex flex-col h-full space-y-6 overflow-x-auto custom-scrollbar"
  >
    <!-- Calendar Controls -->
    <div class="flex items-center justify-between min-w-[700px]">
      <div class="flex items-center gap-4">
        <h3 class="text-2xl font-black text-zinc-900 dark:text-white tracking-tight">
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
        class="flex items-center gap-2 bg-zinc-100 dark:bg-white/5 p-1 rounded-2xl border border-zinc-200 dark:border-white/5"
      >
        <button
          class="w-10 h-10 rounded-xl flex items-center justify-center text-zinc-500 dark:text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white hover:bg-white dark:hover:bg-white/10 shadow-sm dark:shadow-none transition-all"
          @click="previousWeek"
        >
          <span class="material-symbols-outlined text-lg">chevron_left</span>
        </button>
        <button
          class="w-10 h-10 rounded-xl flex items-center justify-center text-zinc-500 dark:text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white hover:bg-white dark:hover:bg-white/10 shadow-sm dark:shadow-none transition-all"
          @click="nextWeek"
        >
          <span class="material-symbols-outlined text-lg">chevron_right</span>
        </button>
      </div>
    </div>

    <!-- Calendar Grid -->
    <div class="grid grid-cols-7 gap-4 min-w-[700px] flex-1">
      <div
        v-for="day in weekDays"
        :key="day.iso"
        class="flex flex-col h-full bg-zinc-50 dark:bg-white/[0.02] border border-zinc-200 dark:border-white/5 rounded-2xl overflow-hidden hover:border-zinc-300 dark:hover:border-white/10 transition-colors cursor-pointer group"
        :class="{ 'ring-2 ring-orange-400 border-transparent': day.isToday }"
        @click="emit('dayClick', { date: day.date, sessions: day.sessions })"
      >
        <!-- Day Header -->
        <div
          class="p-3 text-center border-b border-zinc-200 dark:border-white/5"
          :class="
            day.isToday ? 'bg-orange-50 dark:bg-orange-500/10' : 'bg-zinc-100 dark:bg-black/20'
          "
        >
          <p
            class="text-[10px] font-black uppercase tracking-widest mb-1"
            :class="
              day.isToday
                ? 'text-orange-600 dark:text-orange-400'
                : day.isWeekend
                  ? 'text-zinc-400 dark:text-zinc-600'
                  : 'text-zinc-600 dark:text-zinc-400'
            "
          >
            {{ day.label }}
          </p>
          <div
            class="w-9 h-9 rounded-full flex items-center justify-center mx-auto text-sm font-black transition-all"
            :class="
              day.isToday
                ? 'bg-gradient-to-br from-orange-500 to-orange-600 text-white shadow-md shadow-orange-500/20'
                : 'text-zinc-900 dark:text-zinc-300'
            "
          >
            {{ day.dateNum }}
          </div>
        </div>

        <!-- Session List -->
        <div class="p-2 space-y-2 flex-1 relative min-h-[120px]">
          <div
            v-for="session in day.sessions"
            :key="session.id"
            class="px-2.5 py-2 rounded-xl border-l-[3px] shadow-sm transform group-hover:translate-x-0.5 transition-transform"
            :class="themeStatusStyles(session.status)"
          >
            <div class="flex items-center justify-between mb-0.5">
              <span class="font-black text-[11px]">{{ formatTime(session.startTime) }}</span>
            </div>
            <p class="text-[9px] font-bold uppercase tracking-wider opacity-80 truncate">
              {{ statusLabel(session.status) }}
            </p>
          </div>

          <!-- Empty State Add Button -->
          <div
            class="absolute inset-x-0 bottom-2 flex justify-center opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <span
              class="w-8 h-8 rounded-full bg-white dark:bg-zinc-800 shadow flex items-center justify-center text-zinc-500 dark:text-zinc-400 dark:text-zinc-500"
            >
              <span class="material-symbols-outlined text-sm">add</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<template>
  <div class="space-y-4">
    <!-- Week Navigation -->
    <div class="flex items-center justify-between">
      <button
        @click="weekOffset--"
        class="flex items-center gap-1.5 px-4 py-2 rounded-2xl bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white border border-white/5 transition-all text-sm font-medium"
      >
        <span class="material-symbols-outlined text-lg">chevron_left</span>
        Prev
      </button>
      <div class="text-center">
        <p class="text-white font-bold text-base">{{ weekLabel }}</p>
        <p class="text-zinc-500 text-xs">{{ weekSubLabel }}</p>
      </div>
      <button
        @click="weekOffset++"
        class="flex items-center gap-1.5 px-4 py-2 rounded-2xl bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white border border-white/5 transition-all text-sm font-medium"
      >
        Next
        <span class="material-symbols-outlined text-lg">chevron_right</span>
      </button>
    </div>

    <!-- 7-Day Grid -->
    <div class="grid grid-cols-7 gap-3">
      <div
        v-for="day in weekDays"
        :key="day.iso"
        @click="$emit('dayClick', { date: day.date, sessions: day.sessions })"
        class="group cursor-pointer"
      >
        <!-- Day Header -->
        <div
          class="text-center mb-2 px-2 py-2 rounded-2xl transition-all"
          :class="day.isToday
            ? 'bg-orange-500/15 border border-orange-500/30'
            : day.isWeekend
              ? 'bg-white/[0.02] border border-white/5'
              : 'bg-white/[0.02] border border-white/5 group-hover:bg-white/5'"
        >
          <p
            class="text-[10px] font-black uppercase tracking-widest mb-1"
            :class="day.isToday ? 'text-orange-500' : day.isWeekend ? 'text-zinc-600' : 'text-zinc-500'"
          >{{ day.label }}</p>
          <div
            class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-black mx-auto"
            :class="day.isToday
              ? 'bg-gradient-to-br from-orange-500 to-orange-700 text-white shadow-lg shadow-orange-900/30'
              : 'text-zinc-400'"
          >{{ day.dateNum }}</div>
        </div>

        <!-- Sessions for this day -->
        <div
          class="min-h-[100px] rounded-2xl p-2 space-y-1.5 border transition-all"
          :class="day.isToday
            ? 'border-orange-500/20 bg-orange-500/5'
            : 'border-white/5 bg-white/[0.02] group-hover:bg-white/[0.04] group-hover:border-white/10'"
        >
          <div
            v-for="session in day.sessions"
            :key="session.id"
            class="rounded-xl px-2 py-1.5 text-[10px] font-bold border-l-2"
            :class="statusCardClass(session.status)"
          >
            <p class="font-black truncate">{{ formatTime(session.startTime) }}</p>
            <p
              class="truncate text-[9px] uppercase tracking-wide mt-0.5"
              :class="statusLabelClass(session.status)"
            >{{ statusLabel(session.status) }}</p>
          </div>

          <!-- Empty day hint -->
          <div
            v-if="day.sessions.length === 0"
            class="h-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pt-4"
          >
            <span class="material-symbols-outlined text-zinc-700 text-xl">add</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

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

defineEmits<{
  dayClick: [{ date: Date; sessions: Session[] }]
}>()

const weekOffset = ref(0)

const weekDays = computed<DayData[]>(() => {
  const today = new Date()
  const dayOfWeek = today.getDay() || 7 // Sunday = 7
  const monday = new Date(today)
  monday.setDate(today.getDate() - dayOfWeek + 1 + weekOffset.value * 7)
  monday.setHours(0, 0, 0, 0)

  const dayLabels = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']

  return dayLabels.map((label, i) => {
    const date = new Date(monday)
    date.setDate(monday.getDate() + i)

    const iso = date.toDateString()
    const isToday = iso === today.toDateString()
    const isWeekend = i >= 5 // SAT and SUN

    const daySessions = props.sessions.filter(s => {
      return new Date(s.startTime).toDateString() === iso
    })

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

const weekLabel = computed(() => {
  const monday = weekDays.value[0]?.date
  const sunday = weekDays.value[6]?.date
  if (!monday || !sunday) return ''
  const fmt = (d: Date) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  return `${fmt(monday)} – ${fmt(sunday)}`
})

const weekSubLabel = computed(() => {
  const monday = weekDays.value[0]?.date
  if (!monday) return ''
  return monday.toLocaleDateString('en-US', { year: 'numeric' })
})

function formatTime(iso: string) {
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
}

function statusCardClass(status: string): string {
  const map: Record<string, string> = {
    scheduled:       'bg-orange-500/10 border-orange-500 text-orange-300',
    completed:       'bg-emerald-500/10 border-emerald-500 text-emerald-300',
    pending_teacher: 'bg-amber-500/10 border-amber-500 text-amber-300',
    pending_admin:   'bg-blue-500/10 border-blue-500 text-blue-300',
    rejected:        'bg-red-500/10 border-red-500 text-red-300',
    cancelled:       'bg-zinc-500/10 border-zinc-500 text-zinc-400',
  }
  return map[status] ?? 'bg-white/5 border-white/20 text-zinc-400'
}

function statusLabelClass(status: string): string {
  const map: Record<string, string> = {
    scheduled:       'text-orange-500/70',
    completed:       'text-emerald-500/70',
    pending_teacher: 'text-amber-500/70',
    pending_admin:   'text-blue-500/70',
    rejected:        'text-red-500/70',
    cancelled:       'text-zinc-500',
  }
  return map[status] ?? 'text-zinc-500'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    scheduled:       'Confirmed',
    completed:       'Done',
    pending_teacher: 'Awaiting Teacher',
    pending_admin:   'Awaiting Admin',
    rejected:        'Declined',
    cancelled:       'Cancelled',
  }
  return map[status] ?? status
}
</script>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useScheduleStore } from '../../stores/schedule'
import { useUsersStore } from '../../stores/users'

const authStore = useAuthStore()
const scheduleStore = useScheduleStore()
const usersStore = useUsersStore()

onMounted(async () => {
  if (authStore.currentUser?.id) {
    await Promise.all([
      scheduleStore.fetchUserSessions(authStore.currentUser.id),
      usersStore.fetchUsersByRole('student'),
    ])
  }
})

const myId = computed(() => authStore.currentUser?.id ?? '')

const mySessions = computed(() =>
  scheduleStore.allSessions.filter((s) => s.teacherId === myId.value)
)

const todaySessions = computed(() => {
  const today = new Date().toDateString()
  return mySessions.value.filter(
    (s) => s.startTime && new Date(s.startTime).toDateString() === today
  )
})

const nextSession = computed(
  () =>
    mySessions.value
      .filter((s) => s.status === 'scheduled')
      .sort((a, b) => new Date(a.startTime!).getTime() - new Date(b.startTime!).getTime())[0] ??
    null
)

// Build unique student entries for the roster
const rosterEntries = computed(() => {
  const seen = new Set<string>()
  return mySessions.value
    .filter((s) => {
      if (seen.has(s.studentId)) return false
      seen.add(s.studentId)
      return true
    })
    .map((s) => {
      const user = usersStore.users.find((u) => u.id === s.studentId)
      return {
        studentId: s.studentId,
        name: user?.name ?? `Student #${s.studentId}`,
        startTime: s.startTime,
        status: s.status,
      }
    })
})

// 7-day week grid (Mon–Sun of current week)
const weekDays = computed(() => {
  const days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
  const now = new Date()
  const dayOfWeek = now.getDay() || 7
  const monday = new Date(now)
  monday.setDate(now.getDate() - dayOfWeek + 1)
  monday.setHours(0, 0, 0, 0)

  return days.map((label, i) => {
    const date = new Date(monday)
    date.setDate(monday.getDate() + i)
    const isToday = date.toDateString() === now.toDateString()
    const isWeekend = i >= 5
    const session =
      mySessions.value.find((s) => {
        if (!s.startTime) return false
        return new Date(s.startTime).toDateString() === date.toDateString()
      }) ?? null
    return { label, date, dateNum: date.getDate(), session, isToday, isWeekend }
  })
})

const pendingProposals = computed(() =>
  mySessions.value.filter(s => s.status === 'pending_teacher').length
)

const formatTime = (dt: string | undefined) => {
  if (!dt) return '—'
  return new Date(dt).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
</script>

<template>
  <div class="max-w-5xl mx-auto pb-28">
    <!-- Hero Header -->
    <section class="flex items-start justify-between gap-4 mb-6">
      <div>
        <h1 class="text-5xl font-black tracking-tight text-white mb-3">
          Welcome back, <span class="text-orange-500">Maestro.</span>
        </h1>
        <p class="text-zinc-400 text-lg font-medium mb-6">
          You have
          <span class="text-white font-bold">{{ todaySessions.length || 0 }} sessions</span>
          today. Performance index is at
          <span class="text-emerald-400 font-bold">98%</span>.
        </p>
        <div
          v-if="nextSession"
          class="liquid-glass p-5 rounded-3xl inline-flex items-center gap-5 border border-white/10"
        >
          <div
            class="w-12 h-12 rounded-2xl bg-orange-500/20 flex items-center justify-center text-orange-500"
          >
            <span
              class="material-symbols-outlined"
              style="font-variation-settings: 'FILL' 1"
              >timer</span
            >
          </div>
          <div>
            <p class="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Next Up</p>
            <p class="font-bold text-xl text-white">{{ formatTime(nextSession.startTime) }} • Session</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Main Grid -->
    <div class="grid grid-cols-1 md:grid-cols-8 lg:grid-cols-12 gap-4">
      <!-- Left Column: Roster & Schedule -->
      <div class="col-span-1 md:col-span-8 space-y-4">
        <!-- Student Roster -->
        <div class="liquid-glass rounded-3xl p-4 border border-white/5 space-y-3">
          <div class="flex justify-between items-center">
            <h3 class="text-2xl font-black text-white flex items-center gap-3">
              <span
                class="material-symbols-outlined text-orange-500 text-3xl"
                style="font-variation-settings: 'FILL' 1"
                >diversity_3</span
              >
              Student Roster
            </h3>
            <button
              class="text-orange-500 font-bold text-sm hover:underline tracking-wide uppercase"
            >
              View All Roster
            </button>
          </div>

          <!-- Loading -->
          <div v-if="usersStore.isLoading" class="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div v-for="i in 2" :key="i" class="h-28 rounded-3xl bg-white/5 animate-pulse" />
          </div>

          <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <!-- Real roster from sessions -->
            <div
              v-for="entry in rosterEntries"
              :key="entry.studentId"
              class="bg-black/40 backdrop-blur-xl border border-white/5 p-5 rounded-3xl flex items-center gap-4 hover:border-orange-500/40 transition-all group cursor-pointer"
            >
              <div
                class="w-16 h-16 rounded-2xl overflow-hidden shadow-2xl border border-white/10 group-hover:scale-105 transition-transform bg-surface-container-highest flex items-center justify-center shrink-0"
              >
                <span class="text-2xl font-black text-white">{{
                  entry.name.charAt(0).toUpperCase()
                }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <h4 class="font-bold text-white text-lg truncate">{{ entry.name }}</h4>
                <p class="text-xs text-zinc-500 font-medium mb-2 uppercase tracking-tighter">
                  {{ formatTime(entry.startTime) }}
                </p>
                <div class="flex gap-2 flex-wrap">
                  <span
                    class="px-2.5 py-1 bg-orange-500/10 text-orange-400 text-[9px] font-bold rounded-full border border-orange-500/20 uppercase"
                    >{{ entry.status }}</span
                  >
                </div>
              </div>
              <span
                class="material-symbols-outlined text-zinc-600 group-hover:text-orange-500 transition-colors"
                >chevron_right</span
              >
            </div>

            <!-- Enroll New -->
            <div
              class="bg-black/40 backdrop-blur-xl p-5 rounded-3xl flex items-center justify-center border-2 border-dashed border-white/10 hover:border-orange-500/50 hover:bg-white/5 transition-all group cursor-pointer"
            >
              <div class="text-center">
                <span
                  class="material-symbols-outlined text-zinc-600 group-hover:text-orange-500 text-3xl mb-1 block"
                  >person_add</span
                >
                <p class="text-[10px] font-black text-zinc-500 uppercase tracking-widest">
                  Enroll New
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Weekly Schedule -->
        <div class="liquid-glass rounded-3xl p-4 border border-white/5 space-y-3">
          <div class="flex justify-between items-center">
            <div>
              <h3 class="text-2xl font-black text-white flex items-center gap-3">
                <span class="material-symbols-outlined text-orange-500 text-3xl">calendar_month</span>
                Weekly Schedule
              </h3>
              <p v-if="pendingProposals > 0" class="text-amber-400 text-sm font-bold mt-1">
                {{ pendingProposals }} student proposal{{ pendingProposals !== 1 ? 's' : '' }} await your review
                <RouterLink to="/teacher/schedule" class="underline ml-1">Review →</RouterLink>
              </p>
            </div>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-3">
            <div v-for="day in weekDays" :key="day.label" class="space-y-3">
              <div class="text-center">
                <p
                  class="text-[10px] font-black uppercase tracking-[0.2em]"
                  :class="day.isToday ? 'text-orange-500' : day.isWeekend ? 'text-zinc-600' : 'text-zinc-500'"
                >{{ day.label }}</p>
                <div
                  class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-black mx-auto mt-1"
                  :class="day.isToday ? 'bg-gradient-to-br from-orange-500 to-orange-700 text-white' : 'text-zinc-500'"
                >{{ day.dateNum }}</div>
              </div>
              <!-- Has session -->
              <div
                v-if="day.session"
                class="rounded-2xl p-3 border-l-2"
                :class="day.session.status === 'scheduled' ? 'bg-orange-500/10 border-orange-500' :
                        day.session.status === 'pending_admin' ? 'bg-blue-500/10 border-blue-500' :
                        day.session.status === 'pending_teacher' ? 'bg-amber-500/10 border-amber-500' :
                        'bg-white/5 border-white/20'"
              >
                <p class="text-[10px] font-black text-orange-500 mb-1">{{ formatTime(day.session.startTime) }}</p>
                <p class="text-xs font-bold text-white truncate">S#{{ day.session.studentId.slice(-4) }}</p>
                <p
                  class="text-[9px] font-bold mt-0.5"
                  :class="day.session.status === 'pending_admin' ? 'text-blue-400' :
                          day.session.status === 'pending_teacher' ? 'text-amber-400' : 'text-zinc-500'"
                >{{ day.session.status === 'pending_admin' ? 'Pending Admin' : day.session.status === 'pending_teacher' ? 'Pending Review' : 'Confirmed' }}</p>
              </div>
              <!-- Empty slot -->
              <div
                v-else
                class="h-20 border border-dashed rounded-2xl flex items-center justify-center"
                :class="day.isWeekend ? 'border-white/[0.03] bg-white/[0.01]' : 'border-white/5 bg-black/20'"
              >
                <span class="material-symbols-outlined text-zinc-800 text-base">add</span>
              </div>
            </div>
          </div>
          <RouterLink to="/teacher/schedule" class="block text-center text-xs text-zinc-600 hover:text-orange-500 transition-colors font-bold">
            View Full Schedule →
          </RouterLink>
        </div>
      </div>

      <!-- Right Column: Live Session Card -->
      <div class="col-span-1 md:col-span-4">
        <div
          class="liquid-glass rounded-3xl overflow-hidden border border-white/10 shadow-2xl sticky top-4 flex flex-col"
        >
          <!-- Orange header -->
          <div
            class="p-4 bg-gradient-to-br from-orange-500 to-orange-700 relative overflow-hidden"
          >
            <div
              class="absolute -top-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl"
            ></div>
            <div class="flex justify-between items-start mb-6 relative z-10">
              <span
                class="px-3 py-1 bg-white/20 backdrop-blur-md rounded-full text-[9px] font-black tracking-widest uppercase border border-white/30 text-white"
                >Live Session</span
              >
              <button class="text-white/80 hover:text-white">
                <span class="material-symbols-outlined">more_horiz</span>
              </button>
            </div>
            <div v-if="nextSession" class="relative z-10">
              <h3 class="text-2xl font-black text-white leading-tight">
                Session #{{ nextSession.id }}
              </h3>
              <p
                class="text-white/70 text-[11px] mt-2 font-bold uppercase tracking-widest"
              >
                {{ formatTime(nextSession.startTime) }} • Student #{{ nextSession.studentId }}
              </p>
            </div>
            <div v-else class="relative z-10">
              <h3 class="text-2xl font-black text-white leading-tight">No Active Session</h3>
              <p class="text-white/70 text-[11px] mt-2 font-bold uppercase tracking-widest">
                Sessions will appear here
              </p>
            </div>
          </div>

          <!-- Body -->
          <div class="p-4 space-y-4 flex-1">
            <!-- Proof Upload -->
            <div class="space-y-4">
              <label class="text-[10px] font-black text-zinc-500 uppercase tracking-widest"
                >Visual Evidence</label
              >
              <div
                class="aspect-video bg-black/40 rounded-3xl border-2 border-dashed border-white/10 flex flex-col items-center justify-center cursor-pointer hover:bg-white/5 hover:border-orange-500/50 transition-all group overflow-hidden relative"
              >
                <div class="text-center group-hover:scale-105 transition-transform">
                  <div
                    class="w-14 h-14 bg-orange-500/10 rounded-full flex items-center justify-center mx-auto mb-3"
                  >
                    <span
                      class="material-symbols-outlined text-3xl text-orange-500"
                      style="font-variation-settings: 'FILL' 1"
                      >add_a_photo</span
                    >
                  </div>
                  <p class="text-[11px] font-black text-zinc-300 uppercase tracking-wide">
                    Take Photo or Upload
                  </p>
                </div>
                <input type="file" accept="image/*" class="absolute inset-0 opacity-0 cursor-pointer" aria-label="Upload session proof" />
              </div>
            </div>

            <!-- Practice Goals -->
            <div class="space-y-4">
              <label class="text-[10px] font-black text-zinc-500 uppercase tracking-widest"
                >Next Week's Practice Goals</label
              >
              <textarea
                class="w-full h-32 bg-black/40 border border-white/5 rounded-3xl focus:ring-2 focus:ring-orange-500/40 text-sm p-5 text-white placeholder-zinc-600 resize-none transition-all"
                placeholder="E.g. Focus on paradiddle transitions at 120bpm..."
              ></textarea>
            </div>

            <!-- Shared Resources -->
            <div class="space-y-4">
              <label class="text-[10px] font-black text-zinc-500 uppercase tracking-widest"
                >Shared Resources</label
              >
              <div class="space-y-3">
                <div
                  class="bg-black/40 p-4 rounded-2xl flex items-center justify-between border border-white/5"
                >
                  <div class="flex items-center gap-3">
                    <div
                      class="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-500"
                    >
                      <span class="material-symbols-outlined text-lg">music_note</span>
                    </div>
                    <div>
                      <p class="text-xs font-bold text-white">Drum_Fills_Intermediate.pdf</p>
                      <p class="text-[9px] text-zinc-500 uppercase">1.2 MB • Sheet Music</p>
                    </div>
                  </div>
                  <button class="text-zinc-500 hover:text-red-400 transition-colors">
                    <span class="material-symbols-outlined text-lg">close</span>
                  </button>
                </div>
                <button
                  class="w-full py-3 bg-white/5 rounded-2xl text-[10px] font-black text-zinc-400 hover:bg-white/10 hover:text-white border border-white/5 transition-all flex items-center justify-center gap-2 uppercase tracking-widest"
                >
                  <span class="material-symbols-outlined text-lg">attach_file</span>
                  Attach Media
                </button>
              </div>
            </div>
          </div>

          <div class="p-4 border-t border-white/5 bg-black/20">
            <button
              class="w-full py-5 bg-gradient-to-br from-orange-500 to-orange-700 text-white rounded-3xl font-black text-lg shadow-[0_15px_40px_rgba(249,115,22,0.3)] hover:scale-[1.02] active:scale-95 transition-all uppercase tracking-tighter"
            >
              Complete Session
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer Stats -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
      <div
        class="liquid-glass p-4 rounded-3xl border border-white/10 flex items-center gap-4 group hover:bg-white/5 transition-all"
      >
        <div
          class="w-20 h-20 rounded-3xl bg-orange-500 text-white flex items-center justify-center text-4xl font-black shadow-2xl group-hover:scale-110 transition-transform"
        >
          {{ mySessions.length }}
        </div>
        <div>
          <h4 class="font-black text-xl text-white">Active Roster</h4>
          <p class="text-sm text-zinc-500">Enrolled for Summer Term</p>
        </div>
      </div>
      <div
        class="liquid-glass p-4 rounded-3xl border border-white/10 flex items-center gap-4 group hover:bg-white/5 transition-all"
      >
        <div
          class="w-20 h-20 rounded-3xl bg-orange-500/20 text-orange-500 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform"
        >
          <span
            class="material-symbols-outlined text-4xl"
            style="font-variation-settings: 'FILL' 1"
            >star</span
          >
        </div>
        <div>
          <h4 class="font-black text-xl text-white">Rating: 4.98</h4>
          <p class="text-sm text-zinc-500">Based on 142 reviews</p>
        </div>
      </div>
      <div
        class="liquid-glass p-4 rounded-3xl border border-white/10 flex items-center gap-4 group hover:bg-white/5 transition-all"
      >
        <div
          class="w-20 h-20 rounded-3xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform"
        >
          <span
            class="material-symbols-outlined text-4xl"
            style="font-variation-settings: 'FILL' 1"
            >analytics</span
          >
        </div>
        <div>
          <h4 class="font-black text-xl text-white">Growth Hub</h4>
          <p class="text-sm text-zinc-500">+15% Month-over-Month</p>
        </div>
      </div>
    </section>
  </div>
</template>

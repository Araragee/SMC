<template>
  <div class="flex">
    <TeacherSidebar />
    <div class="ml-64 w-full p-8 pt-28 min-h-screen">
      <!-- Header -->
      <div class="mb-8 flex items-center justify-between">
        <div>
          <h2 class="text-3xl font-black text-white tracking-tight">My Sessions</h2>
          <p class="text-zinc-400 mt-1">Welcome back, {{ authStore.currentUser?.name }}</p>
        </div>
        <button @click="authStore.logout(); router.push('/')"
          class="flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white text-sm font-medium transition-all">
          <span class="material-symbols-outlined text-sm">logout</span>
          Sign out
        </button>
      </div>

      <!-- Stats row -->
      <div class="grid grid-cols-2 gap-4 mb-8">
        <div class="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5">
          <p class="text-xs text-zinc-500 uppercase tracking-widest font-semibold">My Sessions</p>
          <p class="text-3xl font-black text-white mt-1">{{ mySessions.length }}</p>
        </div>
        <div class="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5">
          <p class="text-xs text-zinc-500 uppercase tracking-widest font-semibold">Homework Pending</p>
          <p class="text-3xl font-black text-amber-400 mt-1">{{ mySessions.filter(s => s.homeworkAssigned && !s.homeworkCompleted).length }}</p>
        </div>
      </div>

      <!-- Sessions list -->
      <div class="bg-zinc-900/60 border border-zinc-800 rounded-xl overflow-hidden">
        <div class="px-6 py-4 border-b border-zinc-800">
          <h3 class="font-bold text-white">My Upcoming Sessions</h3>
        </div>

        <div v-if="scheduleStore.isLoading" class="p-6 space-y-3">
          <div v-for="i in 3" :key="i" class="h-16 rounded-lg bg-zinc-800 animate-pulse" />
        </div>

        <div v-else-if="mySessions.length === 0"
          class="p-12 flex flex-col items-center text-center text-zinc-600">
          <span class="material-symbols-outlined text-5xl mb-3" style="font-variation-settings: 'FILL' 1;">event_available</span>
          <p class="font-semibold text-zinc-400">No sessions assigned yet</p>
          <p class="text-sm mt-1">Check back later — sessions will appear here once they are booked.</p>
        </div>

        <div v-else class="divide-y divide-zinc-800">
          <div v-for="session in mySessions" :key="session.id"
            class="px-6 py-4 flex items-center justify-between hover:bg-zinc-800/30 transition-colors">
            <div>
              <p class="text-white font-medium">Session #{{ session.id }}</p>
              <p class="text-sm text-zinc-500">{{ formatDate(session.startTime) }}</p>
            </div>
            <div class="flex items-center gap-3">
              <span v-if="session.homeworkAssigned"
                class="text-xs px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-400 font-semibold">
                HW Assigned
              </span>
              <span class="text-xs px-2.5 py-1 rounded-full font-semibold capitalize"
                :class="statusClass(session.status)">{{ session.status }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import TeacherSidebar from '../../components/TeacherSidebar.vue'
import { useScheduleStore } from '../../stores/schedule'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const scheduleStore = useScheduleStore()
const authStore = useAuthStore()

onMounted(() => {
  if (authStore.currentUser?.id) {
    scheduleStore.fetchUserSessions(authStore.currentUser.id)
  }
})

const mySessions = computed(() => {
  if (!authStore.currentUser?.id) return []
  return scheduleStore.getSessionsByTeacherId(authStore.currentUser.id)
})

const formatDate = (dt: string | undefined) => {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })
}

const statusClass = (status: string) => ({
  'bg-emerald-500/20 text-emerald-400': status === 'completed',
  'bg-blue-500/20 text-blue-400': status === 'scheduled',
  'bg-amber-500/20 text-amber-400': status === 'ongoing',
  'bg-red-500/20 text-red-400': status === 'cancelled',
})
</script>

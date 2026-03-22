<template>
  <div class="flex">
    <AdminSidebar />
    <div class="ml-64 w-full p-8 pt-28 min-h-screen">
      <!-- Header -->
      <div class="mb-8 flex items-center justify-between">
        <div>
          <h2 class="text-3xl font-black text-white tracking-tight">Admin Dashboard</h2>
          <p class="text-zinc-400 mt-1">Overview of Sernan's Music Clinic</p>
        </div>
        <button @click="authStore.logout(); router.push('/')"
          class="flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white text-sm font-medium transition-all">
          <span class="material-symbols-outlined text-sm">logout</span>
          Sign out
        </button>
      </div>

      <!-- Stats Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div v-for="stat in stats" :key="stat.label"
          class="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5 flex items-center gap-4">
          <div class="w-12 h-12 rounded-lg flex items-center justify-center" :class="stat.bgColor">
            <span class="material-symbols-outlined" :class="stat.iconColor" style="font-variation-settings: 'FILL' 1;">{{ stat.icon }}</span>
          </div>
          <div>
            <p class="text-2xl font-black text-white">{{ scheduleStore.isLoading ? '—' : stat.value }}</p>
            <p class="text-sm text-zinc-500">{{ stat.label }}</p>
          </div>
        </div>
      </div>

      <!-- Recent Sessions -->
      <div class="bg-zinc-900/60 border border-zinc-800 rounded-xl overflow-hidden">
        <div class="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
          <h3 class="font-bold text-white">Recent Sessions</h3>
          <span v-if="scheduleStore.isLoading" class="text-xs text-zinc-500 animate-pulse">Loading...</span>
        </div>

        <!-- Loading skeleton -->
        <div v-if="scheduleStore.isLoading" class="p-6 space-y-3">
          <div v-for="i in 4" :key="i" class="h-12 rounded-lg bg-zinc-800 animate-pulse" />
        </div>

        <!-- Empty state -->
        <div v-else-if="scheduleStore.allSessions.length === 0" class="p-12 flex flex-col items-center text-center text-zinc-600">
          <span class="material-symbols-outlined text-5xl mb-3" style="font-variation-settings: 'FILL' 1;">event_busy</span>
          <p class="font-semibold text-zinc-400">No sessions yet</p>
          <p class="text-sm mt-1">Sessions will appear here once they are booked.</p>
        </div>

        <!-- Table -->
        <table v-else class="w-full text-sm">
          <thead class="bg-zinc-800/40">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Session ID</th>
              <th class="px-6 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Start Time</th>
              <th class="px-6 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Status</th>
              <th class="px-6 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Image Proof</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-zinc-800">
            <tr v-for="session in scheduleStore.allSessions.slice(0, 10)" :key="session.id"
              class="hover:bg-zinc-800/30 transition-colors">
              <td class="px-6 py-3 text-zinc-400 font-mono">#{{ session.id }}</td>
              <td class="px-6 py-3 text-zinc-300">{{ formatDate(session.startTime) }}</td>
              <td class="px-6 py-3">
                <span class="px-2.5 py-1 rounded-full text-xs font-semibold capitalize"
                  :class="statusClass(session.status)">{{ session.status }}</span>
              </td>
              <td class="px-6 py-3">
                <span v-if="session.imageProofUrl" class="text-emerald-400 text-xs">✓ Uploaded</span>
                <span v-else class="text-zinc-600 text-xs">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import AdminSidebar from '../../components/AdminSidebar.vue'
import { useScheduleStore } from '../../stores/schedule'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const scheduleStore = useScheduleStore()
const authStore = useAuthStore()

onMounted(() => scheduleStore.fetchAllSessions())

const stats = computed(() => [
  {
    label: 'Total Sessions',
    value: scheduleStore.allSessions.length,
    icon: 'calendar_month',
    bgColor: 'bg-indigo-500/20',
    iconColor: 'text-indigo-400',
  },
  {
    label: 'Completed Sessions',
    value: scheduleStore.allSessions.filter(s => s.status === 'completed').length,
    icon: 'check_circle',
    bgColor: 'bg-emerald-500/20',
    iconColor: 'text-emerald-400',
  },
  {
    label: 'With Image Proof',
    value: scheduleStore.allSessions.filter(s => s.imageProofUrl).length,
    icon: 'photo_camera',
    bgColor: 'bg-amber-500/20',
    iconColor: 'text-amber-400',
  }
])

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

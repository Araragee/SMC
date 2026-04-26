<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '@stores/auth'
import { API_URL } from '@typescript/constants'

interface ActivityEntry {
  id: number
  action_type: string
  actor_id: number | null
  actor_name: string | null
  target_type: string | null
  target_id: number | null
  description: string
  created_at: string
}

const authStore = useAuthStore()
const authHeaders = () =>
  authStore.token ? { Authorization: `Bearer ${authStore.token}` } : {}

const entries = ref<ActivityEntry[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)
const search = ref('')
const actionFilter = ref('all')

onMounted(() => fetchLog())

async function fetchLog() {
  isLoading.value = true
  error.value = null
  try {
    const res = await axios.get(`${API_URL}/activity-log/`, { headers: authHeaders() })
    entries.value = res.data
  } catch (err: any) {
    error.value = err?.response?.data?.detail || err.message || 'Failed to load activity log.'
  } finally {
    isLoading.value = false
  }
}

// ── filter & search ───────────────────────────────────────────────────────────
const uniqueActions = computed(() => {
  const types = [...new Set(entries.value.map((e) => e.action_type))]
  return types.sort()
})

const filtered = computed(() => {
  let list = entries.value
  if (actionFilter.value !== 'all') {
    list = list.filter((e) => e.action_type === actionFilter.value)
  }
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(
      (e) =>
        e.description.toLowerCase().includes(q) ||
        (e.actor_name || '').toLowerCase().includes(q) ||
        (e.target_type || '').toLowerCase().includes(q),
    )
  }
  return list
})

// ── helpers ───────────────────────────────────────────────────────────────────
function actionLabel(type: string) {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function actionColor(type: string): string {
  if (type.includes('complete')) return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
  if (type.includes('scheduled') || type.includes('created'))
    return 'bg-blue-500/10 text-blue-500 border-blue-500/20'
  if (type.includes('reject') || type.includes('fail'))
    return 'bg-red-500/10 text-red-500 border-red-500/20'
  if (type.includes('payment')) return 'bg-teal-500/10 text-teal-500 border-teal-500/20'
  if (type.includes('force')) return 'bg-amber-500/10 text-amber-500 border-amber-500/20'
  return 'bg-surface-container text-on-surface-variant border-outline-variant/30'
}

function actionIcon(type: string): string {
  if (type.includes('complete')) return 'check_circle'
  if (type.includes('force')) return 'warning'
  if (type.includes('scheduled')) return 'calendar_month'
  if (type.includes('payment')) return 'payments'
  if (type.includes('reject')) return 'cancel'
  if (type.includes('user')) return 'person'
  return 'history'
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}
</script>

<template>
  <div class="max-w-[1000px] mx-auto pb-28 space-y-10 px-4 sm:px-6">
    <!-- Header -->
    <header class="pt-8">
      <div class="flex items-center gap-3 mb-3">
        <div
          class="w-10 h-10 rounded-2xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center"
        >
          <span class="material-symbols-outlined text-violet-500 text-2xl">history</span>
        </div>
        <p class="text-[10px] font-black text-violet-500 uppercase tracking-[0.25em]">
          Audit Trail
        </p>
      </div>
      <div class="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 class="text-5xl font-black tracking-tight text-on-surface mb-2">Activity Log</h1>
          <p class="text-on-surface-variant font-medium text-lg">
            A chronological record of all administrative actions in the system.
          </p>
        </div>
        <button
          class="flex items-center gap-2 px-5 py-3 glass-medium border border-outline-variant/30 hover:bg-black/5 dark:hover:bg-white/5 rounded-2xl font-black text-sm text-on-surface transition-all"
          @click="fetchLog"
        >
          <span class="material-symbols-outlined text-lg">refresh</span>
          Refresh
        </button>
      </div>
    </header>

    <!-- Summary strip -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div class="glass-heavy rounded-3xl p-4 border border-outline-variant/30 text-center">
        <p class="text-2xl font-black text-on-surface">{{ entries.length }}</p>
        <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mt-1">
          Total Events
        </p>
      </div>
      <div class="glass-heavy rounded-3xl p-4 border border-outline-variant/30 text-center">
        <p class="text-2xl font-black text-emerald-500">
          {{ entries.filter((e) => e.action_type.includes('complete')).length }}
        </p>
        <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mt-1">
          Completions
        </p>
      </div>
      <div class="glass-heavy rounded-3xl p-4 border border-outline-variant/30 text-center">
        <p class="text-2xl font-black text-blue-500">
          {{ entries.filter((e) => e.action_type.includes('scheduled')).length }}
        </p>
        <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mt-1">
          Scheduled
        </p>
      </div>
      <div class="glass-heavy rounded-3xl p-4 border border-outline-variant/30 text-center">
        <p class="text-2xl font-black text-teal-500">
          {{ entries.filter((e) => e.action_type.includes('payment')).length }}
        </p>
        <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mt-1">
          Payments
        </p>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-3">
      <div
        class="flex items-center gap-2 flex-1 min-w-[200px] glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3"
      >
        <span class="material-symbols-outlined text-on-surface-variant text-lg">search</span>
        <input
          v-model="search"
          placeholder="Search descriptions, actors…"
          class="bg-transparent text-sm text-on-surface placeholder:text-on-surface-variant/50 outline-none flex-1 font-medium"
        />
      </div>
      <select
        v-model="actionFilter"
        class="glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3 text-sm font-bold text-on-surface outline-none bg-transparent cursor-pointer"
      >
        <option value="all">All Actions</option>
        <option v-for="a in uniqueActions" :key="a" :value="a">{{ actionLabel(a) }}</option>
      </select>
    </div>

    <!-- Log Feed -->
    <section>
      <!-- Loading -->
      <div
        v-if="isLoading"
        class="glass-medium rounded-3xl p-20 text-center border border-outline-variant/30"
      >
        <span
          class="material-symbols-outlined text-5xl text-on-surface-variant/30 mb-4 animate-spin block"
          >progress_activity</span
        >
        <p class="text-sm font-bold text-on-surface-variant">Loading activity log…</p>
      </div>

      <!-- Error -->
      <div
        v-else-if="error"
        class="glass-medium rounded-3xl p-12 text-center border border-red-500/20"
      >
        <span class="material-symbols-outlined text-4xl text-red-500/60 mb-3 block">error</span>
        <p class="text-sm font-bold text-on-surface-variant">{{ error }}</p>
      </div>

      <!-- Empty -->
      <div
        v-else-if="filtered.length === 0"
        class="glass-medium rounded-[3rem] p-20 text-center border-dashed border-2 border-outline-variant/30"
      >
        <span class="material-symbols-outlined text-5xl text-on-surface-variant/20 mb-4 block"
          >manage_history</span
        >
        <p class="text-lg font-black text-on-surface">No activity recorded yet</p>
        <p class="text-sm text-on-surface-variant mt-1">
          Events will appear here as admins take actions in the system.
        </p>
      </div>

      <!-- Timeline -->
      <div v-else class="relative">
        <!-- vertical line -->
        <div
          class="absolute left-[22px] top-4 bottom-4 w-px bg-outline-variant/20 hidden sm:block"
        ></div>

        <div class="space-y-3">
          <div
            v-for="entry in filtered"
            :key="entry.id"
            class="glass-heavy rounded-3xl px-5 py-4 border border-outline-variant/30 flex gap-4 items-start hover:border-violet-500/20 transition-all sm:ml-12"
          >
            <!-- Icon bubble (positioned over the timeline line) -->
            <div
              class="hidden sm:flex absolute -left-[3px] w-11 h-11 rounded-full border-2 border-surface-container-low items-center justify-center shrink-0"
              :class="actionColor(entry.action_type)"
            >
              <span class="material-symbols-outlined text-lg" style="font-variation-settings: 'FILL' 1">{{
                actionIcon(entry.action_type)
              }}</span>
            </div>

            <!-- Mobile icon (inline) -->
            <div
              class="sm:hidden w-9 h-9 rounded-2xl flex items-center justify-center shrink-0 border"
              :class="actionColor(entry.action_type)"
            >
              <span class="material-symbols-outlined text-base" style="font-variation-settings: 'FILL' 1">{{
                actionIcon(entry.action_type)
              }}</span>
            </div>

            <!-- Content -->
            <div class="flex-1 min-w-0">
              <div class="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <span
                    class="inline-flex px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border mb-1"
                    :class="actionColor(entry.action_type)"
                  >
                    {{ actionLabel(entry.action_type) }}
                  </span>
                  <p class="text-sm font-medium text-on-surface">{{ entry.description }}</p>
                </div>
                <div class="text-right shrink-0">
                  <p class="text-[10px] font-black text-on-surface-variant">
                    {{ timeAgo(entry.created_at) }}
                  </p>
                  <p class="text-[10px] text-on-surface-variant/60">
                    {{ formatDate(entry.created_at) }}
                  </p>
                </div>
              </div>
              <div v-if="entry.actor_name" class="flex items-center gap-1.5 mt-2">
                <span class="material-symbols-outlined text-sm text-on-surface-variant/60"
                  >person</span
                >
                <p class="text-[11px] font-bold text-on-surface-variant">
                  {{ entry.actor_name }}
                </p>
                <span
                  v-if="entry.target_type && entry.target_id"
                  class="text-on-surface-variant/40 text-[11px]"
                  >· {{ entry.target_type }} #{{ entry.target_id }}</span
                >
              </div>
            </div>
          </div>
        </div>
      </div>

      <p
        v-if="filtered.length > 0"
        class="text-center text-[10px] font-bold text-on-surface-variant/50 uppercase tracking-widest mt-6"
      >
        {{ filtered.length }} event{{ filtered.length !== 1 ? 's' : '' }} shown
      </p>
    </section>
  </div>
</template>

<style scoped>
.glass-heavy {
  @apply bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl shadow-lg;
}
.glass-medium {
  @apply bg-white/40 dark:bg-white/5 backdrop-blur-md;
}
</style>

<template>
  <aside class="liquid-glass rounded-3xl p-5 border border-white/5 space-y-5 inner-glow-white-10 shadow-2xl w-52">
    <!-- Brand -->
    <div class="flex items-center gap-3">
      <div
        class="w-10 h-10 rounded-2xl bg-gradient-to-br from-orange-500 to-orange-700 flex items-center justify-center shadow-lg shadow-orange-900/40 shrink-0"
      >
        <span
          class="material-symbols-outlined text-white"
          style="font-variation-settings: 'FILL' 1"
          >music_note</span
        >
      </div>
      <div>
        <h2 class="text-white font-black tracking-tight leading-none text-sm">Sernan's</h2>
        <p class="text-orange-500 text-xs font-bold mt-0.5">Music Clinic</p>
      </div>
    </div>

    <div class="h-px bg-white/5"></div>

    <!-- User info -->
    <div class="flex items-center gap-3">
      <div
        class="w-10 h-10 rounded-full bg-orange-500/20 border border-orange-500/30 flex items-center justify-center text-orange-400 font-black text-sm shrink-0"
      >
        {{ authStore.currentUser?.name?.charAt(0)?.toUpperCase() || '?' }}
      </div>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-bold text-white truncate">
          {{ authStore.currentUser?.name || 'User' }}
        </p>
        <p class="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mt-0.5">
          {{ roleLabel }}
        </p>
      </div>
    </div>

    <div class="h-px bg-white/5"></div>

    <!-- Logout -->
    <button
      class="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-zinc-400 hover:text-red-400 hover:bg-red-500/10 transition-colors text-sm font-medium"
      aria-label="Sign out"
      @click="logout"
    >
      <span class="material-symbols-outlined text-lg">logout</span>
      Sign Out
    </button>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const roleLabel = computed(() => {
  const labels: Record<string, string> = {
    admin: 'Admin Portal',
    teacher: 'Teacher',
    student: 'Student',
  }
  return labels[authStore.userRole || ''] || authStore.userRole || ''
})

const logout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

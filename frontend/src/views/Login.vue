<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const email = ref('')
const password = ref('')

const handleLogin = async () => {
    await authStore.login(email.value, password.value)
    if (authStore.isAuthenticated && authStore.user) {
        router.push(`/${authStore.user.role || 'student'}`)
    }
}
</script>

<template>
  <main class="relative z-10 w-full max-w-[1200px] px-6 py-12 flex flex-col items-center justify-center lg:flex-row gap-8 lg:gap-16 sm:px-8 md:px-12">
    <div class="w-full lg:w-1/2 space-y-8 text-center lg:text-left">
      <div class="inline-flex items-center gap-3">
        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-tertiary_container flex items-center justify-center shadow-[inset_1px_1px_0px_0px_rgba(255,255,255,0.15)]">
          <span class="material-symbols-outlined text-on_primary_container" style="font-variation-settings: 'FILL' 1;">music_note</span>
        </div>
        <span class="text-2xl font-black tracking-tighter text-zinc-900 dark:text-white uppercase font-sans">Sernan's Music Clinic</span>
      </div>
      <div class="space-y-4">
        <h1 class="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.1] text-on_surface font-sans">
          Welcome back, <br/>
          <span class="text-transparent bg-clip-text bg-gradient-to-r from-primary to-tertiary_container">Maestro.</span>
        </h1>
        <p class="text-on_surface_variant text-lg max-w-md mx-auto lg:mx-0">
          Your digital conservatory awaits. Tune into your projects and continue the orchestration.
        </p>
      </div>
    </div>
    <div class="w-full max-w-md">
      <div class="relative group">
        <div class="absolute -inset-1 bg-gradient-to-br from-primary/20 to-transparent blur-2xl opacity-50"></div>
        <div class="relative bg-surface-container-low/40 backdrop-blur-3xl p-6 sm:p-8 md:p-10 rounded-xl shadow-[inset_1px_1px_0px_0px_rgba(255,255,255,0.15)] border border-black/[0.04] dark:border-white/5 space-y-8">
          <form class="space-y-6" @submit.prevent="handleLogin">
            <div class="space-y-4">
              <div class="space-y-2">
                <label class="block text-[10px] tracking-widest uppercase text-neutral-500 font-bold px-1">Email</label>
                <input v-model="email" type="email" required placeholder="admin@example.com" class="w-full h-16 bg-surface-container-highest/50 border-none rounded-lg pl-6 pr-6 text-on_surface focus:ring-1 focus:ring-primary/50 transition-all duration-300" />
              </div>
              <div class="space-y-2">
                <label class="block text-[10px] tracking-widest uppercase text-neutral-500 font-bold px-1">Password</label>
                <input v-model="password" type="password" required placeholder="••••••••" class="w-full h-16 bg-surface-container-highest/50 border-none rounded-lg pl-6 pr-6 text-on_surface focus:ring-1 focus:ring-primary/50 transition-all duration-300" />
              </div>
            </div>
            <p v-if="authStore.error" class="text-red-400 text-sm text-center">{{ authStore.error }}</p>
            <button :disabled="authStore.isLoading" class="group relative w-full h-16 bg-gradient-to-br from-primary to-tertiary_container rounded-lg font-bold text-on_primary_container uppercase tracking-wider overflow-hidden active:scale-[0.98] transition-all duration-300 disabled:opacity-50" type="submit">
              <span class="relative z-10">{{ authStore.isLoading ? 'Signing In...' : 'Sign In' }}</span>
              <div class="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </button>
          </form>        </div>
      </div>
    </div>
  </main>
</template>


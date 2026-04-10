<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const username = ref('')
const password = ref('')

const handleLogin = async () => {
    await authStore.login(username.value, password.value)
    if (authStore.isAuthenticated && authStore.user) {
        router.push(`/${authStore.user.role || 'student'}`)
    }
}
</script>

<template>
  <main class="relative z-10 w-full max-w-[1200px] px-6 py-12 flex flex-col items-center justify-center lg:flex-row gap-8 lg:gap-16 sm:px-8 md:px-12">
    <div class="w-full lg:w-1/2 space-y-8 text-center lg:text-left">
      <div class="inline-flex items-center gap-3">
        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-tertiary-container flex items-center justify-center shadow-[inset_1px_1px_0px_0px_rgba(255,255,255,0.15)] overflow-hidden">
          <img src="/logo.png" alt="Logo" class="w-full h-full object-cover" />
        </div>
        <span class="text-2xl font-black tracking-tighter text-on-surface dark:text-on-surface uppercase font-sans">Sernan's Music Clinic</span>
      </div>
      <div class="space-y-4">
        <h1 class="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.1] text-on-surface dark:text-on-surface font-sans">
          Welcome back, <br/>
          <span class="text-transparent bg-clip-text bg-gradient-to-r from-primary to-tertiary-container">Maestro.</span>
        </h1>
        <p class="text-on-surface-variant dark:text-on-surface-variant text-lg max-w-md mx-auto lg:mx-0">
          Your digital conservatory awaits. Tune into your projects and continue the orchestration.
        </p>
      </div>
    </div>
    <div class="w-full max-w-md">
      <div class="relative group">
        <div class="absolute -inset-1 bg-gradient-to-br from-primary/20 to-transparent blur-2xl opacity-50"></div>
        <div class="relative glass-heavy rounded-[2rem] p-6 sm:p-8 md:p-10 glass-specular space-y-8">
          <form class="space-y-6" @submit.prevent="handleLogin">
            <div class="space-y-4">
              <div class="space-y-2">
                <label class="block text-[10px] tracking-widest uppercase text-on-surface-variant dark:text-on-surface-variant font-bold px-1">Username</label>
                <input v-model="username" type="text" required placeholder="admin" class="w-full h-16 bg-black/5 dark:bg-white/5 border border-black/8 dark:border-white/10 rounded-2xl pl-6 pr-6 text-on-surface dark:text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/40 transition-all  placeholder:text-on-surface-variant dark:placeholder:text-on-surface-variant" />
              </div>
              <div class="space-y-2">
                <label class="block text-[10px] tracking-widest uppercase text-on-surface-variant dark:text-on-surface-variant font-bold px-1">Password</label>
                <input v-model="password" type="password" required placeholder="••••••••" class="w-full h-16 bg-black/5 dark:bg-white/5 border border-black/8 dark:border-white/10 rounded-2xl pl-6 pr-6 text-on-surface dark:text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/40 transition-all  placeholder:text-on-surface-variant dark:placeholder:text-on-surface-variant" />
              </div>
            </div>
            <p v-if="authStore.error" class="text-error dark:text-error text-sm text-center">{{ authStore.error }}</p>
            <button :disabled="authStore.isLoading" class="group relative w-full h-16 bg-gradient-to-br from-primary to-tertiary-container rounded-lg font-bold text-white dark:text-white uppercase tracking-wider overflow-hidden active:scale-[0.98] transition-all  disabled:opacity-50" type="submit">
              <span class="relative z-10">{{ authStore.isLoading ? 'Signing In...' : 'Sign In' }}</span>
              <div class="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </button>
          </form>        </div>
      </div>
    </div>
  </main>
</template>

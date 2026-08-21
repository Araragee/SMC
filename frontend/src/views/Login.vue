<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@stores/auth'
import TwoFAVerifyModal from '@components/TwoFAVerifyModal.vue'

const router = useRouter()
const authStore = useAuthStore()
const username = ref('')
const password = ref('')
const isTwoFAModalOpen = ref(false)

const handleLogin = async () => {
    try {
        const res = await authStore.login(username.value, password.value)
        if (res && res.requires2FA) {
            isTwoFAModalOpen.value = true
            return
        }
        if (authStore.isAuthenticated && authStore.user) {
            router.push(`/${authStore.user.role || 'student'}`)
        }
    } catch {
        // error handled by store toast
    }
}

const on2FAVerified = () => {
    isTwoFAModalOpen.value = false
    if (authStore.isAuthenticated && authStore.user) {
        router.push(`/${authStore.user.role || 'student'}`)
    }
}
</script>

<template>
  <main class="relative z-10 w-full max-w-[1200px] px-6 py-12 flex flex-col items-center justify-center lg:flex-row gap-8 lg:gap-16 sm:px-8 md:px-12">
    <div class="w-full lg:w-1/2 space-y-8 text-center lg:text-left">
      <div class="inline-flex items-center gap-3">
        <div class="size-12 rounded-xl bg-gradient-to-br from-primary to-tertiary-container flex items-center justify-center shadow-[inset_1px_1px_0px_0px_rgba(255,255,255,0.15)] overflow-hidden">
          <img src="/logo.png" alt="Logo" class="w-full h-full object-cover" />
        </div>
        <span class="text-2xl font-semibold tracking-tighter text-on-surface dark:text-on-surface uppercase font-sans">Sernan's Music Clinic</span>
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
        <div class="relative glass-heavy rounded-3xl p-6 sm:p-8 md:p-10 glass-specular space-y-8">
          <form class="space-y-6" @submit.prevent="handleLogin">
            <div class="space-y-4">
              <div class="space-y-2">
                <label class="block text-xs uppercase text-on-surface-variant dark:text-on-surface-variant font-bold px-1">Username</label>
                <input v-model="username" type="text" required placeholder="admin" class="input" />
              </div>
              <div class="space-y-2">
                <label class="block text-xs uppercase text-on-surface-variant dark:text-on-surface-variant font-bold px-1">Password</label>
                <input v-model="password" type="password" required placeholder="••••••••" class="input" />
              </div>
            </div>
            <p v-if="authStore.error" class="text-error dark:text-error text-sm text-center">{{ authStore.error }}</p>
            <button :disabled="authStore.isLoading" class="group relative w-full h-16 bg-gradient-to-br from-primary to-tertiary-container rounded-lg font-bold text-white dark:text-white uppercase overflow-hidden active:scale-[0.98] transition-all disabled:opacity-50" type="submit">
              <span class="relative z-10">{{ authStore.isLoading ? 'Signing In...' : 'Sign In' }}</span>
              <div class="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </button>
            <div class="text-center">
              <router-link
                to="/forgot-password"
                class="text-xs font-semibold uppercase text-on-surface-variant hover:text-on-surface transition-colors"
              >
                Forgot your password?
              </router-link>
            </div>
          </form>        </div>
      </div>
    </div>
  </main>

  <TwoFAVerifyModal
    :is-open="isTwoFAModalOpen"
    @close="isTwoFAModalOpen = false"
    @verified="on2FAVerified"
  />
</template>

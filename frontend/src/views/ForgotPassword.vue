<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'
import { useToastStore } from '@stores/toast'
import { API_URL } from '@typescript/constants'

// "Forgot password" is intentionally enumeration-resistant: the API
// always returns 200 with the same generic message, whether the email
// exists or not. So the UI displays a uniform confirmation as long as
// the request itself completed — no "we don't know that email" tell.

const toast = useToastStore()
const email = ref('')
const submitted = ref(false)
const isLoading = ref(false)

const submit = async () => {
  if (!email.value || isLoading.value) return
  isLoading.value = true
  try {
    await axios.post(`${API_URL}/auth/forgot-password`, { email: email.value })
    submitted.value = true
  } catch (err: any) {
    // 422 = bad email format; 429 = rate limited. Everything else falls
    // through to the generic confirmation so users in those cases still
    // get the same UX.
    const code = err.response?.status
    if (code === 422) {
      toast.error('Invalid email', 'Please enter a valid email address.')
    } else if (code === 429) {
      toast.error('Too many attempts', 'Please wait a minute before trying again.')
    } else {
      submitted.value = true
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <main class="relative z-10 w-full max-w-md px-6 py-12">
    <div class="relative glass-heavy rounded-[2rem] p-8 md:p-10 space-y-6">
      <div class="space-y-2 text-center">
        <h1 class="text-3xl font-extrabold tracking-tight text-on-surface">Reset password</h1>
        <p class="text-on-surface-variant text-sm">
          Enter your email and we'll send you a link to choose a new one.
        </p>
      </div>

      <form v-if="!submitted" class="space-y-4" @submit.prevent="submit">
        <div class="space-y-2">
          <label class="block text-[10px] tracking-widest uppercase text-on-surface-variant font-bold px-1">
            Email
          </label>
          <input
            v-model="email"
            type="email"
            required
            autocomplete="email"
            placeholder="you@example.com"
            class="w-full h-14 bg-black/5 dark:bg-white/5 border border-black/8 dark:border-white/10 rounded-2xl px-5 text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/40 transition-all"
          />
        </div>
        <button
          :disabled="isLoading"
          type="submit"
          class="w-full h-14 bg-gradient-to-br from-primary to-tertiary-container rounded-lg font-bold text-white uppercase tracking-wider active:scale-[0.98] transition-all disabled:opacity-50"
        >
          {{ isLoading ? 'Sending…' : 'Send reset link' }}
        </button>
      </form>

      <!-- Same message regardless of whether the email existed: prevents
           enumeration. -->
      <div v-else class="space-y-3 text-center">
        <div class="w-12 h-12 mx-auto rounded-full bg-emerald-500/15 flex items-center justify-center">
          <span class="material-symbols-outlined text-emerald-500">mark_email_read</span>
        </div>
        <p class="text-on-surface font-semibold">Check your inbox</p>
        <p class="text-on-surface-variant text-sm">
          If an account exists for <strong>{{ email }}</strong>, we just emailed a reset link.
          It expires in 30&nbsp;minutes.
        </p>
      </div>

      <div class="text-center">
        <router-link
          to="/login"
          class="text-xs font-semibold uppercase tracking-widest text-on-surface-variant hover:text-on-surface transition-colors"
        >
          Back to sign in
        </router-link>
      </div>
    </div>
  </main>
</template>

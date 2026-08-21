<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { useToastStore } from '@stores/toast'
import { API_URL } from '@typescript/constants'

// The reset link is /reset-password?token=<one-time-token>. The token is
// hashed server-side and consumed on use; this view just collects the
// new password and POSTs to /auth/reset-password.

const toast = useToastStore()
const route = useRoute()
const router = useRouter()

const token = computed(() => String(route.query.token ?? ''))
const newPassword = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const successful = ref(false)

// Mirrors the backend's StrongPassword rule so the user gets immediate
// feedback instead of a 422 round-trip.
const passwordIssue = computed<string | null>(() => {
  if (!newPassword.value) return null
  if (newPassword.value.length < 8) return 'At least 8 characters'
  if (!/[A-Za-z]/.test(newPassword.value)) return 'Must include a letter'
  if (!/\d/.test(newPassword.value)) return 'Must include a digit'
  if (confirmPassword.value && newPassword.value !== confirmPassword.value) {
    return 'Passwords do not match'
  }
  return null
})

const canSubmit = computed(
  () =>
    !!token.value &&
    !!newPassword.value &&
    newPassword.value === confirmPassword.value &&
    !passwordIssue.value &&
    !isLoading.value
)

const submit = async () => {
  if (!canSubmit.value) return
  isLoading.value = true
  try {
    await axios.post(`${API_URL}/auth/reset-password`, {
      token: token.value,
      new_password: newPassword.value,
    })
    successful.value = true
    toast.success('Password updated', 'You can now sign in with your new password.')
    setTimeout(() => router.push('/login'), 1500)
  } catch (err: any) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') {
      toast.error('Reset failed', detail)
    } else {
      toast.error('Reset failed', 'Please try requesting a new link.')
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <main class="relative z-10 w-full max-w-md px-6 py-12">
    <div class="relative glass-heavy rounded-3xl p-8 md:p-10 space-y-6">
      <div class="space-y-2 text-center">
        <h1 class="text-3xl font-extrabold tracking-tight text-on-surface">Choose a new password</h1>
        <p v-if="!token" class="text-error text-sm">
          This link is missing or malformed. Please request a new reset email.
        </p>
        <p v-else class="text-on-surface-variant text-sm">
          Pick something memorable but hard to guess. At least 8 characters with a letter and a digit.
        </p>
      </div>

      <form v-if="token && !successful" class="space-y-4" @submit.prevent="submit">
        <div class="space-y-2">
          <label class="block text-xs uppercase text-on-surface-variant font-bold px-1">
            New password
          </label>
          <input
            v-model="newPassword"
            type="password"
            required
            autocomplete="new-password"
            placeholder="••••••••"
            class="input"
          />
        </div>
        <div class="space-y-2">
          <label class="block text-xs uppercase text-on-surface-variant font-bold px-1">
            Confirm new password
          </label>
          <input
            v-model="confirmPassword"
            type="password"
            required
            autocomplete="new-password"
            placeholder="••••••••"
            class="input"
          />
        </div>

        <p v-if="passwordIssue" class="text-amber-500 text-sm">{{ passwordIssue }}</p>

        <button
          :disabled="!canSubmit"
          type="submit"
          class="w-full h-14 bg-gradient-to-br from-primary to-tertiary-container rounded-lg font-bold text-white uppercase active:scale-[0.98] transition-all disabled:opacity-50"
        >
          {{ isLoading ? 'Saving…' : 'Save new password' }}
        </button>
      </form>

      <div v-else-if="successful" class="space-y-3 text-center">
        <div class="size-12 mx-auto rounded-full bg-emerald-500/15 flex items-center justify-center">
          <span class="material-symbols-outlined text-emerald-500">verified</span>
        </div>
        <p class="text-on-surface font-semibold">Password updated</p>
        <p class="text-on-surface-variant text-sm">Redirecting to sign-in…</p>
      </div>

      <div class="text-center">
        <router-link
          to="/login"
          class="text-xs font-semibold uppercase text-on-surface-variant hover:text-on-surface transition-colors"
        >
          Back to sign in
        </router-link>
      </div>
    </div>
  </main>
</template>

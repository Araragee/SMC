<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@stores/auth'
import { useToastStore } from '@stores/toast'
import { API_URL } from '@typescript/constants'

// Used in two cases:
//   1) ``must_change_password`` is set on the user (default admin seed,
//      admin-initiated reset). The router gate redirects them here until
//      this form is completed.
//   2) Voluntary password change from the user-settings modal.
//
// In both cases the backend revokes every refresh token for the user,
// which kicks them back to the login page after a successful save.

const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()

const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)

const forced = computed(() => !!auth.user?.mustChangePassword)

const passwordIssue = computed<string | null>(() => {
  if (!newPassword.value) return null
  if (newPassword.value.length < 8) return 'At least 8 characters'
  if (!/[A-Za-z]/.test(newPassword.value)) return 'Must include a letter'
  if (!/\d/.test(newPassword.value)) return 'Must include a digit'
  if (newPassword.value === currentPassword.value) return 'New password must differ from the current one'
  if (confirmPassword.value && newPassword.value !== confirmPassword.value) {
    return 'Passwords do not match'
  }
  return null
})

const canSubmit = computed(
  () =>
    !!currentPassword.value &&
    !!newPassword.value &&
    newPassword.value === confirmPassword.value &&
    !passwordIssue.value &&
    !isLoading.value
)

const submit = async () => {
  if (!canSubmit.value) return
  isLoading.value = true
  try {
    await axios.post(`${API_URL}/auth/change-password`, {
      current_password: currentPassword.value,
      new_password: newPassword.value,
    })
    toast.success('Password updated', 'Please sign in again with your new password.')
    // Backend revoked the refresh token; force a clean local logout so
    // the next request doesn't hit a 401.
    await auth.logout()
    router.push('/login')
  } catch (err: any) {
    const detail = err.response?.data?.detail
    toast.error('Could not change password', typeof detail === 'string' ? detail : 'Try again')
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <main class="relative z-10 w-full max-w-md px-6 py-12">
    <div class="relative glass-heavy rounded-3xl p-8 md:p-10 space-y-6">
      <div class="space-y-2 text-center">
        <h1 class="text-3xl font-extrabold tracking-tight text-on-surface">
          {{ forced ? 'Set a new password' : 'Change password' }}
        </h1>
        <p v-if="forced" class="text-amber-500 text-sm font-semibold">
          Your account is using a temporary password — please choose a new one before continuing.
        </p>
        <p v-else class="text-on-surface-variant text-sm">
          You'll be signed out on all devices after this change.
        </p>
      </div>

      <form class="space-y-4" @submit.prevent="submit">
        <div class="space-y-2">
          <label class="block text-xs uppercase text-on-surface-variant font-bold px-1">
            Current password
          </label>
          <input
            v-model="currentPassword"
            type="password"
            required
            autocomplete="current-password"
            class="input"
          />
        </div>
        <div class="space-y-2">
          <label class="block text-xs uppercase text-on-surface-variant font-bold px-1">
            New password
          </label>
          <input
            v-model="newPassword"
            type="password"
            required
            autocomplete="new-password"
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
            class="input"
          />
        </div>

        <p v-if="passwordIssue" class="text-amber-500 text-sm">{{ passwordIssue }}</p>

        <button
          :disabled="!canSubmit"
          type="submit"
          class="w-full h-14 bg-primary hover:bg-primary-dim rounded-xl font-bold text-on-primary uppercase active:scale-[0.98] transition-all disabled:opacity-50"
        >
          {{ isLoading ? 'Saving…' : 'Save new password' }}
        </button>
      </form>
    </div>
  </main>
</template>

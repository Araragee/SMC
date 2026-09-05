<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useAuthStore } from '@stores/auth'
import BaseInput from '@components/BaseInput.vue'
import { useThemeStore } from '@stores/theme'
import { useRouter } from 'vue-router'
import TwoFASetupModal from '@components/TwoFASetupModal.vue'
import { apiError } from '@/utils/apiError'
import axios from 'axios'
import { useToastStore } from '@stores/toast'
import { API_URL } from '@typescript/constants'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const authStore = useAuthStore()
const themeStore = useThemeStore()
const router = useRouter()
const toast = useToastStore()

const isTwoFASetupOpen = ref(false)
const showDisableConfirm = ref(false)
const disableError = ref('')
const disableForm = reactive({
  password: '',
  code: '',
})

const form = reactive({
  name: '',
  email: '',
  currentPassword: '',
  password: '',
})

const passwordError = ref('')

// Initialize form when modal opens
watch(
  () => props.isOpen,
  (newVal) => {
    if (newVal && authStore.user) {
      form.name = authStore.user.name || ''
      form.email = authStore.user.email || ''
      form.password = ''
      form.currentPassword = ''
      passwordError.value = ''
      showDisableConfirm.value = false
      disableForm.password = ''
      disableForm.code = ''
      disableError.value = ''
    }
  },
  { immediate: true }
)

const handleSave = async () => {
  passwordError.value = ''

  // A password change goes through /auth/change-password, never the profile
  // endpoint: only that route re-checks the current password and revokes the
  // sessions held elsewhere. It signs this device out too, so it runs last.
  if (form.password) {
    if (!form.currentPassword) {
      passwordError.value = 'Enter your current password to change it'
      return
    }
    if (form.password.length < 8) {
      passwordError.value = 'New password must be at least 8 characters'
      return
    }
  }

  const success = await authStore.updateProfile({
    name: form.name,
    email: form.email,
  })
  if (!success) return

  if (!form.password) {
    emit('close')
    return
  }

  try {
    await axios.post(`${API_URL}/auth/change-password`, {
      current_password: form.currentPassword,
      new_password: form.password,
    })
    toast.success('Password updated', 'Please sign in again with your new password.')
    emit('close')
    await authStore.logout()
    router.push('/login')
  } catch (err: any) {
    const detail = err.response?.data?.detail
    passwordError.value = typeof detail === 'string' ? detail : 'Could not change password'
  }
}

const handleDisable2FA = async () => {
  disableError.value = ''
  try {
    const success = await authStore.disable2FA(disableForm.password, disableForm.code)
    if (success) {
      showDisableConfirm.value = false
      disableForm.password = ''
      disableForm.code = ''
    }
  } catch (err: any) {
    disableError.value = apiError(err, 'Deactivation failed')
  }
}

const handleLogout = () => {
  emit('close')
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 scale-95 translate-y-4 blur-[4px]"
      enter-to-class="opacity-100 scale-100 translate-y-0 blur-0"
      leave-active-class="transition-all duration-300 ease-in"
      leave-from-class="opacity-100 scale-100 translate-y-0 blur-0"
      leave-to-class="opacity-0 scale-95 translate-y-4 blur-[4px]"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[220] flex items-center justify-center p-4"
        @click.self="$emit('close')"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/40 dark:bg-black/70" @click="$emit('close')" />

        <!-- Modal Card -->
        <div
          class="modal-shell relative w-full max-w-xl glass-heavy rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        >
          <!-- Header -->
          <div class="flex items-start justify-between gap-4 px-5 pt-5 sm:px-8 sm:pt-7">
            <div class="min-w-0">
              <p class="text-xs font-semibold text-primary uppercase mb-1">Account Control</p>
              <h2 class="text-2xl sm:text-3xl font-semibold text-on-surface tracking-tight">
                User Settings
              </h2>
            </div>
            <button
              class="icon-btn shrink-0 bg-on-surface/5 hover:bg-on-surface/10"
              aria-label="Close settings"
              @click="$emit('close')"
            >
              <span class="material-symbols-outlined text-xl">close</span>
            </button>
          </div>

          <div class="flex-1 overflow-y-auto px-5 py-6 sm:px-8 custom-scrollbar">
            <!-- Identity -->
            <div class="flex items-center gap-4">
              <div
                class="size-14 shrink-0 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center overflow-hidden"
              >
                <img
                  v-if="authStore.user?.avatarUrl"
                  :src="authStore.user.avatarUrl"
                  alt=""
                  class="w-full h-full object-cover"
                />
                <span v-else class="text-xl font-semibold text-primary">{{
                  authStore.user?.name?.charAt(0).toUpperCase()
                }}</span>
              </div>
              <div class="min-w-0">
                <h3 class="text-base font-bold text-on-surface truncate">
                  {{ authStore.user?.name }}
                </h3>
                <p class="text-sm text-on-surface-variant truncate">{{ authStore.user?.email }}</p>
              </div>
              <span class="ml-auto shrink-0 text-xs font-semibold uppercase text-primary">{{
                authStore.user?.role
              }}</span>
            </div>

            <div class="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <BaseInput
                v-model="form.name"
                label="Full Name"
                placeholder="Your Name"
                icon-left="person"
              />
              <BaseInput
                v-model="form.email"
                label="Email Address"
                placeholder="email@smc.edu"
                icon-left="mail"
              />
            </div>

            <!-- Security -->
            <h3
              class="mt-9 mb-4 pb-2 border-b border-outline-variant/20 text-xs font-semibold uppercase text-on-surface-variant"
            >
              Security
            </h3>

            <BaseInput
              v-model="form.currentPassword"
              label="Current Password"
              type="password"
              placeholder="Required to change your password"
              icon-left="lock"
            />
            <div class="mt-4">
              <BaseInput
                v-model="form.password"
                label="New Password"
                type="password"
                placeholder="Enter new password"
                icon-left="lock"
              />
            </div>
            <p v-if="passwordError" class="field-error mt-2">{{ passwordError }}</p>
            <p class="mt-2 text-xs text-on-surface-variant leading-relaxed">
              Leave empty to keep your current password. New passwords must be at least 8
              characters, and changing it signs you out on every device.
            </p>

            <div class="mt-6 flex items-center justify-between gap-4">
              <div class="min-w-0">
                <h4 class="text-sm font-bold text-on-surface">Two-Factor Authentication</h4>
                <p class="text-xs text-on-surface-variant mt-0.5">
                  Secure your account with a TOTP code.
                </p>
              </div>
              <span
                class="shrink-0 text-xs font-semibold uppercase"
                :class="authStore.user?.totpEnabled ? 'text-success' : 'text-on-surface-variant'"
                >{{ authStore.user?.totpEnabled ? 'Active' : 'Inactive' }}</span
              >
            </div>

            <div v-if="authStore.user?.totpEnabled" class="mt-4">
              <button
                v-if="!showDisableConfirm"
                type="button"
                class="btn-subtle w-full text-error"
                @click="showDisableConfirm = true"
              >
                Deactivate 2FA
              </button>

              <div v-else class="space-y-4">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <BaseInput
                    v-model="disableForm.password"
                    label="Account Password"
                    type="password"
                    placeholder="Confirm password"
                    icon-left="lock"
                  />
                  <BaseInput
                    v-model="disableForm.code"
                    label="Authenticator Code"
                    type="text"
                    placeholder="000000"
                    icon-left="pin"
                  />
                </div>
                <p v-if="disableError" class="field-error">{{ disableError }}</p>
                <div class="flex flex-wrap justify-end gap-2">
                  <button
                    type="button"
                    class="btn-ghost btn-sm"
                    @click="showDisableConfirm = false"
                  >
                    Cancel
                  </button>
                  <button type="button" class="btn-danger btn-sm" @click="handleDisable2FA">
                    Confirm Deactivation
                  </button>
                </div>
              </div>
            </div>

            <button
              v-else
              type="button"
              class="btn-subtle w-full mt-4 text-primary"
              @click="isTwoFASetupOpen = true"
            >
              Set Up Authenticator
            </button>

            <!-- Appearance -->
            <h3
              class="mt-9 mb-4 pb-2 border-b border-outline-variant/20 text-xs font-semibold uppercase text-on-surface-variant"
            >
              Appearance
            </h3>

            <div class="flex rounded-2xl bg-on-surface/[0.04] dark:bg-on-surface/5 p-1 gap-1">
              <button
                v-for="opt in [
                  { value: 'system', icon: 'desktop_windows', label: 'System' },
                  { value: 'light', icon: 'light_mode', label: 'Light' },
                  { value: 'dark', icon: 'dark_mode', label: 'Dark' },
                ] as const"
                :key="opt.value"
                class="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-xs font-bold transition-colors"
                :class="
                  themeStore.preference === opt.value
                    ? 'bg-surface-container-lowest dark:bg-on-surface/15 text-primary shadow-sm'
                    : 'text-on-surface-variant hover:text-on-surface'
                "
                :aria-label="`Switch to ${opt.label} mode`"
                :aria-pressed="themeStore.preference === opt.value"
                @click="themeStore.setPreference(opt.value)"
              >
                <span
                  class="material-symbols-outlined text-base"
                  :style="
                    themeStore.preference === opt.value ? 'font-variation-settings: \'FILL\' 1' : ''
                  "
                  >{{ opt.icon }}</span
                >
                {{ opt.label }}
              </button>
            </div>

            <!-- Session -->
            <h3
              class="mt-9 mb-4 pb-2 border-b border-outline-variant/20 text-xs font-semibold uppercase text-on-surface-variant"
            >
              Session
            </h3>

            <button class="btn-subtle w-full justify-center gap-2" @click="handleLogout">
              <span class="material-symbols-outlined text-xl">logout</span>
              Sign Out
            </button>
          </div>

          <!-- Sticky Footer -->
          <div
            class="shrink-0 flex items-center justify-end gap-3 px-5 py-4 sm:px-8 border-t border-on-surface/5 bg-on-surface/[0.02]"
          >
            <button class="btn-ghost" @click="$emit('close')">Cancel</button>
            <button :disabled="authStore.isLoading" class="btn-primary gap-2" @click="handleSave">
              <span
                v-if="authStore.isLoading"
                class="material-symbols-outlined animate-spin text-sm"
                >progress_activity</span
              >
              {{ authStore.isLoading ? 'Saving…' : 'Save Changes' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <TwoFASetupModal
    v-if="isTwoFASetupOpen"
    :is-open="isTwoFASetupOpen"
    @close="isTwoFASetupOpen = false"
    @success="isTwoFASetupOpen = false"
  />
</template>

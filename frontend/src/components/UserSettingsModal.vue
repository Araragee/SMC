<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useAuthStore } from '@stores/auth'
import BaseInput from '@components/BaseInput.vue'
import { useThemeStore } from '@stores/theme'
import { useRouter } from 'vue-router'
import TwoFASetupModal from '@components/TwoFASetupModal.vue'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const authStore = useAuthStore()
const themeStore = useThemeStore()
const router = useRouter()

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
  avatar_url: '',
  password: '',
})

// Initialize form when modal opens
watch(
  () => props.isOpen,
  (newVal) => {
    if (newVal && authStore.user) {
      form.name = authStore.user.name || ''
      form.email = authStore.user.email || ''
      form.avatar_url = authStore.user.avatarUrl || ''
      form.password = ''
      showDisableConfirm.value = false
      disableForm.password = ''
      disableForm.code = ''
      disableError.value = ''
    }
  },
  { immediate: true }
)

const handleSave = async () => {
  const payload: any = {
    name: form.name,
    email: form.email,
  }

  if (form.avatar_url) payload.avatar_url = form.avatar_url
  if (form.password) payload.password = form.password

  const success = await authStore.updateProfile(payload)
  if (success) {
    emit('close')
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
    disableError.value = err.response?.data?.detail || err.message || 'Deactivation failed'
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
        <div class="absolute inset-0 bg-on-surface/30 dark:bg-on-surface/80" @click="$emit('close')" />

        <!-- Modal Card -->
        <div
          class="relative w-full max-w-xl glass-heavy rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        >
          <!-- Decorative Header -->
          <div
            class="h-2 w-full bg-primary"
          ></div>

          <!-- Header Section -->
          <div class="p-8 pb-0 flex items-start justify-between">
            <div>
              <p class="text-xs font-semibold text-primary uppercase mb-2">
                Account Control
              </p>
              <h2 class="text-3xl font-semibold text-on-surface dark:text-on-surface tracking-tight">User Settings</h2>
            </div>
            <button
              class="size-12 rounded-2xl bg-on-surface/5 dark:bg-on-surface/5 hover:bg-on-surface/10 dark:hover:bg-on-surface/10 border border-on-surface/8 dark:border-on-surface/10 flex items-center justify-center text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-all group"
              @click="$emit('close')"
            >
              <span
                class="material-symbols-outlined text-xl group-hover:rotate-90 transition-transform duration-300"
                >close</span
              >
            </button>
          </div>

          <div class="flex-1 overflow-y-auto p-8 pt-6 space-y-10 custom-scrollbar">
            <!-- Profile Overview -->
            <section class="space-y-6">
              <div class="flex items-center gap-6">
                <div class="relative group">
                  <div
                    class="size-24 rounded-3xl bg-primary/10 border-2 border-dashed border-primary/30 flex items-center justify-center overflow-hidden transition-all group-hover:border-primary/60"
                  >
                    <img
                      v-if="form.avatar_url || authStore.user?.avatarUrl"
                      :src="form.avatar_url || authStore.user?.avatarUrl"
                      class="w-full h-full object-cover"
                    />
                    <span v-else class="text-3xl font-semibold text-primary/40">{{
                      authStore.user?.name?.charAt(0).toUpperCase()
                    }}</span>

                    <!-- Overlay for upload (mock) -->
                    <div
                      class="absolute inset-0 bg-on-surface/30 dark:bg-on-surface/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer"
                    >
                      <span class="material-symbols-outlined text-on-surface dark:text-on-surface text-2xl">add_a_photo</span>
                    </div>
                  </div>
                </div>
                <div>
                  <h3 class="text-xl font-bold text-on-surface dark:text-on-surface mb-1">{{ authStore.user?.name }}</h3>
                  <p class="text-on-surface-variant dark:text-on-surface-variant text-sm font-medium">{{ authStore.user?.email }}</p>
                  <div
                    class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 mt-3"
                  >
                    <span class="text-xs font-semibold text-primary uppercase">{{
                      authStore.user?.role
                    }}</span>
                  </div>
                </div>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
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

              <BaseInput
                v-model="form.avatar_url"
                label="Avatar URL"
                placeholder="https://..."
                icon-left="image"
              />
            </section>

            <!-- Security Section -->
            <section class="space-y-6">
              <div class="flex items-center gap-3 px-1">
                <span class="material-symbols-outlined text-primary text-lg">security</span>
                <h3 class="text-sm font-semibold text-on-surface dark:text-on-surface uppercase">
                  Security &amp; Privacy
                </h3>
              </div>

              <div
                class="bg-surface-container-low dark:bg-surface-container-low border border-outline-variant dark:border-outline-variant rounded-3xl p-6 space-y-6"
              >
                <BaseInput
                  v-model="form.password"
                  label="Change Password"
                  type="password"
                  placeholder="Enter new password"
                  icon-left="lock"
                />
                <p class="text-xs text-on-surface-variant dark:text-on-surface-variant font-medium px-2 italic leading-relaxed">
                  Leave the password field empty if you don't wish to change it. Your new password
                  must be at least 8 characters long.
                </p>
              </div>

              <!-- Two-Factor Authentication Sub-block -->
              <div class="bg-surface-container-low dark:bg-surface-container-low border border-outline-variant dark:border-outline-variant rounded-3xl p-6 space-y-4">
                <div class="flex items-center justify-between">
                  <div>
                    <h4 class="text-on-surface dark:text-on-surface font-bold text-sm">Two-Factor Authentication</h4>
                    <p class="text-on-surface-variant dark:text-on-surface-variant text-xs mt-1">
                      Secure your account with a secondary TOTP code.
                    </p>
                  </div>
                  <div>
                    <span
                      v-if="authStore.user?.totpEnabled"
                      class="px-2 py-1 rounded-full text-xs font-semibold uppercase bg-emerald-500/20 border border-emerald-500/30 text-emerald-400"
                    >
                      Active
                    </span>
                    <span
                      v-else
                      class="px-2 py-1 rounded-full text-xs font-semibold uppercase bg-zinc-500/20 border border-zinc-500/30 text-zinc-400"
                    >
                      Inactive
                    </span>
                  </div>
                </div>

                <div v-if="authStore.user?.totpEnabled" class="space-y-4">
                  <button
                    v-if="!showDisableConfirm"
                    type="button"
                    class="w-full py-3 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-500 font-semibold rounded-2xl text-xs uppercase transition-all"
                    @click="showDisableConfirm = true"
                  >
                    Deactivate 2FA
                  </button>
                  
                  <!-- Disable Confirmation Form -->
                  <div v-else class="space-y-4 pt-4 border-t border-outline-variant/10">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                    <p v-if="disableError" class="text-error text-xs font-bold">{{ disableError }}</p>
                    <div class="flex gap-2 justify-end">
                      <button
                        type="button"
                        class="px-4 py-2 text-xs font-bold text-on-surface-variant hover:text-on-surface transition-colors"
                        @click="showDisableConfirm = false"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        class="px-4 py-2 bg-red-500 text-on-surface text-xs font-semibold rounded-xl uppercase hover:bg-red-600 transition-all"
                        @click="handleDisable2FA"
                      >
                        Confirm Deactivation
                      </button>
                    </div>
                  </div>
                </div>

                <div v-else>
                  <button
                    type="button"
                    class="w-full py-3 bg-primary/10 hover:bg-primary/20 border border-primary/20 text-primary font-semibold rounded-2xl text-xs uppercase transition-all"
                    @click="isTwoFASetupOpen = true"
                  >
                    Set Up Authenticator
                  </button>
                </div>
              </div>
            </section>

            <!-- Appearance Section -->
            <section class="space-y-6">
              <div class="flex items-center gap-3 px-1">
                <span class="material-symbols-outlined text-primary text-lg">palette</span>
                <h3
                  class="text-sm font-semibold text-on-surface dark:text-on-surface uppercase"
                >
                  Appearance
                </h3>
              </div>

              <div
                class="bg-surface-container-low dark:bg-surface-container-low border border-outline-variant dark:border-outline-variant rounded-3xl p-6 space-y-4"
              >
                <div>
                  <h4 class="text-on-surface font-bold text-sm">Color Theme</h4>
                  <p class="text-on-surface-variant text-xs mt-1">
                    Choose how Sernan's Music Clinic appears on your device.
                  </p>
                </div>
                <!-- 3-Way Theme Picker -->
                <div class="flex rounded-2xl bg-on-surface/[0.04] dark:bg-on-surface/5 border border-on-surface/[0.06] dark:border-on-surface/8 p-1 gap-1">
                  <button
                    v-for="opt in ([
                      { value: 'system', icon: 'desktop_windows', label: 'System' },
                      { value: 'light', icon: 'light_mode', label: 'Light' },
                      { value: 'dark', icon: 'dark_mode', label: 'Dark' },
                    ] as const)"
                    :key="opt.value"
                    class="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold transition-all duration-300"
                    :class="themeStore.preference === opt.value ? 'bg-surface-container-lowest dark:bg-on-surface/15 text-primary dark:text-primary shadow-sm border border-on-surface/[0.06] dark:border-on-surface/10' : 'text-on-surface-variant hover:text-on-surface hover:bg-on-surface/[0.04] dark:hover:bg-on-surface/5'"
                    :aria-label="`Switch to ${opt.label} mode`"
                    :aria-pressed="themeStore.preference === opt.value"
                    @click="themeStore.setPreference(opt.value)"
                  >
                    <span class="material-symbols-outlined text-base" :style="themeStore.preference === opt.value ? 'font-variation-settings: \'FILL\' 1' : ''">{{ opt.icon }}</span>
                    {{ opt.label }}
                  </button>
                </div>
              </div>
            </section>

            <!-- Danger Zone -->
            <section class="space-y-4">
              <div class="flex items-center gap-3 px-1">
                <span class="material-symbols-outlined text-red-500 text-lg">warning</span>
                <h3 class="text-sm font-semibold text-red-500 uppercase">
                  Danger Zone
                </h3>
              </div>
              <div class="bg-red-500/5 border border-red-500/10 rounded-3xl p-6">
                <button
                  class="w-full py-4 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-500 font-semibold rounded-2xl transition-all flex items-center justify-center gap-3 group"
                  @click="handleLogout"
                >
                  <span
                    class="material-symbols-outlined text-xl group-hover:translate-x-1 transition-transform"
                    >logout</span
                  >
                  SIGN OUT FROM THIS SESSION
                </button>
              </div>
            </section>
          </div>

          <!-- Sticky Footer -->
          <div
            class="p-8 border-t border-on-surface/5 dark:border-on-surface/5 bg-on-surface/[0.02] dark:bg-on-surface/[0.02] flex items-center justify-end gap-4 shrink-0"
          >
            <button
              class="px-6 py-3 text-sm font-bold text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-colors"
              @click="$emit('close')"
            >
              Cancel
            </button>
            <button
              :disabled="authStore.isLoading"
              class="px-10 py-3 bg-primary text-on-primary dark:text-on-surface font-semibold rounded-2xl shadow-lg transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:scale-100 flex items-center gap-2"
              @click="handleSave"
            >
              <span
                v-if="authStore.isLoading"
                class="material-symbols-outlined animate-spin text-sm"
                >progress_activity</span
              >
              {{ authStore.isLoading ? 'SAVING...' : 'SAVE CHANGES' }}
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

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@stores/auth'
import { useToastStore } from '@stores/toast'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
  success: []
}>()

const authStore = useAuthStore()
const toast = useToastStore()

const loading = ref(true)
const errorMsg = ref('')
const setupData = ref<{ secret: string; provisioning_uri: string; qr_code_png_base64: string } | null>(null)
const code = ref('')
const isEnabling = ref(false)
const isCopied = ref(false)

const loadSetup = async () => {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await authStore.setup2FA()
    setupData.value = data
  } catch (err: any) {
    errorMsg.value = err.response?.data?.detail || err.message || 'Failed to initialize 2FA setup'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (props.isOpen) {
    loadSetup()
  }
})

const handleCopySecret = async () => {
  if (!setupData.value?.secret) return
  try {
    await navigator.clipboard.writeText(setupData.value.secret)
    isCopied.value = true
    setTimeout(() => {
      isCopied.value = false
    }, 2000)
    toast.success('Copied', 'Secret key copied to clipboard.')
  } catch {
    toast.error('Copy failed', 'Please copy the key manually.')
  }
}

const handleConfirm = async () => {
  if (code.value.length < 6) {
    errorMsg.value = 'Please enter a 6-digit code'
    return
  }
  isEnabling.value = true
  errorMsg.value = ''
  try {
    const success = await authStore.enable2FA(code.value)
    if (success) {
      emit('success')
    }
  } catch (err: any) {
    errorMsg.value = err.response?.data?.detail || err.message || 'Invalid confirmation code'
  } finally {
    isEnabling.value = false
  }
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
        class="fixed inset-0 z-[230] flex items-center justify-center p-4"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/40 dark:bg-black/70" @click="$emit('close')" />

        <!-- Modal Card -->
        <div class="relative w-full max-w-lg glass-heavy rounded-3xl shadow-2xl overflow-hidden flex flex-col p-8 max-h-[90vh]">

          <!-- Header -->
          <div class="flex justify-between items-start mt-4">
            <div>
              <p class="text-xs font-semibold text-primary uppercase mb-1">Security Setup</p>
              <h2 class="text-2xl font-semibold text-on-surface dark:text-on-surface tracking-tight">Enable 2FA</h2>
            </div>
            <button
              class="icon-btn"
              @click="$emit('close')"
            >
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <!-- Content Area (Scrollable if needed) -->
          <div class="flex-1 overflow-y-auto space-y-6 pt-4 pr-1 custom-scrollbar">
            <!-- Loading state -->
            <div v-if="loading" class="flex flex-col items-center justify-center py-12 space-y-4">
              <div class="size-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
              <p class="text-xs font-bold text-on-surface-variant uppercase">Generating keys...</p>
            </div>

            <!-- Main Setup UI -->
            <div v-else-if="setupData" class="space-y-6">
              <!-- Step 1: Scan QR Code -->
              <div class="space-y-3">
                <h4 class="text-xs font-semibold text-on-surface dark:text-on-surface uppercase">
                  1. Scan this QR Code
                </h4>
                <p class="text-xs text-on-surface-variant dark:text-on-surface-variant leading-relaxed">
                  Open your authenticator app (Google Authenticator, Microsoft Authenticator, 1Password, Duo, etc.) and scan the QR code below.
                </p>
                <div class="flex items-center justify-center p-4 bg-surface-container-lowest rounded-3xl size-48 mx-auto border border-on-surface/5 dark:border-on-surface/10 shadow-lg">
                  <img :src="`data:image/png;base64,${setupData.qr_code_png_base64}`" alt="2FA QR Code" class="w-full h-full object-contain" />
                </div>
              </div>

              <!-- Step 2: Manual Key backup -->
              <div class="space-y-3">
                <h4 class="text-xs font-semibold text-on-surface dark:text-on-surface uppercase">
                  2. Or enter the Secret Key manually
                </h4>
                <p class="text-xs text-on-surface-variant dark:text-on-surface-variant leading-relaxed">
                  If you cannot scan the QR code, type this secret key into your authenticator app.
                </p>
                <div class="flex items-center justify-between gap-3 bg-on-surface/5 dark:bg-on-surface/5 border border-on-surface/8 dark:border-on-surface/10 rounded-2xl p-4">
                  <span class="font-mono text-sm font-bold text-on-surface select-all overflow-x-auto break-all">{{ setupData.secret }}</span>
                  <button
                    type="button"
                    class="px-4 py-2 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 rounded-xl text-xs font-semibold uppercase transition-all"
                    @click="handleCopySecret"
                  >
                    {{ isCopied ? 'Copied!' : 'Copy' }}
                  </button>
                </div>
              </div>

              <!-- Step 3: Enter confirmation code -->
              <div class="space-y-3">
                <h4 class="text-xs font-semibold text-on-surface dark:text-on-surface uppercase">
                  3. Enter Authenticator Code
                </h4>
                <p class="text-xs text-on-surface-variant dark:text-on-surface-variant leading-relaxed">
                  Enter the 6-digit code shown in your authenticator app to verify the setup.
                </p>
                <input
                  v-model="code"
                  type="text"
                  maxlength="6"
                  pattern="[0-9]*"
                  inputmode="numeric"
                  placeholder="000000"
                  class="input text-center"
                  @input="code = code.replace(/[^0-9]/g, '')"
                />
              </div>

              <p v-if="errorMsg" class="text-error dark:text-error text-xs text-center font-bold">{{ errorMsg }}</p>
            </div>

            <!-- Error fallback -->
            <div v-else class="py-8 text-center space-y-4">
              <span class="material-symbols-outlined text-red-500 text-5xl">warning</span>
              <p class="text-sm font-bold text-on-surface">{{ errorMsg || 'An unexpected error occurred' }}</p>
              <button
                type="button"
                class="px-6 py-3 bg-primary text-on-surface font-bold rounded-2xl text-xs uppercase"
                @click="loadSetup"
              >
                Retry
              </button>
            </div>
          </div>

          <!-- Footer -->
          <div class="pt-6 border-t border-on-surface/5 dark:border-on-surface/5 bg-on-surface/[0.02] dark:bg-on-surface/[0.02] -mx-8 -mb-8 p-8 flex items-center justify-end gap-4 shrink-0">
            <button
              class="px-6 py-3 text-sm font-bold text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface transition-colors"
              @click="$emit('close')"
            >
              Cancel
            </button>
            <button
              v-if="setupData"
              :disabled="isEnabling || code.length < 6"
              class="px-10 py-3 bg-primary text-on-primary font-semibold rounded-2xl shadow-lg transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:scale-100 flex items-center gap-2"
              @click="handleConfirm"
            >
              <span v-if="isEnabling" class="material-symbols-outlined animate-spin text-sm">progress_activity</span>
              {{ isEnabling ? 'VERIFYING...' : 'CONFIRM & ACTIVATE' }}
            </button>
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

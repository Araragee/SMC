<script setup lang="ts">
import BaseModal from '@components/BaseModal.vue'
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
const setupData = ref<{
  secret: string
  provisioning_uri: string
  qr_code_png_base64: string
} | null>(null)
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
  <BaseModal
    :is-open="isOpen"
    size="lg"
    layer="raised"
    eyebrow="Security Setup"
    title="Enable 2FA"
    close-label="Close two-factor setup"
    @close="$emit('close')"
  >
      <div v-if="loading" class="flex flex-col items-center justify-center py-12 space-y-4">
        <div
          class="size-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin"
        ></div>
        <p class="text-xs font-bold text-on-surface-variant uppercase">Generating keys...</p>
      </div>

      <div v-else-if="setupData" class="space-y-6">
        <!-- Step 1: Scan QR Code -->
        <div class="space-y-3">
          <h4 class="text-xs font-semibold text-on-surface uppercase">
            1. Scan this QR Code
          </h4>
          <p class="text-xs text-on-surface-variant leading-relaxed">
            Open your authenticator app (Google Authenticator, Microsoft Authenticator,
            1Password, Duo, etc.) and scan the QR code below.
          </p>
          <div
            class="flex items-center justify-center p-4 bg-surface-container-lowest rounded-3xl size-48 mx-auto border border-on-surface/5 dark:border-on-surface/10 shadow-lg"
          >
            <img
              :src="`data:image/png;base64,${setupData.qr_code_png_base64}`"
              alt="2FA QR Code"
              class="w-full h-full object-contain"
            />
          </div>
        </div>

        <!-- Step 2: Manual Key backup -->
        <div class="space-y-3">
          <h4 class="text-xs font-semibold text-on-surface uppercase">
            2. Or enter the Secret Key manually
          </h4>
          <p class="text-xs text-on-surface-variant leading-relaxed">
            If you cannot scan the QR code, type this secret key into your authenticator app.
          </p>
          <div
            class="flex items-center justify-between gap-3 bg-on-surface/5 border border-on-surface/8 dark:border-on-surface/10 rounded-2xl p-4"
          >
            <span
              class="font-mono text-sm font-bold text-on-surface select-all overflow-x-auto break-all"
              >{{ setupData.secret }}</span
            >
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
          <h4 class="text-xs font-semibold text-on-surface uppercase">
            3. Enter Authenticator Code
          </h4>
          <p class="text-xs text-on-surface-variant leading-relaxed">
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

        <p v-if="errorMsg" class="text-error text-xs text-center font-bold">{{ errorMsg }}</p>
      </div>

      <div v-else class="py-8 text-center space-y-4">
        <span class="material-symbols-outlined text-error text-5xl">warning</span>
        <p class="text-sm font-bold text-on-surface">
          {{ errorMsg || 'An unexpected error occurred' }}
        </p>
        <button
          type="button"
          class="px-6 py-3 bg-primary text-on-primary font-bold rounded-2xl text-xs uppercase"
          @click="loadSetup"
        >
          Retry
        </button>
      </div>

    <template #footer>
      <button class="btn-ghost" @click="$emit('close')">Cancel</button>
      <button
        v-if="setupData"
        :disabled="isEnabling || code.length < 6"
        class="btn-primary gap-2"
        @click="handleConfirm"
      >
        <span v-if="isEnabling" class="material-symbols-outlined animate-spin text-sm"
          >progress_activity</span
        >
        {{ isEnabling ? 'Verifying…' : 'Confirm & activate' }}
      </button>
    </template>
  </BaseModal>
</template>

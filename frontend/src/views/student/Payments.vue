<script setup lang="ts">
import { computed, onMounted } from 'vue'
import axios from 'axios'
import { usePaymentsStore } from '@stores/payments'
import { useAuthStore } from '@stores/auth'
import { useToastStore } from '@stores/toast'
import { API_URL } from '@typescript/constants'

const paymentsStore = usePaymentsStore()
const authStore = useAuthStore()
const toast = useToastStore()

onMounted(async () => {
  await paymentsStore.fetchPayments()
})

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' }).format(amount / 100)
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', year: 'numeric'
  })
}

const statusClass = (status: string) => {
  switch (status.toLowerCase()) {
    case 'completed': return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
    case 'pending':   return 'bg-amber-500/10 text-amber-500 border-amber-500/20'
    case 'failed':    return 'bg-rose-500/10 text-rose-500 border-rose-500/20'
    default:          return 'bg-zinc-500/10 text-zinc-500 border-zinc-500/20'
  }
}

const paymentLabel = (pay: { notes?: string | null; method: string }) => {
  return pay.notes?.trim() || 'Session / Enrollment Fee'
}

async function printReceipt(paymentId: number) {
  try {
    const res = await axios.get(`${API_URL}/payments/${paymentId}/receipt.html`, {
      headers: authStore.token ? { Authorization: `Bearer ${authStore.token}` } : {},
      responseType: 'blob',
    })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'text/html' }))
    const win = window.open(url, '_blank', 'noopener,noreferrer')
    setTimeout(() => URL.revokeObjectURL(url), 10_000)
    if (!win) toast.error('Popup blocked', 'Please allow popups to view the receipt.')
  } catch {
    toast.error('Receipt unavailable', 'Could not load the receipt. Please try again.')
  }
}

const totalPaid = computed(() =>
  paymentsStore.payments
    .filter(p => p.status.toLowerCase() === 'completed')
    .reduce((s, p) => s + p.amount, 0)
)
</script>

<template>
  <div class="max-w-[1000px] mx-auto pb-28 space-y-10 px-4 sm:px-6">
    <header class="pt-8">
      <div class="flex items-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
          <span class="material-symbols-outlined text-emerald-500 text-2xl">account_balance_wallet</span>
        </div>
        <p class="text-[10px] font-black text-emerald-500 uppercase tracking-[0.25em]">Financial Balance</p>
      </div>
      <h1 class="text-5xl font-black tracking-tight text-on-surface mb-2">My Payments</h1>
      <p class="text-on-surface-variant font-medium text-lg">Detailed history of your course enrollments and settlement status.</p>
    </header>

    <!-- Summary card -->
    <div v-if="paymentsStore.payments.length > 0" class="grid grid-cols-2 sm:grid-cols-3 gap-4">
      <div class="glass-medium rounded-3xl p-5 border border-outline-variant/30">
        <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-1">Total Paid</p>
        <p class="text-2xl font-black text-emerald-500">{{ formatCurrency(totalPaid) }}</p>
      </div>
      <div class="glass-medium rounded-3xl p-5 border border-outline-variant/30">
        <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-1">Transactions</p>
        <p class="text-2xl font-black text-on-surface">{{ paymentsStore.payments.length }}</p>
      </div>
      <div class="glass-medium rounded-3xl p-5 border border-outline-variant/30 col-span-2 sm:col-span-1">
        <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-1">Pending</p>
        <p class="text-2xl font-black text-amber-500">{{ paymentsStore.pendingCount }}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6">
      <!-- Loading skeleton -->
      <div v-if="paymentsStore.isLoading" class="space-y-4">
        <div
          v-for="i in 3" :key="i"
          class="glass-medium rounded-3xl p-6 border border-outline-variant/20 flex items-center gap-4 animate-pulse"
        >
          <div class="w-12 h-12 rounded-2xl bg-on-surface/5 shrink-0" />
          <div class="flex-1 space-y-2">
            <div class="h-3 rounded-full bg-on-surface/5 w-24" />
            <div class="h-4 rounded-full bg-on-surface/5 w-48" />
            <div class="h-3 rounded-full bg-on-surface/5 w-16" />
          </div>
          <div class="h-6 rounded-full bg-on-surface/5 w-20" />
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="paymentsStore.payments.length === 0"
        class="glass-medium rounded-[3rem] p-20 text-center border-dashed border-2 border-outline-variant/30"
      >
        <span class="material-symbols-outlined text-5xl text-on-surface-variant/20 mb-4">history</span>
        <p class="text-lg font-black text-on-surface">No transaction history</p>
        <p class="text-sm text-on-surface-variant">Your payment records will appear here once processed by admin.</p>
      </div>

      <!-- Payment list -->
      <div v-else class="space-y-4">
        <div
          v-for="pay in paymentsStore.payments"
          :key="pay.id"
          class="glass-heavy rounded-3xl p-6 border border-outline-variant/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-emerald-500/30 transition-all hover:translate-x-1"
        >
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-2xl bg-surface-container-highest flex items-center justify-center shrink-0">
              <span class="material-symbols-outlined text-on-surface-variant">receipt</span>
            </div>
            <div>
              <p class="text-xs font-black text-on-surface-variant uppercase tracking-widest">{{ formatDate(pay.date) }}</p>
              <h4 class="text-lg font-black text-on-surface">{{ paymentLabel(pay) }}</h4>
              <p class="text-xs text-on-surface-variant font-medium">via {{ pay.method.toUpperCase() }}</p>
            </div>
          </div>

          <div class="flex flex-row sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-2">
            <span class="text-2xl font-black text-on-surface">{{ formatCurrency(pay.amount) }}</span>
            <div class="flex items-center gap-2">
              <span
                class="px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-wider border"
                :class="statusClass(pay.status)"
              >
                {{ pay.status }}
              </span>
              <button
                @click="printReceipt(pay.id)"
                title="Print Receipt"
                class="w-7 h-7 rounded-xl bg-on-surface/5 hover:bg-on-surface/10 flex items-center justify-center transition-colors"
              >
                <span class="material-symbols-outlined text-on-surface-variant text-base">print</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.glass-heavy {
  @apply bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl shadow-lg;
}
.glass-medium {
  @apply bg-white/40 dark:bg-white/5 backdrop-blur-md;
}
</style>

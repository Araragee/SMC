<script setup lang="ts">
import { onMounted } from 'vue'
import { usePaymentsStore } from '../../stores/payments'

const paymentsStore = usePaymentsStore()

onMounted(async () => {
  await paymentsStore.fetchPayments()
})

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount / 100)
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', year: 'numeric'
  })
}
</script>

<template>
  <div class="max-w-[1000px] mx-auto pb-28 space-y-10 px-4 sm:px-6   ">
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

    <div class="grid grid-cols-1 gap-6">
      <div v-if="paymentsStore.payments.length === 0" class="glass-medium rounded-[3rem] p-20 text-center border-dashed border-2 border-outline-variant/30">
        <span class="material-symbols-outlined text-5xl text-on-surface-variant/20 mb-4">history</span>
        <p class="text-lg font-black text-on-surface">No transaction history</p>
        <p class="text-sm text-on-surface-variant">Your payment records will appear here once processed by admin.</p>
      </div>

      <div v-else class="space-y-4">
        <div 
          v-for="pay in paymentsStore.payments" 
          :key="pay.id"
          class="glass-heavy rounded-3xl p-6 border border-outline-variant/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-emerald-500/30 transition-all hover:translate-x-1"
        >
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-2xl bg-surface-container-highest flex items-center justify-center">
              <span class="material-symbols-outlined text-on-surface-variant">receipt</span>
            </div>
            <div>
              <p class="text-xs font-black text-on-surface-variant uppercase tracking-widest">{{ formatDate(pay.date) }}</p>
              <h4 class="text-lg font-black text-on-surface">Course Enrollment Fee</h4>
              <p class="text-xs text-on-surface-variant font-medium">via {{ pay.method.toUpperCase() }}</p>
            </div>
          </div>
          
          <div class="flex flex-row sm:flex-col items-center sm:items-end justify-between sm:justify-center">
            <span class="text-2xl font-black text-on-surface">{{ formatCurrency(pay.amount) }}</span>
            <span class="px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-wider bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 mt-1">
              {{ pay.status }}
            </span>
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

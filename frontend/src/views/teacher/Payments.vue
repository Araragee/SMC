<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { usePaymentsStore } from '../../stores/payments'
import { useUsersStore } from '../../stores/users'
import { useToastStore } from '../../stores/toast'

const paymentsStore = usePaymentsStore()
const usersStore = useUsersStore()
const toast = useToastStore()

onMounted(async () => {
  await Promise.all([
    paymentsStore.fetchPayments(),
    usersStore.fetchUsersByRole('student')
  ])
})

const getStudentName = (id: number) => {
  const s = usersStore.users.find(u => String(u.id) === String(id))
  return s ? s.name : `Student #${id}`
}

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount / 100)
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric'
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
</script>

<template>
  <div class="max-w-[1600px] mx-auto pb-28 space-y-8 px-4 sm:px-6 animate-in fade-in duration-700">
    <!-- Header -->
    <header class="flex flex-col md:flex-row md:items-end justify-between gap-6 py-8">
      <div>
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
            <span class="material-symbols-outlined text-primary text-2xl">payments</span>
          </div>
          <p class="text-[10px] font-black text-primary uppercase tracking-[0.25em]">Financial Ledger</p>
        </div>
        <h1 class="text-5xl font-black tracking-tight text-on-surface mb-2">Earnings & Payments</h1>
        <p class="text-on-surface-variant font-medium text-lg">
          Track course enrollments and student payments for your roster.
        </p>
      </div>
      
      <div class="flex gap-4">
        <div class="glass-medium rounded-[2rem] px-8 py-4 border border-outline-variant/30 flex flex-col items-center">
          <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-1">Total Distributed</p>
          <p class="text-3xl font-black text-primary">{{ formatCurrency(paymentsStore.payments.reduce((s, p) => s + p.amount, 0)) }}</p>
        </div>
      </div>
    </header>

    <!-- Ledger Table -->
    <section class="glass-heavy rounded-[2.5rem] border border-outline-variant/30 overflow-hidden shadow-2xl shadow-black/5 dark:shadow-black/20">
      <div v-if="paymentsStore.isLoading" class="p-24 text-center">
        <span class="material-symbols-outlined text-5xl animate-spin text-primary/40">progress_activity</span>
      </div>
      
      <div v-else-if="paymentsStore.payments.length === 0" class="py-32 text-center">
        <div class="w-20 h-20 rounded-full bg-surface-container-highest/50 flex items-center justify-center mx-auto mb-6">
          <span class="material-symbols-outlined text-5xl text-on-surface-variant/30">receipt_long</span>
        </div>
        <p class="text-xl font-black text-on-surface">No transactions found</p>
        <p class="text-on-surface-variant mt-2 font-medium">When students complete enrollments, they will appear here.</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="text-[10px] font-black text-on-surface-variant uppercase tracking-[0.25em] bg-surface-container-highest/20">
              <th class="py-6 px-8">Transaction Date</th>
              <th class="py-6 px-8">Student Identity</th>
              <th class="py-6 px-8">Gateway / Method</th>
              <th class="py-6 px-8">Status</th>
              <th class="py-6 px-8 text-right">Settlement Amount</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/10">
            <tr v-for="pay in paymentsStore.payments" :key="pay.id" class="group hover:bg-primary/[0.02] transition-colors">
              <td class="py-6 px-8 text-sm font-bold text-on-surface">{{ formatDate(pay.date) }}</td>
              <td class="py-6 px-8">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-lg bg-surface-container-highest flex items-center justify-center text-[10px] font-black">
                    {{ getStudentName(pay.student_id).charAt(0).toUpperCase() }}
                  </div>
                  <span class="text-sm font-bold text-on-surface">{{ getStudentName(pay.student_id) }}</span>
                </div>
              </td>
              <td class="py-6 px-8">
                <span class="text-xs font-medium text-on-surface-variant flex items-center gap-2">
                  <span class="material-symbols-outlined text-sm opacity-50">{{ pay.method === 'card' ? 'credit_card' : 'account_balance' }}</span>
                  {{ pay.method.toUpperCase().replace('_', ' ') }}
                </span>
              </td>
              <td class="py-6 px-8">
                <span class="px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-wider border" :class="statusClass(pay.status)">
                  {{ pay.status }}
                </span>
              </td>
              <td class="py-6 px-8 text-right text-lg font-black text-on-surface">
                {{ formatCurrency(pay.amount) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.glass-heavy {
  @apply bg-white/70 dark:bg-zinc-900/70 backdrop-blur-xl shadow-2xl;
}
.glass-medium {
  @apply bg-white/40 dark:bg-white/5 backdrop-blur-md;
}
</style>

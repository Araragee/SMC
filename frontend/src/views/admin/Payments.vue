<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePaymentsStore } from '@stores/payments'
import { useUsersStore } from '@stores/users'
import { useToastStore } from '@stores/toast'

const paymentsStore = usePaymentsStore()
const usersStore = useUsersStore()
const toast = useToastStore()

// ── filters & search ──────────────────────────────────────────────────────────
const search = ref('')
const statusFilter = ref('all')
const methodFilter = ref('all')
const sortBy = ref('date-desc')

// ── add payment modal ─────────────────────────────────────────────────────────
const showAddModal = ref(false)
const newPayment = ref({
  student_id: null as number | null,
  amount: '' as string | number,
  method: 'cash',
  status: 'completed',
  notes: '',
})
const isSaving = ref(false)
const isUpdating = ref(false)

// ── edit payment modal ────────────────────────────────────────────────────────
const showEditModal = ref(false)
const editingPayment = ref<any>(null)

function openEditModal(pay: any) {
  editingPayment.value = {
    id: pay.id,
    student_id: pay.student_id,
    amount: (pay.amount / 100).toFixed(2),
    method: pay.method,
    status: pay.status,
    notes: pay.notes || '',
  }
  showEditModal.value = true
}

async function submitUpdate() {
  if (!editingPayment.value.amount) {
    toast.error('Missing amount', 'Please provide a valid amount.')
    return
  }
  isUpdating.value = true
  try {
    await paymentsStore.updatePayment(editingPayment.value.id, {
      amount: Math.round(Number(editingPayment.value.amount) * 100),
      method: editingPayment.value.method,
      status: editingPayment.value.status,
      notes: editingPayment.value.notes || undefined,
    })
    toast.success('Payment updated', 'The record has been updated successfully.')
    showEditModal.value = false
    editingPayment.value = null
  } catch (err: any) {
    toast.error('Failed to update', err?.response?.data?.detail || err.message)
  } finally {
    isUpdating.value = false
  }
}

onMounted(async () => {
  await Promise.all([paymentsStore.fetchPayments(), usersStore.fetchUsers()])
})

// ── computed helpers ──────────────────────────────────────────────────────────
const students = computed(() => usersStore.getUsersByRole('student'))

const filteredPayments = computed(() => {
  let list = [...paymentsStore.payments]

  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(
      (p) =>
        (p.student_name || '').toLowerCase().includes(q) ||
        p.method.toLowerCase().includes(q) ||
        (p.notes || '').toLowerCase().includes(q),
    )
  }
  if (statusFilter.value !== 'all') {
    list = list.filter((p) => p.status === statusFilter.value)
  }
  if (methodFilter.value !== 'all') {
    list = list.filter((p) => p.method === methodFilter.value)
  }

  list.sort((a, b) => {
    switch (sortBy.value) {
      case 'date-desc':
        return new Date(b.date).getTime() - new Date(a.date).getTime()
      case 'date-asc':
        return new Date(a.date).getTime() - new Date(b.date).getTime()
      case 'amount-desc':
        return b.amount - a.amount
      case 'amount-asc':
        return a.amount - b.amount
      default:
        return 0
    }
  })
  return list
})

const totalRevenue = computed(() =>
  paymentsStore.payments
    .filter((p) => p.status === 'completed')
    .reduce((s, p) => s + p.amount, 0),
)
const pendingTotal = computed(() =>
  paymentsStore.payments
    .filter((p) => p.status === 'pending')
    .reduce((s, p) => s + p.amount, 0),
)
const thisMonthRevenue = computed(() => {
  const now = new Date()
  return paymentsStore.payments
    .filter((p) => {
      const d = new Date(p.date)
      return (
        p.status === 'completed' &&
        d.getMonth() === now.getMonth() &&
        d.getFullYear() === now.getFullYear()
      )
    })
    .reduce((s, p) => s + p.amount, 0)
})

// ── formatters ────────────────────────────────────────────────────────────────
function formatCurrency(cents: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100)
}
function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function statusColor(status: string) {
  switch (status) {
    case 'completed':
      return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
    case 'pending':
      return 'bg-amber-500/10 text-amber-500 border-amber-500/20'
    case 'failed':
      return 'bg-red-500/10 text-red-500 border-red-500/20'
    default:
      return 'bg-surface-container text-on-surface-variant border-outline-variant/30'
  }
}

function methodIcon(method: string) {
  switch (method.toLowerCase()) {
    case 'cash':
      return 'payments'
    case 'bank_transfer':
      return 'account_balance'
    case 'card':
      return 'credit_card'
    default:
      return 'receipt'
  }
}

// ── add payment ───────────────────────────────────────────────────────────────
async function submitPayment() {
  if (!newPayment.value.student_id || !newPayment.value.amount) {
    toast.error('Missing fields', 'Please fill in all required fields.')
    return
  }
  isSaving.value = true
  try {
    await paymentsStore.createPayment({
      student_id: newPayment.value.student_id,
      amount: Math.round(Number(newPayment.value.amount) * 100),
      method: newPayment.value.method,
      status: newPayment.value.status,
      notes: newPayment.value.notes || undefined,
    })
    toast.success('Payment recorded', 'The payment has been added to the ledger.')
    showAddModal.value = false
    newPayment.value = { student_id: null, amount: '', method: 'cash', status: 'completed', notes: '' }
  } catch (err: any) {
    toast.error('Failed to save', err?.response?.data?.detail || err.message)
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <div class="max-w-[1100px] mx-auto pb-28 space-y-10 px-4 sm:px-6">
    <!-- Header -->
    <header class="pt-8">
      <div class="flex items-center gap-3 mb-3">
        <div
          class="w-10 h-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center"
        >
          <span class="material-symbols-outlined text-emerald-500 text-2xl">payments</span>
        </div>
        <p class="text-[10px] font-black text-emerald-500 uppercase tracking-[0.25em]">
          Finance & Records
        </p>
      </div>
      <div class="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 class="text-5xl font-black tracking-tight text-on-surface mb-2">Ledger</h1>
          <p class="text-on-surface-variant font-medium text-lg">
            All student payment records and transaction history.
          </p>
        </div>
        <button
          class="flex items-center gap-2 px-5 py-3 bg-emerald-500 hover:bg-emerald-600 text-white rounded-2xl font-black text-sm transition-all shadow-lg shadow-emerald-900/30 hover:scale-[1.02]"
          @click="showAddModal = true"
        >
          <span class="material-symbols-outlined text-lg">add</span>
          Record Payment
        </button>
      </div>
    </header>

    <!-- KPI Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="glass-heavy rounded-3xl p-6 border border-outline-variant/30">
        <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-[0.2em] mb-2">
          Total Revenue
        </p>
        <p class="text-3xl font-black text-on-surface">{{ formatCurrency(totalRevenue) }}</p>
        <p class="text-xs text-emerald-500 font-bold mt-1">
          {{ paymentsStore.completedCount }} completed payments
        </p>
      </div>
      <div class="glass-heavy rounded-3xl p-6 border border-outline-variant/30">
        <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-[0.2em] mb-2">
          This Month
        </p>
        <p class="text-3xl font-black text-on-surface">{{ formatCurrency(thisMonthRevenue) }}</p>
        <p class="text-xs text-on-surface-variant font-bold mt-1">Collected in current month</p>
      </div>
      <div class="glass-heavy rounded-3xl p-6 border border-outline-variant/30">
        <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-[0.2em] mb-2">
          Pending
        </p>
        <p class="text-3xl font-black text-on-surface">{{ formatCurrency(pendingTotal) }}</p>
        <p class="text-xs text-amber-500 font-bold mt-1">
          {{ paymentsStore.pendingCount }} payments awaiting
        </p>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-3 items-center">
      <div
        class="flex items-center gap-2 flex-1 min-w-[200px] glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3"
      >
        <span class="material-symbols-outlined text-on-surface-variant text-lg">search</span>
        <input
          v-model="search"
          placeholder="Search by student, method, notes…"
          class="bg-transparent text-sm text-on-surface placeholder:text-on-surface-variant/50 outline-none flex-1 font-medium"
        />
      </div>

      <select
        v-model="statusFilter"
        class="glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3 text-sm font-bold text-on-surface outline-none bg-transparent cursor-pointer"
      >
        <option value="all">All Statuses</option>
        <option value="completed">Completed</option>
        <option value="pending">Pending</option>
        <option value="failed">Failed</option>
      </select>

      <select
        v-model="methodFilter"
        class="glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3 text-sm font-bold text-on-surface outline-none bg-transparent cursor-pointer"
      >
        <option value="all">All Methods</option>
        <option value="cash">Cash</option>
        <option value="bank_transfer">Bank Transfer</option>
        <option value="card">Card</option>
      </select>

      <select
        v-model="sortBy"
        class="glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3 text-sm font-bold text-on-surface outline-none bg-transparent cursor-pointer"
      >
        <option value="date-desc">Newest First</option>
        <option value="date-asc">Oldest First</option>
        <option value="amount-desc">Highest Amount</option>
        <option value="amount-asc">Lowest Amount</option>
      </select>
    </div>

    <!-- Table / List -->
    <section>
      <!-- Loading -->
      <div
        v-if="paymentsStore.isLoading"
        class="glass-medium rounded-3xl p-20 text-center border border-outline-variant/30"
      >
        <span
          class="material-symbols-outlined text-5xl text-on-surface-variant/30 mb-4 animate-spin block"
          >progress_activity</span
        >
        <p class="text-sm font-bold text-on-surface-variant">Loading ledger…</p>
      </div>

      <!-- Empty -->
      <div
        v-else-if="filteredPayments.length === 0"
        class="glass-medium rounded-[3rem] p-20 text-center border-dashed border-2 border-outline-variant/30"
      >
        <span class="material-symbols-outlined text-5xl text-on-surface-variant/20 mb-4 block"
          >receipt_long</span
        >
        <p class="text-lg font-black text-on-surface">No payments found</p>
        <p class="text-sm text-on-surface-variant mt-1">
          Try adjusting your filters, or record a new payment above.
        </p>
      </div>

      <!-- Rows -->
      <div v-else class="space-y-3">
        <!-- Header row (hidden on mobile) -->
        <div
          class="hidden sm:grid grid-cols-[2fr_1fr_1fr_1fr_100px_40px] gap-4 px-6 py-2 text-[10px] font-black uppercase tracking-widest text-on-surface-variant"
        >
          <span>Student</span>
          <span>Date</span>
          <span>Method</span>
          <span>Amount</span>
          <span>Status</span>
          <span class="text-right">Edit</span>
        </div>

        <div
          v-for="pay in filteredPayments"
          :key="pay.id"
          class="glass-heavy rounded-3xl px-6 py-5 border border-outline-variant/30 grid grid-cols-1 sm:grid-cols-[2fr_1fr_1fr_1fr_100px_40px] gap-3 sm:gap-4 items-center hover:border-emerald-500/20 transition-all"
        >
          <!-- Student -->
          <div class="flex items-center gap-3">
            <div
              class="w-10 h-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0"
            >
              <span class="material-symbols-outlined text-emerald-500 text-lg">{{
                methodIcon(pay.method)
              }}</span>
            </div>
            <div>
              <p class="text-sm font-black text-on-surface">
                {{ pay.student_name || `Student #${pay.student_id}` }}
              </p>
              <p v-if="pay.notes" class="text-xs text-on-surface-variant truncate max-w-[200px]">
                {{ pay.notes }}
              </p>
            </div>
          </div>

          <!-- Date -->
          <p class="text-sm font-medium text-on-surface-variant">{{ formatDate(pay.date) }}</p>

          <!-- Method -->
          <p class="text-sm font-bold text-on-surface capitalize">
            {{ pay.method.replace('_', ' ') }}
          </p>

          <!-- Amount -->
          <p class="text-sm font-black text-on-surface">{{ formatCurrency(pay.amount) }}</p>

          <!-- Status badge -->
          <span
            class="px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-wider border self-start sm:self-center"
            :class="statusColor(pay.status)"
          >
            {{ pay.status }}
          </span>

          <!-- Actions -->
          <button
            class="p-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 text-on-surface-variant transition-colors"
            @click="openEditModal(pay)"
          >
            <span class="material-symbols-outlined text-xl">edit_note</span>
          </button>
        </div>
      </div>

      <!-- Summary footer -->
      <div
        v-if="filteredPayments.length > 0"
        class="mt-4 px-6 py-3 glass-medium rounded-2xl border border-outline-variant/20 flex items-center justify-between text-sm"
      >
        <span class="text-on-surface-variant font-bold"
          >{{ filteredPayments.length }} record{{ filteredPayments.length !== 1 ? 's' : '' }}</span
        >
        <span class="font-black text-on-surface">
          Filtered total:
          <span class="text-emerald-500">{{
            formatCurrency(filteredPayments.reduce((s, p) => s + p.amount, 0))
          }}</span>
        </span>
      </div>
    </section>
  </div>

  <!-- Add Payment Modal -->
  <Teleport to="body">
    <div
      v-if="showAddModal"
      class="fixed inset-0 z-[200] flex items-end sm:items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      @click.self="showAddModal = false"
    >
      <div
        class="w-full max-w-md glass-heavy rounded-[2rem] border border-outline-variant/30 shadow-2xl p-6 space-y-5"
      >
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-black text-on-surface">Record Payment</h2>
          <button
            class="w-8 h-8 rounded-full flex items-center justify-center hover:bg-black/10 dark:hover:bg-white/10"
            @click="showAddModal = false"
          >
            <span class="material-symbols-outlined text-lg text-on-surface-variant">close</span>
          </button>
        </div>

        <div class="space-y-4">
          <!-- Student -->
          <div>
            <label
              class="text-[10px] font-black uppercase tracking-widest text-on-surface-variant block mb-1.5"
              >Student *</label
            >
            <select
              v-model="newPayment.student_id"
              class="w-full glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3 text-sm font-medium text-on-surface outline-none bg-transparent cursor-pointer"
            >
              <option :value="null" disabled>Select a student…</option>
              <option v-for="s in students" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </div>

          <!-- Amount -->
          <div>
            <label
              class="text-[10px] font-black uppercase tracking-widest text-on-surface-variant block mb-1.5"
              >Amount (USD) *</label
            >
            <input
              v-model="newPayment.amount"
              type="number"
              min="0"
              step="0.01"
              placeholder="e.g. 150.00"
              class="w-full glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3 text-sm font-medium text-on-surface outline-none bg-transparent"
            />
          </div>

          <!-- Method -->
          <div>
            <label
              class="text-[10px] font-black uppercase tracking-widest text-on-surface-variant block mb-1.5"
              >Method</label
            >
            <select
              v-model="newPayment.method"
              class="w-full glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3 text-sm font-medium text-on-surface outline-none bg-transparent cursor-pointer"
            >
              <option value="cash">Cash</option>
              <option value="bank_transfer">Bank Transfer</option>
              <option value="card">Card</option>
            </select>
          </div>

          <!-- Status -->
          <div>
            <label
              class="text-[10px] font-black uppercase tracking-widest text-on-surface-variant block mb-1.5"
              >Status</label
            >
            <select
              v-model="newPayment.status"
              class="w-full glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3 text-sm font-medium text-on-surface outline-none bg-transparent cursor-pointer"
            >
              <option value="completed">Completed</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <!-- Notes -->
          <div>
            <label
              class="text-[10px] font-black uppercase tracking-widest text-on-surface-variant block mb-1.5"
              >Notes (optional)</label
            >
            <input
              v-model="newPayment.notes"
              type="text"
              placeholder="e.g. January enrollment fee"
              class="w-full glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3 text-sm font-medium text-on-surface outline-none bg-transparent"
            />
          </div>
        </div>

        <button
          :disabled="isSaving"
          class="w-full py-4 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white rounded-2xl font-black text-sm transition-all"
          @click="submitPayment"
        >
          <span v-if="isSaving">Saving…</span>
          <span v-else>Save Payment</span>
        </button>
      </div>
    </div>
  </Teleport>

  <!-- Edit Payment Modal -->
  <Teleport to="body">
    <div
      v-if="showEditModal"
      class="fixed inset-0 z-[200] flex items-end sm:items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      @click.self="showEditModal = false"
    >
      <div
        class="w-full max-w-md glass-heavy rounded-[2rem] border border-outline-variant/30 shadow-2xl p-6 space-y-5"
      >
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-black text-on-surface">Edit Payment</h2>
          <button
            class="w-8 h-8 rounded-full flex items-center justify-center hover:bg-black/10 dark:hover:bg-white/10"
            @click="showEditModal = false"
          >
            <span class="material-symbols-outlined text-lg text-on-surface-variant">close</span>
          </button>
        </div>

        <div v-if="editingPayment" class="space-y-4">
          <!-- Student (Read-only in edit) -->
          <div>
            <label
              class="text-[10px] font-black uppercase tracking-widest text-on-surface-variant block mb-1.5"
              >Student</label
            >
            <div class="w-full glass-medium border border-outline-variant/10 rounded-2xl px-4 py-3 text-sm font-bold text-on-surface/50 bg-black/5">
              {{ students.find(s => s.id === editingPayment.student_id)?.name || 'Unknown Student' }}
            </div>
          </div>

          <!-- Amount -->
          <div>
            <label
              class="text-[10px] font-black uppercase tracking-widest text-on-surface-variant block mb-1.5"
              >Amount (USD) *</label
            >
            <input
              v-model="editingPayment.amount"
              type="number"
              min="0"
              step="0.01"
              placeholder="e.g. 150.00"
              class="w-full glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3 text-sm font-medium text-on-surface outline-none bg-transparent"
            />
          </div>

          <!-- Method -->
          <div>
            <label
              class="text-[10px] font-black uppercase tracking-widest text-on-surface-variant block mb-1.5"
              >Method</label
            >
            <select
              v-model="editingPayment.method"
              class="w-full glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3 text-sm font-medium text-on-surface outline-none bg-transparent cursor-pointer"
            >
              <option value="cash">Cash</option>
              <option value="bank_transfer">Bank Transfer</option>
              <option value="card">Card</option>
            </select>
          </div>

          <!-- Status -->
          <div>
            <label
              class="text-[10px] font-black uppercase tracking-widest text-on-surface-variant block mb-1.5"
              >Status</label
            >
            <select
              v-model="editingPayment.status"
              class="w-full glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3 text-sm font-medium text-on-surface outline-none bg-transparent cursor-pointer"
            >
              <option value="completed">Completed</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <!-- Notes -->
          <div>
            <label
              class="text-[10px] font-black uppercase tracking-widest text-on-surface-variant block mb-1.5"
              >Notes (optional)</label
            >
            <input
              v-model="editingPayment.notes"
              type="text"
              placeholder="e.g. January enrollment fee"
              class="w-full glass-medium border border-outline-variant/30 rounded-2xl px-4 py-3 text-sm font-medium text-on-surface outline-none bg-transparent"
            />
          </div>
        </div>

        <button
          :disabled="isUpdating"
          class="w-full py-4 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white rounded-2xl font-black text-sm transition-all"
          @click="submitUpdate"
        >
          <span v-if="isUpdating">Updating…</span>
          <span v-else>Update Payment</span>
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.glass-heavy {
  @apply bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl shadow-lg;
}
.glass-medium {
  @apply bg-white/40 dark:bg-white/5 backdrop-blur-md;
}
</style>

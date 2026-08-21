<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useUsersStore } from '@stores/users'
import { useAuthStore } from '@stores/auth'
import { useToastStore } from '@stores/toast'
import { useShopStore } from '@stores/shop'
import OrderStatusBadge from '@components/shop/OrderStatusBadge.vue'
import { API_URL } from '@typescript/constants'
import type { InstrumentRecord } from '@types'

const usersStore = useUsersStore()
const authStore = useAuthStore()
const toast = useToastStore()
const shopStore = useShopStore()

const isSaving = ref(false)
const searchQuery = ref('')
const activeTab = ref<'my-instruments' | 'order-history'>('my-instruments')

onMounted(async () => {
  await Promise.all([
    usersStore.fetchInstruments(),
    shopStore.fetchMyOrders(),
    // Refresh current user to get latest instruments
    authStore.currentUser?.id ? usersStore.fetchUsersByRole('teacher') : Promise.resolve()
  ])
})

const formatPrice = function(cents: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'PHP'
  }).format(cents / 100)
}

const formatDate = function(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })
}

const currentTeacher = computed(() => {
  return usersStore.users.find(u => u.id === authStore.currentUser?.id) || authStore.currentUser
})

const myInstruments = computed(() => currentTeacher.value?.instruments || [])

const availableInstruments = computed(() => {
  const myIds = new Set(myInstruments.value.map(i => i.id))
  let list = usersStore.instruments.filter(i => !myIds.has(i.id))
  
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(i => i.name.toLowerCase().includes(q))
  }
  
  return list
})

async function addInstrument(instrument: InstrumentRecord) {
  if (!currentTeacher.value) return
  isSaving.value = true
  try {
    const newInstruments = [...myInstruments.value, instrument]
    await usersStore.updateUser(currentTeacher.value.id, {
      instruments: newInstruments
    })
    toast.success('Instrument added', `You are now teaching ${instrument.name}.`)
  } catch (err: any) {
    toast.error('Failed to add', err.message || 'Something went wrong.')
  } finally {
    isSaving.value = false
  }
}

async function removeInstrument(instrumentId: string | number) {
  if (!currentTeacher.value) return
  isSaving.value = true
  try {
    const newInstruments = myInstruments.value.filter(i => i.id !== instrumentId && String(i.id) !== String(instrumentId))
    await usersStore.updateUser(currentTeacher.value.id, {
      instruments: newInstruments
    })
    toast.success('Instrument removed', 'Your teaching profile has been updated.')
  } catch (err: any) {
    toast.error('Failed to remove', err.message || 'Something went wrong.')
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <div class="max-w-[1200px] mx-auto pb-28 space-y-8 px-4 sm:px-6">
    <!-- Header -->
    <header class="relative py-8">
      <div class="absolute -top-10 -left-10 size-64 bg-orange-500/10 blur-[100px] rounded-full -z-10 animate-pulse" />
      <div class="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 rounded-2xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center shadow-inner">
              <span class="material-symbols-outlined text-orange-500 text-2xl">piano</span>
            </div>
            <p class="text-xs font-semibold text-orange-500 uppercase">Professional Profile</p>
          </div>
          <h1 class="text-5xl font-semibold tracking-tight text-on-surface mb-2">My Instruments</h1>
          <p class="text-on-surface-variant font-medium text-lg">
            Manage the instruments you are currently certified to teach.
          </p>
        </div>
      </div>
    </header>

    <!-- Tabs -->
    <div class="flex gap-4 mb-10 border-b border-outline-variant/20 dark:border-white/5 pb-4">
      <button
        @click="activeTab = 'my-instruments'"
        class="px-6 py-2 rounded-xl text-sm font-semibold uppercase transition-all"
        :class="activeTab === 'my-instruments' ? 'text-orange-500 bg-orange-500/10 shadow-sm' : 'text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface'"
      >
        My Certified Instruments
      </button>
      <button
        @click="activeTab = 'order-history'"
        class="px-6 py-2 rounded-xl text-sm font-semibold uppercase transition-all"
        :class="activeTab === 'order-history' ? 'text-orange-500 bg-orange-500/10 shadow-sm' : 'text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface'"
      >
        Order History
      </button>
    </div>

    <div v-if="activeTab === 'my-instruments'" class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      
      <!-- Currently Teaching -->
      <section class="lg:col-span-8 space-y-6">
        <div class="flex items-center justify-between px-2">
          <h2 class="text-xl font-semibold text-on-surface uppercase flex items-center gap-2">
            <span class="size-2 rounded-full bg-emerald-500"></span>
            Active Repertoire
          </h2>
          <span class="text-xs font-bold text-on-surface-variant bg-black/5 dark:bg-white/5 px-3 py-1 rounded-full border border-black/5 dark:border-white/5 uppercase">
            {{ myInstruments.length }} Assigned
          </span>
        </div>

        <div v-if="myInstruments.length === 0" class="glass-medium rounded-3xl p-16 text-center border-dashed border-2 border-outline-variant/30">
          <div class="size-20 rounded-full bg-surface-container-highest/30 flex items-center justify-center mx-auto mb-6 shadow-xl">
            <span class="material-symbols-outlined text-5xl text-on-surface-variant/40">music_off</span>
          </div>
          <p class="text-xl font-semibold text-on-surface mb-2">No instruments mapped</p>
          <p class="text-on-surface-variant max-w-sm mx-auto mb-8 font-medium">Your teaching profile is empty. Select from the global registry to begin accepting students.</p>
        </div>

        <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div 
            v-for="inst in myInstruments" 
            :key="inst.id"
            class="group relative overflow-hidden glass-heavy rounded-3xl border border-outline-variant/20 hover:border-orange-500/30 transition-all hover:shadow-2xl hover:shadow-orange-500/5 hover:-translate-y-1 p-6"
          >
            <!-- Decorative bg -->
            <div class="absolute -right-4 -bottom-4 opacity-[0.03] group-hover:opacity-[0.08] group-hover:scale-110 transition-all">
              <span class="material-symbols-outlined text-9xl">music_note</span>
            </div>

            <div class="flex justify-between items-start relative z-10">
              <div class="flex items-center gap-4">
                <div class="size-12 rounded-2xl bg-orange-400 flex items-center justify-center shadow-lg shadow-orange-900/20 text-white">
                  <span class="material-symbols-outlined text-2xl">music_note</span>
                </div>
                <div>
                  <h4 class="text-lg font-semibold text-on-surface uppercase tracking-tight">{{ inst.name }}</h4>
                  <p class="text-xs font-bold text-emerald-500 dark:text-emerald-400 uppercase">Certified Instructor</p>
                </div>
              </div>
              <button 
                class="size-8 rounded-xl bg-rose-500/10 text-rose-500 border border-rose-500/10 opacity-0 group-hover:opacity-100 transition-all hover:bg-rose-500 hover:text-white flex items-center justify-center"
                @click="removeInstrument(inst.id)"
                title="Remove from profile"
              >
                <span class="material-symbols-outlined text-sm">close</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Global Registry / Search -->
      <section class="lg:col-span-4 space-y-6">
        <h2 class="text-xl font-semibold text-on-surface uppercase px-2">Registry</h2>
        
        <div class="glass-medium rounded-3xl border border-outline-variant/30 p-6 space-y-6 shadow-xl">
          <!-- Search box -->
          <div class="relative group">
            <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant transition-colors group-focus-within:text-orange-500">search</span>
            <input 
              v-model="searchQuery"
              type="text" 
              placeholder="Filter catalog..."
              class="input pl-12"
            />
          </div>

          <div class="h-px bg-outline-variant/10 mx-2" />

          <!-- Instrument list -->
          <div class="space-y-2 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
            <div 
              v-for="inst in availableInstruments" 
              :key="inst.id"
              class="flex items-center justify-between p-3 rounded-2xl hover:bg-black/5 dark:hover:bg-white/5 transition-all group"
            >
              <div class="flex items-center gap-3">
                <span class="material-symbols-outlined text-on-surface-variant group-hover:text-orange-500 transition-colors">circle</span>
                <span class="text-sm font-bold text-on-surface">{{ inst.name }}</span>
              </div>
              <button 
                class="size-8 rounded-xl bg-orange-500/10 text-orange-500 border border-orange-500/10 hover:bg-orange-500 hover:text-white flex items-center justify-center transition-all disabled:opacity-30"
                @click="addInstrument(inst)"
                :disabled="isSaving"
              >
                <span class="material-symbols-outlined text-sm">add</span>
              </button>
            </div>
            
            <div v-if="availableInstruments.length === 0" class="py-12 text-center text-on-surface-variant">
              <span class="material-symbols-outlined text-2xl mb-2 opacity-30">inventory_2</span>
              <p class="text-xs font-medium">No results found in the catalog.</p>
            </div>
          </div>
          
          <div class="pt-4 mt-2 border-t border-outline-variant/10">
            <p class="text-xs font-semibold text-on-surface-variant uppercase leading-relaxed">
              Don't see your instrument? Contact the Clinical Director to update the global registry.
            </p>
          </div>
        </div>
      </section>

    </div>

    <!-- Order History View -->
    <div v-else class="space-y-6">
      <div v-if="shopStore.myOrders.length > 0" class="grid gap-4">
        <div
          v-for="order in shopStore.myOrders"
          :key="order.id"
          class="glass-heavy rounded-3xl p-6 border border-outline-variant/20 dark:border-white/5 hover:border-orange-500/30 transition-all group"
        >
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div class="flex items-center gap-4">
              <div class="size-12 rounded-2xl bg-orange-500/10 flex items-center justify-center text-orange-500">
                <span class="material-symbols-outlined">receipt_long</span>
              </div>
              <div>
                <h4 class="font-semibold text-on-surface dark:text-on-surface">Order #{{ order.id }}</h4>
                <p class="text-xs font-bold text-on-surface-variant dark:text-on-surface-variant uppercase">
                  Placed on {{ formatDate(order.createdAt) }}
                </p>
              </div>
            </div>

            <div class="flex items-center gap-6">
              <div class="text-right hidden sm:block">
                <p class="text-xs font-semibold text-on-surface-variant dark:text-on-surface-variant uppercase mb-1">Total Amount</p>
                <p class="text-lg font-semibold text-on-surface dark:text-on-surface">{{ formatPrice(order.totalCents) }}</p>
              </div>

              <OrderStatusBadge :status="order.status" />

              <button
                v-if="order.status === 'pending'"
                @click="shopStore.cancelMyOrder(order.id)"
                class="px-4 py-2 rounded-xl bg-rose-500/10 text-rose-500 text-xs font-semibold uppercase hover:bg-rose-500 hover:text-white transition-all"
              >
                Cancel
              </button>
            </div>
          </div>

          <!-- Order Items Preview -->
          <div class="mt-6 pt-6 border-t border-outline-variant/20 dark:border-white/5 flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
            <div
              v-for="item in order.items"
              :key="item.id"
              class="flex items-center gap-3 px-4 py-2 bg-black/5 dark:bg-black/20 rounded-2xl border border-outline-variant/20 dark:border-white/5 shrink-0"
            >
              <div class="size-8 rounded-lg overflow-hidden bg-black/10 dark:bg-black/40">
                <img v-if="item.product?.imageUrl" :src="item.product.imageUrl.startsWith('http') ? item.product.imageUrl : `${API_URL}${item.product.imageUrl}`" class="w-full h-full object-cover" />
                <div v-else class="w-full h-full flex items-center justify-center text-white/10">
                  <span class="material-symbols-outlined text-xs">image</span>
                </div>
              </div>
              <span class="text-xs font-bold text-on-surface dark:text-on-surface">{{ item.quantity }}x {{ item.product?.name || 'Product' }}</span>
            </div>
          </div>

          <!-- Rejection Reason -->
          <div v-if="order.status === 'rejected' && order.rejectionReason" class="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400 font-bold">
            Rejection Reason: {{ order.rejectionReason }}
          </div>
        </div>
      </div>

      <!-- Empty Orders -->
      <div v-else class="flex flex-col items-center justify-center py-20 glass-heavy rounded-[3rem] border border-outline-variant/20 dark:border-white/5 bg-surface-container-low/50 dark:bg-transparent">
        <div class="size-20 rounded-full bg-orange-500/10 flex items-center justify-center text-orange-500 mb-6 shadow-inner">
          <span class="material-symbols-outlined text-4xl">history</span>
        </div>
        <h3 class="text-xl font-semibold text-on-surface dark:text-on-surface mb-2">No orders yet</h3>
        <p class="text-on-surface-variant dark:text-on-surface-variant font-bold">Your order history will appear here.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.glass-heavy {
  @apply bg-white/70 dark:bg-zinc-900/70 backdrop-blur-xl shadow-2xl;
}
.glass-medium {
  @apply bg-white/40 dark:bg-white/5 backdrop-blur-md;
}
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  @apply bg-transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  @apply bg-outline-variant/30 rounded-full;
}
</style>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useShopStore } from '@stores/shop'
import ProductGrid from '@components/shop/ProductGrid.vue'
import CartDrawer from '@components/shop/CartDrawer.vue'
import OrderStatusBadge from '@components/shop/OrderStatusBadge.vue'

const shopStore = useShopStore()
const isCartOpen = ref(false)
const activeTab = ref<'products' | 'orders'>('products')

onMounted(async () => {
  await Promise.all([
    shopStore.fetchProducts(),
    shopStore.fetchMyOrders()
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
</script>

<template>
  <div class="min-h-screen pb-20">
    <!-- Header -->
    <div class="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6">
      <div>
        <h1 class="text-4xl md:text-5xl font-black text-on-surface mb-4 tracking-tight">
          Instrument <span class="text-orange-500">Shop</span>
        </h1>
        <p class="text-on-surface-variant font-bold max-w-xl">
          Premium instruments and accessories curated for our students and teachers.
          Browse our collection and place an order request.
        </p>
      </div>

      <div class="flex items-center gap-4">
        <button
          @click="isCartOpen = true"
          class="relative h-16 px-8 bg-orange-500 hover:bg-orange-600 text-white rounded-3xl font-black text-sm uppercase tracking-widest transition-all hover:scale-105 active:scale-95 shadow-xl shadow-orange-500/20 flex items-center gap-3"
        >
          <span class="material-symbols-outlined">shopping_cart</span>
          Cart
          <span
            v-if="shopStore.cartItemsCount > 0"
            class="absolute -top-2 -right-2 w-7 h-7 bg-white text-orange-500 rounded-full flex items-center justify-center text-xs font-black shadow-lg"
          >
            {{ shopStore.cartItemsCount }}
          </span>
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-4 mb-10 border-b border-white/5 pb-4">
      <button
        @click="activeTab = 'products'"
        class="px-6 py-2 rounded-xl text-sm font-black uppercase tracking-widest transition-all"
        :class="activeTab === 'products' ? 'text-orange-500 bg-orange-500/10' : 'text-on-surface-variant hover:text-on-surface'"
      >
        Products
      </button>
      <button
        @click="activeTab = 'orders'"
        class="px-6 py-2 rounded-xl text-sm font-black uppercase tracking-widest transition-all"
        :class="activeTab === 'orders' ? 'text-orange-500 bg-orange-500/10' : 'text-on-surface-variant hover:text-on-surface'"
      >
        My Orders
      </button>
    </div>

    <!-- Content -->
    <div v-if="activeTab === 'products'">
      <div v-if="shopStore.isLoading" class="flex flex-col items-center justify-center py-40">
        <div class="w-16 h-16 border-4 border-orange-500/20 border-t-orange-500 rounded-full animate-spin"></div>
        <p class="mt-4 text-on-surface-variant font-black uppercase tracking-widest text-xs">Loading Catalog...</p>
      </div>
      <ProductGrid v-else :products="shopStore.products" />
    </div>

    <div v-else class="space-y-6">
      <div v-if="shopStore.myOrders.length > 0" class="grid gap-4">
        <div
          v-for="order in shopStore.myOrders"
          :key="order.id"
          class="glass-thin rounded-[2rem] p-6 border border-white/5 hover:border-orange-500/30 transition-all group"
        >
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-2xl bg-orange-500/10 flex items-center justify-center text-orange-500">
                <span class="material-symbols-outlined">receipt_long</span>
              </div>
              <div>
                <h4 class="font-black text-on-surface">Order #{{ order.id }}</h4>
                <p class="text-xs font-bold text-on-surface-variant uppercase tracking-widest">
                  Placed on {{ formatDate(order.createdAt) }}
                </p>
              </div>
            </div>

            <div class="flex items-center gap-6">
              <div class="text-right hidden sm:block">
                <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-1">Total Amount</p>
                <p class="text-lg font-black text-on-surface">{{ formatPrice(order.totalCents) }}</p>
              </div>

              <OrderStatusBadge :status="order.status" />

              <button
                v-if="order.status === 'pending'"
                @click="shopStore.cancelMyOrder(order.id)"
                class="px-4 py-2 rounded-xl bg-rose-500/10 text-rose-500 text-xs font-black uppercase tracking-widest hover:bg-rose-500 hover:text-white transition-all"
              >
                Cancel
              </button>
            </div>
          </div>

          <!-- Order Items Preview -->
          <div class="mt-6 pt-6 border-t border-white/5 flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
            <div
              v-for="item in order.items"
              :key="item.id"
              class="flex items-center gap-3 px-4 py-2 bg-black/20 rounded-2xl border border-white/5 shrink-0"
            >
              <div class="w-8 h-8 rounded-lg overflow-hidden bg-black/20">
                <img v-if="item.product?.imageUrl" :src="item.product.imageUrl" class="w-full h-full object-cover" />
                <div v-else class="w-full h-full flex items-center justify-center text-white/10">
                  <span class="material-symbols-outlined text-xs">image</span>
                </div>
              </div>
              <span class="text-xs font-bold text-on-surface">{{ item.quantity }}x {{ item.product?.name || 'Product' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty Orders -->
      <div v-else class="flex flex-col items-center justify-center py-20 glass-thin rounded-[3rem] border border-white/5">
        <div class="w-20 h-20 rounded-full bg-orange-500/10 flex items-center justify-center text-orange-500 mb-6">
          <span class="material-symbols-outlined text-4xl">history</span>
        </div>
        <h3 class="text-xl font-black text-on-surface mb-2">No orders yet</h3>
        <p class="text-on-surface-variant font-bold">Your order history will appear here.</p>
        <button
          @click="activeTab = 'products'"
          class="mt-8 px-8 py-4 bg-orange-500 text-white rounded-2xl font-black text-xs uppercase tracking-widest transition-all hover:scale-105"
        >
          Go to Shop
        </button>
      </div>
    </div>

    <CartDrawer
      :is-open="isCartOpen"
      @close="isCartOpen = false"
      @checkout="activeTab = 'orders'"
    />
  </div>
</template>

<style scoped>
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>

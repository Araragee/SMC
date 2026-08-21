<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useShopStore } from '@stores/shop'
import ProductGrid from '@components/shop/ProductGrid.vue'
import CartDrawer from '@components/shop/CartDrawer.vue'
import OrderStatusBadge from '@components/shop/OrderStatusBadge.vue'
import { API_URL } from '@typescript/constants'

const shopStore = useShopStore()
const isCartOpen = ref(false)
const activeTab = ref<'products' | 'orders'>('products')
const selectedProduct = ref<any>(null)
const isProductModalOpen = ref(false)

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

const openProductDetails = function(product: any) {
  selectedProduct.value = product
  isProductModalOpen.value = true
}

const handleAddToCart = function(product: any) {
  shopStore.addToCart(product.id)
  isProductModalOpen.value = false
}
</script>

<template>
  <div class="min-h-screen pb-20">
    <!-- Header -->
    <div class="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6">
      <div>
        <h1 class="text-4xl md:text-5xl font-black text-on-surface dark:text-on-surface mb-4 tracking-tight">
          Instrument <span class="text-primary">Shop</span>
        </h1>
        <p class="text-on-surface-variant dark:text-on-surface-variant font-bold max-w-xl">
          Premium instruments and accessories curated for our students and teachers.
          Browse our collection and place an order request.
        </p>
      </div>

      <div class="flex items-center gap-4">
        <button
          @click="isCartOpen = true"
          class="relative h-16 px-8 bg-primary hover:bg-primary-dim text-on-surface rounded-3xl font-black text-sm uppercase tracking-widest transition-all hover:scale-105 active:scale-95 shadow-xl flex items-center gap-3"
        >
          <span class="material-symbols-outlined">shopping_cart</span>
          Cart
          <span
            v-if="shopStore.cartItemsCount > 0"
            class="absolute -top-2 -right-2 w-7 h-7 bg-surface-container-lowest text-primary rounded-full flex items-center justify-center text-xs font-black shadow-lg"
          >
            {{ shopStore.cartItemsCount }}
          </span>
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-4 mb-10 border-b border-outline-variant/20 dark:border-on-surface/5 pb-4">
      <button
        @click="activeTab = 'products'"
        class="px-6 py-2 rounded-xl text-sm font-black uppercase tracking-widest transition-all"
        :class="activeTab === 'products' ? 'text-primary bg-primary/10 shadow-sm' : 'text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface'"
      >
        Products
      </button>
      <button
        @click="activeTab = 'orders'"
        class="px-6 py-2 rounded-xl text-sm font-black uppercase tracking-widest transition-all"
        :class="activeTab === 'orders' ? 'text-primary bg-primary/10 shadow-sm' : 'text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface'"
      >
        My Orders
      </button>
    </div>

    <!-- Content -->
    <div v-if="activeTab === 'products'">
      <div v-if="shopStore.isLoading" class="flex flex-col items-center justify-center py-40">
        <div class="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
        <p class="mt-4 text-on-surface-variant font-black uppercase tracking-widest text-xs">Loading Catalog...</p>
      </div>
      <ProductGrid v-else :products="shopStore.products" @view-product="openProductDetails" />
    </div>

    <div v-else class="space-y-6">
      <div v-if="shopStore.myOrders.length > 0" class="grid gap-4">
        <div
          v-for="order in shopStore.myOrders"
          :key="order.id"
          class="glass-thin rounded-[2rem] p-6 border border-outline-variant/20 dark:border-on-surface/5 bg-surface-container-low/50 dark:bg-transparent hover:border-primary/30 transition-all group"
        >
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                <span class="material-symbols-outlined">receipt_long</span>
              </div>
              <div>
                <h4 class="font-black text-on-surface dark:text-on-surface">Order #{{ order.id }}</h4>
                <p class="text-xs font-bold text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest">
                  Placed on {{ formatDate(order.createdAt) }}
                </p>
              </div>
            </div>

            <div class="flex items-center gap-6">
              <div class="text-right hidden sm:block">
                <p class="text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest mb-1">Total Amount</p>
                <p class="text-lg font-black text-on-surface dark:text-on-surface">{{ formatPrice(order.totalCents) }}</p>
              </div>

              <OrderStatusBadge :status="order.status" />

              <button
                v-if="order.status === 'pending'"
                @click="shopStore.cancelMyOrder(order.id)"
                class="px-4 py-2 rounded-xl bg-rose-500/10 text-rose-500 text-xs font-black uppercase tracking-widest hover:bg-rose-500 hover:text-on-surface transition-all"
              >
                Cancel
              </button>
            </div>
          </div>

          <!-- Order Items Preview -->
          <div class="mt-6 pt-6 border-t border-outline-variant/20 dark:border-on-surface/5 flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
            <div
              v-for="item in order.items"
              :key="item.id"
              class="flex items-center gap-3 px-4 py-2 bg-on-surface/5 dark:bg-on-surface/20 rounded-2xl border border-outline-variant/20 dark:border-on-surface/5 shrink-0"
            >
              <div class="w-8 h-8 rounded-lg overflow-hidden bg-on-surface/10 dark:bg-on-surface/40">
                <img v-if="item.product?.imageUrl" :src="item.product.imageUrl.startsWith('http') ? item.product.imageUrl : `${API_URL}${item.product.imageUrl}`" class="w-full h-full object-cover" />
                <div v-else class="w-full h-full flex items-center justify-center text-on-surface/10">
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
      <div v-else class="flex flex-col items-center justify-center py-20 glass-thin rounded-[3rem] border border-outline-variant/20 dark:border-on-surface/5 bg-surface-container-low/50 dark:bg-transparent">
        <div class="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-6 shadow-inner">
          <span class="material-symbols-outlined text-4xl">history</span>
        </div>
        <h3 class="text-xl font-black text-on-surface dark:text-on-surface mb-2">No orders yet</h3>
        <p class="text-on-surface-variant dark:text-on-surface-variant font-bold">Your order history will appear here.</p>
        <button
          @click="activeTab = 'products'"
          class="mt-8 px-8 py-4 bg-primary text-on-surface rounded-2xl font-black text-xs uppercase tracking-widest transition-all hover:scale-105"
        >
          Go to Shop
        </button>
      </div>
    </div>

    <!-- Product Detail Modal -->
    <div v-if="isProductModalOpen && selectedProduct" class="fixed inset-0 z-[60] flex items-center justify-center p-6">
      <div class="absolute inset-0 bg-on-surface/80 transition-opacity" @click="isProductModalOpen = false"></div>

      <div class="relative w-full max-w-4xl glass-heavy rounded-[3rem] border border-outline-variant/20 dark:border-on-surface/10 overflow-hidden flex flex-col md:flex-row max-h-[90vh]">
        <!-- Product Image -->
        <div class="w-full md:w-1/2 bg-on-surface/20 relative aspect-square md:aspect-auto">
          <img
            :src="selectedProduct.imageUrl?.startsWith('http') ? selectedProduct.imageUrl : `${API_URL}${selectedProduct.imageUrl}`"
            class="w-full h-full object-cover"
            v-if="selectedProduct.imageUrl"
          />
          <div v-else class="w-full h-full flex items-center justify-center text-on-surface/10">
            <span class="material-symbols-outlined text-9xl">image</span>
          </div>

          <button
            @click="isProductModalOpen = false"
            class="absolute top-6 left-6 w-12 h-12 rounded-2xl bg-on-surface/40 text-on-surface flex items-center justify-center md:hidden"
          >
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <!-- Product Info -->
        <div class="w-full md:w-1/2 p-10 md:p-12 overflow-y-auto custom-scrollbar flex flex-col">
          <div class="hidden md:flex justify-end mb-8">
            <button
              @click="isProductModalOpen = false"
              class="w-12 h-12 rounded-2xl bg-on-surface/5 dark:bg-on-surface/5 text-on-surface-variant hover:text-on-surface transition-all flex items-center justify-center"
            >
              <span class="material-symbols-outlined font-black">close</span>
            </button>
          </div>

          <div class="flex-grow">
            <div class="flex items-center gap-3 mb-4">
              <span class="px-4 py-1.5 rounded-full bg-primary/10 text-primary text-[10px] font-black uppercase tracking-widest border border-primary/20">
                {{ selectedProduct.category?.name || 'Instrument' }}
              </span>
              <span v-if="selectedProduct.stock > 0" class="text-[10px] font-black text-emerald-500 uppercase tracking-widest">
                In Stock
              </span>
              <span v-else class="text-[10px] font-black text-rose-500 uppercase tracking-widest">
                Out of Stock
              </span>
            </div>

            <h2 class="text-4xl font-black text-on-surface dark:text-on-surface mb-6 leading-tight">
              {{ selectedProduct.name }}
            </h2>

            <div class="prose prose-invert max-w-none mb-10">
              <p class="text-lg text-on-surface-variant dark:text-on-surface-variant font-medium leading-relaxed">
                {{ selectedProduct.description }}
              </p>
            </div>
          </div>

          <div class="mt-auto pt-8 border-t border-outline-variant/20 dark:border-on-surface/5">
            <div class="flex items-end justify-between gap-6 mb-8">
              <div>
                <p class="text-xs font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-[0.2em] mb-1">Price</p>
                <p class="text-4xl font-black text-primary tracking-tighter">{{ formatPrice(selectedProduct.priceCents) }}</p>
              </div>
              <div class="text-right">
                <p class="text-xs font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-[0.2em] mb-1">Stock</p>
                <p class="text-xl font-black text-on-surface dark:text-on-surface">{{ selectedProduct.stock }} <span class="text-sm text-on-surface-variant uppercase tracking-widest">units</span></p>
              </div>
            </div>

            <button
              @click="handleAddToCart(selectedProduct)"
              :disabled="selectedProduct.stock <= 0"
              class="w-full h-20 bg-primary hover:bg-primary-dim disabled:opacity-30 text-on-surface rounded-[2rem] font-black text-sm uppercase tracking-[0.2em] transition-all hover:scale-[1.02] active:scale-95 shadow-2xl flex items-center justify-center gap-4 group"
            >
              <span class="material-symbols-outlined font-black group-hover:rotate-12 transition-transform">add_shopping_cart</span>
              Add to Cart
            </button>
          </div>
        </div>
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

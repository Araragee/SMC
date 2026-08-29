<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useShopStore } from '@stores/shop'
import OrderStatusBadge from '@components/shop/OrderStatusBadge.vue'
import { API_URL } from '@typescript/constants'
import type { OrderStatus, InstrumentProduct, Order } from '@types'
import { useDialog } from '@composables/useDialog'

const shopStore = useShopStore()
const dialog = useDialog()
const activeTab = ref<'catalog' | 'orders'>('catalog')
const isEditorOpen = ref(false)
const selectedProduct = ref<InstrumentProduct | null>(null)
const selectedOrder = ref<Order | null>(null)
const isOrderDetailOpen = ref(false)

const orderFilter = ref<string>('all')
const filteredOrders = computed(() => {
  if (orderFilter.value === 'all') {
    return shopStore.orders
  }
  return shopStore.orders.filter(order => order.status === orderFilter.value)
})

const fileInputRef = ref<HTMLInputElement | null>(null)
const imageFile = ref<File | null>(null)
const previewImage = ref<string | null>(null)
const displayPricePHP = ref<number>(0)

onMounted(async () => {
  await Promise.all([
    shopStore.fetchProducts(),
    shopStore.fetchAllOrders()
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
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const openEditor = function(product: any = null) {
  imageFile.value = null
  previewImage.value = product?.imageUrl || null
  displayPricePHP.value = product ? (product.priceCents / 100) : 0

  selectedProduct.value = product ? {
    id: product.id,
    name: product.name,
    description: product.description,
    priceCents: product.priceCents,
    stock: product.stock,
    isActive: product.isActive,
    createdAt: product.createdAt,
    updatedAt: product.updatedAt,
  } : {
    id: 0,
    name: '',
    description: '',
    priceCents: 0,
    stock: 0,
    isActive: true,
    createdAt: '',
    updatedAt: '',
  }
  isEditorOpen.value = true
}

const saveProduct = async function() {
  try {
    const payload = { ...selectedProduct.value, price_cents: Math.round(displayPricePHP.value * 100) }
    let savedProduct: any;
    if (payload.id) {
      savedProduct = await shopStore.updateProduct(payload.id, payload)
    } else {
      savedProduct = await shopStore.createProduct(payload)
    }

    const targetId = savedProduct?.id || payload.id
    if (imageFile.value && targetId) {
      // uploadProductImage already upserts the product in the store; no full re-fetch needed
      await shopStore.uploadProductImage(targetId, imageFile.value)
    }

    isEditorOpen.value = false
    // createProduct/updateProduct already upsert the local store list,
    // so a full re-fetch is redundant — skip it to avoid the extra round-trip.
  } catch (error) {
    console.error('Error saving product:', error)
  }
}

const triggerFileInput = () => {
  fileInputRef.value?.click()
}

const onFileSelected = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  imageFile.value = file
  previewImage.value = URL.createObjectURL(file)
}

const handleFileUpload = async function(event: Event, productId: number) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  await shopStore.uploadProductImage(productId, file)
}

const viewOrder = function(order: any) {
  selectedOrder.value = order
  isOrderDetailOpen.value = true
}

const updateOrderStatus = async function(id: number, status: OrderStatus) {
  let actionText = ''
  let isDestructive = false
  if (status === 'approved') {
    actionText = 'approve this order and deduct stock'
  } else if (status === 'rejected') {
    actionText = 'reject this order'
    isDestructive = true
  } else if (status === 'fulfilled') {
    actionText = 'mark this order as fulfilled'
  }

  const ok = await dialog.confirm(`Are you sure you want to ${actionText}?`, {
    title: `${status.charAt(0).toUpperCase() + status.slice(1)} Order`,
    destructive: isDestructive
  })
  if (!ok) return

  try {
    await shopStore.updateOrderStatus(id, status)
    isOrderDetailOpen.value = false
  } catch (error) {
    console.error('Error updating order status:', error)
  }
}
</script>

<template>
  <div class="min-h-screen pb-20">
    <!-- Header -->
    <div class="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6">
      <div>
        <h1 class="text-4xl md:text-5xl font-semibold text-on-surface mb-4 tracking-tight">
          Shop <span class="text-primary">Management</span>
        </h1>
        <p class="text-on-surface-variant font-bold max-w-xl">
          Manage your instrument inventory and process student order requests.
        </p>
      </div>

      <div class="flex items-center gap-4">
        <button
          @click="openEditor()"
          class="h-16 px-8 bg-surface-container-lowest text-on-surface rounded-3xl font-semibold text-sm uppercase transition-all hover:scale-105 active:scale-95 shadow-xl shadow-e2 flex items-center gap-3"
        >
          <span class="material-symbols-outlined">add</span>
          New Product
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-4 mb-10 border-b border-on-surface/5 pb-4">
      <button
        @click="activeTab = 'catalog'"
        class="px-6 py-2 rounded-xl text-sm font-semibold uppercase transition-all"
        :class="activeTab === 'catalog' ? 'text-primary bg-primary/10' : 'text-on-surface-variant hover:text-on-surface'"
      >
        Catalog
      </button>
      <button
        @click="activeTab = 'orders'"
        class="px-6 py-2 rounded-xl text-sm font-semibold uppercase transition-all"
        :class="activeTab === 'orders' ? 'text-primary bg-primary/10' : 'text-on-surface-variant hover:text-on-surface'"
      >
        Order Requests
      </button>
    </div>

    <!-- Catalog View -->
    <div v-if="activeTab === 'catalog'" class="grid grid-cols-1 gap-4">
      <div v-for="product in shopStore.products" :key="product.id" class="glass-thin rounded-3xl p-6 border border-on-surface/5 flex flex-col md:flex-row items-center gap-6">
        <div class="size-24 rounded-2xl bg-on-surface/20 dark:bg-on-surface/40 overflow-hidden shrink-0 border border-on-surface/5">
          <img v-if="product.imageUrl" :src="product.imageUrl.startsWith('http') ? product.imageUrl : `${API_URL}${product.imageUrl}`" class="w-full h-full object-cover" />
          <div v-else class="w-full h-full flex items-center justify-center text-on-surface/10">
            <span class="material-symbols-outlined">image</span>
          </div>
        </div>

        <div class="flex-1 min-w-0 text-center md:text-left">
          <h3 class="text-xl font-semibold text-on-surface">{{ product.name }}</h3>
          <p class="text-sm font-bold text-on-surface-variant line-clamp-1">{{ product.description }}</p>
          <div class="flex flex-wrap justify-center md:justify-start gap-4 mt-2">
            <span class="text-xs font-semibold text-primary uppercase">{{ formatPrice(product.priceCents) }}</span>
            <span class="text-xs font-semibold uppercase" :class="product.stock <= 3 ? 'text-rose-500 font-extrabold animate-pulse' : 'text-on-surface/40'">
              Stock: {{ product.stock }} {{ product.stock <= 3 ? '[Low Stock]' : '' }}
            </span>
            <span :class="product.isActive ? 'text-emerald-500' : 'text-rose-500'" class="text-xs font-semibold uppercase">
              {{ product.isActive ? 'Active' : 'Hidden' }}
            </span>
          </div>
        </div>

        <div class="flex gap-3">
          <label class="h-12 w-12 rounded-2xl bg-on-surface/5 text-on-surface-variant hover:text-on-surface transition-all flex items-center justify-center cursor-pointer">
            <input type="file" class="hidden" @change="e => handleFileUpload(e, product.id)" accept="image/*" />
            <span class="material-symbols-outlined">add_a_photo</span>
          </label>
          <button @click="openEditor(product)" class="h-12 w-12 rounded-2xl bg-on-surface/5 text-on-surface-variant hover:text-on-surface transition-all flex items-center justify-center">
            <span class="material-symbols-outlined">edit</span>
          </button>
          <button @click="shopStore.deleteProduct(product.id)" class="h-12 w-12 rounded-2xl bg-on-surface/5 text-on-surface-variant hover:text-rose-500 transition-all flex items-center justify-center">
            <span class="material-symbols-outlined">delete</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Orders View -->
    <div v-else class="space-y-4">
      <!-- Order Status Filter Tabs -->
      <div class="flex flex-wrap gap-2 mb-6 bg-on-surface/5 p-1.5 rounded-2xl border border-on-surface/5 max-w-max">
        <button
          v-for="status in ['all', 'pending', 'approved', 'fulfilled', 'rejected']"
          :key="status"
          @click="orderFilter = status"
          class="px-4 py-2 rounded-xl text-xs font-semibold uppercase transition-all"
          :class="orderFilter === status ? 'bg-primary text-on-surface shadow-lg' : 'text-on-surface-variant hover:text-on-surface'"
        >
          {{ status }}
        </button>
      </div>

      <div v-for="order in filteredOrders" :key="order.id" @click="viewOrder(order)" class="glass-thin rounded-3xl p-6 border border-on-surface/5 hover:border-primary/30 transition-all cursor-pointer group flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex items-center gap-4">
          <div class="size-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
            <span class="material-symbols-outlined">receipt_long</span>
          </div>
          <div>
            <h4 class="font-semibold text-on-surface">Order #{{ order.id }} - {{ order.user?.name }}</h4>
            <p class="text-xs font-bold text-on-surface-variant uppercase">{{ formatDate(order.createdAt) }}</p>
          </div>
        </div>

        <div class="flex items-center gap-6">
          <div class="text-right">
            <p class="text-lg font-semibold text-on-surface">{{ formatPrice(order.totalCents) }}</p>
          </div>
          <OrderStatusBadge :status="order.status" />
          <span class="material-symbols-outlined text-on-surface/10 group-hover:text-primary transition-colors">chevron_right</span>
        </div>
      </div>
    </div>

    <!-- Product Editor Modal -->
    <div v-if="isEditorOpen && selectedProduct" class="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div class="absolute inset-0 bg-on-surface/90" @click="isEditorOpen = false"></div>
      <div class="relative w-full max-w-lg glass-thin rounded-[3rem] border border-on-surface/10 p-10">
        <h2 class="text-3xl font-semibold text-on-surface mb-8">{{ selectedProduct?.id ? 'Edit' : 'New' }} Product</h2>

        <div class="space-y-6">
          <div>
            <label class="text-xs font-semibold text-on-surface-variant uppercase mb-2 block">Product Image</label>
            <div 
              class="w-full h-48 border-2 border-dashed border-on-surface/10 rounded-2xl flex flex-col items-center justify-center bg-on-surface/5 hover:bg-on-surface/10 transition-colors cursor-pointer overflow-hidden relative group"
              @click="triggerFileInput"
            >
                <img v-if="previewImage" :src="previewImage.startsWith('blob:') || previewImage.startsWith('http') ? previewImage : `${API_URL}${previewImage}`" class="absolute inset-0 w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
              <div v-else class="flex flex-col items-center text-on-surface/40 group-hover:text-on-surface/60 transition-colors">
                <span class="material-symbols-outlined text-4xl mb-2">add_a_photo</span>
                <span class="text-xs font-bold uppercase">Upload Photo</span>
              </div>
              <input ref="fileInputRef" type="file" class="hidden" @change="onFileSelected" accept="image/*" />
            </div>
          </div>
          <div>
            <label class="text-xs font-semibold text-on-surface-variant uppercase mb-2 block">Name</label>
            <input v-model="selectedProduct.name" type="text" class="input" />
          </div>
          <div>
            <label class="text-xs font-semibold text-on-surface-variant uppercase mb-2 block">Description</label>
            <textarea v-model="selectedProduct.description" class="input h-24 resize-none"></textarea>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-xs font-semibold text-on-surface-variant uppercase mb-2 block">Price (PHP)</label>
              <input v-model.number="displayPricePHP" type="number" step="0.01" class="input" />
            </div>
            <div>
              <label class="text-xs font-semibold text-on-surface-variant uppercase mb-2 block">Stock</label>
              <input v-model.number="selectedProduct.stock" type="number" class="input" />
            </div>
          </div>
        </div>

        <div class="mt-10 flex gap-4">
          <button @click="isEditorOpen = false" class="flex-1 h-14 rounded-2xl bg-on-surface/5 text-on-surface font-semibold uppercase text-xs hover:bg-on-surface/10 transition-all">Cancel</button>
          <button @click="saveProduct" class="flex-1 h-14 rounded-2xl bg-primary text-on-surface font-semibold uppercase text-xs hover:bg-primary-dim transition-all shadow-xl">Save Product</button>
        </div>
      </div>
    </div>

    <!-- Order Detail Modal -->
    <div v-if="isOrderDetailOpen && selectedOrder" class="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div class="absolute inset-0 bg-on-surface/90" @click="isOrderDetailOpen = false"></div>
      <div class="relative w-full max-w-2xl glass-thin rounded-[3rem] border border-on-surface/10 p-10 max-h-[90vh] overflow-y-auto scrollbar-hide">
        <div class="flex items-center justify-between mb-8">
          <h2 class="text-3xl font-semibold text-on-surface">Order Details</h2>
          <OrderStatusBadge :status="selectedOrder.status" />
        </div>

        <div class="space-y-8">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-8 border-b border-on-surface/5 pb-6">
            <div>
              <p class="text-xs font-semibold text-on-surface-variant uppercase mb-1">Customer Info</p>
              <p class="font-semibold text-on-surface">{{ selectedOrder.user?.name }} ({{ selectedOrder.user?.role }})</p>
              <p class="text-xs font-bold text-on-surface-variant">{{ selectedOrder.user?.email }}</p>
              <p v-if="selectedOrder.user?.contactNumber" class="text-xs font-bold text-on-surface-variant mt-1">Phone: {{ selectedOrder.user?.contactNumber }}</p>
            </div>
            <div>
              <p class="text-xs font-semibold text-on-surface-variant uppercase mb-1">Order Details</p>
              <p class="text-sm font-bold text-on-surface">Order ID: #{{ selectedOrder.id }}</p>
              <p class="text-xs font-bold text-on-surface-variant mt-1">Placed: {{ formatDate(selectedOrder.createdAt) }}</p>
            </div>
          </div>

          <!-- Parent Contact Info if available -->
          <div v-if="selectedOrder.user?.parentName || selectedOrder.user?.parentContact" class="grid grid-cols-1 md:grid-cols-2 gap-8 border-b border-on-surface/5 pb-6">
            <div v-if="selectedOrder.user?.parentName">
              <p class="text-xs font-semibold text-on-surface-variant uppercase mb-1">Parent/Guardian Name</p>
              <p class="text-sm font-bold text-on-surface">{{ selectedOrder.user?.parentName }}</p>
            </div>
            <div v-if="selectedOrder.user?.parentContact">
              <p class="text-xs font-semibold text-on-surface-variant uppercase mb-1">Parent/Guardian Contact</p>
              <p class="text-sm font-bold text-on-surface">{{ selectedOrder.user?.parentContact }}</p>
            </div>
          </div>

          <div>
            <p class="text-xs font-semibold text-on-surface-variant uppercase mb-4">Items</p>
            <div class="space-y-3">
              <div v-for="item in selectedOrder.items" :key="item.id" class="flex items-center justify-between p-4 rounded-2xl bg-on-surface/5 border border-on-surface/5">
                <div class="flex items-center gap-4">
                  <div class="size-10 rounded-xl bg-on-surface/20 dark:bg-on-surface/40 overflow-hidden">
                    <img v-if="item.product?.imageUrl" :src="item.product.imageUrl.startsWith('http') ? item.product.imageUrl : `${API_URL}${item.product.imageUrl}`" class="w-full h-full object-cover" />
                  </div>
                  <div>
                    <p class="font-semibold text-on-surface text-sm">{{ item.product?.name }}</p>
                    <p class="text-xs font-bold text-on-surface-variant uppercase">{{ item.quantity }} units @ {{ formatPrice(item.priceCentsAtPurchase) }}</p>
                  </div>
                </div>
                <p class="font-semibold text-on-surface">{{ formatPrice(item.priceCentsAtPurchase * item.quantity) }}</p>
              </div>
            </div>
            <div class="mt-6 flex justify-between items-center p-6 rounded-3xl bg-primary/10 border border-primary/20">
              <span class="font-semibold text-primary uppercase text-xs">Total Amount</span>
              <span class="text-2xl font-semibold text-on-surface">{{ formatPrice(selectedOrder.totalCents) }}</span>
            </div>
          </div>

          <div v-if="selectedOrder.notes">
            <p class="text-xs font-semibold text-on-surface-variant uppercase mb-2">Customer Notes</p>
            <p class="p-4 rounded-2xl bg-on-surface/5 text-xs font-bold text-on-surface italic">"{{ selectedOrder.notes }}"</p>
          </div>

          <!-- Actions -->
          <div v-if="selectedOrder.status === 'pending'" class="flex gap-4 pt-4">
            <button @click="updateOrderStatus(selectedOrder.id, 'rejected')" class="flex-1 h-14 rounded-2xl bg-rose-500/10 text-rose-500 font-semibold uppercase text-xs hover:bg-rose-500 hover:text-on-surface transition-all">Reject</button>
            <button @click="updateOrderStatus(selectedOrder.id, 'approved')" class="flex-1 h-14 rounded-2xl bg-primary text-on-surface font-semibold uppercase text-xs hover:bg-primary-dim transition-all shadow-xl shadow-e2">Approve & Deduct Stock</button>
          </div>
          <div v-else-if="selectedOrder.status === 'approved'" class="pt-4">
            <button @click="updateOrderStatus(selectedOrder.id, 'fulfilled')" class="w-full h-14 rounded-2xl bg-emerald-500 text-on-surface font-semibold uppercase text-xs hover:bg-emerald-600 transition-all shadow-xl shadow-emerald-500/20">Mark as Fulfilled</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

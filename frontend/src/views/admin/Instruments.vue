<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useShopStore } from '@stores/shop'
import OrderStatusBadge from '@components/shop/OrderStatusBadge.vue'

const shopStore = useShopStore()
const activeTab = ref<'catalog' | 'orders'>('catalog')
const isEditorOpen = ref(false)
const selectedProduct = ref<any>(null)
const selectedOrder = ref<any>(null)
const isOrderDetailOpen = ref(false)

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
    price_cents: product.priceCents,
    stock: product.stock,
    is_active: product.isActive
  } : {
    name: '',
    description: '',
    price_cents: 0,
    stock: 0,
    is_active: true
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
      await shopStore.uploadProductImage(targetId, imageFile.value)
    }

    isEditorOpen.value = false
    await shopStore.fetchProducts()
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

const updateOrderStatus = async function(id: number, status: any) {
  await shopStore.updateOrderStatus(id, status)
  isOrderDetailOpen.value = false
}
</script>

<template>
  <div class="min-h-screen pb-20">
    <!-- Header -->
    <div class="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6">
      <div>
        <h1 class="text-4xl md:text-5xl font-black text-on-surface mb-4 tracking-tight">
          Shop <span class="text-orange-500">Management</span>
        </h1>
        <p class="text-on-surface-variant font-bold max-w-xl">
          Manage your instrument inventory and process student order requests.
        </p>
      </div>

      <div class="flex items-center gap-4">
        <button
          @click="openEditor()"
          class="h-16 px-8 bg-white text-black rounded-3xl font-black text-sm uppercase tracking-widest transition-all hover:scale-105 active:scale-95 shadow-xl shadow-white/5 flex items-center gap-3"
        >
          <span class="material-symbols-outlined">add</span>
          New Product
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-4 mb-10 border-b border-white/5 pb-4">
      <button
        @click="activeTab = 'catalog'"
        class="px-6 py-2 rounded-xl text-sm font-black uppercase tracking-widest transition-all"
        :class="activeTab === 'catalog' ? 'text-orange-500 bg-orange-500/10' : 'text-on-surface-variant hover:text-on-surface'"
      >
        Catalog
      </button>
      <button
        @click="activeTab = 'orders'"
        class="px-6 py-2 rounded-xl text-sm font-black uppercase tracking-widest transition-all"
        :class="activeTab === 'orders' ? 'text-orange-500 bg-orange-500/10' : 'text-on-surface-variant hover:text-on-surface'"
      >
        Order Requests
      </button>
    </div>

    <!-- Catalog View -->
    <div v-if="activeTab === 'catalog'" class="grid grid-cols-1 gap-4">
      <div v-for="product in shopStore.products" :key="product.id" class="glass-thin rounded-[2rem] p-6 border border-white/5 flex flex-col md:flex-row items-center gap-6">
        <div class="w-24 h-24 rounded-2xl bg-black/20 overflow-hidden shrink-0 border border-white/5">
          <img v-if="product.imageUrl" :src="product.imageUrl" class="w-full h-full object-cover" />
          <div v-else class="w-full h-full flex items-center justify-center text-white/10">
            <span class="material-symbols-outlined">image</span>
          </div>
        </div>

        <div class="flex-1 min-w-0 text-center md:text-left">
          <h3 class="text-xl font-black text-on-surface">{{ product.name }}</h3>
          <p class="text-sm font-bold text-on-surface-variant line-clamp-1">{{ product.description }}</p>
          <div class="flex flex-wrap justify-center md:justify-start gap-4 mt-2">
            <span class="text-xs font-black text-orange-500 uppercase tracking-widest">{{ formatPrice(product.priceCents) }}</span>
            <span class="text-xs font-black text-white/40 uppercase tracking-widest">Stock: {{ product.stock }}</span>
            <span :class="product.isActive ? 'text-emerald-500' : 'text-rose-500'" class="text-xs font-black uppercase tracking-widest">
              {{ product.isActive ? 'Active' : 'Hidden' }}
            </span>
          </div>
        </div>

        <div class="flex gap-3">
          <label class="h-12 w-12 rounded-2xl bg-white/5 text-on-surface-variant hover:text-white transition-all flex items-center justify-center cursor-pointer">
            <input type="file" class="hidden" @change="e => handleFileUpload(e, product.id)" accept="image/*" />
            <span class="material-symbols-outlined">add_a_photo</span>
          </label>
          <button @click="openEditor(product)" class="h-12 w-12 rounded-2xl bg-white/5 text-on-surface-variant hover:text-white transition-all flex items-center justify-center">
            <span class="material-symbols-outlined">edit</span>
          </button>
          <button @click="shopStore.deleteProduct(product.id)" class="h-12 w-12 rounded-2xl bg-white/5 text-on-surface-variant hover:text-rose-500 transition-all flex items-center justify-center">
            <span class="material-symbols-outlined">delete</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Orders View -->
    <div v-else class="space-y-4">
      <div v-for="order in shopStore.orders" :key="order.id" @click="viewOrder(order)" class="glass-thin rounded-[2rem] p-6 border border-white/5 hover:border-orange-500/30 transition-all cursor-pointer group flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-2xl bg-orange-500/10 flex items-center justify-center text-orange-500">
            <span class="material-symbols-outlined">receipt_long</span>
          </div>
          <div>
            <h4 class="font-black text-on-surface">Order #{{ order.id }} - {{ order.user?.name }}</h4>
            <p class="text-xs font-bold text-on-surface-variant uppercase tracking-widest">{{ formatDate(order.createdAt) }}</p>
          </div>
        </div>

        <div class="flex items-center gap-6">
          <div class="text-right">
            <p class="text-lg font-black text-on-surface">{{ formatPrice(order.totalCents) }}</p>
          </div>
          <OrderStatusBadge :status="order.status" />
          <span class="material-symbols-outlined text-white/10 group-hover:text-orange-500 transition-colors">chevron_right</span>
        </div>
      </div>
    </div>

    <!-- Product Editor Modal -->
    <div v-if="isEditorOpen" class="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div class="absolute inset-0 bg-black/90 backdrop-blur-md" @click="isEditorOpen = false"></div>
      <div class="relative w-full max-w-lg glass-thin rounded-[3rem] border border-white/10 p-10">
        <h2 class="text-3xl font-black text-on-surface mb-8">{{ selectedProduct?.id ? 'Edit' : 'New' }} Product</h2>

        <div class="space-y-6">
          <div>
            <label class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-2 block">Product Image</label>
            <div 
              class="w-full h-48 border-2 border-dashed border-white/10 rounded-2xl flex flex-col items-center justify-center bg-white/5 hover:bg-white/10 transition-colors cursor-pointer overflow-hidden relative group"
              @click="triggerFileInput"
            >
              <img v-if="previewImage" :src="previewImage" class="absolute inset-0 w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
              <div v-else class="flex flex-col items-center text-white/40 group-hover:text-white/60 transition-colors">
                <span class="material-symbols-outlined text-4xl mb-2">add_a_photo</span>
                <span class="text-xs font-bold uppercase tracking-widest">Upload Photo</span>
              </div>
              <input ref="fileInputRef" type="file" class="hidden" @change="onFileSelected" accept="image/*" />
            </div>
          </div>
          <div>
            <label class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-2 block">Name</label>
            <input v-model="selectedProduct.name" type="text" class="w-full bg-white/5 border border-white/10 rounded-2xl p-4 text-sm font-bold text-on-surface outline-none focus:ring-2 focus:ring-orange-500/50" />
          </div>
          <div>
            <label class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-2 block">Description</label>
            <textarea v-model="selectedProduct.description" class="w-full bg-white/5 border border-white/10 rounded-2xl p-4 text-sm font-bold text-on-surface outline-none focus:ring-2 focus:ring-orange-500/50 h-24 resize-none"></textarea>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-2 block">Price (PHP)</label>
              <input v-model.number="displayPricePHP" type="number" step="0.01" class="w-full bg-white/5 border border-white/10 rounded-2xl p-4 text-sm font-bold text-on-surface outline-none focus:ring-2 focus:ring-orange-500/50" />
            </div>
            <div>
              <label class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-2 block">Stock</label>
              <input v-model.number="selectedProduct.stock" type="number" class="w-full bg-white/5 border border-white/10 rounded-2xl p-4 text-sm font-bold text-on-surface outline-none focus:ring-2 focus:ring-orange-500/50" />
            </div>
          </div>
        </div>

        <div class="mt-10 flex gap-4">
          <button @click="isEditorOpen = false" class="flex-1 h-14 rounded-2xl bg-white/5 text-on-surface font-black uppercase tracking-widest text-xs hover:bg-white/10 transition-all">Cancel</button>
          <button @click="saveProduct" class="flex-1 h-14 rounded-2xl bg-orange-500 text-white font-black uppercase tracking-widest text-xs hover:bg-orange-600 transition-all shadow-xl shadow-orange-500/20">Save Product</button>
        </div>
      </div>
    </div>

    <!-- Order Detail Modal -->
    <div v-if="isOrderDetailOpen" class="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div class="absolute inset-0 bg-black/90 backdrop-blur-md" @click="isOrderDetailOpen = false"></div>
      <div class="relative w-full max-w-2xl glass-thin rounded-[3rem] border border-white/10 p-10 max-h-[90vh] overflow-y-auto scrollbar-hide">
        <div class="flex items-center justify-between mb-8">
          <h2 class="text-3xl font-black text-on-surface">Order Details</h2>
          <OrderStatusBadge :status="selectedOrder.status" />
        </div>

        <div class="space-y-8">
          <div class="grid grid-cols-2 gap-8">
            <div>
              <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-1">Customer</p>
              <p class="font-black text-on-surface">{{ selectedOrder.user?.name }}</p>
              <p class="text-xs font-bold text-on-surface-variant">{{ selectedOrder.user?.email }}</p>
            </div>
            <div>
              <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-1">Date</p>
              <p class="font-black text-on-surface">{{ formatDate(selectedOrder.createdAt) }}</p>
            </div>
          </div>

          <div>
            <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-4">Items</p>
            <div class="space-y-3">
              <div v-for="item in selectedOrder.items" :key="item.id" class="flex items-center justify-between p-4 rounded-2xl bg-white/5 border border-white/5">
                <div class="flex items-center gap-4">
                  <div class="w-10 h-10 rounded-xl bg-black/20 overflow-hidden">
                    <img v-if="item.product?.imageUrl" :src="item.product.imageUrl" class="w-full h-full object-cover" />
                  </div>
                  <div>
                    <p class="font-black text-on-surface text-sm">{{ item.product?.name }}</p>
                    <p class="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">{{ item.quantity }} units @ {{ formatPrice(item.priceCentsAtPurchase) }}</p>
                  </div>
                </div>
                <p class="font-black text-on-surface">{{ formatPrice(item.priceCentsAtPurchase * item.quantity) }}</p>
              </div>
            </div>
            <div class="mt-6 flex justify-between items-center p-6 rounded-[2rem] bg-orange-500/10 border border-orange-500/20">
              <span class="font-black text-orange-500 uppercase tracking-widest text-xs">Total Amount</span>
              <span class="text-2xl font-black text-on-surface">{{ formatPrice(selectedOrder.totalCents) }}</span>
            </div>
          </div>

          <div v-if="selectedOrder.notes">
            <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-2">Customer Notes</p>
            <p class="p-4 rounded-2xl bg-white/5 text-xs font-bold text-on-surface italic">"{{ selectedOrder.notes }}"</p>
          </div>

          <!-- Actions -->
          <div v-if="selectedOrder.status === 'pending'" class="flex gap-4 pt-4">
            <button @click="updateOrderStatus(selectedOrder.id, 'rejected')" class="flex-1 h-14 rounded-2xl bg-rose-500/10 text-rose-500 font-black uppercase tracking-widest text-xs hover:bg-rose-500 hover:text-white transition-all">Reject</button>
            <button @click="updateOrderStatus(selectedOrder.id, 'approved')" class="flex-1 h-14 rounded-2xl bg-orange-500 text-white font-black uppercase tracking-widest text-xs hover:bg-orange-600 transition-all shadow-xl shadow-orange-500/20">Approve & Deduct Stock</button>
          </div>
          <div v-else-if="selectedOrder.status === 'approved'" class="pt-4">
            <button @click="updateOrderStatus(selectedOrder.id, 'fulfilled')" class="w-full h-14 rounded-2xl bg-emerald-500 text-white font-black uppercase tracking-widest text-xs hover:bg-emerald-600 transition-all shadow-xl shadow-emerald-500/20">Mark as Fulfilled</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

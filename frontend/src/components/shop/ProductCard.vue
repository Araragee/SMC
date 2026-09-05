<script setup lang="ts">
import type { InstrumentProduct } from '@types'
import { useShopStore } from '@stores/shop'
import { API_URL } from '@typescript/constants'

const props = defineProps<{
  product: InstrumentProduct
}>()

const shopStore = useShopStore()

const formatPrice = function (cents: number) {
  return new Intl.NumberFormat('en-PH', {
    style: 'currency',
    currency: 'PHP',
  }).format(cents / 100)
}

const handleAddToCart = function (e: Event) {
  e.stopPropagation()
  shopStore.addToCart(props.product.id)
}
</script>

<template>
  <div
    class="glass-thin rounded-3xl overflow-hidden border border-outline-variant/20 dark:border-on-surface/5 hover:border-primary/30 transition-all group flex flex-col h-full bg-surface-container-low/50 dark:bg-transparent"
  >
    <!-- Image -->
    <div class="aspect-square relative overflow-hidden bg-on-surface/5 dark:bg-on-surface/40">
      <img
        v-if="product.imageUrl"
        :src="
          product.imageUrl.startsWith('http') ? product.imageUrl : `${API_URL}${product.imageUrl}`
        "
        class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
      />
      <div v-else class="w-full h-full flex items-center justify-center text-on-surface/5">
        <span class="material-symbols-outlined text-6xl">image</span>
      </div>

      <!-- Category Badge -->
      <div v-if="product.category" class="absolute top-4 left-4">
        <span
          class="px-4 py-1.5 rounded-full bg-on-surface/40 dark:bg-on-surface/60 border border-on-surface/10 text-xs font-semibold uppercase text-on-surface"
        >
          {{ product.category.name }}
        </span>
      </div>

      <!-- Out of Stock Overlay -->
      <div
        v-if="product.stock <= 0"
        class="absolute inset-0 bg-black/40 dark:bg-black/70 flex items-center justify-center"
      >
        <span
          class="px-6 py-2 rounded-xl bg-error/20 border border-error/30 text-error font-semibold uppercase tracking-tighter text-sm"
        >
          Out of Stock
        </span>
      </div>
    </div>

    <!-- Info -->
    <div class="p-6 flex flex-col flex-grow">
      <div class="mb-4">
        <h3 class="text-xl font-semibold text-on-surface line-clamp-1 mb-1">{{ product.name }}</h3>
        <p class="text-xs font-bold text-on-surface-variant line-clamp-2 h-8">
          {{ product.description }}
        </p>
      </div>

      <div class="mt-auto flex items-center justify-between gap-4">
        <div>
          <p class="text-xs font-semibold text-on-surface-variant uppercase mb-0.5">Price</p>
          <p class="text-xl font-semibold text-primary tracking-tighter">
            {{ formatPrice(product.priceCents) }}
          </p>
        </div>

        <button
          @click="handleAddToCart"
          :disabled="product.stock <= 0"
          class="h-12 w-12 rounded-2xl bg-on-surface text-surface dark:bg-surface-container-lowest dark:text-on-primary hover:bg-primary hover:text-on-primary dark:hover:bg-primary dark:hover:text-on-primary disabled:opacity-20 transition-all flex items-center justify-center shadow-lg shadow-e2 dark:shadow-e2 active:scale-90"
        >
          <span class="material-symbols-outlined font-semibold">add_shopping_cart</span>
        </button>
      </div>
    </div>
  </div>
</template>

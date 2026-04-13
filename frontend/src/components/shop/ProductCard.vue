<script setup lang="ts">
import type { InstrumentProduct } from '@types'
import { useShopStore } from '@stores/shop'

const props = defineProps<{
  product: InstrumentProduct
}>()

const shopStore = useShopStore()

const formatPrice = function(cents: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'PHP'
  }).format(cents / 100)
}

const handleAddToCart = function() {
  shopStore.addToCart(props.product.id)
}
</script>

<template>
  <div class="glass-thin rounded-[2.5rem] overflow-hidden border border-white/5 hover:border-orange-500/30 transition-all group flex flex-col h-full">
    <!-- Image -->
    <div class="aspect-square relative overflow-hidden bg-black/20">
      <img
        v-if="product.imageUrl"
        :src="product.imageUrl"
        class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
      />
      <div v-else class="w-full h-full flex items-center justify-center text-white/5">
        <span class="material-symbols-outlined text-6xl">image</span>
      </div>

      <!-- Category Badge -->
      <div v-if="product.category" class="absolute top-4 left-4">
        <span class="px-4 py-1.5 rounded-full bg-black/60 backdrop-blur-md border border-white/10 text-[10px] font-black uppercase tracking-widest text-white">
          {{ product.category.name }}
        </span>
      </div>

      <!-- Out of Stock Overlay -->
      <div v-if="product.stock <= 0" class="absolute inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center">
        <span class="px-6 py-2 rounded-xl bg-rose-500/20 border border-rose-500/30 text-rose-500 font-black uppercase tracking-tighter text-sm">
          Out of Stock
        </span>
      </div>
    </div>

    <!-- Info -->
    <div class="p-6 flex flex-col flex-grow">
      <div class="mb-4">
        <h3 class="text-xl font-black text-on-surface line-clamp-1 mb-1">{{ product.name }}</h3>
        <p class="text-xs font-bold text-on-surface-variant line-clamp-2 h-8">{{ product.description }}</p>
      </div>

      <div class="mt-auto flex items-center justify-between gap-4">
        <div>
          <p class="text-[10px] font-black text-on-surface-variant uppercase tracking-widest mb-0.5">Price</p>
          <p class="text-xl font-black text-orange-500 tracking-tighter">{{ formatPrice(product.priceCents) }}</p>
        </div>

        <button
          @click="handleAddToCart"
          :disabled="product.stock <= 0"
          class="h-12 w-12 rounded-2xl bg-white text-black hover:bg-orange-500 hover:text-white disabled:opacity-20 disabled:hover:bg-white disabled:hover:text-black transition-all flex items-center justify-center shadow-lg shadow-white/5 active:scale-90"
        >
          <span class="material-symbols-outlined font-black">add_shopping_cart</span>
        </button>
      </div>
    </div>
  </div>
</template>

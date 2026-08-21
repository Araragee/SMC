<script setup lang="ts">
import { ref, computed } from 'vue'
import type { InstrumentProduct } from '@types'
import ProductCard from './ProductCard.vue'

const props = defineProps<{
  products: InstrumentProduct[]
}>()

const emit = defineEmits(['view-product'])

const searchQuery = ref('')
const selectedCategory = ref<number | null>(null)

const categories = computed(() => {
  const cats = new Map<number, string>()
  props.products.forEach(p => {
    if (p.category) cats.set(p.category.id, p.category.name)
  })
  return Array.from(cats.entries()).map(([id, name]) => ({ id, name }))
})

const filteredProducts = computed(() => {
  return props.products.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
                         p.description?.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesCategory = !selectedCategory.value || p.categoryId === selectedCategory.value
    return matchesSearch && matchesCategory
  })
})
</script>

<template>
  <div class="space-y-8">
    <!-- Filters -->
    <div class="flex flex-col md:flex-row gap-4 items-center justify-between glass-thin p-4 rounded-3xl border border-outline-variant/20 dark:border-on-surface/5 bg-surface-container-low/50 dark:bg-transparent">
      <div class="relative w-full md:w-96 group">
        <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant dark:text-on-surface-variant group-focus-within:text-primary transition-colors">search</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search instruments..."
          class="input pl-12"
        />
      </div>

      <div class="flex gap-2 overflow-x-auto w-full md:w-auto pb-2 md:pb-0 scrollbar-hide">
        <button
          @click="selectedCategory = null"
          class="px-4 py-2 rounded-xl text-xs font-semibold uppercase transition-all shrink-0"
          :class="!selectedCategory ? 'bg-primary text-on-surface shadow-lg' : 'bg-on-surface/5 dark:bg-on-surface/5 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface'"
        >
          All
        </button>
        <button
          v-for="cat in categories"
          :key="cat.id"
          @click="selectedCategory = cat.id"
          class="px-4 py-2 rounded-xl text-xs font-semibold uppercase transition-all shrink-0"
          :class="selectedCategory === cat.id ? 'bg-primary text-on-surface shadow-lg' : 'bg-on-surface/5 dark:bg-on-surface/5 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface'"
        >
          {{ cat.name }}
        </button>
      </div>
    </div>

    <!-- Grid -->
    <div v-if="filteredProducts.length > 0" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      <ProductCard
        v-for="product in filteredProducts"
        :key="product.id"
        :product="product"
        @click="emit('view-product', product)"
      />
    </div>

    <!-- Empty State -->
    <div v-else class="py-40 flex flex-col items-center justify-center glass-thin rounded-[3rem] border border-on-surface/5">
      <div class="size-20 rounded-full bg-on-surface/5 flex items-center justify-center text-on-surface-variant mb-6">
        <span class="material-symbols-outlined text-4xl">search_off</span>
      </div>
      <h3 class="text-xl font-semibold text-on-surface mb-2">No instruments found</h3>
      <p class="text-on-surface-variant font-bold text-center max-w-xs">
        Try adjusting your search or category filter to find what you're looking for.
      </p>
    </div>
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

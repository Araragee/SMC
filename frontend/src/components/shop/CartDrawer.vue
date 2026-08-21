<script setup lang="ts">
import { ref } from 'vue'
import { useShopStore } from '@stores/shop'
import { API_URL } from '@typescript/constants'

defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits(['close', 'checkout'])
const shopStore = useShopStore()
const notes = ref('')

const formatPrice = function(cents: number) {
  return new Intl.NumberFormat('en-PH', {
    style: 'currency',
    currency: 'PHP'
  }).format(cents / 100)
}

const handleCheckout = async function() {
  await shopStore.placeOrder(notes.value)
  notes.value = ''
  emit('checkout')
  emit('close')
}
</script>

<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 overflow-hidden"
    aria-labelledby="slide-over-title"
    role="dialog"
    aria-modal="true"
  >
    <div class="absolute inset-0 bg-on-surface/80 transition-opacity" @click="emit('close')"></div>

    <div class="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
      <div class="pointer-events-auto w-screen max-w-md transform transition-transform duration-500 ease-in-out">
        <div class="flex h-full flex-col bg-surface border-l border-outline-variant/20 dark:border-on-surface/5 shadow-e3">
          <!-- Header -->
          <div class="p-8 border-b border-outline-variant/20 dark:border-on-surface/5 flex items-center justify-between">
            <h2 class="text-2xl font-black text-on-surface dark:text-on-surface uppercase tracking-tight" id="slide-over-title">
              Shopping <span class="text-primary">Cart</span>
            </h2>
            <button
              @click="emit('close')"
              class="w-10 h-10 rounded-xl bg-on-surface/5 dark:bg-on-surface/5 text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface transition-all flex items-center justify-center"
            >
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <!-- Items -->
          <div class="flex-1 overflow-y-auto p-8 scrollbar-hide">
            <div v-if="shopStore.cart.length > 0" class="space-y-6">
              <div
                v-for="item in shopStore.cart"
                :key="item.productId"
                class="flex gap-4 p-4 rounded-3xl bg-on-surface/5 dark:bg-on-surface/5 border border-outline-variant/20 dark:border-on-surface/5"
              >
                <div class="w-20 h-20 rounded-2xl overflow-hidden bg-on-surface/20 dark:bg-on-surface/40 shrink-0">
                  <img
                    v-if="shopStore.getCartProduct(item.productId)?.imageUrl"
                    :src="shopStore.getCartProduct(item.productId)?.imageUrl?.startsWith('http') ? shopStore.getCartProduct(item.productId)?.imageUrl : `${API_URL}${shopStore.getCartProduct(item.productId)?.imageUrl}`"
                    class="w-full h-full object-cover"
                  />
                  <div v-else class="w-full h-full flex items-center justify-center text-on-surface/5">
                    <span class="material-symbols-outlined">image</span>
                  </div>
                </div>

                <div class="flex-1 min-w-0">
                  <h4 class="font-black text-on-surface dark:text-on-surface truncate">{{ shopStore.getCartProduct(item.productId)?.name }}</h4>
                  <p class="text-sm font-black text-primary mb-3">
                    {{ formatPrice(shopStore.getCartProduct(item.productId)?.priceCents || 0) }}
                  </p>

                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-3 bg-on-surface/5 dark:bg-on-surface/20 rounded-xl px-2 py-1">
                      <button
                        @click="shopStore.updateCartItem(item.productId, item.quantity - 1)"
                        class="text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface transition-colors"
                      >
                        <span class="material-symbols-outlined text-sm">remove</span>
                      </button>
                      <span class="text-xs font-black text-on-surface dark:text-on-surface w-4 text-center">{{ item.quantity }}</span>
                      <button
                        @click="shopStore.updateCartItem(item.productId, item.quantity + 1)"
                        class="text-on-surface-variant dark:text-on-surface-variant hover:text-on-surface dark:hover:text-on-surface transition-colors"
                      >
                        <span class="material-symbols-outlined text-sm">add</span>
                      </button>
                    </div>

                    <button
                      @click="shopStore.removeFromCart(item.productId)"
                      class="text-on-surface-variant hover:text-rose-500 transition-colors"
                    >
                      <span class="material-symbols-outlined text-sm">delete</span>
                    </button>
                  </div>
                </div>
              </div>

              <!-- Notes -->
              <div class="pt-6">
                <label class="text-[10px] font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest mb-3 block">Order Notes</label>
                <textarea
                  v-model="notes"
                  placeholder="Anything we should know? (e.g. delivery preferences)"
                  class="w-full bg-on-surface/5 dark:bg-on-surface/5 border border-outline-variant/20 dark:border-on-surface/10 rounded-2xl p-4 text-xs font-bold text-on-surface dark:text-on-surface placeholder:text-on-surface-variant/50 focus:ring-2 focus:ring-primary/50 transition-all outline-none resize-none h-24"
                ></textarea>
              </div>
            </div>

            <div v-else class="h-full flex flex-col items-center justify-center text-center py-20">
              <div class="w-20 h-20 rounded-full bg-on-surface/5 flex items-center justify-center text-on-surface-variant mb-6">
                <span class="material-symbols-outlined text-4xl">shopping_basket</span>
              </div>
              <h3 class="text-xl font-black text-on-surface mb-2">Cart is empty</h3>
              <p class="text-on-surface-variant font-bold text-sm">Add some instruments to get started!</p>
            </div>
          </div>

          <!-- Footer -->
          <div v-if="shopStore.cart.length > 0" class="p-8 border-t border-outline-variant/20 dark:border-on-surface/5 bg-surface-container dark:bg-on-surface/20">
            <div class="flex items-center justify-between mb-6">
              <span class="text-sm font-black text-on-surface-variant dark:text-on-surface-variant uppercase tracking-widest">Total Amount</span>
              <span class="text-2xl font-black text-on-surface dark:text-on-surface tracking-tighter">{{ formatPrice(shopStore.cartTotalCents) }}</span>
            </div>

            <button
              @click="handleCheckout"
              class="w-full h-16 bg-primary hover:bg-primary-dim text-on-surface rounded-2xl font-black text-sm uppercase tracking-widest transition-all hover:scale-[1.02] active:scale-95 shadow-xl"
            >
              Place Order Request
            </button>
            <p class="text-[10px] text-center text-on-surface-variant/50 font-bold mt-4 uppercase tracking-wider">
              Payments are handled manually after order approval
            </p>
          </div>
        </div>
      </div>
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

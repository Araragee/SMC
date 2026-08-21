<script setup lang="ts">
import type { OrderStatus } from '@types'

defineProps<{
  status: OrderStatus
}>()

const getStatusColor = (status: OrderStatus) => {
  switch (status) {
    case 'pending': return 'bg-amber-500/10 text-amber-500 border-amber-500/20'
    case 'approved': return 'bg-blue-500/10 text-blue-500 border-blue-500/20'
    case 'fulfilled': return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
    case 'rejected': return 'bg-rose-500/10 text-rose-500 border-rose-500/20'
    case 'cancelled': return 'bg-zinc-500/10 text-zinc-500 border-zinc-500/20'
    default: return 'bg-black/5 dark:bg-white/5 text-on-surface-variant dark:text-on-surface-variant border-outline-variant/20 dark:border-white/10'
  }
}
</script>

<template>
  <span
    class="px-4 py-1.5 rounded-full border text-xs font-semibold uppercase"
    :class="getStatusColor(status)"
  >
    {{ status }}
  </span>
</template>

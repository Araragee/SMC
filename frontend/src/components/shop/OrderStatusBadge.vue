<script setup lang="ts">
import type { OrderStatus } from '@types'

defineProps<{
  status: OrderStatus
}>()

const getStatusColor = (status: OrderStatus) => {
  switch (status) {
    case 'pending':
      return 'bg-warning/10 text-warning border-warning/20'
    case 'approved':
      return 'bg-tertiary/10 text-tertiary border-tertiary/20'
    case 'fulfilled':
      return 'bg-success/10 text-success border-success/20'
    case 'rejected':
      return 'bg-error/10 text-error border-error/20'
    case 'cancelled':
      return 'bg-surface-container-high/10 text-on-surface-variant border-outline-variant/20'
    default:
      return 'bg-on-surface/5 text-on-surface-variant border-outline-variant/20 dark:border-on-surface/10'
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

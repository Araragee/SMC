<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AuthLayout from './layouts/AuthLayout.vue'

const route = useRoute()
const layout = computed(() => route.meta.layout || AuthLayout)
</script>

<template>
  <component :is="layout">
    <router-view />
  </component>
</template>

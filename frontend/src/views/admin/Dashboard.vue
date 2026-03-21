<template>
  <div class="flex">
    <AdminSidebar />
    <div class="ml-64 w-full p-8 pt-28">
      <h2 class="text-3xl font-black mb-6 text-white">Admin Dashboard</h2>
      <p class="text-zinc-400">Welcome to the central command center for Sernan's Music Clinic.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import AdminSidebar from '../../components/AdminSidebar.vue'
</script>

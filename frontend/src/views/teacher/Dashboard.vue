<template>
  <div class="flex">
    <TeacherSidebar />
    <div class="ml-64 w-full p-8 pt-28">
      <h2 class="text-3xl font-black mb-6 text-white">Teacher Dashboard</h2>
      <p class="text-zinc-400">Manage your roster, schedule, and student progress.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import TeacherSidebar from '../../components/TeacherSidebar.vue'
</script>

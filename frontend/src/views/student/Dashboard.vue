<template>
  <div class="flex">
    <StudentSidebar />
    <div class="ml-64 w-full p-8 pt-28">
      <h2 class="text-3xl font-black mb-6 text-white">Student Dashboard</h2>
      <p class="text-zinc-400">View your schedule, homework, and track your progress.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import StudentSidebar from '../../components/StudentSidebar.vue'
</script>

<template>
  <main class="relative z-10 w-full max-w-[1200px] px-6 py-12 flex flex-col items-center justify-center lg:flex-row gap-16">
    <div class="w-full lg:w-1/2 space-y-8 text-center lg:text-left">
      <div class="inline-flex items-center gap-3">
        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-tertiary_container flex items-center justify-center inner-glow-top-left">
          <span class="material-symbols-outlined text-on_primary_container" style="font-variation-settings: 'FILL' 1;">music_note</span>
        </div>
        <span class="text-2xl font-black tracking-tighter text-white uppercase font-sans">Sernan's Music Clinic</span>
      </div>
      <div class="space-y-4">
        <h1 class="text-5xl md:text-7xl font-extrabold tracking-tight leading-[1.1] text-on_surface font-sans">
          Welcome back, <br/>
          <span class="text-transparent bg-clip-text bg-gradient-to-r from-primary to-tertiary_container">Maestro.</span>
        </h1>
        <p class="text-on_surface_variant text-lg max-w-md mx-auto lg:mx-0">
          Your digital conservatory awaits. Tune into your projects and continue the orchestration.
        </p>
      </div>
    </div>
    <div class="w-full max-w-md">
      <div class="relative group">
        <div class="absolute -inset-1 bg-gradient-to-br from-primary/20 to-transparent blur-2xl opacity-50"></div>
        <div class="relative bg-surface-container-low/40 backdrop-blur-3xl p-10 rounded-xl inner-glow-top-left border border-white/5 space-y-8">
          <form class="space-y-6" @submit.prevent="handleLogin">
            <div class="space-y-2">
              <label class="block text-[10px] tracking-widest uppercase text-neutral-500 font-bold px-1">Identity / Role</label>
              <div class="relative">
                <select v-model="role" class="w-full h-16 bg-surface-container-highest/50 border-none rounded-lg pl-6 pr-6 text-on_surface focus:ring-1 focus:ring-primary/50 transition-all duration-300 appearance-none">
                  <option value="admin">Admin</option>
                  <option value="teacher">Teacher</option>
                  <option value="student">Student</option>
                </select>
                <span class="material-symbols-outlined absolute right-5 top-1/2 -translate-y-1/2 text-neutral-500">expand_more</span>
              </div>
            </div>
            <button class="group relative w-full h-16 bg-gradient-to-br from-primary to-tertiary_container rounded-lg font-bold text-on_primary_container uppercase tracking-wider overflow-hidden active:scale-[0.98] transition-all duration-300" type="submit">
              <span class="relative z-10">Sign In</span>
              <div class="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </button>
          </form>
        </div>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const role = ref<'admin' | 'teacher' | 'student'>('admin')

const handleLogin = () => {
    // Basic mock navigation for Phase 1
    router.push(`/${role.value}`)
}
</script>

<style scoped>
.inner-glow-top-left {
  box-shadow: inset 1px 1px 0px 0px rgba(255, 255, 255, 0.15);
}
</style>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import BaseInput from './BaseInput.vue'
import { useRouter } from 'vue-router'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const authStore = useAuthStore()
const router = useRouter()

const form = reactive({
  name: '',
  email: '',
  avatar_url: '',
  password: ''
})

// Initialize form when modal opens
watch(() => props.isOpen, (newVal) => {
  if (newVal && authStore.user) {
    form.name = authStore.user.name || ''
    form.email = authStore.user.email || ''
    form.avatar_url = authStore.user.avatarUrl || ''
    form.password = ''
  }
}, { immediate: true })

const handleSave = async () => {
  const payload: any = {
    name: form.name,
    email: form.email
  }

  if (form.avatar_url) payload.avatar_url = form.avatar_url
  if (form.password) payload.password = form.password

  const success = await authStore.updateProfile(payload)
  if (success) {
    emit('close')
  }
}

const handleLogout = () => {
  emit('close')
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <Teleport to="body">
    <Transition enter-active-class="transition-all duration-300 ease-out" enter-from-class="opacity-0 scale-95 translate-y-4 blur-[4px]" enter-to-class="opacity-100 scale-100 translate-y-0 blur-0" leave-active-class="transition-all duration-300 ease-in" leave-from-class="opacity-100 scale-100 translate-y-0 blur-0" leave-to-class="opacity-0 scale-95 translate-y-4 blur-[4px]">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[220] flex items-center justify-center p-4"
        @click.self="$emit('close')"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/80 backdrop-blur-md" @click="$emit('close')" />

        <!-- Modal Card -->
        <div class="relative w-full max-w-xl liquid-glass rounded-[2.5rem] border border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
          <!-- Decorative Header -->
          <div class="h-2 w-full bg-gradient-to-r from-orange-600 via-orange-400 to-orange-600"></div>

          <!-- Header Section -->
          <div class="p-8 pb-0 flex items-start justify-between">
            <div>
              <p class="text-[10px] font-black text-orange-500 uppercase tracking-[0.3em] mb-2">Account Control</p>
              <h2 class="text-3xl font-black text-white tracking-tight">User Settings</h2>
            </div>
            <button
              @click="$emit('close')"
              class="w-12 h-12 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 flex items-center justify-center text-zinc-400 hover:text-white transition-all group"
            >
              <span class="material-symbols-outlined text-xl group-hover:rotate-90 transition-transform duration-300">close</span>
            </button>
          </div>

          <div class="flex-1 overflow-y-auto p-8 pt-6 space-y-10 custom-scrollbar">
            <!-- Profile Overview -->
            <section class="space-y-6">
              <div class="flex items-center gap-6">
                <div class="relative group">
                  <div class="w-24 h-24 rounded-[2rem] bg-orange-500/10 border-2 border-dashed border-orange-500/30 flex items-center justify-center overflow-hidden transition-all group-hover:border-orange-500/60">
                    <img v-if="form.avatar_url || authStore.user?.avatarUrl" :src="form.avatar_url || authStore.user?.avatarUrl" class="w-full h-full object-cover" />
                    <span v-else class="text-3xl font-black text-orange-500/40">{{ authStore.user?.name?.charAt(0).toUpperCase() }}</span>
                    
                    <!-- Overlay for upload (mock) -->
                    <div class="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer">
                      <span class="material-symbols-outlined text-white text-2xl">add_a_photo</span>
                    </div>
                  </div>
                </div>
                <div>
                  <h3 class="text-xl font-bold text-white mb-1">{{ authStore.user?.name }}</h3>
                  <p class="text-zinc-500 text-sm font-medium">{{ authStore.user?.email }}</p>
                  <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-orange-500/10 border border-orange-500/20 mt-3">
                    <span class="text-[9px] font-black text-orange-500 uppercase tracking-widest">{{ authStore.user?.role }}</span>
                  </div>
                </div>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <BaseInput
                  v-model="form.name"
                  label="Full Name"
                  placeholder="Your Name"
                  icon-left="person"
                />
                <BaseInput
                  v-model="form.email"
                  label="Email Address"
                  placeholder="email@example.com"
                  icon-left="mail"
                />
              </div>
              
              <BaseInput
                v-model="form.avatar_url"
                label="Avatar URL"
                placeholder="https://..."
                icon-left="image"
              />
            </section>

            <!-- Security Section -->
            <section class="space-y-6">
              <div class="flex items-center gap-3 px-1">
                <span class="material-symbols-outlined text-orange-500 text-lg">security</span>
                <h3 class="text-sm font-black text-white uppercase tracking-widest">Security & Privacy</h3>
              </div>
              
              <div class="bg-white/[0.03] border border-white/5 rounded-3xl p-6 space-y-6">
                <BaseInput
                  v-model="form.password"
                  label="Change Password"
                  type="password"
                  placeholder="Enter new password"
                  icon-left="lock"
                />
                <p class="text-[10px] text-zinc-500 font-medium px-2 italic leading-relaxed">
                  Leave the password field empty if you don't wish to change it. Your new password must be at least 8 characters long.
                </p>
              </div>
            </section>

            <!-- Danger Zone -->
            <section class="space-y-4">
              <div class="flex items-center gap-3 px-1">
                <span class="material-symbols-outlined text-red-500 text-lg">warning</span>
                <h3 class="text-sm font-black text-red-500 uppercase tracking-widest">Danger Zone</h3>
              </div>
              <div class="bg-red-500/5 border border-red-500/10 rounded-3xl p-6">
                <button
                  @click="handleLogout"
                  class="w-full py-4 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-500 font-black rounded-2xl transition-all flex items-center justify-center gap-3 group"
                >
                  <span class="material-symbols-outlined text-xl group-hover:translate-x-1 transition-transform">logout</span>
                  SIGN OUT FROM THIS SESSION
                </button>
              </div>
            </section>
          </div>

          <!-- Sticky Footer -->
          <div class="p-8 border-t border-white/5 bg-white/[0.02] flex items-center justify-end gap-4 shrink-0">
            <button
              @click="$emit('close')"
              class="px-6 py-3 text-sm font-bold text-zinc-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              @click="handleSave"
              :disabled="authStore.isLoading"
              class="px-10 py-3 bg-gradient-to-br from-orange-500 to-orange-700 hover:from-orange-400 hover:to-orange-600 text-white font-black rounded-2xl shadow-lg shadow-orange-950/20 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:scale-100 flex items-center gap-2"
            >
              <span v-if="authStore.isLoading" class="material-symbols-outlined animate-spin text-sm">progress_activity</span>
              {{ authStore.isLoading ? 'SAVING...' : 'SAVE CHANGES' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>


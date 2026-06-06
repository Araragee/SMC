<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { API_URL } from '@typescript/constants'
import axios from 'axios'
import { useAuthStore } from '@stores/auth'
import { useToastStore } from '@stores/toast'
import type { Homework } from '@types'

const authStore = useAuthStore()
const toast = useToastStore()

const homeworks = ref<Homework[]>([])
const isLoading = ref(false)
const isUploading = ref<number | null>(null)

onMounted(async () => {
  isLoading.value = true
  try {
    const res = await axios.get(`${API_URL}/homework/user/${authStore.currentUser?.id}`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    homeworks.value = res.data.map((hw: any) => ({
      id: hw.id,
      sessionId: hw.session_id,
      description: hw.description,
      isCompleted: hw.is_completed,
      fileUrl: hw.file_url,
      createdAt: hw.created_at
    }))
  } catch (err) {
    toast.error('Failed to load homework')
  } finally {
    isLoading.value = false
  }
})

const pendingHomework = computed(() => homeworks.value.filter(h => !h.isCompleted))
const completedHomework = computed(() => homeworks.value.filter(h => h.isCompleted))

async function handleFileUpload(event: Event, homeworkId: number) {
  const target = event.target as HTMLInputElement
  if (!target.files?.length) return
  
  const file = target.files[0]
  const formData = new FormData()
  formData.append('file', file)
  
  isUploading.value = homeworkId
  try {
    const res = await axios.post(`${API_URL}/homework/${homeworkId}/upload`, formData, {
      headers: { 
        Authorization: `Bearer ${authStore.token}`,
        'Content-Type': 'multipart/form-data'
      }
    })
    const index = homeworks.value.findIndex(h => h.id === homeworkId)
    if (index !== -1) {
      homeworks.value[index].isCompleted = true
      homeworks.value[index].fileUrl = res.data.file_url
    }
    toast.success('Upload Successful', 'Your homework has been submitted.')
  } catch (err) {
    toast.error('Upload Failed', 'Please try again later.')
  } finally {
    isUploading.value = null
  }
}
</script>

<template>
  <div class="max-w-[1200px] mx-auto pb-28 space-y-10 px-4 sm:px-6">
    <!-- Header -->
    <header class="pt-8">
      <div class="flex items-center gap-3 mb-3">
        <div class="w-10 h-10 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
          <span class="material-symbols-outlined text-indigo-500 text-2xl">menu_book</span>
        </div>
        <p class="text-[10px] font-black text-indigo-500 uppercase tracking-[0.25em]">Self Study</p>
      </div>
      <h1 class="text-5xl font-black tracking-tight text-on-surface mb-2">Homework & Assignments</h1>
      <p class="text-on-surface-variant font-medium text-lg">Review your practice goals and upload completion proofs.</p>
    </header>

    <div class="space-y-12">
      <!-- Pending Section -->
      <section class="space-y-6">
        <div class="flex items-center gap-4">
          <h2 class="text-xl font-black text-on-surface uppercase tracking-wider">Active Tasks</h2>
          <div class="h-px flex-1 bg-outline-variant/20"></div>
          <span class="text-[10px] font-black px-3 py-1 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20">
            {{ pendingHomework.length }} Pending
          </span>
        </div>

        <div v-if="pendingHomework.length === 0" class="glass-medium rounded-[3rem] p-16 text-center border-dashed border-2 border-outline-variant/30">
          <p class="text-on-surface-variant font-bold">All caught up! No pending assignments.</p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div 
            v-for="hw in pendingHomework" 
            :key="hw.id"
            class="glass-heavy rounded-[2.5rem] p-8 border border-outline-variant/30 hover:shadow-2xl hover:shadow-indigo-500/10 transition-all group overflow-hidden relative"
          >
            <div class="absolute -right-8 -top-8 w-32 h-32 bg-indigo-500/5 blur-3xl rounded-full" />
            
            <div class="relative z-10 flex flex-col h-full">
              <div class="flex justify-between items-start mb-4">
                <span class="text-[10px] font-black text-indigo-500 uppercase tracking-widest">Session #{{ hw.sessionId }}</span>
                <span class="text-[10px] font-bold text-on-surface-variant">{{ new Date(hw.createdAt).toLocaleDateString() }}</span>
              </div>
              
              <h3 class="text-xl font-black text-on-surface mb-4 leading-tight group-hover:text-indigo-500 transition-colors">
                {{ hw.description }}
              </h3>
              
              <div class="mt-auto pt-6 flex items-center gap-4">
                <label 
                  class="flex-1 cursor-pointer"
                  :class="isUploading === hw.id ? 'pointer-events-none opacity-50' : ''"
                >
                  <input 
                    type="file" 
                    class="hidden" 
                    @change="(e) => handleFileUpload(e, hw.id)"
                    accept="image/*,.pdf,.doc,.docx"
                  />
                  <div class="w-full py-4 bg-indigo-500 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20 hover:scale-[1.02] active:scale-95 transition-all">
                    <span class="material-symbols-outlined text-sm">{{ isUploading === hw.id ? 'progress_activity' : 'cloud_upload' }}</span>
                    {{ isUploading === hw.id ? 'Uploading...' : 'Submit Proof' }}
                  </div>
                </label>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Completed Section -->
      <section class="space-y-6">
        <div class="flex items-center gap-4">
          <h2 class="text-xl font-black text-on-surface uppercase tracking-wider text-on-surface-variant">Archive</h2>
          <div class="h-px flex-1 bg-outline-variant/10"></div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div 
            v-for="hw in completedHomework" 
            :key="hw.id"
            class="glass-medium rounded-[2rem] p-6 border border-outline-variant/20 flex items-center justify-between group"
          >
            <div class="min-w-0 flex-1">
              <p class="text-[10px] font-black text-emerald-500 uppercase tracking-widest mb-1 flex items-center gap-1">
                <span class="material-symbols-outlined text-xs">check_circle</span>
                Completed
              </p>
              <h4 class="font-bold text-on-surface truncate text-sm">{{ hw.description }}</h4>
            </div>
            
            <a 
              v-if="hw.fileUrl" 
              :href="hw.fileUrl" 
              target="_blank"
              class="ml-4 w-10 h-10 rounded-xl bg-surface-container-highest flex items-center justify-center text-on-surface-variant hover:text-primary transition-colors"
            >
              <span class="material-symbols-outlined">visibility</span>
            </a>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.glass-heavy {
  @apply bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl shadow-xl;
}
.glass-medium {
  @apply bg-white/40 dark:bg-white/5 backdrop-blur-md;
}
</style>

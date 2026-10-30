<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { API_URL } from '@typescript/constants'
import axios from 'axios'
import { useAuthStore } from '@stores/auth'
import { useToastStore } from '@stores/toast'
import { mapHomework } from '@stores/homework'
import { apiError } from '@/utils/apiError'
import { IMAGE_ACCEPT_ATTR, validateImageUpload } from '@/utils/upload'
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
      headers: { Authorization: `Bearer ${authStore.token}` },
    })
    // Shared with the teacher view so both sides read the same shape — and so
    // `status`, `grade` and `feedback` do not get silently dropped here.
    homeworks.value = res.data.map(mapHomework)
  } catch (err) {
    toast.error('Failed to load homework', apiError(err, 'Please try again.'))
  } finally {
    isLoading.value = false
  }
})

const pendingHomework = computed(() => homeworks.value.filter((h) => !h.isCompleted))
const completedHomework = computed(() => homeworks.value.filter((h) => h.isCompleted))

const formatDate = (value?: string | null) =>
  value
    ? new Date(value).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
    : null

const dueLabel = (hw: Homework) => {
  if (!hw.dueDate) return null
  return hw.status === 'overdue' ? `Overdue — was due ${formatDate(hw.dueDate)}` : `Due ${formatDate(hw.dueDate)}`
}

async function handleFileUpload(event: Event, homeworkId: number) {
  const target = event.target as HTMLInputElement
  if (!target.files?.length) return

  const file = target.files[0]
  // Clear the input so picking the same file again after a failure still fires
  // a change event.
  target.value = ''

  const problem = validateImageUpload(file)
  if (problem) {
    toast.error('Upload failed', problem)
    return
  }

  const formData = new FormData()
  formData.append('file', file)

  isUploading.value = homeworkId
  try {
    // No Content-Type header: the browser must set it so the multipart
    // boundary is included.
    const res = await axios.post(`${API_URL}/homework/${homeworkId}/upload`, formData, {
      headers: { Authorization: `Bearer ${authStore.token}` },
    })
    const index = homeworks.value.findIndex((h) => h.id === homeworkId)
    if (index !== -1) homeworks.value[index] = mapHomework(res.data)
    toast.success('Upload Successful', 'Your homework has been submitted for review.')
  } catch (err) {
    toast.error('Upload Failed', apiError(err, 'Please try again later.'))
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
        <div
          class="size-10 rounded-2xl bg-tertiary/10 border border-tertiary/20 flex items-center justify-center"
        >
          <span class="material-symbols-outlined text-tertiary text-2xl">menu_book</span>
        </div>
        <p class="text-xs font-semibold text-tertiary uppercase">Self Study</p>
      </div>
      <h1 class="text-5xl font-semibold tracking-tight text-on-surface mb-2">
        Homework & Assignments
      </h1>
      <p class="text-on-surface-variant font-medium text-lg">
        Review your practice goals and upload completion proofs.
      </p>
    </header>

    <div class="space-y-12">
      <!-- Pending Section -->
      <section class="space-y-6">
        <div class="flex items-center gap-4">
          <h2 class="text-xl font-semibold text-on-surface uppercase">Active Tasks</h2>
          <div class="h-px flex-1 bg-outline-variant/20"></div>
          <span
            class="text-xs font-semibold px-3 py-1 rounded-full bg-warning/10 text-warning border border-warning/20"
          >
            {{ pendingHomework.length }} Pending
          </span>
        </div>

        <div
          v-if="pendingHomework.length === 0"
          class="glass-medium rounded-[3rem] p-16 text-center border-dashed border-2 border-outline-variant/30"
        >
          <p class="text-on-surface-variant font-bold">All caught up! No pending assignments.</p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div
            v-for="hw in pendingHomework"
            :key="hw.id"
            class="glass-heavy rounded-3xl p-8 border border-outline-variant/30 hover:shadow-2xl hover:shadow-tertiary/10 transition-all group overflow-hidden relative"
          >
            <div class="absolute -right-8 -top-8 size-32 bg-tertiary/5 blur-3xl rounded-full" />

            <div class="relative z-10 flex flex-col h-full">
              <div class="flex justify-between items-start mb-4">
                <span class="text-xs font-semibold text-tertiary uppercase"
                  >Session #{{ hw.sessionId }}</span
                >
                <span
                  class="text-xs font-bold"
                  :class="hw.status === 'overdue' ? 'text-error' : 'text-on-surface-variant'"
                >
                  {{ dueLabel(hw) || new Date(hw.createdAt).toLocaleDateString() }}
                </span>
              </div>

              <h3
                class="text-xl font-semibold text-on-surface mb-4 leading-tight group-hover:text-tertiary transition-colors"
              >
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
                    :accept="IMAGE_ACCEPT_ATTR"
                  />
                  <div
                    class="w-full py-4 bg-tertiary text-on-tertiary rounded-2xl text-xs font-semibold uppercase flex items-center justify-center gap-2 shadow-lg shadow-tertiary/20 hover:scale-[1.02] active:scale-95 transition-all"
                  >
                    <span class="material-symbols-outlined text-sm">{{
                      isUploading === hw.id ? 'progress_activity' : 'cloud_upload'
                    }}</span>
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
          <h2 class="text-xl font-semibold text-on-surface uppercase text-on-surface-variant">
            Archive
          </h2>
          <div class="h-px flex-1 bg-outline-variant/10"></div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="hw in completedHomework"
            :key="hw.id"
            class="glass-medium rounded-3xl p-6 border border-outline-variant/20 space-y-3 group"
          >
            <div class="flex items-center justify-between gap-4">
              <div class="min-w-0 flex-1">
                <p
                  class="text-xs font-semibold uppercase mb-1 flex items-center gap-1"
                  :class="hw.status === 'reviewed' ? 'text-secondary' : 'text-success'"
                >
                  <span class="material-symbols-outlined text-xs">
                    {{ hw.status === 'reviewed' ? 'grading' : 'check_circle' }}
                  </span>
                  {{ hw.status === 'reviewed' ? 'Reviewed' : 'Awaiting review' }}
                </p>
                <h4 class="font-bold text-on-surface truncate text-sm">{{ hw.description }}</h4>
              </div>

              <a
                v-if="hw.fileUrl"
                :href="hw.fileUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="ml-4 size-10 shrink-0 rounded-xl bg-surface-container-highest flex items-center justify-center text-on-surface-variant hover:text-primary transition-colors"
              >
                <span class="material-symbols-outlined">visibility</span>
              </a>
            </div>

            <!-- The teacher's response. Without this the whole review workflow
                 is invisible to the person it is for. -->
            <div
              v-if="hw.grade || hw.feedback"
              class="rounded-2xl bg-secondary/5 border border-secondary/15 px-4 py-3 space-y-1"
            >
              <p v-if="hw.grade" class="text-sm font-semibold text-on-surface">
                Grade: {{ hw.grade }}
              </p>
              <p v-if="hw.feedback" class="text-sm text-on-surface/70 whitespace-pre-line">
                {{ hw.feedback }}
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.glass-heavy {
  @apply bg-on-surface/80 dark:bg-surface-container-lowest/80 shadow-xl;
}
.glass-medium {
  @apply bg-on-surface/40 dark:bg-on-surface/5;
}
</style>

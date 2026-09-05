<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useInteractionsStore } from '@/stores/interactions'
import { useToastStore } from '@/stores/toast'

interface HomeworkSession {
  id: number
  homeworkAssigned?: string | null
  homeworkCompleted?: boolean | null
  teacherName?: string | null
  startTime?: string | null
}

const props = withDefaults(
  defineProps<{
    isOpen?: boolean
    session?: HomeworkSession | null
  }>(),
  {
    isOpen: false,
    session: null,
  }
)

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submitted'): void
}>()

const interactionsStore = useInteractionsStore()
const toast = useToastStore()

const file = ref<File | null>(null)
const previewUrl = ref<string | null>(null)
const isSubmitting = ref(false)

const dueLabel = computed(() => {
  if (!props.session?.startTime) return 'Due for next session'
  return `From your session on ${new Date(props.session.startTime).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })}`
})

const reset = () => {
  if (previewUrl.value) window.URL.revokeObjectURL(previewUrl.value)
  file.value = null
  previewUrl.value = null
  isSubmitting.value = false
}

// Clear the staged file whenever the modal closes, so reopening it for a
// different homework never shows the previous one's preview.
watch(
  () => props.isOpen,
  (open) => {
    if (!open) reset()
  }
)

const selectFile = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (!input.files?.[0]) return
  if (previewUrl.value) window.URL.revokeObjectURL(previewUrl.value)
  file.value = input.files[0]
  previewUrl.value = window.URL.createObjectURL(file.value)
}

const close = () => emit('close')

const submitWithFile = async () => {
  if (!props.session || !file.value) return
  isSubmitting.value = true
  try {
    await interactionsStore.uploadHomeworkFile(props.session.id, file.value)
    toast.success('Homework submitted!', 'Your teacher can now review it.')
    emit('submitted')
    close()
  } catch {
    // The store surfaces the error toast; keep the modal open so the student
    // can retry without re-picking the file.
  } finally {
    isSubmitting.value = false
  }
}

const markDoneWithoutFile = async () => {
  if (!props.session) return
  isSubmitting.value = true
  try {
    await interactionsStore.completeHomework(props.session.id)
    toast.success('Marked as done', 'Your teacher has been notified.')
    emit('submitted')
    close()
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <transition
    enter-active-class="transition duration-150 ease-out"
    enter-from-class="opacity-0"
    leave-active-class="transition duration-150 ease-in"
    leave-to-class="opacity-0"
  >
    <div v-if="isOpen" class="fixed inset-0 z-[200] flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/40 dark:bg-black/70" @click="close" />

      <div
        class="modal-shell relative z-10 w-full max-w-lg rounded-3xl border border-outline-variant bg-surface-container shadow-2xl"
      >
        <div class="flex items-start justify-between p-6 pb-4">
          <div>
            <p class="mb-1 text-xs font-semibold uppercase text-primary">Homework</p>
            <h2 class="text-2xl font-semibold tracking-tight text-on-surface">Submit your work</h2>
          </div>
          <button
            class="icon-btn rounded-full border border-outline-variant"
            aria-label="Close"
            @click="close"
          >
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="space-y-4 px-6 pb-6">
          <div class="rounded-2xl bg-surface-container-highest/30 p-4">
            <p class="font-bold text-on-surface">{{ session?.homeworkAssigned }}</p>
            <p class="mt-1 text-xs text-on-surface-variant">{{ dueLabel }}</p>
            <p v-if="session?.teacherName" class="mt-1 text-xs text-on-surface-variant">
              Assigned by {{ session.teacherName }}
            </p>
          </div>

          <label
            class="flex min-h-[150px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed border-outline-variant p-4 text-center transition-colors hover:border-primary/50"
            :class="previewUrl ? 'border-primary/50' : ''"
          >
            <img
              v-if="previewUrl"
              :src="previewUrl"
              alt="Homework preview"
              class="max-h-40 rounded-xl object-contain"
            />
            <template v-else>
              <span class="material-symbols-outlined mb-2 text-3xl text-primary">add_a_photo</span>
              <p class="font-semibold text-on-surface">Attach a photo of your work</p>
              <p class="mt-1 text-xs text-on-surface-variant">
                Optional — you can also just mark it done
              </p>
            </template>
            <input type="file" accept="image/*" class="hidden" @change="selectFile" />
          </label>

          <div class="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button class="btn-ghost" :disabled="isSubmitting" @click="close">Cancel</button>
            <button
              class="btn-subtle"
              :disabled="isSubmitting || !!file"
              @click="markDoneWithoutFile"
            >
              Mark as done
            </button>
            <button class="btn-primary" :disabled="isSubmitting || !file" @click="submitWithFile">
              {{ isSubmitting ? 'Submitting…' : 'Upload & submit' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

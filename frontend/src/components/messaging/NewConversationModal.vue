<script setup lang="ts">
import { ref, computed } from 'vue'
import { useUsersStore } from '@stores/users'
import { useAuthStore } from '@stores/auth'
import { useMessagingStore } from '@stores/messaging'

const emit = defineEmits<{ close: []; created: [id: number] }>()

const usersStore = useUsersStore()
const authStore  = useAuthStore()
const store      = useMessagingStore()

const tab       = ref<'dm' | 'group'>('dm')
const search    = ref('')
const groupName = ref('')
const selectedDM  = ref<number | null>(null)
const selectedGroup = ref<number[]>([])
const isSubmitting = ref(false)

// Exclude self from list
const allUsers = computed(() =>
  usersStore.users.filter(u => u.id !== authStore.currentUser?.id)
)

const filtered = computed(() =>
  allUsers.value.filter(u =>
    u.name.toLowerCase().includes(search.value.toLowerCase()) ||
    u.email.toLowerCase().includes(search.value.toLowerCase())
  )
)

const toggleGroup = function(id: number) {
  const idx = selectedGroup.value.indexOf(id)
  if (idx >= 0) selectedGroup.value.splice(idx, 1)
  else selectedGroup.value.push(id)
}

const confirm = async function() {
  if (isSubmitting.value) return
  isSubmitting.value = true
  try {
    let id: number
    if (tab.value === 'dm') {
      if (!selectedDM.value) return
      id = await store.startDM(selectedDM.value)
    } else {
      if (!groupName.value.trim() || selectedGroup.value.length === 0) return
      id = await store.createGroup(groupName.value.trim(), selectedGroup.value)
    }
    emit('created', id)
  } finally {
    isSubmitting.value = false
  }
}

const getRoleColor = function(role: string) {
  if (role === 'teacher') return 'text-primary bg-primary/10'
  if (role === 'admin')   return 'text-blue-400 bg-blue-500/10'
  return 'text-emerald-400 bg-emerald-500/10'
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-[400] flex items-center justify-center p-4"
      @click.self="emit('close')"
    >
      <div class="absolute inset-0 bg-black/40 dark:bg-black/70" @click="emit('close')" />
      <div class="modal-shell relative w-full max-w-md glass-heavy rounded-3xl p-6 shadow-2xl flex flex-col gap-4 max-h-[80vh]">
        <!-- Header -->
        <div class="flex items-center justify-between">
          <h3 class="text-xl font-semibold text-on-surface">New Conversation</h3>
          <button
            class="size-9 rounded-xl bg-on-surface/[0.04] dark:bg-on-surface/5 flex items-center justify-center text-on-surface-variant hover:text-on-surface transition-colors"
            @click="emit('close')"
          >
            <span class="material-symbols-outlined text-lg">close</span>
          </button>
        </div>

        <!-- Tabs -->
        <div class="flex gap-2 p-1 bg-on-surface/[0.04] dark:bg-on-surface/5 rounded-2xl">
          <button
            class="flex-1 py-2 rounded-xl text-xs font-semibold uppercase transition-all"
            :class="tab === 'dm' ? 'bg-primary text-on-surface shadow-lg' : 'text-on-surface-variant hover:text-on-surface'"
            @click="tab = 'dm'; search = ''"
          >Direct Message</button>
          <button
            class="flex-1 py-2 rounded-xl text-xs font-semibold uppercase transition-all"
            :class="tab === 'group' ? 'bg-primary text-on-surface shadow-lg' : 'text-on-surface-variant hover:text-on-surface'"
            @click="tab = 'group'; search = ''"
          >Group Chat</button>
        </div>

        <!-- Group name input -->
        <input
          v-if="tab === 'group'"
          v-model="groupName"
          class="input"
          placeholder="Group name…"
        />

        <!-- Search -->
        <input
          v-model="search"
          class="input"
          placeholder="Search people…"
        />

        <!-- User list -->
        <div class="flex-1 overflow-y-auto space-y-1 max-h-48">
          <button
            v-for="user in filtered"
            :key="user.id"
            class="w-full flex items-center gap-3 px-3 py-2 rounded-2xl transition-colors text-left"
            :class="tab === 'dm' ? selectedDM === user.id ? 'bg-primary/10 border border-primary/30' : 'hover:bg-on-surface/[0.04] dark:hover:bg-on-surface/5' : selectedGroup.includes(user.id) ? 'bg-primary/10 border border-primary/30' : 'hover:bg-on-surface/[0.04] dark:hover:bg-on-surface/5'"
            @click="tab === 'dm' ? (selectedDM = user.id) : toggleGroup(user.id)"
          >
            <div class="size-9 rounded-xl bg-primary/10 flex items-center justify-center text-primary font-semibold text-sm shrink-0">
              {{ user.name.charAt(0).toUpperCase() }}
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-bold text-on-surface truncate">{{ user.name }}</p>
              <p class="text-xs text-on-surface-variant truncate">{{ user.email }}</p>
            </div>
            <span
              class="text-xs font-semibold uppercase px-2 py-0.5 rounded-full"
              :class="getRoleColor(user.role)"
            >{{ user.role }}</span>
            <span
              v-if="(tab === 'dm' && selectedDM === user.id) || (tab === 'group' && selectedGroup.includes(user.id))"
              class="material-symbols-outlined text-primary text-lg shrink-0"
              style="font-variation-settings: 'FILL' 1"
            >check_circle</span>
          </button>

          <p v-if="filtered.length === 0" class="text-center text-xs text-on-surface-variant py-4">No users found</p>
        </div>

        <!-- Confirm -->
        <button
          class="w-full py-3 rounded-2xl bg-primary text-on-primary font-semibold text-sm uppercase disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 transition-opacity active:scale-[0.98]"
          :disabled="isSubmitting || (tab === 'dm' ? !selectedDM : (!groupName.trim() || selectedGroup.length === 0))"
          @click="confirm"
        >
          {{ isSubmitting ? 'Creating…' : (tab === 'dm' ? 'Open Chat' : 'Create Group') }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

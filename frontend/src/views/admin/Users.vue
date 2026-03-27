<script setup lang="ts">
import { onMounted, computed, ref, reactive } from 'vue'
import { useUsersStore } from '../../stores/users'
import { useToastStore } from '../../stores/toast'
import type { User, Role } from '../../types'

const usersStore = useUsersStore()
const toast = useToastStore()

const showAddModal = ref(false)
const isSubmitting = ref(false)
const selectedUser = ref<User | null>(null)
const showEditModal = ref(false)

const form = reactive({
  name: '',
  email: '',
  role: 'student' as Role,
  sessionsLeft: 0,
})

const editForm = reactive({
  name: '',
  email: '',
  role: 'student' as Role,
  sessionsLeft: 0,
})

onMounted(async () => {
  await usersStore.fetchUsers()
})

const users = computed(() => usersStore.users)

const openAddModal = () => {
  Object.assign(form, {
    name: '',
    email: '',
    role: 'student',
    sessionsLeft: 0,
  })
  showAddModal.value = true
}

const openEditModal = (user: User) => {
  selectedUser.value = user
  Object.assign(editForm, {
    name: user.name,
    email: user.email,
    role: user.role,
    sessionsLeft: user.sessionsLeft || 0,
  })
  showEditModal.value = true
}

const handleCreateUser = async () => {
  isSubmitting.value = true
  try {
    await usersStore.createUser({
      name: form.name,
      email: form.email,
      role: form.role,
      sessionsLeft: form.sessionsLeft,
    })
    toast.success('User created', `${form.name} was successfully created.`)
    showAddModal.value = false
  } catch (err: any) {
    toast.error('Failed to create user', err.message || 'Something went wrong.')
  } finally {
    isSubmitting.value = false
  }
}

const handleUpdateUser = async () => {
  if (!selectedUser.value) return
  isSubmitting.value = true
  try {
    await usersStore.updateUser(selectedUser.value.id, {
      name: editForm.name,
      email: editForm.email,
      role: editForm.role,
      sessionsLeft: editForm.sessionsLeft,
    })
    toast.success('User updated', `${editForm.name} was successfully updated.`)
    showEditModal.value = false
    selectedUser.value = null
  } catch (err: any) {
    toast.error('Failed to update user', err.message || 'Something went wrong.')
  } finally {
    isSubmitting.value = false
  }
}

const handleDeleteUser = async (user: User) => {
  if (!window.confirm(`Are you sure you want to deactivate ${user.name}?`)) return
  try {
    await usersStore.deleteUser(user.id)
    toast.success('User deactivated', `${user.name} was removed.`)
  } catch (err: any) {
    toast.error('Failed to deactivate user', err.message || 'Something went wrong.')
  }
}
</script>

<template>
  <div class="max-w-[80vw] mx-auto pb-28 space-y-4">
    <!-- Header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-5xl font-black tracking-tight text-white mb-2">Users Management</h1>
        <p class="text-zinc-500 font-medium">Manage students, teachers, and their enrollments</p>
      </div>
      <button
        class="px-5 py-2.5 bg-gradient-to-br from-orange-500 to-orange-700 text-white text-[10px] font-black uppercase tracking-widest rounded-2xl hover:opacity-90 transition-opacity flex items-center gap-2 shadow-lg shadow-orange-900/30"
        @click="openAddModal"
      >
        <span class="material-symbols-outlined text-sm">person_add</span>
        Add User
      </button>
    </div>

    <!-- Users List -->
    <section class="liquid-glass rounded-3xl p-4 border border-white/5 overflow-hidden mt-8">
      <div v-if="usersStore.isLoading && users.length === 0" class="space-y-4">
        <div v-for="i in 5" :key="i" class="h-16 rounded-2xl bg-white/5 animate-pulse" />
      </div>

      <div v-else-if="users.length === 0" class="py-10 text-center">
        <span class="material-symbols-outlined text-4xl text-zinc-700 mb-2 block">group_off</span>
        <p class="text-sm font-bold text-white mb-1">No users found</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-left">
          <thead>
            <tr class="text-[10px] font-black text-zinc-500 uppercase tracking-[0.2em]">
              <th class="pb-6 px-4">User</th>
              <th class="pb-6 px-4">Role</th>
              <th class="pb-6 px-4">Sessions Left</th>
              <th class="pb-6 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/5">
            <tr
              v-for="user in users"
              :key="user.id"
              class="group hover:bg-white/[0.02] transition-colors"
            >
              <td class="py-4 px-4">
                <div class="flex items-center gap-4">
                  <div
                    class="w-10 h-10 rounded-2xl bg-surface-container-highest border border-white/10 flex items-center justify-center text-white font-black text-sm"
                  >
                    {{ user.avatarUrl ? '' : user.name.charAt(0) }}
                    <img v-if="user.avatarUrl" :src="user.avatarUrl" class="w-full h-full object-cover rounded-2xl" />
                  </div>
                  <div>
                    <p class="text-sm font-black text-white">{{ user.name }}</p>
                    <p class="text-xs text-zinc-500">{{ user.email }}</p>
                  </div>
                </div>
              </td>
              <td class="py-4 px-4">
                <span
                  class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider border"
                  :class="{
                    'bg-orange-500/10 text-orange-400 border-orange-500/20': user.role === 'admin',
                    'bg-blue-500/10 text-blue-400 border-blue-500/20': user.role === 'teacher',
                    'bg-emerald-500/10 text-emerald-400 border-emerald-500/20': user.role === 'student'
                  }"
                >
                  {{ user.role }}
                </span>
              </td>
              <td class="py-4 px-4">
                <span v-if="user.role === 'student'" class="text-sm font-black text-white">
                  {{ user.sessionsLeft !== undefined ? user.sessionsLeft : 'N/A' }}
                </span>
                <span v-else class="text-xs text-zinc-500">—</span>
              </td>
              <td class="py-4 px-4 text-right">
                <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button class="p-2 text-zinc-500 hover:text-white transition-colors" @click="openEditModal(user)">
                    <span class="material-symbols-outlined text-lg">edit</span>
                  </button>
                  <button class="p-2 text-zinc-500 hover:text-red-400 transition-colors" @click="handleDeleteUser(user)">
                    <span class="material-symbols-outlined text-lg">delete</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Add User Modal -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition opacity-200 ease-out duration-200"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition opacity-200 ease-in duration-200"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="showAddModal"
          class="fixed inset-0 z-[200] flex items-center justify-center p-4"
          @click.self="showAddModal = false"
        >
          <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="showAddModal = false" />
          <div class="relative w-full max-w-md bg-zinc-900 border border-white/10 rounded-3xl p-6 shadow-2xl">
            <h3 class="text-xl font-black text-white mb-6">Add New User</h3>
            <form class="space-y-4" @submit.prevent="handleCreateUser">
              <div>
                <label class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60 block mb-2">Name</label>
                <input v-model="form.name" type="text" required class="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50" />
              </div>
              <div>
                <label class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60 block mb-2">Email</label>
                <input v-model="form.email" type="email" required class="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50" />
              </div>
              <div>
                <label class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60 block mb-2">Role</label>
                <select v-model="form.role" class="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 appearance-none">
                  <option value="student" class="text-zinc-900">Student</option>
                  <option value="teacher" class="text-zinc-900">Teacher</option>
                  <option value="admin" class="text-zinc-900">Admin</option>
                </select>
              </div>
              <div v-if="form.role === 'student'">
                <label class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60 block mb-2">Sessions Left</label>
                <input v-model.number="form.sessionsLeft" type="number" min="0" class="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50" />
              </div>
              <div class="flex gap-3 pt-4">
                <button type="button" class="flex-1 py-3 rounded-xl border border-white/10 text-zinc-400 hover:text-white text-sm font-semibold transition-all" @click="showAddModal = false">Cancel</button>
                <button type="submit" :disabled="isSubmitting" class="flex-1 py-3 rounded-xl bg-gradient-to-br from-orange-500 to-orange-700 hover:scale-[1.02] text-white text-sm font-black transition-all active:scale-95 disabled:opacity-50">
                  {{ isSubmitting ? 'Saving...' : 'Create' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Edit User Modal -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition opacity-200 ease-out duration-200"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition opacity-200 ease-in duration-200"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="showEditModal"
          class="fixed inset-0 z-[200] flex items-center justify-center p-4"
          @click.self="showEditModal = false"
        >
          <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="showEditModal = false" />
          <div class="relative w-full max-w-md bg-zinc-900 border border-white/10 rounded-3xl p-6 shadow-2xl">
            <h3 class="text-xl font-black text-white mb-6">Edit User</h3>
            <form class="space-y-4" @submit.prevent="handleUpdateUser">
              <div>
                <label class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60 block mb-2">Name</label>
                <input v-model="editForm.name" type="text" required class="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50" />
              </div>
              <div>
                <label class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60 block mb-2">Email</label>
                <input v-model="editForm.email" type="email" required class="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50" />
              </div>
              <div>
                <label class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60 block mb-2">Role</label>
                <select v-model="editForm.role" class="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 appearance-none">
                  <option value="student" class="text-zinc-900">Student</option>
                  <option value="teacher" class="text-zinc-900">Teacher</option>
                  <option value="admin" class="text-zinc-900">Admin</option>
                </select>
              </div>
              <div v-if="editForm.role === 'student'">
                <label class="text-[10px] font-black uppercase tracking-[0.2em] text-white/60 block mb-2">Sessions Left</label>
                <input v-model.number="editForm.sessionsLeft" type="number" min="0" class="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50" />
              </div>
              <div class="flex gap-3 pt-4">
                <button type="button" class="flex-1 py-3 rounded-xl border border-white/10 text-zinc-400 hover:text-white text-sm font-semibold transition-all" @click="showEditModal = false">Cancel</button>
                <button type="submit" :disabled="isSubmitting" class="flex-1 py-3 rounded-xl bg-gradient-to-br from-orange-500 to-orange-700 hover:scale-[1.02] text-white text-sm font-black transition-all active:scale-95 disabled:opacity-50">
                  {{ isSubmitting ? 'Saving...' : 'Update' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

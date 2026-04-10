<script setup lang="ts">
import { onMounted, computed, ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUsersStore } from '../../stores/users'
import { useToastStore } from '../../stores/toast'
import type { User, Role } from '../../types'
import CreateUserModal from '../../components/CreateUserModal.vue'

const router = useRouter()
const route = useRoute()
const usersStore = useUsersStore()
const toast = useToastStore()

const showAddModal = ref(false)
const isSubmitting = ref(false)
const selectedUser = ref<User | null>(null)
const showEditModal = ref(false)

const editForm = reactive({
  name: '',
  email: '',
  role: 'student' as Role,
  sessionsLeft: 0,
})

onMounted(async () => {
  await usersStore.fetchUsers()
  
  // Handle query parameters
  if (route.query.action === 'create') {
    showAddModal.value = true
  }
  
  if (route.query.edit) {
    const userId = String(route.query.edit)
    const user = usersStore.users.find(u => String(u.id) === userId)
    if (user) {
      openEditModal(user)
    }
  }
})

const users = computed(() => usersStore.users)

const openAddModal = () => {
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

const handleUserCreated = (user: User) => {
  toast.success('User created', `${user.name} was successfully created.`)
}

const navigateToRecords = (userId: string) => {
  router.push(`/admin/students/${userId}/records`)
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
  <div class="max-w-[1600px] mx-auto pb-28 space-y-6 px-4 sm:px-6">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-6">
      <div class="space-y-1">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-10 h-10 rounded-2xl bg-primary/10 flex items-center justify-center border border-primary/20">
            <span class="material-symbols-outlined text-primary text-2xl">group</span>
          </div>
          <p class="text-[10px] font-black text-primary uppercase tracking-[0.2em]">Administration</p>
        </div>
        <h1 class="text-4xl font-black tracking-tight text-on-surface">Users Management</h1>
        <p class="text-on-surface-variant font-medium max-w-lg">
          Onboard new participants, manage permissions, and update student enrollment status.
        </p>
      </div>
      <button
        class="group px-6 py-3.5 bg-primary text-white text-[11px] font-black uppercase tracking-[0.15em] rounded-2xl hover:bg-primary/90 transition-all flex items-center gap-3 shadow-lg shadow-primary/20 active:scale-95 whitespace-nowrap"
        @click="openAddModal"
      >
        <span class="material-symbols-outlined text-lg group-hover:rotate-90 transition-transform">add</span>
        Create New User
      </button>
    </div>

    <!-- Users List Section -->
    <section class="glass-medium rounded-[2.5rem] border border-outline-variant/30 overflow-hidden mt-4 shadow-xl">
      <div v-if="usersStore.isLoading && users.length === 0" class="p-6 space-y-4">
        <div v-for="i in 5" :key="i" class="h-20 rounded-2xl bg-surface-container-highest/20 animate-pulse" />
      </div>

      <div v-else-if="users.length === 0" class="py-24 text-center">
        <div class="w-16 h-16 rounded-full bg-surface-container-highest/30 flex items-center justify-center mx-auto mb-4">
          <span class="material-symbols-outlined text-4xl text-on-surface-variant">group_off</span>
        </div>
        <p class="text-lg font-black text-on-surface mb-1">No users found</p>
        <p class="text-sm text-on-surface-variant mb-6">Start by creating your first student or teacher.</p>
        <button class="text-primary text-xs font-black uppercase tracking-widest border-b-2 border-primary/20 pb-0.5 hover:border-primary transition-all" @click="openAddModal">Add User</button>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="text-[10px] font-black text-on-surface-variant uppercase tracking-[0.25em] bg-surface-container-highest/20">
              <th class="py-6 px-8">Member Identity</th>
              <th class="py-6 px-4">Access Level</th>
              <th class="py-6 px-4">Quota / Status</th>
              <th class="py-6 px-8 text-right">Operations</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/10">
            <tr
              v-for="user in users"
              :key="user.id"
              class="group hover:bg-primary/[0.03] dark:hover:bg-primary/[0.05] transition-all"
            >
              <td class="py-5 px-8">
                <div class="flex items-center gap-4">
                  <div
                    class="w-12 h-12 rounded-2xl bg-surface-container-highest border border-outline-variant/30 flex items-center justify-center text-on-surface font-black text-lg shadow-sm overflow-hidden"
                  >
                    <img v-if="user.avatarUrl" :src="user.avatarUrl" class="w-full h-full object-cover" />
                    <span v-else>{{ user.name.charAt(0) }}</span>
                  </div>
                  <div class="min-w-0">
                    <p class="text-sm font-black text-on-surface truncate">{{ user.name }}</p>
                    <p class="text-xs text-on-surface-variant truncate">{{ user.email }}</p>
                  </div>
                </div>
              </td>
              <td class="py-5 px-4 whitespace-nowrap">
                <span
                  class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-wider border transition-colors shadow-sm"
                  :class="{
                    'bg-primary/10 text-primary border-primary/20': user.role === 'admin',
                    'bg-blue-500/10 text-blue-500 border-blue-500/20': user.role === 'teacher',
                    'bg-emerald-500/10 text-emerald-500 border-emerald-500/20': user.role === 'student'
                  }"
                >
                  <span class="w-1 h-1 rounded-full bg-current"></span>
                  {{ user.role }}
                </span>
              </td>
              <td class="py-5 px-4">
                <div v-if="user.role === 'student'" class="flex items-center gap-2">
                  <span class="text-sm font-black text-on-surface">
                    {{ user.sessionsLeft !== undefined ? user.sessionsLeft : '0' }}
                  </span>
                  <span class="text-[10px] font-bold text-on-surface-variant uppercase tracking-tight">Credits</span>
                </div>
                <span v-else class="text-xs text-on-surface-variant italic opacity-50">Authorized Access</span>
              </td>
              <td class="py-5 px-8 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button
                    v-if="user.role === 'student'"
                    class="w-10 h-10 rounded-xl bg-surface-container-highest/20 text-on-surface-variant hover:text-secondary hover:bg-secondary/10 border border-transparent hover:border-secondary/20 transition-all active:scale-90"
                    title="View Records"
                    @click="navigateToRecords(user.id)"
                  >
                    <span class="material-symbols-outlined text-lg">folder_open</span>
                  </button>
                  <button
                    class="w-10 h-10 rounded-xl bg-surface-container-highest/20 text-on-surface-variant hover:text-primary hover:bg-primary/10 border border-transparent hover:border-primary/20 transition-all active:scale-90"
                    title="Edit Profile"
                    @click="openEditModal(user)"
                  >
                    <span class="material-symbols-outlined text-lg">edit_note</span>
                  </button>
                  <button
                    class="w-10 h-10 rounded-xl bg-surface-container-highest/20 text-on-surface-variant hover:text-red-500 hover:bg-red-500/10 border border-transparent hover:border-red-500/20 transition-all active:scale-90"
                    title="Deactivate Account"
                    @click="handleDeleteUser(user)"
                  >
                    <span class="material-symbols-outlined text-lg">no_accounts</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Add User Modal -->
    <CreateUserModal
      :is-open="showAddModal"
      @close="showAddModal = false"
      @created="handleUserCreated"
    />

    <!-- Edit User Modal -->
    <Teleport to="body">
      <Transition
        enter-active-class="transition-all  ease-out"
        enter-from-class="opacity-0 scale-95 blur-[8px]"
        enter-to-class="opacity-100 scale-100 blur-0"
        leave-active-class="transition-all  ease-in"
        leave-from-class="opacity-100 scale-100 blur-0"
        leave-to-class="opacity-0 scale-95 blur-[8px]"
      >
        <div
          v-if="showEditModal"
          class="fixed inset-0 z-[200] flex items-center justify-center p-4"
          @click.self="showEditModal = false"
        >
          <div class="absolute inset-0 bg-black/40 dark:bg-black/80 backdrop-blur-sm" @click="showEditModal = false" />
          <div class="relative w-full max-w-md glass-heavy border border-outline-variant/30 rounded-[2.5rem] p-8 shadow-2xl overflow-hidden">
            <div class="absolute top-0 right-0 w-32 h-32 bg-primary/10 blur-[64px] rounded-full -z-10" />

            <div class="flex items-center justify-between mb-8">
              <div>
                <p class="text-[10px] font-black text-primary uppercase tracking-[0.2em] mb-1">Update Member</p>
                <h3 class="text-2xl font-black text-on-surface">Edit User</h3>
              </div>
              <button class="w-10 h-10 rounded-full hover:bg-on-surface/5 flex items-center justify-center transition-colors" @click="showEditModal = false">
                <span class="material-symbols-outlined text-on-surface-variant">close</span>
              </button>
            </div>

            <form class="space-y-5" @submit.prevent="handleUpdateUser">
              <div class="space-y-4">
                <div class="space-y-1.5">
                  <label class="text-[10px] font-black uppercase tracking-[0.2em] text-on-surface-variant ml-1">Full Name</label>
                  <input v-model="editForm.name" type="text" required class="w-full bg-surface-container-highest/20 border border-outline-variant/30 text-on-surface rounded-2xl px-5 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all" />
                </div>
                <div class="space-y-1.5">
                  <label class="text-[10px] font-black uppercase tracking-[0.2em] text-on-surface-variant ml-1">Email Address</label>
                  <input v-model="editForm.email" type="email" required class="w-full bg-surface-container-highest/20 border border-outline-variant/30 text-on-surface rounded-2xl px-5 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all opacity-70" readonly />
                </div>
                <div class="grid grid-cols-2 gap-4">
                  <div class="space-y-1.5">
                    <label class="text-[10px] font-black uppercase tracking-[0.2em] text-on-surface-variant ml-1">System Role</label>
                    <div class="relative">
                      <select v-model="editForm.role" class="w-full bg-surface-container-highest/20 border border-outline-variant/30 text-on-surface rounded-2xl px-5 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all appearance-none cursor-pointer">
                        <option value="student" class="bg-surface-container">Student</option>
                        <option value="teacher" class="bg-surface-container">Teacher</option>
                        <option value="admin" class="bg-surface-container">Admin</option>
                      </select>
                      <span class="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none text-lg">expand_more</span>
                    </div>
                  </div>
                  <div v-if="editForm.role === 'student'" class="space-y-1.5">
                    <label class="text-[10px] font-black uppercase tracking-[0.2em] text-on-surface-variant ml-1">Remaining Credits</label>
                    <input v-model.number="editForm.sessionsLeft" type="number" min="0" class="w-full bg-surface-container-highest/20 border border-outline-variant/30 text-on-surface rounded-2xl px-5 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all" />
                  </div>
                </div>
              </div>

              <div class="flex gap-3 pt-6">
                <button type="submit" :disabled="isSubmitting" class="flex-1 py-4 rounded-2xl bg-primary text-white text-sm font-black uppercase tracking-widest transition-all hover:opacity-90 active:scale-95 disabled:opacity-50 shadow-lg shadow-primary/20">
                  {{ isSubmitting ? 'Updating...' : 'Save Changes' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

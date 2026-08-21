<script setup lang="ts">
import { onMounted, computed, ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUsersStore } from '@stores/users'
import { useToastStore } from '@stores/toast'
import type { User, Role } from '@types'
import CreateUserModal from '@components/CreateUserModal.vue'
import { useDialog } from '@composables/useDialog'

const router = useRouter()
const route = useRoute()
const usersStore = useUsersStore()
const toast = useToastStore()
const dialog = useDialog()

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
    const userId = Number(route.query.edit)
    const user = usersStore.users.find(u => u.id === userId)
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

const navigateToRecords = (userId: number) => {
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
  const entered = await dialog.prompt(`Type "${user.name}" to confirm deactivating this account:`, {
    title: 'Deactivate User',
    placeholder: user.name
  })
  if (entered !== user.name) {
    if (entered !== null) {
      toast.error('Confirmation failed', 'The typed name did not match.')
    }
    return
  }
  try {
    await usersStore.deleteUser(user.id)
    toast.success('User deactivated', `${user.name} was removed.`)
  } catch (err: any) {
    toast.error('Failed to deactivate user', err.message || 'Something went wrong.')
  }
}
</script>

<template>
  <div class="page">
    <!-- Header -->
    <header class="page-header">
      <div class="space-y-2">
        <p class="page-eyebrow">Administration</p>
        <h1 class="page-title">Users</h1>
        <p class="page-subtitle">
          Onboard participants, manage permissions, and update student credit balances.
        </p>
      </div>
      <button class="btn-primary" @click="openAddModal">
        <span class="material-symbols-outlined text-lg" aria-hidden="true">add</span>
        Create user
      </button>
    </header>

    <!-- Users List Section -->
    <section class="card overflow-hidden">
      <div v-if="usersStore.isLoading && users.length === 0" class="space-y-3 p-6">
        <div v-for="i in 5" :key="i" class="skeleton-row" />
      </div>

      <div v-else-if="users.length === 0" class="empty-state">
        <span class="material-symbols-outlined text-4xl text-on-surface-variant" aria-hidden="true">group_off</span>
        <p class="section-title">No users yet</p>
        <p class="section-caption">Start by creating your first student or teacher.</p>
        <button class="btn-primary btn-sm" @click="openAddModal">Create user</button>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr class="text-xs font-semibold text-on-surface-variant uppercase bg-surface-container-highest/20">
              <th>Member Identity</th>
              <th>Access Level</th>
              <th>Quota / Status</th>
              <th class="text-right">Operations</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-variant/10">
            <tr
              v-for="user in users"
              :key="user.id"
              class="group hover:bg-primary/[0.03] dark:hover:bg-primary/[0.05] transition-all"
            >
              <td>
                <div class="flex items-center gap-4">
                  <div
                    class="size-12 rounded-2xl bg-surface-container-highest border border-outline-variant/30 flex items-center justify-center text-on-surface font-semibold text-lg shadow-sm overflow-hidden"
                  >
                    <img v-if="user.avatarUrl" :src="user.avatarUrl" class="w-full h-full object-cover" />
                    <span v-else>{{ user.name.charAt(0) }}</span>
                  </div>
                  <div class="min-w-0">
                    <p class="text-sm font-semibold text-on-surface truncate">{{ user.name }}</p>
                    <p class="text-xs text-on-surface-variant truncate">{{ user.email }}</p>
                  </div>
                </div>
              </td>
              <td class="whitespace-nowrap">
                <span
                  class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold uppercase border transition-colors shadow-sm"
                  :class="{ 'bg-primary/10 text-primary border-primary/20': user.role === 'admin', 'bg-blue-500/10 text-blue-500 border-blue-500/20': user.role === 'teacher', 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20': user.role === 'student' }"
                >
                  <span class="size-1 rounded-full bg-current"></span>
                  {{ user.role }}
                </span>
              </td>
              <td>
                <div v-if="user.role === 'student'" class="flex items-center gap-2">
                  <span class="text-sm font-semibold text-on-surface">
                    {{ user.sessionsLeft !== undefined ? user.sessionsLeft : '0' }}
                  </span>
                  <span class="text-xs font-bold text-on-surface-variant uppercase tracking-tight">Credits</span>
                </div>
                <span v-else class="text-xs text-on-surface-variant italic opacity-50">Authorized Access</span>
              </td>
              <td class="text-right">
                <div class="flex items-center justify-end gap-2">
                  <button
                    v-if="user.role === 'student'"
                    class="icon-btn"
                    title="View Records"
                    @click="navigateToRecords(user.id)"
                  >
                    <span class="material-symbols-outlined text-lg">folder_open</span>
                  </button>
                  <button
                    class="icon-btn"
                    title="Edit Profile"
                    @click="openEditModal(user)"
                  >
                    <span class="material-symbols-outlined text-lg">edit_note</span>
                  </button>
                  <button
                    class="icon-btn-danger"
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
        enter-active-class="transition-all ease-out"
        enter-from-class="opacity-0 scale-95 blur-[8px]"
        enter-to-class="opacity-100 scale-100 blur-0"
        leave-active-class="transition-all ease-in"
        leave-from-class="opacity-100 scale-100 blur-0"
        leave-to-class="opacity-0 scale-95 blur-[8px]"
      >
        <div
          v-if="showEditModal"
          class="fixed inset-0 z-[200] flex items-center justify-center p-4"
          @click.self="showEditModal = false"
        >
          <div class="absolute inset-0 bg-on-surface/40 dark:bg-on-surface/80" @click="showEditModal = false" />
          <div class="relative w-full max-w-md glass-heavy border border-outline-variant/30 rounded-3xl p-8 shadow-2xl overflow-hidden">
            <div class="absolute top-0 right-0 size-32 bg-primary/10 blur-[64px] rounded-full -z-10" />

            <div class="flex items-center justify-between mb-8">
              <div>
                <p class="text-xs font-semibold text-primary uppercase mb-1">Update Member</p>
                <h3 class="text-2xl font-semibold text-on-surface">Edit User</h3>
              </div>
              <button class="icon-btn" @click="showEditModal = false">
                <span class="material-symbols-outlined text-on-surface-variant">close</span>
              </button>
            </div>

            <form class="space-y-4" @submit.prevent="handleUpdateUser">
              <div class="space-y-4">
                <div class="space-y-1.5">
                  <label class="field-label">Full Name</label>
                  <input v-model="editForm.name" type="text" required class="input" />
                </div>
                <div class="space-y-1.5">
                  <label class="field-label">Email Address</label>
                  <input v-model="editForm.email" type="email" required class="input" readonly />
                </div>
                <div class="grid grid-cols-2 gap-4">
                  <div class="space-y-1.5">
                    <label class="field-label">System Role</label>
                    <div class="relative">
                      <select v-model="editForm.role" class="input appearance-none">
                        <option value="student" class="bg-surface-container">Student</option>
                        <option value="teacher" class="bg-surface-container">Teacher</option>
                        <option value="admin" class="bg-surface-container">Admin</option>
                      </select>
                      <span class="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none text-lg">expand_more</span>
                    </div>
                  </div>
                  <div v-if="editForm.role === 'student'" class="space-y-1.5">
                    <label class="field-label">Remaining Credits</label>
                    <input v-model.number="editForm.sessionsLeft" type="number" min="0" class="input" />
                  </div>
                </div>
              </div>

              <div class="flex gap-3 pt-6">
                <button type="submit" :disabled="isSubmitting" class="flex-1 py-4 rounded-2xl bg-primary text-on-primary text-sm font-semibold uppercase transition-all hover:opacity-90 active:scale-95 disabled:opacity-50 shadow-lg shadow-primary/20">
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

import { defineStore } from 'pinia';
import axios from 'axios';
import type { User, Role } from '../types';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface UsersState {
  users: User[];
  isLoading: boolean;
  error: string | null;
}

export const useUsersStore = defineStore('users', {
  state: (): UsersState => ({
    users: [],
    isLoading: false,
    error: null,
  }),
  getters: {
    getUsersByRole: (state) => (role: Role) => {
      return state.users.filter((user) => user.role === role);
    },
  },
  actions: {
    async fetchUsers() {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/users/`);
        this.users = response.data.map((user: any) => ({
          id: String(user.id),
          name: user.name,
          email: user.email,
          role: user.role?.name?.toLowerCase() as Role || 'student',
          avatarUrl: user.avatar_url,
          sessionsLeft: user.sessions_left
        }));
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch users';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async fetchUsersByRole(role: Role) {
      this.isLoading = true;
      this.error = null;
      // Backend stores roles as lowercase: 'teacher', 'student', 'admin'
      const roleName = role.toLowerCase();
      try {
        const response = await axios.get(`${API_URL}/users/role/${roleName}`);
        const newUsers = response.data.map((user: any) => ({
          id: String(user.id),
          name: user.name,
          email: user.email,
          role: user.role?.name?.toLowerCase() as Role || role,
          avatarUrl: user.avatar_url,
          sessionsLeft: user.sessions_left
        }));

        // Merge fetched users into the state
        for (const newUser of newUsers) {
          const index = this.users.findIndex(u => u.id === newUser.id);
          if (index !== -1) {
            this.users[index] = newUser;
          } else {
            this.users.push(newUser);
          }
        }
      } catch (err: any) {
        this.error = err.message || `Failed to fetch ${role}s`;
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async createUser(userData: Partial<User>, password = "password123") {
      this.isLoading = true;
      this.error = null;
      try {
        // Find role_id first. Hardcoding for mock purposes, but ideally we fetch roles first.
        // Assuming Admin=1, Teacher=2, Student=3. Wait, we should probably fetch roles if we want to be safe.
        const rolesResp = await axios.get(`${API_URL}/roles/`);
        const roles = rolesResp.data;
        const roleName = (userData.role || 'student').charAt(0).toUpperCase() + (userData.role || 'student').slice(1);
        const role = roles.find((r: any) => r.name === roleName);
        const role_id = role ? role.id : 3;

        const payload = {
          email: userData.email,
          name: userData.name,
          role_id: role_id,
          password: password,
          avatar_url: userData.avatarUrl || null,
          sessions_left: userData.sessionsLeft || 0
        };

        const response = await axios.post(`${API_URL}/users/`, payload);
        const newUser = response.data;

        const frontendUser: User = {
          id: String(newUser.id),
          name: newUser.name,
          email: newUser.email,
          role: userData.role as Role || 'student',
          avatarUrl: newUser.avatar_url,
          sessionsLeft: newUser.sessions_left
        };
        this.users.push(frontendUser);
        return frontendUser;
      } catch (err: any) {
        this.error = err.message || 'Failed to create user';
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async updateUser(userId: string, updateData: Partial<User>) {
      this.isLoading = true;
      this.error = null;
      try {
        const payload: any = {};
        if (updateData.name) payload.name = updateData.name;
        if (updateData.email) payload.email = updateData.email;
        if (updateData.avatarUrl !== undefined) payload.avatar_url = updateData.avatarUrl;
        if (updateData.sessionsLeft !== undefined) payload.sessions_left = updateData.sessionsLeft;

        // Handling role change would require fetching role_id again
        if (updateData.role) {
            const rolesResp = await axios.get(`${API_URL}/roles/`);
            const roles = rolesResp.data;
            const roleName = updateData.role.charAt(0).toUpperCase() + updateData.role.slice(1);
            const role = roles.find((r: any) => r.name === roleName);
            if (role) payload.role_id = role.id;
        }

        const response = await axios.put(`${API_URL}/users/${userId}`, payload);
        const updatedUser = response.data;

        const index = this.users.findIndex(u => u.id === userId);
        if (index !== -1) {
          this.users[index] = {
            ...this.users[index],
            name: updatedUser.name,
            email: updatedUser.email,
            avatarUrl: updatedUser.avatar_url,
            sessionsLeft: updatedUser.sessions_left,
            role: updateData.role || this.users[index].role
          };
        }
      } catch (err: any) {
        this.error = err.message || 'Failed to update user';
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async deleteUser(userId: string) {
      this.isLoading = true;
      this.error = null;
      try {
        await axios.delete(`${API_URL}/users/${userId}`);
        this.users = this.users.filter((user) => user.id !== userId);
      } catch (err: any) {
        this.error = err.message || 'Failed to delete user';
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    }
  },
});

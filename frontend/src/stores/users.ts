import { defineStore } from 'pinia';
import axios from 'axios';
import { useAuthStore } from './auth';
import type { User, Role, InstrumentRecord } from '../types';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const authHeaders = function() {
  const auth = useAuthStore();
  return auth.token ? { Authorization: `Bearer ${auth.token}` } : {};
}

interface UsersState {
  users: User[];
  instruments: InstrumentRecord[];
  isLoading: boolean;
  error: string | null;
}

export const useUsersStore = defineStore('users', {
  state: (): UsersState => ({
    users: [],
    instruments: [],
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
          sessionsLeft: user.sessions_left,
          username: user.username,
          contactNumber: user.contact_number,
          homeAddress: user.home_address,
          birthday: user.birthday,
          age: user.age,
          school: user.school,
          parentName: user.parent_name,
          parentContact: user.parent_contact,
          sessionsEnrolled: user.sessions_enrolled,
          instruments: user.instruments
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
        const response = await axios.get(`${API_URL}/users/role/${roleName}`, { headers: authHeaders() });
        const newUsers = response.data.map((user: any) => ({
          id: String(user.id),
          name: user.name,
          email: user.email,
          role: user.role?.name?.toLowerCase() as Role || role,
          avatarUrl: user.avatar_url,
          sessionsLeft: user.sessions_left,
          username: user.username,
          contactNumber: user.contact_number,
          homeAddress: user.home_address,
          birthday: user.birthday,
          age: user.age,
          school: user.school,
          parentName: user.parent_name,
          parentContact: user.parent_contact,
          sessionsEnrolled: user.sessions_enrolled,
          instruments: user.instruments
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

    async fetchInstruments() {
      try {
        const response = await axios.get(`${API_URL}/instruments/`);
        this.instruments = response.data;
      } catch (err: any) {
        console.error("Failed to fetch instruments", err);
      }
    },

    async createUser(userData: Partial<User>, password?: string) {
      this.isLoading = true;
      this.error = null;
      try {
        const rolesResp = await axios.get(`${API_URL}/roles/`);
        const roles = rolesResp.data;
        const roleName = (userData.role || 'student').toLowerCase();
        const role = roles.find((r: any) => r.name.toLowerCase() === roleName);
        const role_id = role ? role.id : 3;

        const payload: any = {
          email: userData.email,
          name: userData.name,
          role_id: role_id,
          password: password,
          avatar_url: userData.avatarUrl || null,
          sessions_left: userData.sessionsLeft || 0,
          username: userData.username || null,
          contact_number: userData.contactNumber || null,
          home_address: userData.homeAddress || null,
          birthday: userData.birthday || null,
          age: userData.age || null,
          school: userData.school || null,
          parent_name: userData.parentName || null,
          parent_contact: userData.parentContact || null,
          sessions_enrolled: userData.sessionsEnrolled || null,
          instrument_ids: userData.instruments ? userData.instruments.map(i => i.id) : []
        };

        const response = await axios.post(`${API_URL}/users/`, payload);
        const { user: newUser, access_token } = response.data;

        const frontendUser: User = {
          id: String(newUser.id),
          name: newUser.name,
          email: newUser.email,
          role: (newUser.role?.name?.toLowerCase() || roleName) as Role,
          avatarUrl: newUser.avatar_url,
          sessionsLeft: newUser.sessions_left,
          username: newUser.username,
          contactNumber: newUser.contact_number,
          homeAddress: newUser.home_address,
          birthday: newUser.birthday,
          age: newUser.age,
          school: newUser.school,
          parentName: newUser.parent_name,
          parentContact: newUser.parent_contact,
          sessionsEnrolled: newUser.sessions_enrolled,
          instruments: newUser.instruments
        };
        
        this.users.push(frontendUser);

        // If not already logged in, automatically log in as the new user
        // OR if this was a student creation from a register-like flow
        const authStore = (await import('./auth')).useAuthStore();
        if (!authStore.token) {
           authStore.setTokenAndUser(access_token, frontendUser);
        }

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
        if (updateData.username !== undefined) payload.username = updateData.username;
        if (updateData.contactNumber !== undefined) payload.contact_number = updateData.contactNumber;
        if (updateData.homeAddress !== undefined) payload.home_address = updateData.homeAddress;
        if (updateData.birthday !== undefined) payload.birthday = updateData.birthday;
        if (updateData.age !== undefined) payload.age = updateData.age;
        if (updateData.school !== undefined) payload.school = updateData.school;
        if (updateData.parentName !== undefined) payload.parent_name = updateData.parentName;
        if (updateData.parentContact !== undefined) payload.parent_contact = updateData.parentContact;
        if (updateData.sessionsEnrolled !== undefined) payload.sessions_enrolled = updateData.sessionsEnrolled;
        if (updateData.instruments !== undefined) payload.instrument_ids = updateData.instruments.map(i => i.id);


        // Handling role change would require fetching role_id again
        if (updateData.role) {
            const rolesResp = await axios.get(`${API_URL}/roles/`, { headers: authHeaders() });
            const roles = rolesResp.data;
            const roleName = updateData.role.charAt(0).toUpperCase() + updateData.role.slice(1);
            const role = roles.find((r: any) => r.name === roleName);
            if (role) payload.role_id = role.id;
        }

        const response = await axios.put(`${API_URL}/users/${userId}`, payload, { headers: authHeaders() });
        const updatedUser = response.data;

        const index = this.users.findIndex(u => u.id === userId);
        if (index !== -1) {
          this.users[index] = {
            ...this.users[index],
            name: updatedUser.name,
            email: updatedUser.email,
            avatarUrl: updatedUser.avatar_url,
            sessionsLeft: updatedUser.sessions_left,
            role: updateData.role || this.users[index].role,
            username: updatedUser.username,
            contactNumber: updatedUser.contact_number,
            homeAddress: updatedUser.home_address,
            birthday: updatedUser.birthday,
            age: updatedUser.age,
            school: updatedUser.school,
            parentName: updatedUser.parent_name,
            parentContact: updatedUser.parent_contact,
            sessionsEnrolled: updatedUser.sessions_enrolled,
            instruments: updatedUser.instruments
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
        await axios.delete(`${API_URL}/users/${userId}`, { headers: authHeaders() });
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

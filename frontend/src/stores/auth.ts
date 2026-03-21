import { defineStore } from 'pinia';
import { User, Role } from '../types';
import { mockUsers } from '../mock';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    token: null,
    isLoading: false,
    error: null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
    userRole: (state): Role | null => state.user?.role || null,
    currentUser: (state) => state.user,
  },
  actions: {
    async login(email: string) {
      this.isLoading = true;
      this.error = null;
      try {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 500));

        const user = mockUsers.find(u => u.email === email);
        if (!user) {
          throw new Error('User not found');
        }

        this.user = user;
        this.token = `mock-token-for-${user.id}`;
      } catch (err: any) {
        this.error = err.message || 'Login failed';
      } finally {
        this.isLoading = false;
      }
    },
    logout() {
      this.user = null;
      this.token = null;
    },
  },
});

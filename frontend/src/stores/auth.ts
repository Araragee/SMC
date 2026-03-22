import { defineStore } from 'pinia';
import axios from 'axios';
import type { User, Role } from '../types';

const API_URL = 'http://localhost:8000';

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
    async login(email: string, password = "password123") {
      this.isLoading = true;
      this.error = null;
      try {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await axios.post(`${API_URL}/login`, formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });

        const data = response.data;
        const user = data.user;

        // Map backend user to frontend user type
        this.user = {
          id: String(user.id),
          name: user.name,
          email: user.email,
          role: user.role?.name?.toLowerCase() as Role || 'student',
          avatarUrl: user.avatar_url,
          sessionsLeft: user.sessions_left
        };
        this.token = data.access_token;
      } catch (err: any) {
        this.error = err.response?.data?.detail || err.message || 'Login failed';
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

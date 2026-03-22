import { defineStore } from 'pinia';
import axios from 'axios';
import type { User, Role } from '../types';

const API_URL = 'http://localhost:8000';

const savedToken = localStorage.getItem('token');
const savedUser = localStorage.getItem('user');

if (savedToken) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: savedUser ? JSON.parse(savedUser) : null,
    token: savedToken || null,
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

        // ... setup user ...
        this.user = {
          id: String(user.id),
          name: user.name,
          email: user.email,
          role: typeof user.role === 'string' ? user.role.toLowerCase() as Role : (user.role?.name?.toLowerCase() || 'student') as Role,
          avatarUrl: user.avatar_url,
          sessionsLeft: user.sessions_left
        };
        this.token = data.access_token;
        
        if (this.token && this.user) {
          localStorage.setItem('token', this.token);
          localStorage.setItem('user', JSON.stringify(this.user));
          axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`;
        }

      } catch (err: any) {
        this.error = err.response?.data?.detail || err.message || 'Login failed';
      } finally {
        this.isLoading = false;
      }
    },
    logout() {
      this.user = null;
      this.token = null;
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      delete axios.defaults.headers.common['Authorization'];
    },
  },
});

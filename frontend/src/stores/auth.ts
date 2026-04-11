import { defineStore } from 'pinia'
import axios from 'axios'
import type { User, Role } from '@types'
import { useToastStore } from '@stores/toast'
import { API_URL } from '@typscript/constants'

const savedToken = localStorage.getItem('token')
const savedUser = localStorage.getItem('user')

if (savedToken) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`
}

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  error: string | null
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
    async login(username: string, password: string) {
      const toast = useToastStore()
      this.isLoading = true
      this.error = null
      try {
        const formData = new URLSearchParams()
        formData.append('username', username)
        formData.append('password', password)

        const response = await axios.post(`${API_URL}/login`, formData, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        })

        const data = response.data
        const user = data.user

        this.user = {
          id: String(user.id),
          name: user.name,
          email: user.email,
          role: typeof user.role === 'string'
            ? user.role.toLowerCase() as Role
            : (user.role?.name?.toLowerCase() || 'student') as Role,
          avatarUrl: user.avatar_url,
          sessionsLeft: user.sessions_left
        }
        this.token = data.access_token

        if (this.token && this.user) {
          localStorage.setItem('token', this.token)
          localStorage.setItem('user', JSON.stringify(this.user))
          axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        }

        toast.success('Welcome back!', `Signed in as ${this.user?.name}`)
      } catch (err: any) {
        this.error = err.response?.data?.detail || err.message || 'Login failed'
        toast.error('Login failed', this.error || undefined)
      } finally {
        this.isLoading = false
      }
    },

    logout() {
      const toast = useToastStore()
      this.user = null
      this.token = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      delete axios.defaults.headers.common['Authorization']
      toast.info('Signed out', 'See you next time!')
    },

    setTokenAndUser(token: string, user: User) {
      this.token = token
      this.user = user
      localStorage.setItem('token', token)
      localStorage.setItem('user', JSON.stringify(user))
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    },

    async updateProfile(payload: { name?: string; email?: string; avatar_url?: string; password?: string }) {
      const toast = useToastStore()
      if (!this.user?.id) return
      
      this.isLoading = true
      try {
        const response = await axios.put(`${API_URL}/users/${this.user.id}`, payload)
        const updatedUser = response.data
        
        // Update local state
        this.user = {
          ...this.user,
          name: updatedUser.name,
          email: updatedUser.email,
          avatarUrl: updatedUser.avatar_url
        }
        localStorage.setItem('user', JSON.stringify(this.user))
        toast.success('Profile updated', 'Your changes have been saved.')
        return true
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || 'Failed to update profile'
        toast.error('Update failed', errorMsg)
        return false
      } finally {
        this.isLoading = false
      }
    }
  },
})

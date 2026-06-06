import { defineStore } from 'pinia'
import axios from 'axios'
import type { User, Role } from '@types'
import { useToastStore } from '@stores/toast'
import { API_URL } from '@typescript/constants'

const savedToken = localStorage.getItem('token')
const savedRefreshToken = localStorage.getItem('refresh_token')
const rawSavedUser = localStorage.getItem('user')

// Safely hydrate the persisted user. If JSON is malformed or required
// fields are missing, treat as logged out and clean up storage.
const hydrateUser = (raw: string | null): User | null => {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    if (
      !parsed ||
      typeof parsed.id !== 'number' ||
      typeof parsed.name !== 'string' ||
      typeof parsed.role !== 'string'
    ) {
      throw new Error('Persisted user missing required fields')
    }
    return parsed as User
  } catch {
    localStorage.removeItem('user')
    localStorage.removeItem('token')
    return null
  }
}

const initialUser = hydrateUser(rawSavedUser)
const initialToken = initialUser ? savedToken : null

if (initialToken) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${initialToken}`
}

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isLoading: boolean
  error: string | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: initialUser,
    token: initialToken,
    refreshToken: initialToken ? savedRefreshToken : null,
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
          id: Number(user.id),
          name: user.name,
          email: user.email,
          role: (user.role?.name?.toLowerCase() || 'student') as Role,
          avatarUrl: user.avatar_url,
          sessionsLeft: user.sessions_left
        }
        this.token = data.access_token
        this.refreshToken = data.refresh_token ?? null

        if (this.token && this.user) {
          localStorage.setItem('token', this.token)
          localStorage.setItem('user', JSON.stringify(this.user))
          if (this.refreshToken) localStorage.setItem('refresh_token', this.refreshToken)
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

    async logout() {
      const toast = useToastStore()

      // Tear down feature stores. Dynamic imports avoid circular deps and
      // keep auth importable from any store. `$reset()` is available on
      // Options-API Pinia stores (all stores here use that style).
      try {
        const { useScheduleStore } = await import('@stores/schedule')
        const schedule = useScheduleStore()
        schedule.$reset?.()
      } catch { /* store not loaded */ }

      try {
        const { useMessagingStore } = await import('@stores/messaging')
        const messaging = useMessagingStore()
        messaging.disconnectWS?.()
        messaging.$reset?.()
      } catch { /* store not loaded */ }

      try {
        const { useShopStore } = await import('@stores/shop')
        const shop = useShopStore()
        shop.$reset?.()
      } catch { /* store not loaded */ }

      // Purge per-session nudge throttling keys.
      const keysToRemove: string[] = []
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i)
        if (k && k.startsWith('nudge_last_')) keysToRemove.push(k)
      }
      keysToRemove.forEach((k) => localStorage.removeItem(k))

      // Clear cart persistence too — it's user-scoped.
      localStorage.removeItem('smc_cart')

      this.user = null
      this.token = null
      this.refreshToken = null
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      delete axios.defaults.headers.common['Authorization']
      toast.info('Signed out', 'See you next time!')
    },

    /** Silently rotate the access token using the stored refresh token.
     *  Returns true on success, false if the refresh token is missing or rejected. */
    async refreshAccessToken(): Promise<boolean> {
      if (!this.refreshToken) return false
      try {
        const response = await axios.post(
          `${API_URL}/auth/refresh`,
          { refresh_token: this.refreshToken },
          // Skip the default Authorization header — the refresh token IS the credential
          { headers: { Authorization: undefined } }
        )
        this.token = response.data.access_token
        this.refreshToken = response.data.refresh_token ?? this.refreshToken
        if (this.token) {
          localStorage.setItem('token', this.token)
          if (this.refreshToken) localStorage.setItem('refresh_token', this.refreshToken)
          axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        }
        return true
      } catch {
        // Refresh token revoked / expired — force full logout
        await this.logout()
        return false
      }
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
          role: (updatedUser.role?.name?.toLowerCase() || this.user.role) as Role,
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

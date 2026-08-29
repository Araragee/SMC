import { defineStore } from 'pinia'
import axios from 'axios'
import type { User, Role } from '@types'
import { useToastStore } from '@stores/toast'
import { API_URL } from '@typescript/constants'

// Phase 2: refresh token lives in an HttpOnly cookie now. We need
// axios to send cookies on cross-origin requests, otherwise the browser
// will strip them. Backend CORS must also have allow_credentials=true
// (already set in backend/main.py).
axios.defaults.withCredentials = true

const savedToken = localStorage.getItem('token')
// Legacy localStorage refresh token — read once at boot for the migration
// window. New logins do NOT write this; the value here is a vestige from
// pre-Phase 2 sessions and is naturally retired the next time the user
// signs in/out. We never SEND it anywhere — the HttpOnly cookie is the
// source of truth.
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
  requires2FA: boolean
  challengeToken: string | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: initialUser,
    token: initialToken,
    // Hidden behind the cookie now. Kept as a state slot only so other
    // store consumers don't break on undefined access during the migration.
    refreshToken: null,
    isLoading: false,
    error: null,
    requires2FA: false,
    challengeToken: null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
    userRole: (state): Role | null => state.user?.role || null,
    currentUser: (state) => state.user,
  },
  actions: {
    async login(username: string, password: string): Promise<{ requires2FA: boolean }> {
      const toast = useToastStore()
      this.isLoading = true
      this.error = null
      this.requires2FA = false
      this.challengeToken = null
      try {
        const formData = new URLSearchParams()
        formData.append('username', username)
        formData.append('password', password)

        const response = await axios.post(`${API_URL}/login`, formData, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        })

        const data = response.data

        // Handle 2FA login challenge response
        if (data.requires_2fa) {
          this.requires2FA = true
          this.challengeToken = data.challenge_token
          this.isLoading = false
          return { requires2FA: true }
        }

        const user = data.user
        this.user = {
          id: Number(user.id),
          name: user.name,
          email: user.email,
          role: (user.role?.name?.toLowerCase() || 'student') as Role,
          avatarUrl: user.avatar_url,
          sessionsLeft: user.sessions_left,
          totpEnabled: user.totp_enabled,
          mustChangePassword: !!user.must_change_password,
        }
        this.token = data.access_token
        // The refresh token is set as an HttpOnly cookie by the server.
        // We intentionally do NOT persist it in localStorage — that was
        // the XSS hole this phase closes.
        this.refreshToken = null

        if (this.token && this.user) {
          localStorage.setItem('token', this.token)
          localStorage.setItem('user', JSON.stringify(this.user))
          // Purge any leftover legacy refresh token from pre-Phase 2 logins.
          localStorage.removeItem('refresh_token')
          axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        }

        toast.success('Welcome back!', `Signed in as ${this.user?.name}`)
        return { requires2FA: false }
      } catch (err: any) {
        this.error = err.response?.data?.detail || err.message || 'Login failed'
        toast.error('Login failed', this.error || undefined)
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async verify2FA(code: string) {
      const toast = useToastStore()
      this.isLoading = true
      this.error = null
      try {
        if (!this.challengeToken) {
          throw new Error('No 2FA challenge token found')
        }

        const response = await axios.post(`${API_URL}/auth/2fa/verify`, {
          challenge_token: this.challengeToken,
          code
        })

        const data = response.data
        const user = data.user

        this.user = {
          id: Number(user.id),
          name: user.name,
          email: user.email,
          role: (user.role?.name?.toLowerCase() || 'student') as Role,
          avatarUrl: user.avatar_url,
          sessionsLeft: user.sessions_left,
          totpEnabled: user.totp_enabled,
          mustChangePassword: !!user.must_change_password,
        }
        this.token = data.access_token
        // Same story as login(): refresh token lives in the HttpOnly cookie.
        this.refreshToken = null

        if (this.token && this.user) {
          localStorage.setItem('token', this.token)
          localStorage.setItem('user', JSON.stringify(this.user))
          if (this.refreshToken) localStorage.setItem('refresh_token', this.refreshToken)
          axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        }

        this.requires2FA = false
        this.challengeToken = null

        toast.success('Welcome back!', `Signed in as ${this.user?.name}`)
        return true
      } catch (err: any) {
        this.error = err.response?.data?.detail || err.message || '2FA verification failed'
        toast.error('Verification failed', this.error || undefined)
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async setup2FA() {
      this.isLoading = true
      try {
        const response = await axios.post(`${API_URL}/auth/2fa/setup`)
        return response.data // secret, provisioning_uri, qr_code_png_base64
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || 'Failed to setup 2FA'
        useToastStore().error('Setup failed', errorMsg)
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async enable2FA(code: string) {
      this.isLoading = true
      try {
        await axios.post(`${API_URL}/auth/2fa/enable`, { code })
        if (this.user) {
          this.user.totpEnabled = true
          localStorage.setItem('user', JSON.stringify(this.user))
        }
        useToastStore().success('2FA Enabled', 'Two-factor authentication is now active.')
        return true
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || 'Failed to enable 2FA'
        useToastStore().error('Activation failed', errorMsg)
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async disable2FA(password: string, code: string) {
      this.isLoading = true
      try {
        await axios.post(`${API_URL}/auth/2fa/disable`, { password, code })
        if (this.user) {
          this.user.totpEnabled = false
          localStorage.setItem('user', JSON.stringify(this.user))
        }
        useToastStore().success('2FA Disabled', 'Two-factor authentication has been deactivated.')
        return true
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || 'Failed to disable 2FA'
        useToastStore().error('Deactivation failed', errorMsg)
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async logout() {
      const toast = useToastStore()

      // Best-effort: tell the server to revoke the refresh token and clear
      // the cookie. We don't wait long or surface errors here — even if the
      // server is down we still want to wipe local state.
      try {
        await axios.post(
          `${API_URL}/auth/logout`,
          {},
          { withCredentials: true, timeout: 3000, headers: { Authorization: undefined } }
        )
      } catch { /* offline / 401 — local cleanup proceeds either way */ }

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
      this.requires2FA = false
      this.challengeToken = null
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      delete axios.defaults.headers.common['Authorization']
      toast.info('Signed out', 'See you next time!')
    },

    /** Silently rotate the access token using the HttpOnly refresh cookie.
     *  Returns true on success, false if the cookie is missing or rejected.
     *
     *  No body is sent: the server reads the refresh token from the
     *  ``smc_rt`` cookie (set on login / 2FA-verify / previous refresh)
     *  and writes a fresh one on the way back. ``withCredentials`` is the
     *  axios flag that lets the browser attach the cookie at all. */
    async refreshAccessToken(): Promise<boolean> {
      try {
        const response = await axios.post(
          `${API_URL}/auth/refresh`,
          {},
          {
            withCredentials: true,
            // Skip the stale Authorization header — the cookie IS the credential
            headers: { Authorization: undefined },
          }
        )
        this.token = response.data.access_token
        this.refreshToken = null
        if (this.token) {
          localStorage.setItem('token', this.token)
          // Make sure no stale localStorage refresh token survives a refresh.
          localStorage.removeItem('refresh_token')
          axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        }
        return true
      } catch {
        // Refresh cookie missing / revoked / expired — force full logout
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
          avatarUrl: updatedUser.avatar_url,
          totpEnabled: updatedUser.totp_enabled !== undefined ? updatedUser.totp_enabled : this.user.totpEnabled
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

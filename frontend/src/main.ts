import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from 'axios'
import FloatingVue from 'floating-vue'
import 'floating-vue/dist/style.css'
import '@/style.css'
import App from '@/App.vue'
import router from '@/router'
import { useThemeStore } from '@stores/theme'

// Phase 2: the refresh token is delivered as an HttpOnly cookie. Cookies
// only ride along on cross-origin requests when withCredentials is true.
// Backend CORS already sets allow_credentials=true (backend/main.py).
axios.defaults.withCredentials = true

// Restore axios auth header from persisted token on every app boot
const token = localStorage.getItem('token')
if (token) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
}

const pinia = createPinia()
const app = createApp(App)

app.use(pinia)
app.use(FloatingVue)

// Initialize Theme
const themeStore = useThemeStore()
themeStore.applyTheme(themeStore.isDarkMode)

app.use(router)

// Global 401 handler: attempt silent token refresh, then retry original request.
// Falls back to logout + redirect if the refresh token is also rejected.
// Dynamic import of the store avoids a circular dep (auth store imports axios).
let isRefreshing = false
let refreshQueue: Array<(token: string | null) => void> = []

const drainQueue = (token: string | null) => {
  refreshQueue.forEach((cb) => cb(token))
  refreshQueue = []
}

axios.interceptors.response.use(
  (r) => r,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 503) {
      const { useMaintenanceStore } = await import('@stores/maintenance')
      const maintenance = useMaintenanceStore()
      maintenance.setMaintenance(true)
      return Promise.reject(error)
    }

    // Endpoints where a 401 means "these credentials are wrong", not "this
    // session expired". Refreshing on those is nonsense: there is no session
    // to refresh, the refresh call fails, and the failure path runs a full
    // logout() — which fires a "Signed out" toast at someone who was never
    // signed in and wipes their cart and store state. Let the caller's own
    // error handling report it.
    const CREDENTIAL_ENDPOINTS = ['/login', '/auth/refresh', '/auth/2fa/verify', '/auth/logout']
    const isCredentialCheck = CREDENTIAL_ENDPOINTS.some((path) =>
      originalRequest?.url?.includes(path)
    )

    // Only intercept 401s that haven't already been retried and aren't a
    // credential check (infinite-loop and false-logout guard).
    if (error.response?.status !== 401 || originalRequest?._refreshRetry || isCredentialCheck) {
      return Promise.reject(error)
    }

    originalRequest._refreshRetry = true

    if (isRefreshing) {
      // Another refresh is already in flight — queue this request
      return new Promise((resolve, reject) => {
        refreshQueue.push((token) => {
          if (token) {
            originalRequest.headers['Authorization'] = `Bearer ${token}`
            resolve(axios(originalRequest))
          } else {
            reject(error)
          }
        })
      })
    }

    isRefreshing = true
    try {
      const { useAuthStore } = await import('@stores/auth')
      const auth = useAuthStore()
      const ok = await auth.refreshAccessToken()

      if (ok && auth.token) {
        drainQueue(auth.token)
        originalRequest.headers['Authorization'] = `Bearer ${auth.token}`
        return axios(originalRequest)
      } else {
        drainQueue(null)
        if (router.currentRoute.value.path !== '/login') {
          router.push('/login')
        }
        return Promise.reject(error)
      }
    } finally {
      isRefreshing = false
    }
  }
)

app.mount('#app')

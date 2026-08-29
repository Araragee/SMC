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
  refreshQueue.forEach(cb => cb(token))
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

    // Only intercept 401s that haven't already been retried and aren't the
    // refresh endpoint itself (infinite-loop guard).
    if (
      error.response?.status !== 401 ||
      originalRequest?._refreshRetry ||
      originalRequest?.url?.includes('/auth/refresh')
    ) {
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

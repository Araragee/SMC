import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from 'axios'
import FloatingVue from 'floating-vue'
import 'floating-vue/dist/style.css'
import '@/style.css'
import App from '@/App.vue'
import router from '@/router'
import { useThemeStore } from '@stores/theme'

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

app.mount('#app')

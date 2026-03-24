import { defineStore } from 'pinia'
import { ref, watch, onMounted } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  // Check local storage first, then default to system preference, 
  // but if nothing is set, we default to the legacy dark theme.
  const getInitialPreference = () => {
    const saved = localStorage.getItem('theme')
    if (saved) return saved === 'dark'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  }

  const isDarkMode = ref(!localStorage.getItem('theme') ? true : getInitialPreference())

  const applyTheme = (dark: boolean) => {
    if (dark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  // Watch for changes and apply to document + save to localStorage
  watch(isDarkMode, (newVal) => {
    applyTheme(newVal)
    localStorage.setItem('theme', newVal ? 'dark' : 'light')
  })

  // Apply immediately on mount
  onMounted(() => {
    applyTheme(isDarkMode.value)
  })

  function toggleTheme() {
    isDarkMode.value = !isDarkMode.value
  }

  return { isDarkMode, toggleTheme, applyTheme }
})

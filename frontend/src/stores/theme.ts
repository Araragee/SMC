import { defineStore } from 'pinia'
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

export type ThemePreference = 'light' | 'dark' | 'system'

export const useThemeStore = defineStore('theme', () => {
  const systemPrefersDark = ref(window.matchMedia('(prefers-color-scheme: dark)').matches)

  // 'light' | 'dark' | 'system'
  const saved = localStorage.getItem('theme') as ThemePreference | null
  const preference = ref<ThemePreference>(saved && ['light', 'dark', 'system'].includes(saved) ? saved : 'system')

  /** Resolved boolean — true when we should be in dark mode */
  const isDarkMode = computed(() => {
    if (preference.value === 'system') return systemPrefersDark.value
    return preference.value === 'dark'
  })

  const applyTheme = (dark: boolean) => {
    if (dark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  // Watch resolved dark mode and re-apply
  watch(isDarkMode, (newVal) => {
    applyTheme(newVal)
  })

  // Persist preference when it changes
  watch(preference, (pref) => {
    localStorage.setItem('theme', pref)
    applyTheme(isDarkMode.value)
  })

  // Listen for OS-level changes
  // eslint-disable-next-line no-undef
  let mediaQuery: MediaQueryList | null = null
  // eslint-disable-next-line no-undef
  const handleSystemChange = (e: MediaQueryListEvent) => {
    systemPrefersDark.value = e.matches
  }

  onMounted(() => {
    mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQuery.addEventListener('change', handleSystemChange)
    applyTheme(isDarkMode.value)
  })

  onUnmounted(() => {
    mediaQuery?.removeEventListener('change', handleSystemChange)
  })

  /** Cycle: system → light → dark → system */
  const toggleTheme = function() {
    if (preference.value === 'system') {
      preference.value = isDarkMode.value ? 'light' : 'dark'
    } else if (preference.value === 'light') {
      preference.value = 'dark'
    } else {
      preference.value = 'light'
    }
  }

  const setPreference = function(pref: ThemePreference) {
    preference.value = pref
  }

  return { isDarkMode, preference, toggleTheme, setPreference, applyTheme }
})

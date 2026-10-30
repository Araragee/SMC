import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

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

  // Listen for OS-level changes.
  //
  // Bound here at store creation rather than in onMounted. main.ts calls
  // useThemeStore() before app.mount(), so Pinia runs this setup with no
  // active component instance: Vue warned on every boot and the listener was
  // never attached, which left the 'system' preference frozen at whatever the
  // OS reported at startup. Changing appearance did nothing until a reload.
  //
  // There is no matching teardown because the store lives as long as the page
  // does. The old onUnmounted was the more dangerous half anyway — had this
  // store first been touched inside a component, it would have ripped the
  // listener out when that unrelated component unmounted.
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQuery.addEventListener('change', (e) => {
    systemPrefersDark.value = e.matches
  })

  applyTheme(isDarkMode.value)

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

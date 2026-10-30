import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useModalStore = defineStore('modal', () => {
  const isNotificationsOpen = ref(false)
  const isSettingsOpen = ref(false)
  const isPreferencesOpen = ref(false)

  const openNotifications = function () {
    isNotificationsOpen.value = true
  }

  const closeNotifications = function () {
    isNotificationsOpen.value = false
  }

  const openSettings = function () {
    isSettingsOpen.value = true
  }

  const closeSettings = function () {
    isSettingsOpen.value = false
  }

  const openPreferences = function () {
    isPreferencesOpen.value = true
  }

  const closePreferences = function () {
    isPreferencesOpen.value = false
  }

  return {
    isNotificationsOpen,
    isSettingsOpen,
    isPreferencesOpen,
    openNotifications,
    closeNotifications,
    openSettings,
    closeSettings,
    openPreferences,
    closePreferences,
  }
})

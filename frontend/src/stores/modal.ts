import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useModalStore = defineStore('modal', () => {
  const isNotificationsOpen = ref(false)
  const isSettingsOpen = ref(false)
  
  const openNotifications = function() {
    isNotificationsOpen.value = true
  }
  
  const closeNotifications = function() {
    isNotificationsOpen.value = false
  }

  const openSettings = function() {
    isSettingsOpen.value = true
  }

  const closeSettings = function() {
    isSettingsOpen.value = false
  }

  return {
    isNotificationsOpen,
    isSettingsOpen,
    openNotifications,
    closeNotifications,
    openSettings,
    closeSettings
  }
})

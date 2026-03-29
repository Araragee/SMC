import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useModalStore = defineStore('modal', () => {
  const isNotificationsOpen = ref(false)
  const isSettingsOpen = ref(false)
  
  function openNotifications() {
    isNotificationsOpen.value = true
  }
  
  function closeNotifications() {
    isNotificationsOpen.value = false
  }

  function openSettings() {
    isSettingsOpen.value = true
  }

  function closeSettings() {
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

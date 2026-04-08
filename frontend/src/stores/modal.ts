import { defineStore } from 'pinia'
import type { Notification } from '../types'

export const useModalStore = defineStore('modal', {
  state: () => ({
    isNotificationsOpen: false,
    isSettingsOpen: false,
    isPreferencesOpen: false,
    selectedNotification: null as Notification | null,
  }),
  actions: {
    openNotifications() {
      this.isNotificationsOpen = true
    },
    closeNotifications() {
      this.isNotificationsOpen = false
    },
    openSettings() {
      this.isSettingsOpen = true
    },
    closeSettings() {
      this.isSettingsOpen = false
    },
    openPreferences() {
      this.isPreferencesOpen = true
    },
    closePreferences() {
      this.isPreferencesOpen = false
    },
    setSelectedNotification(notification: Notification | null) {
      this.selectedNotification = notification
    },
  },
})

import { defineStore } from 'pinia'

interface MaintenanceState {
  isMaintenance: boolean
}

export const useMaintenanceStore = defineStore('maintenance', {
  state: (): MaintenanceState => ({
    isMaintenance: false,
  }),
  actions: {
    setMaintenance(value: boolean) {
      this.isMaintenance = value
    },
    clearMaintenance() {
      this.isMaintenance = false
      window.location.reload()
    },
  },
})

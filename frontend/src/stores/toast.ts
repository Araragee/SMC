import { defineStore } from 'pinia'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  type: ToastType
  title: string
  message?: string
  duration?: number
}

interface ToastState {
  toasts: Toast[]
}

export const useToastStore = defineStore('toast', {
  state: (): ToastState => ({
    toasts: [],
  }),
  actions: {
    add(toast: Omit<Toast, 'id'>) {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`
      const duration = toast.duration ?? 4000
      this.toasts.push({ ...toast, id })
      setTimeout(() => this.remove(id), duration)
    },
    remove(id: string) {
      const idx = this.toasts.findIndex((t) => t.id === id)
      if (idx !== -1) this.toasts.splice(idx, 1)
    },
    success(title: string, message?: string) {
      this.add({ type: 'success', title, message })
    },
    error(title: string, message?: string) {
      this.add({ type: 'error', title, message })
    },
    warning(title: string, message?: string) {
      this.add({ type: 'warning', title, message })
    },
    info(title: string, message?: string) {
      this.add({ type: 'info', title, message })
    },
  },
})

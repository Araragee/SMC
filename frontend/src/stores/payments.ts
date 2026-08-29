import { defineStore } from 'pinia'
import axios from 'axios'
import { useAuthStore } from '@stores/auth'
import { useToastStore } from '@stores/toast'

import { API_URL } from '@typescript/constants'

const authHeaders = function () {
  const auth = useAuthStore()
  return auth.token ? { Authorization: `Bearer ${auth.token}` } : {}
}

export interface Payment {
  id: number
  student_id: number
  student_name?: string | null
  amount: number
  date: string
  method: string
  status: string
  notes?: string
}

export const usePaymentsStore = defineStore('payments', {
  state: () => ({
    payments: [] as Payment[],
    isLoading: false,
    error: null as string | null,
  }),
  getters: {
    totalRevenue: (state) =>
      state.payments
        .filter((p) => p.status === 'completed')
        .reduce((sum, p) => sum + p.amount, 0),
    pendingCount: (state) => state.payments.filter((p) => p.status === 'pending').length,
    completedCount: (state) => state.payments.filter((p) => p.status === 'completed').length,
  },
  actions: {
    async fetchPayments() {
      this.isLoading = true
      try {
        const response = await axios.get(`${API_URL}/payments/`, { headers: authHeaders() })
        this.payments = response.data
      } catch (err: any) {
        this.error = err.message
        useToastStore().error('Failed to load payments', err?.response?.data?.detail || err.message || 'Please try again.')
      } finally {
        this.isLoading = false
      }
    },
    async createPayment(paymentData: Partial<Payment>) {
      try {
        const response = await axios.post(`${API_URL}/payments/`, paymentData, {
          headers: authHeaders(),
        })
        this.payments.unshift(response.data)
        return response.data
      } catch (err: any) {
        throw err
      }
    },
    async updatePayment(
      paymentId: number,
      payload: Partial<Pick<Payment, 'status' | 'notes' | 'method' | 'amount'>>,
    ) {
      try {
        const response = await axios.patch(`${API_URL}/payments/${paymentId}`, payload, {
          headers: authHeaders(),
        })
        const idx = this.payments.findIndex((p) => p.id === paymentId)
        if (idx !== -1) this.payments[idx] = response.data
        return response.data
      } catch (err: any) {
        throw err
      }
    },
    async deletePayment(paymentId: number) {
      try {
        await axios.delete(`${API_URL}/payments/${paymentId}`, { headers: authHeaders() })
        this.payments = this.payments.filter((p) => p.id !== paymentId)
      } catch (err: any) {
        throw err
      }
    },
  },
})

import { defineStore } from 'pinia'
import axios from 'axios'
import { useAuthStore } from '@stores/auth'

import { API_URL } from '@typescript/constants'

const authHeaders = function() {
  const auth = useAuthStore()
  return auth.token ? { Authorization: `Bearer ${auth.token}` } : {}
}

export interface Payment {
  id: number
  student_id: number
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
  actions: {
    async fetchPayments() {
      this.isLoading = true
      try {
        const response = await axios.get(`${API_URL}/payments/`, { headers: authHeaders() })
        this.payments = response.data
      } catch (err: any) {
        this.error = err.message
      } finally {
        this.isLoading = false
      }
    },
    async createPayment(paymentData: Partial<Payment>) {
      try {
        const response = await axios.post(`${API_URL}/payments/`, paymentData, { headers: authHeaders() })
        this.payments.push(response.data)
        return response.data
      } catch (err: any) {
        throw err
      }
    }
  }
})

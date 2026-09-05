import { defineStore } from 'pinia'
import axios from 'axios'
import type { InstrumentProduct, Order, OrderStatus } from '../types'
import { useAuthStore } from './auth'
import { useToastStore } from './toast'
import { API_URL } from '@typescript/constants'

// Explicit auth header helper — consistent with payments.ts / schedule.ts pattern
const authHeaders = () => {
  const auth = useAuthStore()
  return auth.token ? { Authorization: `Bearer ${auth.token}` } : {}
}

export const useShopStore = defineStore('shop', {
  state: () => ({
    products: [] as InstrumentProduct[],
    orders: [] as Order[],
    myOrders: [] as Order[],
    cart: JSON.parse(localStorage.getItem('smc_cart') || '[]') as {
      productId: number
      quantity: number
    }[],
    isLoading: false,
  }),

  getters: {
    cartItemsCount: (state) => state.cart.reduce((sum, item) => sum + item.quantity, 0),
    cartTotalCents: (state) => {
      return state.cart.reduce((sum, item) => {
        const product = state.products.find((p: InstrumentProduct) => p.id === item.productId)
        return sum + (product ? product.priceCents * item.quantity : 0)
      }, 0)
    },
    getCartProduct: (state) => (productId: number) => {
      const product = state.products.find((p: InstrumentProduct) => p.id === productId)
      const cartItem = state.cart.find((item) => item.productId === productId)
      return product ? { ...product, cartQuantity: cartItem?.quantity || 0 } : null
    },
  },

  actions: {
    async fetchProducts() {
      const toast = useToastStore()
      this.isLoading = true
      try {
        const response = await axios.get(`${API_URL}/shop/products`, { headers: authHeaders() })
        this.products = response.data.map(mapProduct)
      } catch (error) {
        console.error('Error fetching products:', error)
        toast.error('Error', 'Failed to load products. Please try again.')
      } finally {
        this.isLoading = false
      }
    },

    async fetchProduct(id: number) {
      try {
        const response = await axios.get(`${API_URL}/shop/products/${id}`, {
          headers: authHeaders(),
        })
        const product = mapProduct(response.data)
        const index = this.products.findIndex((p: InstrumentProduct) => p.id === id)
        if (index !== -1) this.products[index] = product
        else this.products.push(product)
        return product
      } catch (error) {
        console.error('Error fetching product:', error)
      }
    },

    async createProduct(data: Partial<InstrumentProduct>) {
      const toast = useToastStore()
      try {
        const response = await axios.post(`${API_URL}/shop/products`, data, {
          headers: authHeaders(),
        })
        const product = mapProduct(response.data)
        this.products.unshift(product)
        toast.success('Product created', 'Product created successfully')
        return product
      } catch (error) {
        toast.error('Error', 'Failed to create product')
        throw error
      }
    },

    async updateProduct(id: number, data: Partial<InstrumentProduct>) {
      const toast = useToastStore()
      try {
        const response = await axios.put(`${API_URL}/shop/products/${id}`, data, {
          headers: authHeaders(),
        })
        const product = mapProduct(response.data)
        const index = this.products.findIndex((p: InstrumentProduct) => p.id === id)
        if (index !== -1) this.products[index] = product
        toast.success('Product updated', 'Product updated successfully')
        return product
      } catch (error) {
        toast.error('Error', 'Failed to update product')
        throw error
      }
    },

    async deleteProduct(id: number) {
      const toast = useToastStore()
      try {
        await axios.delete(`${API_URL}/shop/products/${id}`, { headers: authHeaders() })
        const index = this.products.findIndex((p: InstrumentProduct) => p.id === id)
        if (index !== -1) this.products[index].isActive = false
        toast.success('Product deactivated', 'Product has been deactivated')
      } catch (error) {
        toast.error('Error', 'Failed to deactivate product')
      }
    },

    async uploadProductImage(id: number, file: File) {
      const toast = useToastStore()
      const formData = new FormData()
      formData.append('file', file)
      try {
        const response = await axios.post(`${API_URL}/shop/products/${id}/image`, formData, {
          headers: authHeaders(),
        })
        const index = this.products.findIndex((p: InstrumentProduct) => p.id === id)
        if (index !== -1) this.products[index].imageUrl = response.data.url
        return response.data.url
      } catch (error) {
        toast.error('Error', 'Failed to upload image')
        throw error
      }
    },

    // Cart Actions
    addToCart(productId: number, quantity = 1) {
      const existing = this.cart.find((item) => item.productId === productId)
      if (existing) {
        existing.quantity += quantity
      } else {
        this.cart.push({ productId, quantity })
      }
      this.saveCart()
    },

    updateCartItem(productId: number, quantity: number) {
      const item = this.cart.find((item) => item.productId === productId)
      if (item) {
        if (quantity <= 0) {
          this.removeFromCart(productId)
        } else {
          item.quantity = quantity
          this.saveCart()
        }
      }
    },

    removeFromCart(productId: number) {
      this.cart = this.cart.filter((item) => item.productId !== productId)
      this.saveCart()
    },

    clearCart() {
      this.cart = []
      this.saveCart()
    },

    saveCart() {
      localStorage.setItem('smc_cart', JSON.stringify(this.cart))
    },

    // Orders
    async placeOrder(notes?: string) {
      const toast = useToastStore()
      if (this.cart.length === 0) return

      try {
        const response = await axios.post(
          `${API_URL}/shop/orders`,
          {
            notes,
            items: this.cart.map((item) => ({
              product_id: item.productId,
              quantity: item.quantity,
            })),
          },
          { headers: authHeaders() }
        )
        const order = mapOrder(response.data)
        this.myOrders.unshift(order)
        this.clearCart()
        toast.success('Order placed', 'Order placed successfully!')
        return order
      } catch (error: unknown) {
        const msg =
          (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Failed to place order'
        toast.error('Error', msg)
        throw error
      }
    },

    async fetchMyOrders() {
      const toast = useToastStore()
      try {
        const response = await axios.get(`${API_URL}/shop/orders/me`, { headers: authHeaders() })
        this.myOrders = response.data.map(mapOrder)
      } catch (error) {
        console.error('Error fetching my orders:', error)
        toast.error('Error', 'Failed to load your orders. Please try again.')
      }
    },

    async fetchAllOrders(status?: string) {
      const toast = useToastStore()
      try {
        const response = await axios.get(`${API_URL}/shop/orders`, {
          params: { status },
          headers: authHeaders(),
        })
        this.orders = response.data.map(mapOrder)
      } catch (error) {
        console.error('Error fetching all orders:', error)
        toast.error('Error', 'Failed to load orders. Please try again.')
      }
    },

    async updateOrderStatus(id: number, status: OrderStatus, rejectionReason?: string) {
      const toast = useToastStore()
      try {
        const response = await axios.patch(
          `${API_URL}/shop/orders/${id}/status`,
          {
            status,
            rejection_reason: rejectionReason,
          },
          { headers: authHeaders() }
        )
        const updated = mapOrder(response.data)

        // Update in both lists if present
        const oIndex = this.orders.findIndex((o: Order) => o.id === id)
        if (oIndex !== -1) this.orders[oIndex] = updated

        const myIndex = this.myOrders.findIndex((o: Order) => o.id === id)
        if (myIndex !== -1) this.myOrders[myIndex] = updated

        toast.success('Success', `Order ${status} successfully`)

        // Refresh product list so stock counts reflect backend deductions/restorations
        if (['approved', 'cancelled', 'fulfilled'].includes(status)) {
          await this.fetchProducts()
        }

        return updated
      } catch (error: unknown) {
        const msg =
          (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Failed to update order'
        toast.error('Error', msg)
        throw error
      }
    },

    async cancelMyOrder(id: number) {
      const toast = useToastStore()
      try {
        // Uses the user-facing cancel endpoint (not the admin-only /status endpoint)
        const response = await axios.patch(
          `${API_URL}/shop/orders/${id}/cancel`,
          {},
          { headers: authHeaders() }
        )
        const updated = mapOrder(response.data)
        const index = this.myOrders.findIndex((o: Order) => o.id === id)
        if (index !== -1) this.myOrders[index] = updated
        toast.success('Cancelled', 'Order cancelled')
        // Stock is restored on cancel — refresh product list to reflect new counts
        await this.fetchProducts()
      } catch (error: unknown) {
        const msg =
          (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Failed to cancel order'
        toast.error('Error', msg)
      }
    },
  },
})

// Mappers
const mapProduct = (p: any): InstrumentProduct => ({
  id: p.id,
  name: p.name,
  description: p.description,
  priceCents: p.price_cents,
  stock: p.stock,
  imageUrl: p.image_url,
  categoryId: p.category_id ?? null,
  category: p.category ?? null,
  isActive: p.is_active,
  createdAt: p.created_at,
  updatedAt: p.updated_at,
})

const mapOrder = (o: any): Order => ({
  id: o.id,
  userId: o.user_id,
  user: o.user,
  status: o.status as OrderStatus,
  notes: o.notes,
  totalCents: o.total_cents,
  items: o.items.map((item: any) => ({
    id: item.id,
    productId: item.product_id,
    quantity: item.quantity,
    priceCentsAtPurchase: item.price_cents_at_purchase,
    product: item.product ? mapProduct(item.product) : undefined,
  })),
  approvedBy: o.approved_by,
  approvedAt: o.approved_at,
  rejectionReason: o.rejection_reason,
  createdAt: o.created_at,
  updatedAt: o.updated_at,
})

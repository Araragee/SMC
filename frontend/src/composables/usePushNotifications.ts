import { ref } from 'vue'
import axios from 'axios'
import { API_URL } from '@typescript/constants'
import { useAuthStore } from '@stores/auth'

const SW_PATH = '/push-sw.js'

interface PushSubscriptionPayload {
  endpoint: string
  keys_p256dh: string
  keys_auth: string
  user_agent: string | null
}

function urlBase64ToBuffer(base64String: string): ArrayBuffer {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = window.atob(base64)
  const buf = new ArrayBuffer(raw.length)
  const view = new Uint8Array(buf)
  for (let i = 0; i < raw.length; ++i) view[i] = raw.charCodeAt(i)
  return buf
}

function pkToPayload(sub: PushSubscription): PushSubscriptionPayload {
  const json = sub.toJSON() as { endpoint?: string; keys?: { p256dh?: string; auth?: string } }
  return {
    endpoint: json.endpoint || sub.endpoint,
    keys_p256dh: json.keys?.p256dh || '',
    keys_auth: json.keys?.auth || '',
    user_agent: navigator.userAgent,
  }
}

export function usePushNotifications() {
  const isSupported = 'serviceWorker' in navigator && 'PushManager' in window
  const permission = ref<NotificationPermission>(
    isSupported ? Notification.permission : 'denied'
  )
  const subscribed = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const fetchPublicKey = async (): Promise<string> => {
    const auth = useAuthStore()
    const res = await axios.get(`${API_URL}/push/public-key`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    return res.data.key
  }

  const checkSubscribed = async () => {
    if (!isSupported) return
    const reg = await navigator.serviceWorker.getRegistration(SW_PATH)
    if (!reg) return
    const sub = await reg.pushManager.getSubscription()
    subscribed.value = !!sub
  }

  const subscribe = async (): Promise<boolean> => {
    if (!isSupported) {
      error.value = 'Push not supported in this browser'
      return false
    }
    loading.value = true
    error.value = null
    try {
      const perm = await Notification.requestPermission()
      permission.value = perm
      if (perm !== 'granted') {
        error.value = 'Permission denied'
        return false
      }
      const reg =
        (await navigator.serviceWorker.getRegistration(SW_PATH)) ||
        (await navigator.serviceWorker.register(SW_PATH))
      const pubKey = await fetchPublicKey()
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToBuffer(pubKey),
      })
      const auth = useAuthStore()
      await axios.post(`${API_URL}/push/subscribe`, pkToPayload(sub), {
        headers: { Authorization: `Bearer ${auth.token}` },
      })
      subscribed.value = true
      return true
    } catch (e: unknown) {
      const msg = (e as { message?: string })?.message || 'Subscribe failed'
      error.value = msg
      return false
    } finally {
      loading.value = false
    }
  }

  const unsubscribe = async (): Promise<boolean> => {
    if (!isSupported) return false
    loading.value = true
    try {
      const reg = await navigator.serviceWorker.getRegistration(SW_PATH)
      const sub = await reg?.pushManager.getSubscription()
      if (sub) {
        const auth = useAuthStore()
        await axios.post(`${API_URL}/push/unsubscribe`, pkToPayload(sub), {
          headers: { Authorization: `Bearer ${auth.token}` },
        }).catch(() => {})
        await sub.unsubscribe()
      }
      subscribed.value = false
      return true
    } finally {
      loading.value = false
    }
  }

  return { isSupported, permission, subscribed, loading, error, subscribe, unsubscribe, checkSubscribed }
}

import { defineStore } from 'pinia'
import axios from 'axios'
import { useAuthStore } from './auth'
import type { Conversation, ChatMessage } from '../types'

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const WS_URL  = (import.meta.env.VITE_WS_BASE_URL  || 'ws://localhost:8000')

const authHeaders = function() {
  const auth = useAuthStore()
  return auth.token ? { Authorization: `Bearer ${auth.token}` } : {}
}

const mapMessage = function(raw: any): ChatMessage  {
  return {
    id:             String(raw.id),
    conversationId: String(raw.conversation_id),
    senderId:       String(raw.sender_id),
    senderName:     raw.sender_name ?? null,
    body:           raw.body,
    createdAt:      raw.created_at,
    isDeleted:      raw.is_deleted ?? false,
  }
}

const mapParticipant = function(raw: any) {
  return {
    userId:     String(raw.user_id),
    joinedAt:   raw.joined_at,
    lastReadAt: raw.last_read_at ?? null,
    name:       raw.name ?? null,
  }
}

const mapConversation = function(raw: any): Conversation  {
  return {
    id:           String(raw.id),
    type:         raw.type,
    name:         raw.name ?? null,
    createdAt:    raw.created_at,
    participants: (raw.participants ?? []).map(mapParticipant),
    lastMessage:  raw.last_message ? mapMessage(raw.last_message) : null,
    unreadCount:  raw.unread_count ?? 0,
  }
}

interface MessagingState {
  conversations:        Conversation[]
  activeConversationId: string | null
  isOpen:               boolean
  messages:             Record<string, ChatMessage[]>
  unreadCounts:         Record<string, number>
  typingUsers:          Record<string, string[]>
  wsStatus:             'connecting' | 'connected' | 'disconnected'
  _ws:                  WebSocket | null
  _typingTimers:        Record<string, ReturnType<typeof setTimeout>>
  _reconnectTimer:      ReturnType<typeof setTimeout> | null
}

export const useMessagingStore = defineStore('messaging', {
  state: (): MessagingState => ({
    conversations:        [],
    activeConversationId: null,
    isOpen:               false,
    messages:             {},
    unreadCounts:         {},
    typingUsers:          {},
    wsStatus:             'disconnected',
    _ws:                  null,
    _typingTimers:        {},
    _reconnectTimer:      null,
  }),

  getters: {
    totalUnread: (state): number =>
      Object.values(state.unreadCounts).reduce((s, n) => s + n, 0),

    sortedConversations: (state): Conversation[] =>
      [...state.conversations].sort((a, b) => {
        const ta = a.lastMessage?.createdAt ?? a.createdAt
        const tb = b.lastMessage?.createdAt ?? b.createdAt
        return new Date(tb).getTime() - new Date(ta).getTime()
      }),

    activeConversation(state): Conversation | null {
      return state.conversations.find(c => c.id === state.activeConversationId) ?? null
    },
  },

  actions: {
    // ── WebSocket ──────────────────────────────────────────────────────────────

    connectWS() {
      const auth = useAuthStore()
      if (!auth.token || !auth.currentUser) return
      if (this._ws && this._ws.readyState === WebSocket.OPEN) return

      this.wsStatus = 'connecting'
      const userId = auth.currentUser.id
      const ws = new WebSocket(`${WS_URL}/ws/${userId}?token=${auth.token}`)
      this._ws = ws

      ws.onopen = () => {
        this.wsStatus = 'connected'
        this.fetchConversations()
      }

      ws.onmessage = (e) => this._handleIncoming(e)

      ws.onclose = () => {
        this.wsStatus = 'disconnected'
        this._ws = null
        if (this._reconnectTimer) clearTimeout(this._reconnectTimer)
        this._reconnectTimer = setTimeout(() => this.connectWS(), 3000)
      }

      ws.onerror = () => ws.close()
    },

    disconnectWS() {
      if (this._reconnectTimer) {
        clearTimeout(this._reconnectTimer)
        this._reconnectTimer = null
      }
      if (this._ws) {
        this._ws.onclose = null // prevent reconnect loop
        this._ws.close()
        this._ws = null
      }
      this.wsStatus = 'disconnected'
    },

    _handleIncoming(event: MessageEvent) {
      let data: any
      try { data = JSON.parse(event.data) } catch { return }

      if (data.type === 'new_message') {
        const msg = mapMessage(data.message)
        const cid = msg.conversationId
        if (!this.messages[cid]) this.messages[cid] = []
        if (!this.messages[cid].find(m => m.id === msg.id)) {
          this.messages[cid].push(msg)
        }
        const conv = this.conversations.find(c => c.id === cid)
        if (conv) conv.lastMessage = msg

      } else if (data.type === 'unread_update') {
        const cid = String(data.conversation_id)
        this.unreadCounts[cid] = data.count
        const conv = this.conversations.find(c => c.id === cid)
        if (conv) conv.unreadCount = data.count

      } else if (data.type === 'typing') {
        const cid = String(data.conversation_id)
        const uid = String(data.user_id)
        if (!this.typingUsers[cid]) this.typingUsers[cid] = []
        if (!this.typingUsers[cid].includes(uid)) this.typingUsers[cid].push(uid)
        const key = `${cid}:${uid}`
        clearTimeout(this._typingTimers[key])
        this._typingTimers[key] = setTimeout(() => {
          const arr = this.typingUsers[cid]
          if (arr) {
            const idx = arr.indexOf(uid)
            if (idx > -1) arr.splice(idx, 1)
          }
        }, 3000)
      }
    },

    // ── REST ───────────────────────────────────────────────────────────────────

    async fetchConversations() {
      const res = await axios.get(`${API_URL}/conversations`, { headers: authHeaders() })
      this.conversations = res.data.map(mapConversation)
      for (const c of this.conversations) {
        this.unreadCounts[c.id] = c.unreadCount
      }
    },

    async fetchMessages(conversationId: string, cursor?: string) {
      const params: any = { limit: 50 }
      if (cursor) params.cursor = cursor
      const res = await axios.get(`${API_URL}/conversations/${conversationId}/messages`, {
        headers: authHeaders(), params,
      })
      const msgs: ChatMessage[] = res.data.messages.map(mapMessage)
      if (!this.messages[conversationId]) {
        this.messages[conversationId] = msgs
      } else if (cursor) {
        // Prepend older messages
        this.messages[conversationId] = [...msgs, ...this.messages[conversationId]]
      }
      return res.data.next_cursor as string | null
    },

    // ── Send / Mark Read / Typing ──────────────────────────────────────────────

    sendMessage(conversationId: string, body: string) {
      const trimmed = body.trim()
      if (!trimmed) return
      if (this._ws?.readyState === WebSocket.OPEN) {
        this._ws.send(JSON.stringify({
          type: 'send_message',
          conversation_id: Number(conversationId),
          body: trimmed,
        }))
      } else {
        // REST fallback (no WebSocket)
        axios.post(
          `${API_URL}/conversations/${conversationId}/messages`,
          { body: trimmed },
          { headers: authHeaders() }
        ).then(r => {
          const msg = mapMessage(r.data)
          if (!this.messages[conversationId]) this.messages[conversationId] = []
          this.messages[conversationId].push(msg)
          const conv = this.conversations.find(c => c.id === conversationId)
          if (conv) conv.lastMessage = msg
        }).catch(() => {})
      }
    },

    markRead(conversationId: string) {
      if (this._ws?.readyState === WebSocket.OPEN) {
        this._ws.send(JSON.stringify({
          type: 'mark_read',
          conversation_id: Number(conversationId),
        }))
      } else {
        axios.patch(
          `${API_URL}/conversations/${conversationId}/read`,
          {}, { headers: authHeaders() }
        ).then(() => {
          this.unreadCounts[conversationId] = 0
          const conv = this.conversations.find(c => c.id === conversationId)
          if (conv) conv.unreadCount = 0
        }).catch(() => {})
      }
    },

    sendTyping(conversationId: string) {
      if (this._ws?.readyState === WebSocket.OPEN) {
        this._ws.send(JSON.stringify({
          type: 'typing',
          conversation_id: Number(conversationId),
        }))
      }
    },

    // ── Conversation creation ──────────────────────────────────────────────────

    async startDM(userId: string): Promise<string> {
      const res = await axios.post(
        `${API_URL}/conversations/dm`,
        { other_user_id: Number(userId) },
        { headers: authHeaders() }
      )
      const conv = mapConversation(res.data)
      const existing = this.conversations.findIndex(c => c.id === conv.id)
      if (existing >= 0) this.conversations[existing] = conv
      else this.conversations.unshift(conv)
      this.unreadCounts[conv.id] = conv.unreadCount
      return conv.id
    },

    async createGroup(name: string, participantIds: string[]): Promise<string> {
      const res = await axios.post(
        `${API_URL}/conversations/group`,
        { name, participant_ids: participantIds.map(Number) },
        { headers: authHeaders() }
      )
      const conv = mapConversation(res.data)
      this.conversations.unshift(conv)
      this.unreadCounts[conv.id] = 0
      return conv.id
    },

    async getOrCreateSessionThread(sessionId: string): Promise<string> {
      const res = await axios.get(
        `${API_URL}/sessions/${sessionId}/thread`,
        { headers: authHeaders() }
      )
      const conv = mapConversation(res.data)
      const existing = this.conversations.findIndex(c => c.id === conv.id)
      if (existing >= 0) this.conversations[existing] = conv
      else this.conversations.unshift(conv)
      this.unreadCounts[conv.id] = conv.unreadCount
      return conv.id
    },

    // ── Panel helpers ──────────────────────────────────────────────────────────

    openConversation(conversationId: string) {
      this.activeConversationId = conversationId
      this.isOpen = true
    },

    closePanel() {
      this.isOpen = false
      this.activeConversationId = null
    },
  },
})

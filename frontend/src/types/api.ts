/**
 * API response shapes — mirror backend Pydantic schemas in `backend/schemas.py`.
 *
 * These describe the *raw* JSON the backend returns (snake_case fields).
 * Frontend stores then map these into the camelCase domain types defined in
 * `./index.ts`. Keep these in sync with the corresponding Pydantic models.
 */

import type { Role, SessionStatus, ConversationType, OrderStatus } from './index'

// ── Role / Instrument ─────────────────────────────────────────────────────────

/** Backend `Role` schema. */
export interface RoleResponse {
  id: number
  name: string
}

/** Backend `Instrument` schema. */
export interface InstrumentResponse {
  id: number
  name: string
}

// ── Auth ──────────────────────────────────────────────────────────────────────

/** Raw user payload returned by `/login`, `/users/me`, `/users/{id}`. */
export interface UserResponse {
  id: number
  email: string
  name: string
  role_id: number
  is_active: boolean
  role?: RoleResponse | null
  instruments?: InstrumentResponse[]
  avatar_url?: string | null
  sessions_left?: number | null
  username?: string | null
  contact_number?: string | null
  home_address?: string | null
  birthday?: string | null
  age?: number | null
  school?: string | null
  parent_name?: string | null
  parent_contact?: string | null
  sessions_enrolled?: number | null
  totp_enabled?: boolean
}

/** Backend `Role` enum (mirrors `Role` union in domain types). */
export type UserRole = Role

/** Response from `POST /login`. */
export interface LoginResponse {
  access_token: string
  /** Optional — present on register/auto-login flows. */
  refresh_token?: string
  token_type?: string
  user: UserResponse
}

// ── Session ───────────────────────────────────────────────────────────────────

/** Backend `SessionProof` schema. */
export interface SessionProofResponse {
  id: number
  session_id: number
  image_url: string
  uploaded_at: string
  uploader_id?: number | null
  uploader_role?: string | null
}

/** Backend `Homework` schema. */
export interface HomeworkResponse {
  id: number
  session_id: number
  description: string
  is_completed: boolean
  file_url?: string | null
  created_at: string
}

/** Backend `Session` schema (full, with relations). */
export interface SessionResponse {
  id: number
  teacher_id: number
  student_id: number
  start_time: string
  end_time: string
  status: SessionStatus
  proposed_by?: number | null
  notes?: string | null
  instrument_id?: number | null
  is_manual_entry: boolean
  session_number?: number | null
  notified_24h: boolean
  notified_12h: boolean
  proof_justification?: string | null
  rejection_reason?: string | null
  is_force_completed: boolean
  version: number
  proof_image_url?: string | null
  homework_assigned?: string | null
  homework_completed: boolean
  instrument?: InstrumentResponse | null
  proofs?: SessionProofResponse[]
  homeworks?: HomeworkResponse[]
}

// ── Messaging ─────────────────────────────────────────────────────────────────

/** Backend `MessageOut`. */
export interface MessageResponse {
  id: number
  conversation_id: number
  sender_id: number
  body: string
  created_at: string
  is_deleted: boolean
  sender_name?: string | null
}

/** Backend `ParticipantOut`. */
export interface ParticipantResponse {
  user_id: number
  joined_at: string
  last_read_at?: string | null
  name?: string | null
}

/** Backend `ConversationOut`. */
export interface ConversationResponse {
  id: number
  type: ConversationType | string
  name?: string | null
  created_at: string
  participants?: ParticipantResponse[]
  last_message?: MessageResponse | null
  unread_count: number
}

/** Paginated cursor response from `GET /conversations/{id}/messages`. */
export interface MessageCursorPageResponse {
  messages: MessageResponse[]
  next_cursor: string | number | null
}

/**
 * Discriminated union of incoming WebSocket events.
 * Backend sends these via the `/ws/{user_id}` channel.
 */
export type WSIncomingEvent =
  | { type: 'new_message'; message: MessageResponse }
  | { type: 'unread_update'; conversation_id: number; count: number }
  | { type: 'typing'; conversation_id: number; user_id: number }

// ── Payment ───────────────────────────────────────────────────────────────────

export type PaymentMethod = 'cash' | 'bank_transfer' | 'card' | 'gcash' | 'maya'
export type PaymentStatus = 'pending' | 'completed' | 'refunded' | 'cancelled'

/** Backend `Payment` schema. */
export interface PaymentResponse {
  id: number
  student_id: number
  student_name?: string | null
  amount: number
  date: string
  method: PaymentMethod | string
  status: PaymentStatus | string
  notes?: string | null
}

// ── Notification / Activity Log ───────────────────────────────────────────────

/** Backend `Notification` schema. */
export interface NotificationResponse {
  id: number
  user_id: number | null
  message: string
  is_read: boolean
  link?: string | null
  created_at: string
}

/** Backend `ActivityLogEntry`. */
export interface ActivityLogResponse {
  id: number
  action_type: string
  actor_id?: number | null
  actor_name?: string | null
  target_type?: string | null
  target_id?: number | null
  description: string
  created_at: string
}

// ── Enrollment ───────────────────────────────────────────────────────────────

/** Backend `Enrollment` schema. */
export interface EnrollmentResponse {
  id: number
  student_id: number
  teacher_id: number
  sessions_purchased: number
  sessions_used: number
  sessions_left: number
  status?: 'pending' | 'active' | 'rejected'
  created_at: string
}

// ── Shop ──────────────────────────────────────────────────────────────────────

/** Backend `InstrumentProduct` schema. */
export interface InstrumentProductResponse {
  id: number
  name: string
  description?: string | null
  price_cents: number
  stock: number
  image_url?: string | null
  category_id?: number | null
  category?: InstrumentResponse | null
  is_active: boolean
  created_at: string
  updated_at: string
}

/** Backend `OrderItem` schema. */
export interface OrderItemResponse {
  id: number
  product_id: number
  quantity: number
  price_cents_at_purchase: number
  product?: InstrumentProductResponse | null
}

/** Backend `Order` schema. */
export interface OrderResponse {
  id: number
  user_id: number
  user?: UserResponse | null
  status: OrderStatus | string
  notes?: string | null
  total_cents: number
  items: OrderItemResponse[]
  approved_by?: number | null
  approved_at?: string | null
  rejection_reason?: string | null
  created_at: string
  updated_at: string
}

// ── Generic API helpers ───────────────────────────────────────────────────────

/** Shape of `error.response.data` for axios errors (FastAPI default). */
export interface ApiErrorDetail {
  detail?: string | { msg: string; loc?: (string | number)[] }[]
}

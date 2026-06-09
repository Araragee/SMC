export type Role = 'admin' | 'teacher' | 'student';

export type SessionStatus =
  | 'scheduled'
  | 'completed'
  | 'cancelled'
  | 'pending_teacher'
  | 'pending_student'
  | 'pending_admin'
  | 'rejected'
  | 'overdue'
  | 'pending_verification'
  | 'overdue_rejected';

export interface InstrumentRecord {
  id: number;
  name: string;
}

export interface UserInstrument {
  userId: number;
  instrumentId: number;
}

export interface TeacherStudent {
  id: number;
  teacherId: number;
  studentId: number;
  assignedAt: string;
}

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  avatarUrl?: string;
  username?: string;
  contactNumber?: string;
  homeAddress?: string;
  instruments?: InstrumentRecord[];
  totpEnabled?: boolean;
  /** Phase 2: when true, router gate forces the user to /change-password
   *  before they can navigate to any role dashboard. */
  mustChangePassword?: boolean;

  // Specific to students
  sessionsLeft?: number;
  birthday?: string;
  age?: number;
  school?: string;
  parentName?: string;
  parentContact?: string;
  sessionsEnrolled?: number;
}

export interface SessionProof {
  id: number;
  sessionId: number;
  imageUrl: string;
  uploadedAt: string;
  uploaderId?: number;
  uploaderRole?: string;
}

export interface Homework {
  id: number;
  sessionId: number;
  description: string;
  isCompleted: boolean;
  fileUrl?: string;
  createdAt: string;
}

export interface Session {
  id: number;
  studentId: number;
  teacherId: number;
  startTime: string; // ISO 8601 format
  endTime: string; // ISO 8601 format
  status: SessionStatus;
  proposedBy?: number;
  notes?: string;
  imageProofUrl?: string; // Legacy/convenience
  proofs?: SessionProof[];
  homeworkAssigned?: string;
  homeworkCompleted?: boolean;
  instrumentId?: number;
  isManualEntry?: boolean;
  sessionNumber?: number;
  instrument?: InstrumentRecord;
  proofJustification?: string;
  rejectionReason?: string;
  isForceCompleted?: boolean;
  counterCount?: number;
  /** Optimistic-lock counter — pass back to write endpoints so the server can
   *  detect concurrent modifications and respond with HTTP 409. */
  version?: number;
}

export interface Schedule {
  id: number;
  userId: number;
  sessions: Session[];
}

export interface Notification {
  id: number;
  userId: number | null; // Or null for global notifications
  title: string;
  message: string;
  type: 'info' | 'warning' | 'success' | 'error';
  isRead: boolean;
  link?: string;
  createdAt: string; // ISO 8601 format
}

export interface Enrollment {
  id: number;
  studentId: number;
  teacherId: number;
  sessionsPurchased: number;
  sessionsUsed: number;
  sessionsLeft: number;
  createdAt: string;
}

// ── Messaging ─────────────────────────────────────────────────────────────────

export type ConversationType = 'dm' | 'group' | 'session_thread'

export interface ConversationParticipantInfo {
  userId:     number
  joinedAt:   string
  lastReadAt: string | null
  name:       string | null
}

export interface ChatMessage {
  id:             number
  conversationId: number
  senderId:       number
  senderName:     string | null
  body:           string
  createdAt:      string
  isDeleted:      boolean
}

export interface Conversation {
  id:           number
  type:         ConversationType
  name:         string | null
  createdAt:    string
  participants: ConversationParticipantInfo[]
  lastMessage:  ChatMessage | null
  unreadCount:  number
}

// ── Shop ──────────────────────────────────────────────────────────────────────

export interface InstrumentProduct {
  id: number
  name: string
  description?: string
  priceCents: number
  stock: number
  imageUrl?: string
  categoryId?: number
  category?: InstrumentRecord
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export type OrderStatus = 'pending' | 'approved' | 'fulfilled' | 'rejected' | 'cancelled'

export interface OrderItem {
  id: number
  productId: number
  quantity: number
  priceCentsAtPurchase: number
  product?: InstrumentProduct
}

export interface Order {
  id: number
  userId: number
  user?: User
  status: OrderStatus
  notes?: string
  totalCents: number
  items: OrderItem[]
  approvedBy?: number
  approvedAt?: string
  rejectionReason?: string
  createdAt: string
  updatedAt: string
}

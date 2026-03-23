export type Role = 'admin' | 'teacher' | 'student';

export type SessionStatus =
  | 'scheduled'
  | 'completed'
  | 'cancelled'
  | 'pending_teacher'
  | 'pending_admin'
  | 'rejected';

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatarUrl?: string;
  // Specific to students
  sessionsLeft?: number;
}

export interface Session {
  id: string;
  studentId: string;
  teacherId: string;
  startTime: string; // ISO 8601 format
  endTime: string; // ISO 8601 format
  status: SessionStatus;
  proposedBy?: string;
  notes?: string;
  imageProofUrl?: string;
  homeworkAssigned?: string;
  homeworkCompleted?: boolean;
}

export interface Schedule {
  id: string;
  userId: string;
  sessions: Session[];
}

export interface Notification {
  id: string;
  userId: string | null; // Or null for global notifications
  title: string;
  message: string;
  type: 'info' | 'warning' | 'success' | 'error';
  isRead: boolean;
  createdAt: string; // ISO 8601 format
}

export interface Enrollment {
  id: string;
  studentId: string;
  teacherId: string;
  sessionsPurchased: number;
  sessionsUsed: number;
  sessionsLeft: number;
  createdAt: string;
}

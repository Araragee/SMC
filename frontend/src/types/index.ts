export type Role = 'admin' | 'teacher' | 'student';

export type SessionStatus =
  | 'scheduled'
  | 'completed'
  | 'cancelled'
  | 'pending_teacher'
  | 'pending_student'
  | 'pending_admin'
  | 'rejected';

export interface InstrumentRecord {
  id: number;
  name: string;
}

export interface UserInstrument {
  userId: string | number;
  instrumentId: number;
}

export interface TeacherStudent {
  id: string | number;
  teacherId: string | number;
  studentId: string | number;
  assignedAt: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatarUrl?: string;
  username?: string;
  contactNumber?: string;
  homeAddress?: string;
  instruments?: InstrumentRecord[];

  // Specific to students
  sessionsLeft?: number;
  birthday?: string;
  age?: number;
  school?: string;
  parentName?: string;
  parentContact?: string;
  sessionsEnrolled?: number;
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
  instrumentId?: number;
  isManualEntry?: boolean;
  sessionNumber?: number;
  instrument?: InstrumentRecord;
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
  link?: string;
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

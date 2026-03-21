import type { User, Session, Schedule, Notification } from '../types';

export const mockUsers: User[] = [
  {
    id: 'admin-1',
    name: 'Alice Admin',
    email: 'admin@musicschool.com',
    role: 'admin',
    avatarUrl: 'https://i.pravatar.cc/150?u=admin',
  },
  {
    id: 'teacher-1',
    name: 'Trevor Teacher',
    email: 'trevor@musicschool.com',
    role: 'teacher',
    avatarUrl: 'https://i.pravatar.cc/150?u=teacher',
  },
  {
    id: 'student-1',
    name: 'Sam Student',
    email: 'sam@musicschool.com',
    role: 'student',
    avatarUrl: 'https://i.pravatar.cc/150?u=student',
    sessionsLeft: 5,
  },
];

export const mockSessions: Session[] = [
  {
    id: 'session-1',
    studentId: 'student-1',
    teacherId: 'teacher-1',
    startTime: '2023-10-25T10:00:00Z',
    endTime: '2023-10-25T11:00:00Z',
    status: 'scheduled',
    homeworkAssigned: 'Practice C major scale',
    homeworkCompleted: false,
  },
  {
    id: 'session-2',
    studentId: 'student-1',
    teacherId: 'teacher-1',
    startTime: '2023-10-20T10:00:00Z',
    endTime: '2023-10-20T11:00:00Z',
    status: 'completed',
    imageProofUrl: 'https://picsum.photos/400/300',
    homeworkAssigned: 'Review quarter notes',
    homeworkCompleted: true,
  },
];

export const mockSchedules: Schedule[] = [
  {
    id: 'schedule-student-1',
    userId: 'student-1',
    sessions: mockSessions.filter(s => s.studentId === 'student-1'),
  },
  {
    id: 'schedule-teacher-1',
    userId: 'teacher-1',
    sessions: mockSessions.filter(s => s.teacherId === 'teacher-1'),
  },
];

export const mockNotifications: Notification[] = [
  {
    id: 'notification-1',
    userId: 'student-1',
    title: 'Upcoming Session',
    message: 'You have a piano lesson with Trevor tomorrow at 10 AM.',
    type: 'info',
    isRead: false,
    createdAt: '2023-10-24T09:00:00Z',
  },
  {
    id: 'notification-2',
    userId: 'admin-1',
    title: 'New Student Enrollment',
    message: 'Sam Student has just enrolled for 5 sessions.',
    type: 'success',
    isRead: true,
    createdAt: '2023-10-15T14:30:00Z',
  },
];

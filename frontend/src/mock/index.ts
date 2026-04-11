import type { User, Session, Schedule, Notification } from '../types';

export const mockUsers: User[] = [
  {
    id: 1,
    name: 'Alice Admin',
    email: 'admin@musicschool.com',
    role: 'admin',
    avatarUrl: 'https://i.pravatar.cc/150?u=admin',
  },
  {
    id: 2,
    name: 'Trevor Teacher',
    email: 'trevor@musicschool.com',
    role: 'teacher',
    avatarUrl: 'https://i.pravatar.cc/150?u=teacher',
  },
  {
    id: 3,
    name: 'Sam Student',
    email: 'sam@musicschool.com',
    role: 'student',
    avatarUrl: 'https://i.pravatar.cc/150?u=student',
    sessionsLeft: 5,
  },
];

export const mockSessions: Session[] = [
  {
    id: 101,
    studentId: 3,
    teacherId: 2,
    startTime: '2023-10-25T10:00:00Z',
    endTime: '2023-10-25T11:00:00Z',
    status: 'scheduled',
    homeworkAssigned: 'Practice C major scale',
    homeworkCompleted: false,
  },
  {
    id: 102,
    studentId: 3,
    teacherId: 2,
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
    id: 201,
    userId: 3,
    sessions: mockSessions.filter(s => s.studentId === 3),
  },
  {
    id: 202,
    userId: 2,
    sessions: mockSessions.filter(s => s.teacherId === 2),
  },
];

export const mockNotifications: Notification[] = [
  {
    id: 301,
    userId: 3,
    title: 'Upcoming Session',
    message: 'You have a piano lesson with Trevor tomorrow at 10 AM.',
    type: 'info',
    isRead: false,
    createdAt: '2023-10-24T09:00:00Z',
  },
  {
    id: 302,
    userId: 1,
    title: 'New Student Enrollment',
    message: 'Sam Student has just enrolled for 5 sessions.',
    type: 'success',
    isRead: true,
    createdAt: '2023-10-15T14:30:00Z',
  },
];

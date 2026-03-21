import { defineStore } from 'pinia';
import { Session, Schedule } from '../types';
import { mockSchedules, mockSessions } from '../mock';

interface ScheduleState {
  schedules: Schedule[];
  allSessions: Session[];
  isLoading: boolean;
  error: string | null;
}

export const useScheduleStore = defineStore('schedule', {
  state: (): ScheduleState => ({
    schedules: [...mockSchedules],
    allSessions: [...mockSessions],
    isLoading: false,
    error: null,
  }),
  getters: {
    getScheduleByUserId: (state) => {
      return (userId: string) => state.schedules.find(s => s.userId === userId);
    },
    getSessionsByTeacherId: (state) => {
      return (teacherId: string) => state.allSessions.filter(s => s.teacherId === teacherId);
    },
    getSessionsByStudentId: (state) => {
      return (studentId: string) => state.allSessions.filter(s => s.studentId === studentId);
    },
  },
  actions: {
    async fetchSchedules() {
      this.isLoading = true;
      try {
        await new Promise(resolve => setTimeout(resolve, 500));
        // Reset to mock data as simulation
        this.schedules = [...mockSchedules];
        this.allSessions = [...mockSessions];
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch schedules';
      } finally {
        this.isLoading = false;
      }
    },

    async assignHomework(sessionId: string, homework: string) {
      this.isLoading = true;
      try {
        await new Promise(resolve => setTimeout(resolve, 300));
        const session = this.allSessions.find(s => s.id === sessionId);
        if (session) {
          session.homeworkAssigned = homework;
        }
      } catch (err: any) {
        this.error = err.message || 'Failed to assign homework';
      } finally {
        this.isLoading = false;
      }
    },

    async uploadImageProof(sessionId: string, imageUrl: string) {
        this.isLoading = true;
        try {
            await new Promise(resolve => setTimeout(resolve, 300));
            const session = this.allSessions.find(s => s.id === sessionId);
            if (session) {
                session.imageProofUrl = imageUrl;
            }
        } catch (err: any) {
            this.error = err.message || 'Failed to upload image proof';
        } finally {
            this.isLoading = false;
        }
    },

    async completeHomework(sessionId: string) {
        this.isLoading = true;
        try {
            await new Promise(resolve => setTimeout(resolve, 300));
            const session = this.allSessions.find(s => s.id === sessionId);
            if (session) {
                session.homeworkCompleted = true;
            }
        } catch (err: any) {
            this.error = err.message || 'Failed to complete homework';
        } finally {
            this.isLoading = false;
        }
    },

    async bookSession(sessionData: Omit<Session, 'id' | 'status'>) {
        this.isLoading = true;
        try {
            await new Promise(resolve => setTimeout(resolve, 400));
            const newSession: Session = {
                ...sessionData,
                id: `session-${Date.now()}`,
                status: 'scheduled'
            };
            this.allSessions.push(newSession);

            // Also update the schedule for the user
            const studentSchedule = this.schedules.find(s => s.userId === sessionData.studentId);
            if (studentSchedule) {
                studentSchedule.sessions.push(newSession);
            } else {
                this.schedules.push({
                    id: `schedule-${sessionData.studentId}`,
                    userId: sessionData.studentId,
                    sessions: [newSession]
                });
            }
        } catch (err: any) {
            this.error = err.message || 'Failed to book session';
        } finally {
            this.isLoading = false;
        }
    }
  },
});

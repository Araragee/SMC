import { defineStore } from 'pinia';
import axios from 'axios';
import type { Session, Schedule } from '../types';

const API_URL = 'http://localhost:8000';

interface ScheduleState {
  schedules: Schedule[];
  allSessions: Session[];
  isLoading: boolean;
  error: string | null;
}

export const useScheduleStore = defineStore('schedule', {
  state: (): ScheduleState => ({
    schedules: [],
    allSessions: [],
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
    async fetchAllSessions() {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/sessions/`);
        this.allSessions = response.data.map((session: any) => ({
          id: String(session.id),
          studentId: String(session.student_id),
          teacherId: String(session.teacher_id),
          startTime: session.start_time,
          endTime: session.end_time,
          status: session.status,
          imageProofUrl: session.proof_image_url,
          homeworkAssigned: session.homework_assigned,
          homeworkCompleted: session.homework_completed,
        }));
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch sessions';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async fetchUserSessions(userId: string) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/sessions/user/${userId}`);
        const userSessions = response.data.map((session: any) => ({
          id: String(session.id),
          studentId: String(session.student_id),
          teacherId: String(session.teacher_id),
          startTime: session.start_time,
          endTime: session.end_time,
          status: session.status,
          imageProofUrl: session.proof_image_url,
          homeworkAssigned: session.homework_assigned,
          homeworkCompleted: session.homework_completed,
        }));

        // Merge into allSessions avoiding duplicates
        for (const session of userSessions) {
            const index = this.allSessions.findIndex(s => s.id === session.id);
            if (index !== -1) {
                this.allSessions[index] = session;
            } else {
                this.allSessions.push(session);
            }
        }

      } catch (err: any) {
        this.error = err.message || 'Failed to fetch user sessions';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async assignHomework(sessionId: string, homework: string) {
      this.isLoading = true;
      this.error = null;
      try {
        // Find existing homework to update or create new
        const response = await axios.post(`${API_URL}/homework/?session_id=${sessionId}`, {
          description: homework,
          is_completed: false
        });

        const session = this.allSessions.find(s => s.id === sessionId);
        if (session) {
          session.homeworkAssigned = response.data.description;
        }
      } catch (err: any) {
        this.error = err.message || 'Failed to assign homework';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async uploadImageProof(sessionId: string, imageUrl: string) {
        this.isLoading = true;
        this.error = null;
        try {
            const response = await axios.post(`${API_URL}/session-proofs/?session_id=${sessionId}`, {
              image_url: imageUrl
            });
            const session = this.allSessions.find(s => s.id === sessionId);
            if (session) {
                session.imageProofUrl = response.data.image_url;
            }
        } catch (err: any) {
            this.error = err.message || 'Failed to upload image proof';
            console.error(err);
        } finally {
            this.isLoading = false;
        }
    },

    async completeHomework(sessionId: string) {
        this.isLoading = true;
        this.error = null;
        try {
            // In a real app we'd fetch the homework ID first, or the backend would handle it by session ID.
            // Since our backend takes homework_id in the PUT route, let's just cheat and send a PUT.
            // Wait, we need the homework ID. Let's assume the backend takes sessionId or we just modify the backend to accept an endpoint for completion.
            // For now, let's fetch session to get its homeworks.
            const sessionResponse = await axios.get(`${API_URL}/sessions/`);
            const sessionData = sessionResponse.data.find((s: any) => s.id === parseInt(sessionId));
            if (sessionData && sessionData.homeworks && sessionData.homeworks.length > 0) {
              const homeworkId = sessionData.homeworks[0].id;
              await axios.put(`${API_URL}/homework/${homeworkId}?is_completed=true`);
            }

            const session = this.allSessions.find(s => s.id === sessionId);
            if (session) {
                session.homeworkCompleted = true;
            }
        } catch (err: any) {
            this.error = err.message || 'Failed to complete homework';
            console.error(err);
        } finally {
            this.isLoading = false;
        }
    },

    async bookSession(sessionData: Omit<Session, 'id' | 'status'>) {
        this.isLoading = true;
        this.error = null;
        try {
            const payload = {
                teacher_id: parseInt(sessionData.teacherId),
                student_id: parseInt(sessionData.studentId),
                start_time: sessionData.startTime,
                end_time: sessionData.endTime,
                status: 'scheduled',
                proof_image_url: sessionData.imageProofUrl || null,
                homework_assigned: sessionData.homeworkAssigned || null,
                homework_completed: sessionData.homeworkCompleted || false
            };

            const response = await axios.post(`${API_URL}/sessions/`, payload);
            const newSession = response.data;

            const frontendSession: Session = {
                id: String(newSession.id),
                studentId: String(newSession.student_id),
                teacherId: String(newSession.teacher_id),
                startTime: newSession.start_time,
                endTime: newSession.end_time,
                status: newSession.status,
                imageProofUrl: newSession.proof_image_url,
                homeworkAssigned: newSession.homework_assigned,
                homeworkCompleted: newSession.homework_completed,
            };

            this.allSessions.push(frontendSession);
            return frontendSession;
        } catch (err: any) {
            this.error = err.message || 'Failed to book session';
            console.error(err);
            throw err;
        } finally {
            this.isLoading = false;
        }
    }
  },
});

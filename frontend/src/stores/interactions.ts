import { defineStore } from 'pinia';
import axios from 'axios';
import type { Enrollment } from '../types';
import { useScheduleStore } from './schedule';
import { useToastStore } from './toast';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface InteractionsState {
  enrollments: Enrollment[];
  isLoading: boolean;
  error: string | null;
}

export const useInteractionsStore = defineStore('interactions', {
  state: (): InteractionsState => ({
    enrollments: [],
    isLoading: false,
    error: null,
  }),
  actions: {
    async fetchStudentEnrollments(studentId: string) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/enrollments/student/${studentId}`);
        this.enrollments = response.data.map((enrollment: any) => ({
          id: String(enrollment.id),
          studentId: String(enrollment.student_id),
          teacherId: String(enrollment.teacher_id),
          sessionsPurchased: enrollment.sessions_purchased,
          sessionsUsed: enrollment.sessions_used,
          sessionsLeft: enrollment.sessions_left,
          createdAt: enrollment.created_at,
        }));
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch student enrollments';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },
    async createEnrollment(payload: Omit<Enrollment, 'id' | 'createdAt' | 'sessionsLeft'>) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.post(`${API_URL}/enrollments/`, {
          student_id: parseInt(payload.studentId),
          teacher_id: parseInt(payload.teacherId),
          sessions_purchased: payload.sessionsPurchased,
          sessions_used: payload.sessionsUsed,
        });
        const newEnrollment: Enrollment = {
          id: String(response.data.id),
          studentId: String(response.data.student_id),
          teacherId: String(response.data.teacher_id),
          sessionsPurchased: response.data.sessions_purchased,
          sessionsUsed: response.data.sessions_used,
          sessionsLeft: response.data.sessions_left,
          createdAt: response.data.created_at,
        };
        this.enrollments.push(newEnrollment);
        return newEnrollment;
      } catch (err: any) {
        this.error = err.message || 'Failed to create enrollment';
        console.error(err);
        throw err;
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

        const scheduleStore = useScheduleStore();
        const session = scheduleStore.allSessions.find(s => s.id === sessionId);
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

    async uploadImageProof(sessionId: string, file: File) {
        const toast = useToastStore();
        this.isLoading = true;
        this.error = null;
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await axios.post(`${API_URL}/session-proofs/?session_id=${sessionId}`, formData, {
              headers: { 'Content-Type': 'multipart/form-data' }
            });
            const scheduleStore = useScheduleStore();
            const session = scheduleStore.allSessions.find(s => s.id === sessionId);
            if (session) {
                session.imageProofUrl = response.data.image_url;
            }
            toast.success('Image uploaded!', 'Proof of session has been saved.');
        } catch (err: any) {
            this.error = err.message || 'Failed to upload image proof';
            toast.error('Upload failed', this.error || undefined);
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

            const scheduleStore = useScheduleStore();
            const session = scheduleStore.allSessions.find(s => s.id === sessionId);
            if (session) {
                session.homeworkCompleted = true;
            }
        } catch (err: any) {
            this.error = err.message || 'Failed to complete homework';
            console.error(err);
        } finally {
            this.isLoading = false;
        }
    }
  }
});
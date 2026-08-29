import { defineStore } from 'pinia';
import axios from 'axios';
import type { Enrollment } from '@types';
import { useScheduleStore } from '@stores/schedule';
import { useToastStore } from '@stores/toast';
import { useAuthStore } from '@stores/auth';
import { API_URL } from '@typescript/constants';

const authHeaders = function() {
  const auth = useAuthStore();
  return auth.token ? { Authorization: `Bearer ${auth.token}` } : {};
};

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
    async fetchStudentEnrollments(studentId: number) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/enrollments/student/${studentId}`, { headers: authHeaders() });
        this.enrollments = response.data.map((enrollment: any) => ({
          id: Number(enrollment.id),
          studentId: Number(enrollment.student_id),
          teacherId: Number(enrollment.teacher_id),
          sessionsPurchased: enrollment.sessions_purchased,
          sessionsUsed: enrollment.sessions_used,
          sessionsLeft: enrollment.sessions_left,
          createdAt: enrollment.created_at,
        }));
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch student enrollments';
        useToastStore().error('Load failed', this.error ?? undefined);
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
          student_id: Number(payload.studentId),
          teacher_id: Number(payload.teacherId),
          sessions_purchased: payload.sessionsPurchased,
          sessions_used: payload.sessionsUsed,
        }, { headers: authHeaders() });

        const newEnrollment: Enrollment = {
          id: Number(response.data.id),
          studentId: Number(response.data.student_id),
          teacherId: Number(response.data.teacher_id),
          sessionsPurchased: response.data.sessions_purchased,
          sessionsUsed: response.data.sessions_used,
          sessionsLeft: response.data.sessions_left,
          createdAt: response.data.created_at,
        };
        this.enrollments.push(newEnrollment);
        return newEnrollment;
      } catch (err: any) {
        this.error = err.message || 'Failed to create enrollment';
        useToastStore().error('Enrollment failed', this.error ?? undefined);
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async assignHomework(sessionId: number, homework: string) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.post(`${API_URL}/homework/?session_id=${sessionId}`, {
          description: homework,
          is_completed: false
        }, { headers: authHeaders() });

        const scheduleStore = useScheduleStore();
        const session = scheduleStore.allSessions.find(s => s.id === sessionId);
        if (session) {
          session.homeworkAssigned = response.data.description;
        }
      } catch (err: any) {
        this.error = err.message || 'Failed to assign homework';
        useToastStore().error('Homework failed', this.error ?? undefined);
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async uploadImageProof(sessionId: number, file: File) {
      this.isLoading = true;
      this.error = null;
      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await axios.post(`${API_URL}/session-proofs/?session_id=${sessionId}`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
            ...authHeaders()
          }
        });

        const scheduleStore = useScheduleStore();
        const auth = useAuthStore();
        const session = scheduleStore.allSessions.find(s => s.id === sessionId);
        if (session) {
          session.imageProofUrl = response.data.image_url;
          if (!session.proofs) session.proofs = [];
          
          const newProof = {
            id: Number(response.data.id),
            sessionId: sessionId,
            imageUrl: response.data.image_url,
            uploadedAt: response.data.uploaded_at,
            uploaderId: response.data.uploader_id ? Number(response.data.uploader_id) : auth.currentUser?.id,
            uploaderRole: response.data.uploader_role || auth.userRole || 'student',
          };

          session.proofs = session.proofs.filter(p => p.uploaderRole !== newProof.uploaderRole);
          session.proofs.push(newProof);
        }
        return response.data;
      } catch (err: any) {
        const toast = useToastStore();
        this.error = err.message || 'Failed to upload image proof';
        toast.error('Upload failed', this.error || undefined);
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async deleteEnrollment(enrollmentId: number) {
      this.isLoading = true;
      this.error = null;
      const toast = useToastStore();
      try {
        await axios.delete(`${API_URL}/enrollments/${enrollmentId}`, { headers: authHeaders() });
        this.enrollments = this.enrollments.filter(e => e.id !== enrollmentId);
        toast.success('Enrollment removed', 'The enrollment has been deleted and unused sessions rolled back.');
      } catch (err: any) {
        this.error = err.message || 'Failed to delete enrollment';
        toast.error('Delete failed', this.error || undefined);
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async recalculateSessions(studentId: number): Promise<{ old: number; new: number } | null> {
      this.isLoading = true;
      this.error = null;
      const toast = useToastStore();
      try {
        const response = await axios.post(
          `${API_URL}/students/${studentId}/recalculate-sessions`,
          {},
          { headers: authHeaders() }
        );
        const { old_sessions_left, new_sessions_left } = response.data;
        toast.success(
          'Sessions recalculated',
          `sessions_left updated: ${old_sessions_left} → ${new_sessions_left}`
        );
        return { old: old_sessions_left, new: new_sessions_left };
      } catch (err: any) {
        this.error = err.message || 'Failed to recalculate sessions';
        toast.error('Recalculate failed', this.error || undefined);
        console.error(err);
        return null;
      } finally {
        this.isLoading = false;
      }
    },

    async completeHomework(sessionId: number) {
      this.isLoading = true;
      this.error = null;
      try {
        const sessionResponse = await axios.get(`${API_URL}/sessions/`, { headers: authHeaders() });
        const sessionData = sessionResponse.data.find((s: any) => s.id === Number(sessionId));
        
        if (sessionData && sessionData.homeworks && sessionData.homeworks.length > 0) {
          const homeworkId = sessionData.homeworks[0].id;
          await axios.put(`${API_URL}/homework/${homeworkId}?is_completed=true`, {}, { headers: authHeaders() });
        }

        const scheduleStore = useScheduleStore();
        const session = scheduleStore.allSessions.find(s => s.id === sessionId);
        if (session) {
          session.homeworkCompleted = true;
        }
      } catch (err: any) {
        this.error = err.message || 'Failed to complete homework';
        useToastStore().error('Update failed', this.error ?? undefined);
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    /**
     * Upload the student's homework file. The backend marks the homework
     * completed as part of the same request, so this replaces — rather than
     * accompanies — a completeHomework call.
     */
    async uploadHomeworkFile(sessionId: number, file: File) {
      this.isLoading = true;
      this.error = null;
      try {
        const sessionResponse = await axios.get(`${API_URL}/sessions/`, { headers: authHeaders() });
        const sessionData = sessionResponse.data.find((s: any) => s.id === Number(sessionId));
        const homeworkId = sessionData?.homeworks?.[0]?.id;
        if (!homeworkId) throw new Error('No homework found for this session');

        const formData = new FormData();
        formData.append('file', file);
        const response = await axios.post(
          `${API_URL}/homework/${homeworkId}/upload`,
          formData,
          { headers: { 'Content-Type': 'multipart/form-data', ...authHeaders() } }
        );

        const scheduleStore = useScheduleStore();
        const session = scheduleStore.allSessions.find(s => s.id === sessionId);
        if (session) session.homeworkCompleted = true;
        return response.data;
      } catch (err: any) {
        this.error = err.response?.data?.detail || err.message || 'Failed to upload homework';
        useToastStore().error('Upload failed', this.error ?? undefined);
        throw err;
      } finally {
        this.isLoading = false;
      }
    }
  }
});
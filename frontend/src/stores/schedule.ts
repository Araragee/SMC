import { defineStore } from 'pinia';
import axios from 'axios';
import { useAuthStore } from '@stores/auth';
import type { Session, Schedule } from '@types';

import { API_URL } from '@typescript/constants'

const authHeaders = function() {
  const auth = useAuthStore();
  return auth.token ? { Authorization: `Bearer ${auth.token}` } : {};
}

const mapSession = function(session: any): Session  {
  return {
    id: Number(session.id),
    studentId: Number(session.student_id),
    teacherId: Number(session.teacher_id),
    startTime: session.start_time,
    endTime: session.end_time,
    status: session.status,
    proposedBy: session.proposed_by ? Number(session.proposed_by) : undefined,
    notes: session.notes || undefined,
    imageProofUrl: session.proof_image_url,
    proofs: session.proofs ? session.proofs.map((p: any) => ({
      id: Number(p.id),
      sessionId: Number(p.session_id),
      imageUrl: p.image_url,
      uploadedAt: p.uploaded_at,
      uploaderId: p.uploader_id ? Number(p.uploader_id) : undefined,
      uploaderRole: p.uploader_role,
    })) : [],
    homeworkAssigned: session.homework_assigned,
    homeworkCompleted: session.homework_completed,
    instrumentId: session.instrument_id,
    isManualEntry: session.is_manual_entry,
    sessionNumber: session.session_number,
    instrument: session.instrument,
    proofJustification: session.proof_justification || undefined,
    rejectionReason: session.rejection_reason || undefined,
    isForceCompleted: session.is_force_completed || false
  };
}

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
      return (userId: number) => state.schedules.find(s => s.userId === userId);
    },
    getSessionsByTeacherId: (state) => {
      return (teacherId: number) => state.allSessions.filter(s => s.teacherId === teacherId);
    },
    getSessionsByStudentId: (state) => {
      return (studentId: number) => state.allSessions.filter(s => s.studentId === studentId);
    },
    pendingSessions: (state): Session[] =>
      state.allSessions.filter(s => s.status === 'pending_teacher' || s.status === 'pending_admin'),
  },
  actions: {
    _upsertSession(session: Session) {
      const index = this.allSessions.findIndex(s => s.id === session.id);
      if (index !== -1) {
        this.allSessions[index] = session;
      } else {
        this.allSessions.push(session);
      }
    },

    async fetchAllSessions() {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/sessions/`, { headers: authHeaders() });
        this.allSessions = response.data.map(mapSession);
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch sessions';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async fetchUserSessions(userId: number) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/sessions/user/${userId}`, { headers: authHeaders() });
        for (const session of response.data.map(mapSession)) {
          this._upsertSession(session);
        }
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch user sessions';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async fetchPendingSessions() {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/sessions/pending`, { headers: authHeaders() });
        for (const session of response.data.map(mapSession)) {
          this._upsertSession(session);
        }
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch pending sessions';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    /** Admin creates a session directly → scheduled */
    async bookSession(sessionData: Omit<Session, 'id' | 'status'>) {
      this.isLoading = true;
      this.error = null;
      try {
        const payload = {
          teacher_id: Number(sessionData.teacherId),
          student_id: Number(sessionData.studentId),
          start_time: sessionData.startTime,
          end_time: sessionData.endTime,
          status: 'scheduled',
          notes: sessionData.notes || null,
        };
        const response = await axios.post(`${API_URL}/sessions/`, payload, { headers: authHeaders() });
        const session = mapSession(response.data);
        this._upsertSession(session);
        return session;
      } catch (err: any) {
        this.error = err.message || 'Failed to book session';
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    /** Student proposes a session → pending_teacher */
    async proposeSessionAsStudent(data: {
      teacherId: number; studentId: number; startTime: string; endTime: string; notes?: string;
    }) {
      this.isLoading = true;
      this.error = null;
      try {
        const payload = {
          teacher_id: Number(data.teacherId),
          student_id: Number(data.studentId),
          start_time: data.startTime,
          end_time: data.endTime,
          notes: data.notes || null,
        };
        const response = await axios.post(`${API_URL}/sessions/propose/student`, payload, { headers: authHeaders() });
        const session = mapSession(response.data);
        this._upsertSession(session);
        return session;
      } catch (err: any) {
        this.error = err.message || 'Failed to propose session';
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    /** Teacher proposes a session → pending_admin */
    async proposeSessionAsTeacher(data: {
      teacherId: number; studentId: number; startTime: string; endTime: string; notes?: string;
    }) {
      this.isLoading = true;
      this.error = null;
      try {
        const payload = {
          teacher_id: Number(data.teacherId),
          student_id: Number(data.studentId),
          start_time: data.startTime,
          end_time: data.endTime,
          notes: data.notes || null,
        };
        const response = await axios.post(`${API_URL}/sessions/propose/teacher`, payload, { headers: authHeaders() });
        const session = mapSession(response.data);
        this._upsertSession(session);
        return session;
      } catch (err: any) {
        this.error = err.message || 'Failed to propose session';
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async approveAsTeacher(sessionId: number) {
      this.isLoading = true;
      try {
        const response = await axios.post(`${API_URL}/sessions/${sessionId}/approve/teacher`, {}, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: any) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async rejectAsTeacher(sessionId: number, notes?: string) {
      this.isLoading = true;
      try {
        const response = await axios.post(`${API_URL}/sessions/${sessionId}/reject/teacher`, { notes }, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: any) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async approveAsAdmin(sessionId: number) {
      this.isLoading = true;
      try {
        const response = await axios.post(`${API_URL}/sessions/${sessionId}/approve/admin`, {}, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: any) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async rejectAsAdmin(sessionId: number, notes?: string) {
      this.isLoading = true;
      try {
        const response = await axios.post(`${API_URL}/sessions/${sessionId}/reject/admin`, { notes }, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: any) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async editSession(sessionId: number, data: Partial<{
      teacherId: number; studentId: number; startTime: string; endTime: string; notes: string;
    }>) {
      this.isLoading = true;
      try {
        const payload: any = {};
        if (data.teacherId) payload.teacher_id = Number(data.teacherId);
        if (data.studentId) payload.student_id = Number(data.studentId);
        if (data.startTime) payload.start_time = data.startTime;
        if (data.endTime) payload.end_time = data.endTime;
        if (data.notes !== undefined) payload.notes = data.notes;
        const response = await axios.put(`${API_URL}/sessions/${sessionId}`, payload, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: any) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async counterAsTeacher(sessionId: number, data: { startTime: string; endTime: string; notes?: string }) {
      this.isLoading = true;
      try {
        const response = await axios.post(`${API_URL}/sessions/${sessionId}/counter/teacher`, {
          start_time: data.startTime,
          end_time: data.endTime,
          notes: data.notes
        }, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: any) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async counterAsStudent(sessionId: number, data: { startTime: string; endTime: string; notes?: string }) {
      this.isLoading = true;
      try {
        const response = await axios.post(`${API_URL}/sessions/${sessionId}/counter/student`, {
          start_time: data.startTime,
          end_time: data.endTime,
          notes: data.notes
        }, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: any) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async approveAsStudent(sessionId: number) {
      this.isLoading = true;
      try {
        const response = await axios.post(`${API_URL}/sessions/${sessionId}/approve/student`, {}, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: any) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async completeSession(sessionId: number) {
      this.isLoading = true;
      try {
        const response = await axios.post(`${API_URL}/sessions/${sessionId}/complete`, {}, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: any) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async requestApproval(sessionId: number, justification?: string) {
      this.isLoading = true;
      try {
        const response = await axios.post(
          `${API_URL}/sessions/${sessionId}/request-approval`,
          { justification: justification || null },
          { headers: authHeaders() }
        );
        this._upsertSession(mapSession(response.data));
      } catch (err: any) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async rejectProof(sessionId: number, reason: string) {
      this.isLoading = true;
      try {
        const response = await axios.post(
          `${API_URL}/sessions/${sessionId}/reject-proof`,
          { reason },
          { headers: authHeaders() }
        );
        this._upsertSession(mapSession(response.data));
      } catch (err: any) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async nudgeSession(sessionId: number) {
      this.isLoading = true;
      try {
        const response = await axios.post(`${API_URL}/sessions/${sessionId}/nudge`, {}, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: any) {
        this.error = err.message;
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async fetchStudentRecords(studentId: number) {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/sessions/student/${studentId}/records`, { headers: authHeaders() });
        const mapped = response.data.map(mapSession);
        for (const session of mapped) {
          this._upsertSession(session);
        }
        return mapped;
      } catch (err: any) {
        this.error = err.message || 'Failed to fetch student records';
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },
  },
});

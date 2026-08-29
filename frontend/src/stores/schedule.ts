import { defineStore } from 'pinia';
import axios from 'axios';
import { useAuthStore } from '@stores/auth';
import { useUsersStore } from '@stores/users';
import { useToastStore } from '@stores/toast';
import type { Session, Schedule } from '@types';

import { API_URL } from '@typescript/constants'

const authHeaders = function() {
  const auth = useAuthStore();
  return auth.token ? { Authorization: `Bearer ${auth.token}` } : {};
}

const errMsg = (e: unknown): string => {
  if (axios.isAxiosError(e)) {
    const detail = e.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join(', ')
    }
    return e.response?.data?.message || e.message
  }
  if (e instanceof Error) return e.message
  if (typeof e === 'object' && e && 'message' in e) return String((e as { message?: unknown }).message ?? '')
  return String(e ?? '')
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
    isForceCompleted: session.is_force_completed || false,
    counterCount: typeof session.counter_count === 'number' ? session.counter_count : 0,
    conflictSessionId: session.conflict_session_id ? Number(session.conflict_session_id) : undefined,
    version: typeof session.version === 'number' ? session.version : 0,
  };
}

interface ScheduleState {
  schedules: Schedule[];
  allSessions: Session[];
  isLoading: boolean;
  error: string | null;
  stats: {
    totalSessions: number;
    scheduledSessions: number;
    completedSessions: number;
    completionRate: number;
    overdueSessions: number;
    pendingSessions: number;
    awaitingAdmin: number;
  } | null;
  teacherBusySlots: { startTime: string; endTime: string }[];
}

export const useScheduleStore = defineStore('schedule', {
  state: (): ScheduleState => ({
    schedules: [],
    allSessions: [],
    isLoading: false,
    error: null,
    stats: null,
    teacherBusySlots: [],
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

    /** Return the locally-cached version for a session, or undefined if not found. */
    _sessionVersion(sessionId: number): number | undefined {
      return this.allSessions.find(s => s.id === sessionId)?.version;
    },

    async fetchAllSessions() {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/sessions/`, { headers: authHeaders() });
        this.allSessions = response.data.map(mapSession);
      } catch (err: unknown) {
        this.error = errMsg(err) || 'Failed to fetch sessions';
        useToastStore().error('Load failed', this.error);
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async fetchUserSessions(userId: number) {
      if (!userId || userId <= 0) return;
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/sessions/user/${userId}`, { headers: authHeaders() });
        for (const session of response.data.map(mapSession)) {
          this._upsertSession(session);
        }
      } catch (err: unknown) {
        this.error = errMsg(err) || 'Failed to fetch user sessions';
        useToastStore().error('Load failed', this.error);
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async fetchTeacherPublicSessions(teacherId: number) {
      if (!teacherId || teacherId <= 0) return;
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/sessions/teacher/${teacherId}/public`, { headers: authHeaders() });
        this.teacherBusySlots = response.data.map((s: any) => ({
          startTime: s.start_time,
          endTime: s.end_time,
        }));
      } catch (err: unknown) {
        this.error = errMsg(err) || 'Failed to fetch teacher public sessions';
        useToastStore().error('Load failed', this.error);
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
      } catch (err: unknown) {
        this.error = errMsg(err) || 'Failed to fetch pending sessions';
        useToastStore().error('Load failed', this.error);
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
          notes: sessionData.notes || null,
          instrument_id: sessionData.instrumentId ?? null,
        };
        const response = await axios.post(`${API_URL}/sessions/`, payload, { headers: authHeaders() });
        const session = mapSession(response.data);
        this._upsertSession(session);
        return session;
      } catch (err: unknown) {
        this.error = errMsg(err) || 'Failed to book session';
        useToastStore().error('Booking failed', this.error);
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    /** Student proposes a session → pending_teacher */
    async proposeSessionAsStudent(data: {
      teacherId: number; studentId: number; startTime: string; endTime: string; notes?: string; instrumentId?: number | null;
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
          instrument_id: data.instrumentId ?? null,
        };
        const response = await axios.post(`${API_URL}/sessions/propose/student`, payload, { headers: authHeaders() });
        const session = mapSession(response.data);
        this._upsertSession(session);
        return session;
      } catch (err: unknown) {
        this.error = errMsg(err) || 'Failed to propose session';
        useToastStore().error('Proposal failed', this.error);
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    /** Teacher proposes a session → pending_admin */
    async proposeSessionAsTeacher(data: {
      teacherId: number; studentId: number; startTime: string; endTime: string; notes?: string; instrumentId?: number | null;
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
          instrument_id: data.instrumentId ?? null,
        };
        const response = await axios.post(`${API_URL}/sessions/propose/teacher`, payload, { headers: authHeaders() });
        const session = mapSession(response.data);
        this._upsertSession(session);
        return session;
      } catch (err: unknown) {
        this.error = errMsg(err) || 'Failed to propose session';
        useToastStore().error('Proposal failed', this.error);
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
      } catch (err: unknown) {
        this.error = errMsg(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async rejectAsTeacher(sessionId: number, notes?: string) {
      this.isLoading = true;
      try {
        const response = await axios.post(`${API_URL}/sessions/${sessionId}/reject/teacher`, { notes, version: this._sessionVersion(sessionId) }, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: unknown) {
        this.error = errMsg(err);
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
      } catch (err: unknown) {
        this.error = errMsg(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async rejectAsAdmin(sessionId: number, notes?: string) {
      this.isLoading = true;
      try {
        const response = await axios.post(`${API_URL}/sessions/${sessionId}/reject/admin`, { notes, version: this._sessionVersion(sessionId) }, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: unknown) {
        this.error = errMsg(err);
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
        payload.version = this._sessionVersion(sessionId);
        const response = await axios.put(`${API_URL}/sessions/${sessionId}`, payload, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: unknown) {
        this.error = errMsg(err);
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
          notes: data.notes,
          version: this._sessionVersion(sessionId),
        }, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: unknown) {
        this.error = errMsg(err);
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
          notes: data.notes,
          version: this._sessionVersion(sessionId),
        }, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: unknown) {
        this.error = errMsg(err);
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
      } catch (err: unknown) {
        this.error = errMsg(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async rejectAsStudent(sessionId: number, notes?: string) {
      this.isLoading = true;
      try {
        const response = await axios.post(`${API_URL}/sessions/${sessionId}/reject/student`, { notes, version: this._sessionVersion(sessionId) }, { headers: authHeaders() });
        this._upsertSession(mapSession(response.data));
      } catch (err: unknown) {
        this.error = errMsg(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async completeSession(sessionId: number) {
      this.isLoading = true;
      try {
        const response = await axios.post(`${API_URL}/sessions/${sessionId}/complete`, {}, { headers: authHeaders() });
        const session = mapSession(response.data);
        this._upsertSession(session);
        // Decrement sessionsLeft on the student in the users store so the
        // displayed counter is immediately accurate without a full page refresh.
        const usersStore = useUsersStore();
        const student = usersStore.users.find((u) => u.id === session.studentId);
        if (student && student.sessionsLeft != null && student.sessionsLeft > 0) {
          student.sessionsLeft -= 1;
        }
      } catch (err: unknown) {
        this.error = errMsg(err);
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
          { justification: justification || null, version: this._sessionVersion(sessionId) },
          { headers: authHeaders() }
        );
        this._upsertSession(mapSession(response.data));
      } catch (err: unknown) {
        this.error = errMsg(err);
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
          { reason, version: this._sessionVersion(sessionId) },
          { headers: authHeaders() }
        );
        this._upsertSession(mapSession(response.data));
      } catch (err: unknown) {
        this.error = errMsg(err);
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
      } catch (err: unknown) {
        this.error = errMsg(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async fetchStudentRecords(studentId: number) {
      if (!studentId || studentId <= 0) return [];
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/sessions/student/${studentId}/records`, { headers: authHeaders() });
        const mapped = response.data.map(mapSession);
        for (const session of mapped) {
          this._upsertSession(session);
        }
        return mapped;
      } catch (err: unknown) {
        this.error = errMsg(err) || 'Failed to fetch student records';
        useToastStore().error('Load failed', this.error);
        console.error(err);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },


    async fetchStats() {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get(`${API_URL}/sessions/stats`, { headers: authHeaders() });
        const data = response.data;
        this.stats = {
          totalSessions: data.total_sessions,
          scheduledSessions: data.scheduled_sessions,
          completedSessions: data.completed_sessions,
          completionRate: data.completion_rate,
          overdueSessions: data.overdue_sessions,
          pendingSessions: data.pending_sessions,
          awaitingAdmin: data.awaiting_admin,
        };
      } catch (err: unknown) {
        this.error = errMsg(err) || 'Failed to fetch session stats';
        console.error(err);
      } finally {
        this.isLoading = false;
      }
    },

    async bulkAction(sessionIds: number[], action: 'approve' | 'cancel' | 'complete') {
      const toast = useToastStore();
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.post(`${API_URL}/sessions/bulk-action`, {
          session_ids: sessionIds,
          action
        }, { headers: authHeaders() });
        
        const updated = response.data.map(mapSession);
        for (const s of updated) {
          this._upsertSession(s);
        }
        
        toast.success('Bulk action successful', `Successfully processed ${sessionIds.length} sessions.`);
        await this.fetchStats(); // Update dashboard counts
      } catch (err: unknown) {
        this.error = errMsg(err) || 'Failed to process bulk action';
        toast.error('Bulk action failed', this.error);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async cancelSession(sessionId: number, notes?: string) {
      this.isLoading = true;
      try {
        const response = await axios.post(
          `${API_URL}/sessions/${sessionId}/cancel`,
          { notes, version: this._sessionVersion(sessionId) },
          { headers: authHeaders() }
        );
        this._upsertSession(mapSession(response.data));
        useToastStore().success('Session Cancelled', 'The session has been cancelled.');
      } catch (err: unknown) {
        this.error = errMsg(err) || 'Failed to cancel session';
        useToastStore().error('Cancellation failed', this.error);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },

    async uploadSessionProof(sessionId: number, file: File) {
      this.isLoading = true;
      try {
        const formData = new FormData();
        formData.append('file', file);
        await axios.post(
          `${API_URL}/session-proofs/?session_id=${sessionId}`,
          formData,
          {
            headers: {
              ...authHeaders(),
              'Content-Type': 'multipart/form-data',
            },
          }
        );
        const auth = useAuthStore();
        if (auth.user?.role === 'admin') {
          await this.fetchAllSessions();
        } else if (auth.user?.id) {
          await this.fetchUserSessions(auth.user.id);
        }
        useToastStore().success('Proof Uploaded', 'Your proof has been uploaded successfully.');
      } catch (err: unknown) {
        this.error = errMsg(err) || 'Failed to upload proof';
        useToastStore().error('Upload failed', this.error);
        throw err;
      } finally {
        this.isLoading = false;
      }
    },
  },
});

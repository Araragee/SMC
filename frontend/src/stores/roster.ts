import { defineStore } from 'pinia'
import axios from 'axios'
import type { Enrollment, TeacherAssignment } from '@types'
import { useAuthStore } from '@stores/auth'
import { API_URL } from '@typescript/constants'

const authHeaders = function () {
  const auth = useAuthStore()
  return auth.token ? { Authorization: `Bearer ${auth.token}` } : {}
}

const mapAssignment = (a: any): TeacherAssignment => ({
  id: Number(a.id),
  teacherId: Number(a.teacher_id),
  studentId: Number(a.student_id),
  assignedAt: a.assigned_at,
})

const mapEnrollment = (e: any): Enrollment => ({
  id: Number(e.id),
  studentId: Number(e.student_id),
  teacherId: Number(e.teacher_id),
  sessionsPurchased: e.sessions_purchased,
  sessionsUsed: e.sessions_used,
  sessionsLeft: e.sessions_left,
  status: e.status ?? 'active',
  isActive: e.is_active,
  createdAt: e.created_at,
})

/** Result of a bulk operation: how many rows landed and why the rest didn't. */
export interface BulkResult {
  ok: number
  failed: { studentId: number; reason: string }[]
}

const reasonOf = (err: any): string =>
  err?.response?.data?.detail || err?.message || 'Unknown error'

interface RosterState {
  assignments: TeacherAssignment[]
  enrollments: Enrollment[]
  isLoading: boolean
  error: string | null
}

export const useRosterStore = defineStore('roster', {
  state: (): RosterState => ({
    assignments: [],
    enrollments: [],
    isLoading: false,
    error: null,
  }),
  getters: {
    assignmentsByTeacher: (state) => (teacherId: number) =>
      state.assignments.filter((a) => a.teacherId === teacherId),
    enrollmentsByStudent: (state) => (studentId: number) =>
      state.enrollments.filter((e) => e.studentId === studentId),
    /** Student-initiated requests awaiting an admin decision. */
    pendingEnrollments: (state) => state.enrollments.filter((e) => e.status === 'pending'),
    /** Student ids already on a given teacher's roster — drives the "already added" state in the picker. */
    assignedStudentIds: (state) => (teacherId: number) =>
      new Set(state.assignments.filter((a) => a.teacherId === teacherId).map((a) => a.studentId)),
  },
  actions: {
    async fetchAll() {
      this.isLoading = true
      this.error = null
      try {
        const [assignments, enrollments] = await Promise.all([
          axios.get(`${API_URL}/teacher-students/`, { headers: authHeaders() }),
          axios.get(`${API_URL}/enrollments/`, { headers: authHeaders() }),
        ])
        this.assignments = assignments.data.map(mapAssignment)
        this.enrollments = enrollments.data.map(mapEnrollment)
      } catch (err: any) {
        this.error = reasonOf(err)
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async assignStudent(teacherId: number, studentId: number) {
      const { data } = await axios.post(
        `${API_URL}/teacher-students/`,
        { teacher_id: teacherId, student_id: studentId },
        { headers: authHeaders() },
      )
      const assignment = mapAssignment(data)
      this.assignments.push(assignment)
      return assignment
    },

    // ponytail: sequential-ish fan-out over the single-assign endpoint rather
    // than a dedicated bulk route. Partial failures are reported per student,
    // which is what the admin actually needs (e.g. "already assigned").
    // Add a real bulk endpoint if rosters ever grow past a few hundred rows.
    async bulkAssignStudents(teacherId: number, studentIds: number[]): Promise<BulkResult> {
      this.isLoading = true
      try {
        const results = await Promise.allSettled(
          studentIds.map((id) => this.assignStudent(teacherId, id)),
        )
        const failed = results.flatMap((r, i) =>
          r.status === 'rejected' ? [{ studentId: studentIds[i], reason: reasonOf(r.reason) }] : [],
        )
        return { ok: results.length - failed.length, failed }
      } finally {
        this.isLoading = false
      }
    },

    async unassignStudent(assignmentId: number) {
      await axios.delete(`${API_URL}/teacher-students/${assignmentId}`, { headers: authHeaders() })
      this.assignments = this.assignments.filter((a) => a.id !== assignmentId)
    },

    async createEnrollment(payload: { studentId: number; teacherId: number; sessionsPurchased: number }) {
      const { data } = await axios.post(
        `${API_URL}/enrollments/`,
        {
          student_id: payload.studentId,
          teacher_id: payload.teacherId,
          sessions_purchased: payload.sessionsPurchased,
          sessions_used: 0,
        },
        { headers: authHeaders() },
      )
      const enrollment = mapEnrollment(data)
      this.enrollments.unshift(enrollment)
      return enrollment
    },

    async bulkEnroll(
      teacherId: number,
      studentIds: number[],
      sessionsPurchased: number,
    ): Promise<BulkResult> {
      this.isLoading = true
      try {
        const results = await Promise.allSettled(
          studentIds.map((studentId) =>
            this.createEnrollment({ studentId, teacherId, sessionsPurchased }),
          ),
        )
        const failed = results.flatMap((r, i) =>
          r.status === 'rejected' ? [{ studentId: studentIds[i], reason: reasonOf(r.reason) }] : [],
        )
        return { ok: results.length - failed.length, failed }
      } finally {
        this.isLoading = false
      }
    },

    async updateEnrollment(
      id: number,
      patch: { teacherId?: number; sessionsPurchased?: number; isActive?: boolean },
    ) {
      const body: Record<string, unknown> = {}
      if (patch.teacherId !== undefined) body.teacher_id = patch.teacherId
      if (patch.sessionsPurchased !== undefined) body.sessions_purchased = patch.sessionsPurchased
      if (patch.isActive !== undefined) body.is_active = patch.isActive

      const { data } = await axios.put(`${API_URL}/enrollments/${id}`, body, { headers: authHeaders() })
      const updated = mapEnrollment(data)
      const index = this.enrollments.findIndex((e) => e.id === id)
      if (index !== -1) this.enrollments[index] = updated
      return updated
    },

    /** Approve a student's request and grant the hours they paid for. */
    async approveEnrollment(id: number, sessionsPurchased: number) {
      const { data } = await axios.post(
        `${API_URL}/enrollments/${id}/approve`,
        { sessions_purchased: sessionsPurchased },
        { headers: authHeaders() },
      )
      const updated = mapEnrollment(data)
      const index = this.enrollments.findIndex((e) => e.id === id)
      if (index !== -1) this.enrollments[index] = updated
      return updated
    },

    async rejectEnrollment(id: number) {
      const { data } = await axios.post(
        `${API_URL}/enrollments/${id}/reject`,
        {},
        { headers: authHeaders() },
      )
      const updated = mapEnrollment(data)
      const index = this.enrollments.findIndex((e) => e.id === id)
      if (index !== -1) this.enrollments[index] = updated
      return updated
    },

    /** `force` soft-deletes an enrollment that already has usage history. */
    async deleteEnrollment(id: number, force = false) {
      await axios.delete(`${API_URL}/enrollments/${id}`, {
        headers: authHeaders(),
        params: force ? { force: true } : undefined,
      })
      this.enrollments = this.enrollments.filter((e) => e.id !== id)
    },
  },
})

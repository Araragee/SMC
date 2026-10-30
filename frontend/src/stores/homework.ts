import { defineStore } from 'pinia'
import axios from 'axios'
import type { Homework, HomeworkStatus } from '@types'
import type { HomeworkResponse } from '@/types/api'
import { useAuthStore } from '@stores/auth'
import { useToastStore } from '@stores/toast'
import { API_URL } from '@typescript/constants'
import { apiError } from '@/utils/apiError'

const authHeaders = function () {
  const auth = useAuthStore()
  return auth.token ? { Authorization: `Bearer ${auth.token}` } : {}
}

/**
 * One mapper for both sides of the feature.
 *
 * `status` is taken from the server rather than recomputed here: it is derived
 * from timestamps the server owns, and a second implementation in the client
 * would disagree with it the first time a clock or a rule changed.
 */
export const mapHomework = (raw: HomeworkResponse): Homework => ({
  id: Number(raw.id),
  sessionId: Number(raw.session_id),
  description: raw.description,
  isCompleted: raw.is_completed,
  fileUrl: raw.file_url ?? undefined,
  createdAt: raw.created_at,
  dueDate: raw.due_date ?? null,
  assignedById: raw.assigned_by_id ?? null,
  completedAt: raw.completed_at ?? null,
  grade: raw.grade ?? null,
  feedback: raw.feedback ?? null,
  reviewedAt: raw.reviewed_at ?? null,
  status: raw.status,
  studentId: (raw as HomeworkResponse & { student_id?: number | null }).student_id ?? null,
  studentName: (raw as HomeworkResponse & { student_name?: string | null }).student_name ?? null,
  sessionStartTime:
    (raw as HomeworkResponse & { session_start_time?: string | null }).session_start_time ?? null,
})

interface HomeworkState {
  /** The teacher's working list: assignments across their own sessions. */
  assigned: Homework[]
  isLoading: boolean
  isSaving: boolean
  error: string | null
}

export const useHomeworkStore = defineStore('homework', {
  state: (): HomeworkState => ({
    assigned: [],
    isLoading: false,
    isSaving: false,
    error: null,
  }),

  getters: {
    /** Work handed in and waiting on the teacher — what the badge counts. */
    awaitingReview: (state) => state.assigned.filter((h) => h.status === 'submitted'),
    overdue: (state) => state.assigned.filter((h) => h.status === 'overdue'),

    countsByStatus: (state) => {
      const counts: Record<HomeworkStatus, number> = {
        assigned: 0,
        overdue: 0,
        submitted: 0,
        reviewed: 0,
      }
      for (const item of state.assigned) counts[item.status] += 1
      return counts
    },
  },

  actions: {
    /**
     * Load the calling teacher's assignments.
     *
     * The server scopes this to sessions the caller teaches — there is no
     * teacher id to pass, deliberately, so there is no id to tamper with.
     */
    async fetchAssigned(filters: { studentId?: number; status?: HomeworkStatus } = {}) {
      this.isLoading = true
      this.error = null
      try {
        const params = new URLSearchParams()
        if (filters.studentId) params.set('student_id', String(filters.studentId))
        if (filters.status) params.set('status', filters.status)
        const query = params.toString()

        const response = await axios.get(
          `${API_URL}/homework/assigned${query ? `?${query}` : ''}`,
          { headers: authHeaders() }
        )
        this.assigned = response.data.map(mapHomework)
        return this.assigned
      } catch (err: unknown) {
        this.error = apiError(err, 'Failed to load homework')
        useToastStore().error('Could not load homework', this.error)
        throw err
      } finally {
        this.isLoading = false
      }
    },

    /** Replace one row in place, so a single edit does not refetch the list. */
    _upsert(item: Homework) {
      const index = this.assigned.findIndex((h) => h.id === item.id)
      if (index === -1) this.assigned.unshift(item)
      else this.assigned[index] = { ...this.assigned[index], ...item }
    },

    async assign(sessionId: number, description: string, dueDate?: string | null) {
      this.isSaving = true
      this.error = null
      try {
        const response = await axios.post(
          `${API_URL}/homework/?session_id=${sessionId}`,
          { description, due_date: dueDate || null },
          { headers: authHeaders() }
        )
        const created = mapHomework(response.data)
        this._upsert(created)
        useToastStore().success('Homework assigned', 'The student has been notified.')
        return created
      } catch (err: unknown) {
        this.error = apiError(err, 'Failed to assign homework')
        useToastStore().error('Could not assign homework', this.error)
        throw err
      } finally {
        this.isSaving = false
      }
    },

    async edit(
      homeworkId: number,
      changes: { description?: string; dueDate?: string | null; clearDueDate?: boolean }
    ) {
      this.isSaving = true
      this.error = null
      try {
        const response = await axios.patch(
          `${API_URL}/homework/${homeworkId}`,
          {
            description: changes.description,
            due_date: changes.dueDate || null,
            clear_due_date: changes.clearDueDate ?? false,
          },
          { headers: authHeaders() }
        )
        const updated = mapHomework(response.data)
        this._upsert(updated)
        useToastStore().success('Homework updated')
        return updated
      } catch (err: unknown) {
        this.error = apiError(err, 'Failed to update homework')
        useToastStore().error('Could not update homework', this.error)
        throw err
      } finally {
        this.isSaving = false
      }
    },

    async review(homeworkId: number, grade: string | null, feedback: string | null) {
      this.isSaving = true
      this.error = null
      try {
        const response = await axios.post(
          `${API_URL}/homework/${homeworkId}/review`,
          { grade: grade || null, feedback: feedback || null },
          { headers: authHeaders() }
        )
        const reviewed = mapHomework(response.data)
        this._upsert(reviewed)
        useToastStore().success('Review saved', 'The student has been notified.')
        return reviewed
      } catch (err: unknown) {
        this.error = apiError(err, 'Failed to save review')
        useToastStore().error('Could not save review', this.error)
        throw err
      } finally {
        this.isSaving = false
      }
    },

    async remove(homeworkId: number) {
      this.isSaving = true
      this.error = null
      try {
        await axios.delete(`${API_URL}/homework/${homeworkId}`, { headers: authHeaders() })
        this.assigned = this.assigned.filter((h) => h.id !== homeworkId)
        useToastStore().success('Homework withdrawn')
      } catch (err: unknown) {
        this.error = apiError(err, 'Failed to withdraw homework')
        useToastStore().error('Could not withdraw homework', this.error)
        throw err
      } finally {
        this.isSaving = false
      }
    },
  },
})

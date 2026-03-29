# Project Documentation for AI Assistants

This document provides a high-level overview of the Music School Management System (SMC) to help AI assistants navigate and understand the codebase.

## 📁 Repository Structure

### Backend (`/backend`)
- `main.py`: Core FastAPI application, all API routes, and business logic.
- `models.py`: SQLAlchemy database models (SQLite).
- `schemas.py`: Pydantic models for request/response validation.
- `database.py`: Database connection and session management.
- `auth.py`: JWT authentication utilities (if separate, usually integrated in `main.py`).
- `uploads/`: Directory for session proofs and user avatars.

### Frontend (`/frontend`)
- `src/stores/`: Pinia state management (`auth.ts`, `schedule.ts`, `messaging.ts`).
- `src/components/`: Reusable Vue components.
    - `SessionDetailModal.vue`: **CRITICAL** - Handles all session viewing and actions.
    - `BaseCalendar.vue`: Shared calendar component for all roles.
- `src/views/`: Page-level components organized by role (`admin/`, `teacher/`, `student/`).
- `src/types/`: TypeScript interfaces and types.

---

## ⚙️ Backend Critical Logic

### 1. Authentication & Authorization
- Uses JWT tokens stored in localStorage.
- Roles: `admin`, `teacher`, `student`.
- **Dependencies**:
    - `require_admin`: Strictly for admins.
    - `require_teacher`: Allows teachers and admins.
    - `require_student`: Allows students and admins (recently updated to allow admin management).

### 2. Session Lifecycle & Statuses
Sessions go through a complex state machine:
- `scheduled`: Initial state for confirmed sessions.
- `pending_teacher` / `pending_student`: Negotiation phase when one party proposes a time.
- `pending_admin`: Both parties agreed; awaiting final admin "Confirm" to move to `scheduled`.
- `overdue`: Automatic/Manual status when current time > session end time.
- `pending_verification`: Student (or teacher) has uploaded proof of session; awaiting admin review.
- `overdue_rejected`: Admin rejected the uploaded proof; student/teacher must re-upload.
- `completed`: Finalized session. **Triggers analytics updates**:
    - Decrements student's `sessions_left`.
    - Increments `sessions_used` in the relevant `Enrollment`.
- `rejected` / `cancelled`: Terminated states.

### 3. Proofs & Completion
- **Manual Completion**: Admin can force-complete a session without proofs, but only **24 hours after** the session has ended.
- **Nudge**: Users can "nudge" (send notification) to participants who are slow to upload proofs.

---

## 🎨 Frontend Critical Logic

### 1. Session Management (`schedule.ts` store)
- `allSessions`: Reactive array of all sessions the user has access to.
- `fetchUserSessions`: Primary data fetcher.
- `_upsertSession`: Internal helper to update a single session in the local state without re-fetching all.

### 2. The Detail Modal (`SessionDetailModal.vue`)
This is the single source of truth for session interaction. It takes a single `session` prop and renders contextually based on:
- `session.status`
- `props.userRole`
- `props.currentUserId`

**Key Sections**:
- **Negotiation**: Approve/Reject/Counter buttons for proposals.
- **Proofs**: Image thumbnails + Lightbox viewer.
- **Status Messages**: Human-readable descriptions of what's happening.

### 3. Calendar Legend
- **Teal**: Confirmed (`scheduled`)
- **Emerald**: Done (`completed`)
- **Amber**: Aw. Teacher (`pending_teacher`)
- **Orange**: Countered (`pending_student`)
- **Blue**: Aw. Admin (`pending_admin`)
- **Violet**: In Review (`pending_verification`)
- **Rose**: Overdue (`overdue`)
- **Red**: Proof Rej. (`overdue_rejected`)

---

## 💡 Tips for Coding
- **Consistency**: Always use the `selectedSession` ref pattern when opening the `SessionDetailModal`.
- **Reactivity**: Ensure backend changes (like status updates) are mapped back to the store using `_upsertSession`.
- **Notifications**: Most session actions trigger a `notify_users` call in the backend. Verify these messages for clarity.
- **Colors**: Use the established Tailwind/CSS variable system (e.g., `text-on-surface`, `bg-on-surface-variant`).

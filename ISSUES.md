# Audit Report & Remediation Plan

## 1. Identified Issues & Status

### Broken Links & Missing Views
| Issue | Status | Notes |
| :--- | :--- | :--- |
| Teacher `Instruments` & `Payments` views missing | **Fixed** | Full CRUD and ledger views implemented. |
| Student `Homework` view missing | **Fixed** | Implemented with file upload and status tracking. |
| Admin `All Activity` button inactive | **Improved** | Added toast notification for roadmap awareness. |
| Admin `Preferences` link inactive | **Fixed** | Connected to User Settings modal. |
| Missing deep linking for Chat/Notifs | **Fixed** | Implemented via route watchers in SidebarNav. |

### Logic Lapses
| Issue | Status | Notes |
| :--- | :--- | :--- |
| `StudentRecords.vue` hardcoded API calls | **Fixed** | Refactored to use Pinia `scheduleStore.fetchStudentRecords`. |
| Admin Quick Assign Timezone Risk | **Fixed** | Refactored date-time construction to be timezone-agnostic. |
| Backend crash on `is_manual_entry` | **Fixed** | Added Pydantic field validator to handle `NULL` database values. |
| Delete vs Deactivate risk | **Fixed** | Refactored `delete_user` to deactivate if linked records exist. |
| Teacher Dashboard notes not saving | **Fixed** | Ensured `editSession` is called on note updates. |

### UI/UX & Overall Issues
| Issue | Status | Notes |
| :--- | :--- | :--- |
| Inconsistent layout constraints | **Fixed** | Standardized `max-w-[1600px]` across all Admin views. |
| Hardcoded API URLs | **Fixed** | Moved logic into stores with environment variable awareness. |
| Missing error states in `onMounted` | **Improved** | Added `try/catch` blocks to critical data fetching hooks. |
| WebSocket Reconnect Logic | **Fixed** | Implemented exponential backoff for chat stability. |

## 2. Remediation Plan

### Phase 1: Stability & Integrity (Completed)
- [x] Fix backend schema validation to prevent 500 errors on legacy data.
- [x] Implement "Soft Delete" (Deactivate) for users with historical session data.
- [x] Centralize student record fetching into Pinia stores.

### Phase 2: UX Consistency (Completed)
- [x] Standardize horizontal alignment and responsiveness across Admin dashboards.
- [x] Resolve all "dead links" by providing placeholders or connecting to existing modals.
- [x] Fix timezone offsets in scheduling tools.
- [x] Implement deep linking for Chat & Notifications.

### Phase 3: Feature Completeness (Completed)
- [x] Implement full `Instruments` management for Teachers.
- [x] Implement `Payments` and ledger tracking (Admin/Teacher/Student).
- [x] Add student-side `Homework` view with file upload capability.
- [x] Implement real-time WebSocket reconnect logic for Chat.

## 3. Verification Instructions
1. Run backend tests: `python -m pytest backend/`
2. Verify frontend build: `npm run build --prefix frontend`
3. Launch app and verify Admin Dashboard layout at 1600px width.
4. Attempt to "Delete" a user with existing sessions to verify deactivation logic.

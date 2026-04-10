# Audit Report & Remediation Plan

## 1. Identified Issues & Status

### Broken Links & Missing Views
| Issue | Status | Notes |
| :--- | :--- | :--- |
| Teacher `Instruments` & `Payments` views missing | **Mapped** | Linked to `PlaceholderView.vue` to avoid 404s. |
| Student `Homework` view missing | **Mapped** | Linked to `PlaceholderView.vue`. |
| Admin `All Activity` button inactive | **Improved** | Added toast notification for roadmap awareness. |
| Admin `Preferences` link inactive | **Fixed** | Connected to User Settings modal. |
| Missing deep linking for Chat/Notifs | **Pending** | Requires router refactor for state-driven modals. |

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

## 2. Remediation Plan

### Phase 1: Stability & Integrity (Completed)
- [x] Fix backend schema validation to prevent 500 errors on legacy data.
- [x] Implement "Soft Delete" (Deactivate) for users with historical session data.
- [x] Centralize student record fetching into Pinia stores.

### Phase 2: UX Consistency (Completed)
- [x] Standardize horizontal alignment and responsiveness across Admin dashboards.
- [x] Resolve all "dead links" by providing placeholders or connecting to existing modals.
- [x] Fix timezone offsets in scheduling tools.

### Phase 3: Feature Completeness (Future)
- [ ] Implement full `Instruments` management for Teachers.
- [ ] Implement `Payments` and ledger tracking.
- [ ] Add student-side `Homework` view with file upload capability.
- [ ] Implement real-time WebSocket reconnect logic for Chat.

## 3. Verification Instructions
1. Run backend tests: `python -m pytest backend/`
2. Verify frontend build: `npm run build --prefix frontend`
3. Launch app and verify Admin Dashboard layout at 1600px width.
4. Attempt to "Delete" a user with existing sessions to verify deactivation logic.

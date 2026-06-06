# SMC System Scan — 2026-05-24

## Status of plans.md

All items from `plans.md` were already implemented by prior sessions:

- **Alembic migrations** — initialized, 7 versioned migration files present.
- **pydantic-settings / env vars** — `backend/config.py` fully migrated; no hardcoded secrets.
- **ID type standardization** — all frontend types use `number`; `api.ts` is consistent.
- **AdminPayments.vue / `/admin/payments` route** — exists and functional (CRUD + receipt printing).
- **ActivityLog.vue / `/admin/activity-log` route** — exists and functional with search/filter/pagination.
- **"View All Activity" button** — correctly routes to `/admin/activity-log` (not a toast).
- **No PlaceholderView** — zero references remain in the router or sidebar.
- **Shop fulfillment** — full `pending → approved → fulfilled / cancelled` state machine with atomic stock deduction, race-condition guard, and low-stock notifications to admins.
- **`log_activity` wired broadly** — sessions, payments, users, auth, shop all emit activity entries.

---

## Bugs Fixed This Session

### 1. `SidebarNav.vue` — Missing `v-click-outside` directive

**File:** `frontend/src/components/SidebarNav.vue`

`v-click-outside` was used on the user-profile dropdown (line 247) but was never defined in the component — unlike `TopNavbar.vue` and the admin/teacher list views which all define it locally. Vue silently ignores unknown directives, so the dropdown never closed when clicking outside.

**Fix applied:** Added `vClickOutside` definition at the top of the `<script setup>` block, consistent with how other components implement it.

---

### 2. `record_past_session` — Returned raw ORM object instead of `map_session()`

**File:** `backend/routers/sessions.py`

Every other session endpoint returns `map_session(db_session)`, which adds the convenience fields `proof_image_url`, `homework_assigned`, and `homework_completed` that the frontend relies on. `record_past_session` returned the raw `db_session` object directly, bypassing this transform and also skipping the eager-load options (`_session_eager_options()`).

**Fix applied:** Replaced `return db_session` with a re-fetch using `_session_eager_options()` followed by `return map_session(db_session)`.

---

### 3. `SessionPropose.end_time` — Required field with dead fallback code

**File:** `backend/schemas.py`

`SessionPropose.end_time` was typed as `datetime` (required), but both `propose_session_as_student` and `propose_session_as_teacher` had fallback code `end_time = proposal.end_time or (proposal.start_time + timedelta(hours=1))` that could never trigger. This inconsistency would cause a validation error if a frontend client omitted `end_time` expecting the 1-hour default.

**Fix applied:** Changed `end_time: datetime` → `end_time: datetime | None = None` so the router fallback is live again.

---

### 4. No double-booking / scheduling conflict guard

**Files:** `backend/routers/sessions.py`

None of the three session-creation paths (`POST /sessions/`, `POST /sessions/propose/student`, `POST /sessions/propose/teacher`) checked for overlapping active sessions. An admin could accidentally schedule a teacher for two simultaneous sessions; a teacher with two students could propose back-to-back sessions that overlap.

**Fix applied:** Added `_check_overlap()` helper that queries for active sessions (`scheduled`, `pending_*`, `overdue`, `pending_verification`, `overdue_rejected`) where `start_time < new_end AND end_time > new_start`. Raises HTTP 409 with a clear message identifying which participant has a conflict. Wired into all three creation endpoints.

---

## Remaining Improvement Opportunities (Not Yet Fixed)

### A. `session_checker_task` — No stale-state reminders

**File:** `backend/routers/sessions.py` (`session_checker_task`)

The background task sends 24h/12h reminders for upcoming `scheduled` sessions and auto-transitions them to `overdue`. However, sessions stuck in `pending_verification` (proof submitted, no admin action) or `overdue_rejected` (proof rejected, no resubmission) receive no follow-up nudge. A session can sit in these states indefinitely without anyone being reminded.

**Suggested fix:** Add a configurable threshold (e.g. 48h) after which the task emits a reminder notification to the relevant parties. Track a `last_reminded_at` timestamp on the session, or use a separate table.

---

### B. `GET /payments/` — Hardcoded 200-record limit

**File:** `backend/routers/payments.py`

The default `limit=200` on the payments list endpoint means schools with more than 200 payment records will silently see truncated data on the admin Ledger page. The frontend doesn't pass `skip`/`limit` params, so older records become invisible.

**Suggested fix:** Raise the default cap (e.g. `limit=500`) or implement cursor/offset pagination in `AdminPayments.vue` and expose it through the store. For most small music schools this won't be urgent, but it's worth noting before it causes confusion.

---

### C. `session_checker_task` short-circuit may skip `pending_verification` timeouts

**File:** `backend/routers/sessions.py`

The `has_work` guard exits early if there are no `scheduled` sessions. A future feature that adds time-based auto-escalation for `pending_verification` sessions would need to be placed outside this gate (the inline comment mentions this). Low risk now but worth keeping in mind as the checker grows.

---

### D. `notify_users` dual-signature API is fragile

**File:** `backend/routers/notifications.py`

`notify_users` accepts two different calling conventions:
- `notify_users(db, ids, message)` — legacy, message-only style
- `notify_users(db, ids, title, message, link)` — shop-style with title

The disambiguation relies on whether `link` is `None`. This works but is error-prone: a caller that passes a message and a link (without a title) will have its data silently swapped. A small refactor to keyword-only arguments or separate helpers would make call sites clearer.

---

### E. `cancel_my_order` — No notification to the ordering user

**File:** `backend/routers/shop.py`

When a user cancels their own pending order, admins are notified but the user receives no confirmation notification (they only see the UI response). Minor UX gap — a "Your order has been cancelled" notification would be consistent with the approval/rejection notifications the same user receives.

---

### F. Frontend — `v-click-outside` duplicated across 5+ components

**Files:** `SidebarNav.vue`, `TopNavbar.vue`, `admin/Students.vue`, `admin/Teachers.vue`, `teacher/Students.vue`

Each component copy-pastes the same 4-line directive definition. This should be extracted into a shared composable (`composables/useClickOutside.ts`) or registered as a global Vue directive in `main.ts`.

---

## TypeScript Build Check

```
npx tsc --noEmit → 0 errors
```

The frontend type-checks cleanly. (Native `npm run build` cannot be verified in the sandbox due to a Linux/ARM platform mismatch with the Rolldown binding, but all TypeScript is valid.)

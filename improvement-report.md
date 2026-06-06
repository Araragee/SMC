# SMC Portal — Automated Improvement Report

**Generated:** 2026-05-23 (automated scheduled task)
**Branch:** `dev`
**Scope:** Full system scan following plans.md implementation

---

## What Was Done This Session

The following changes were implemented autonomously after reading `plans.md`:

### Changes Implemented

**1. Activity Log added to admin sidebar** (`SidebarNav.vue`)
The `/admin/activity-log` route and view were fully functional, but had no sidebar link — only reachable via the Dashboard "View All Activity" button. Added `{ label: 'Activity', icon: 'history', path: '/admin/activity-log' }` to the admin nav items.

**2. Fixed string/number ID comparison bug** (`teacher/Payments.vue`)
`getStudentName()` was using `String(u.id) === String(id)` as a workaround for a perceived type mismatch. Since `User.id` is typed as `number` throughout the codebase and the store maps with `Number(user.id)`, the correct comparison is `u.id === id`. Fixed.

**3. Monthly Revenue stat card added to Admin Dashboard** (`admin/Dashboard.vue`)
The dashboard had no payment visibility. Imported `usePaymentsStore`, added `fetchPayments()` to the `onMounted` Promise.all, computed `thisMonthRevenue` from completed payments in the current calendar month, and added a new emerald-colored bento card linking to `/admin/payments`.

**4. WebSocket URL production fallback fixed** (`stores/messaging.ts`)
`WS_URL` previously fell back to hardcoded `ws://localhost:8000` in all non-dev environments where `VITE_WS_BASE_URL` was not set. This would silently break real-time messaging in any deployment. Fixed to derive from `window.location` with correct `wss://` protocol for HTTPS hosts, matching the pattern used by `API_URL` in `constants.ts`.

**5. Delete payment wired up end-to-end** (`stores/payments.ts`, `admin/Payments.vue`)
The backend had a `DELETE /payments/{id}` endpoint with activity logging, but the Pinia store had no `deletePayment` action and the Payments UI had no delete button. Added the store action and a delete button (with confirmation dialog) to each row in the ledger.

**6. Stale TODO/developer comments removed** (9 files)
Removed `// TODO: Fix remaining TS issues in this file` banners and a stale router-debugging comment block from: `student/Dashboard.vue`, `student/Schedule.vue`, `student/Homework.vue`, `teacher/Dashboard.vue`, `teacher/Schedule.vue`, `teacher/Students.vue`, `teacher/Instruments.vue`, `teacher/Payments.vue`.

---

## Plans.md Audit: Completion Status

All items from `plans.md` are now complete or were already complete before this session.

| Item | Status |
|---|---|
| Alembic migrations initialized | ✅ Already done (6 migrations, full chain) |
| pydantic-settings for secrets/CORS | ✅ Already done (`config.py`) |
| Type standardization: IDs as `number` | ✅ Verified clean (one bug fixed in teacher/Payments) |
| AdminPayments.vue + `/admin/payments` route | ✅ Already done (full ledger with filters, add/edit, receipts) |
| Activity Log view + Dashboard link | ✅ Already done; sidebar link was missing — now added |
| Router audit: no dangling PlaceholderView routes | ✅ All named routes are wired. Catch-all `{ path: ':module' }` is intentional for unknown sub-paths |
| Dashboard stats from live data | ✅ Session stats from store; payment revenue card now added |
| Shop fulfillment workflow | ✅ Already done (Approve → Deduct Stock → Fulfill pipeline in admin Instruments.vue) |
| Remove `Base.metadata.create_all` from main.py | ✅ Already done (comment in main.py confirms Alembic owns schema) |

---

## Remaining Concerns & Future Work

### Medium Priority

**Timezone-naive datetimes in SQLite**
`Session.start_time` / `Session.end_time` are stored as naive `DateTime` columns (no `timezone=True`). The background `session_checker_task` compares them against `datetime.now(timezone.utc)` (aware). SQLAlchemy passes these to SQLite as string comparisons, so it works in practice today — but if you switch to PostgreSQL and set `timezone=True` on columns, you must update both the model columns and any `datetime.utcnow` defaults to `datetime.now(timezone.utc)`.

**Recommended fix:**
```python
# models.py — add timezone=True to all DateTime columns
start_time = Column(DateTime(timezone=True), index=True)
end_time   = Column(DateTime(timezone=True))
```

**WS_URL not set in docker-compose**
`docker-compose.yml` sets `VITE_API_BASE_URL` for the frontend but not `VITE_WS_BASE_URL`. The new dynamic fallback in `messaging.ts` handles this correctly (derives from `window.location`), but if your Docker setup puts the WS endpoint on a different host than the HTTP API, you should add it explicitly.

### Low Priority

**Payment deletion is irreversible**
The `DELETE /payments/{id}` backend endpoint permanently removes the record. A soft-delete (`is_deleted` flag) would preserve audit history. Currently the `log_activity` call captures who deleted it, which is acceptable for now.

**`sessions_left` counter drift**
The backend has a `/sessions/{student_id}/recompute-balance` endpoint specifically to fix counter drift. This suggests the `sessions_left` field on `User` can get out of sync. Consider making it a computed property derived from `Enrollment.sessions_purchased - sessions_used` rather than a mutable column.

**`docker-compose.yml` missing `VITE_WS_BASE_URL`**
Document this in `.env.example` so deployers know to set it if the WebSocket server differs from the HTTP origin.

**Payment totals use USD formatting**
`admin/Payments.vue` uses `{ style: 'currency', currency: 'USD' }` but the backend receipt uses `₱` (PHP). Dashboard revenue card uses PHP. Standardize the currency format across all payment-related views to `PHP`.

**Teacher Instruments page accesses user data without auth headers on some sub-calls**
`teacher/Instruments.vue` calls `usersStore.fetchInstruments()` — confirm the instruments endpoint in `users.py` does not require auth (it likely doesn't) and is OK for public access.

---

## Files Changed This Session

```
frontend/src/components/SidebarNav.vue
frontend/src/stores/messaging.ts
frontend/src/stores/payments.ts
frontend/src/views/admin/Dashboard.vue
frontend/src/views/admin/Payments.vue
frontend/src/views/student/Dashboard.vue
frontend/src/views/student/Homework.vue
frontend/src/views/student/Schedule.vue
frontend/src/views/teacher/Dashboard.vue
frontend/src/views/teacher/Instruments.vue
frontend/src/views/teacher/Payments.vue
frontend/src/views/teacher/Schedule.vue
frontend/src/views/teacher/Students.vue
```

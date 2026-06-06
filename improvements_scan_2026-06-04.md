# SMC System Scan — Improvements & Bug Report
**Date:** 2026-06-04 | **Branch:** dev

---

## ✅ What's Already Done (from plans.md)

Before anything else — the major items in `plans.md` are **already implemented**:

- **Alembic** is set up with 10 versioned migrations (`alembic/versions/`)
- **`pydantic-settings`** is live in `backend/config.py` — secrets, CORS, SMTP, VAPID all env-driven
- **Activity logging** (`log_activity`) is wired into every router: auth, sessions, payments, shop, users
- **`AdminPayments.vue`** and **`AdminActivityLog.vue`** are built and routed at `/admin/payments` and `/admin/activity-log`
- **"View All Activity"** on the Admin Dashboard is already a `<RouterLink>` — not a toast
- **Shop fulfillment** (Approve → Fulfilled flow with atomic stock deduction) is complete
- **TypeScript types** use `number` for all entity IDs — no string/number mismatch found
- **`vue-tsc --noEmit` passes** with zero type errors

---

## 🐛 Bug Fixed This Run

### MobileDock Active State (Fixed ✅)
**File:** `frontend/src/components/MobileDock.vue`

`isActive` was using strict equality (`route.path === path`) for every route. This meant navigating to a sub-page like `/admin/students/42` would de-highlight the "Students" dock item. `SidebarNav.vue` already uses `startsWith` correctly — MobileDock now matches that logic.

```diff
- const isActive = (path: string) => route.path === path
+ const isActive = (path: string) => {
+   if (path === '/admin' || path === '/teacher' || path === '/student') {
+     return route.path === path
+   }
+   return route.path.startsWith(path)
+ }
```

---

## ⚠️ Bugs & Issues to Address

### 1. Naive DateTime Columns (Latent PostgreSQL Bug)
**File:** `backend/models.py` — all `Column(DateTime, ...)` declarations

All timestamp columns use bare `DateTime` (timezone-naive) but the defaults write `datetime.now(timezone.utc)` (timezone-aware). SQLite silently swallows this mismatch. On PostgreSQL it raises `can't compare offset-naive and offset-aware datetimes`.

**Fix:** Change all datetime columns to `DateTime(timezone=True)` across models.py. This is a migration-required change.

---

### 2. MobileDock Admin Tabs Missing Half the Nav
**File:** `frontend/src/components/MobileDock.vue`

The admin dock only surfaces 4 items: Dashboard, Users, Schedule, Students. The sidebar has 8 items including Ledger, Shop, and Activity Log — which have no mobile access at all.

The dock is limited to 4 by design (space), but Ledger and Activity Log are admin-critical and completely inaccessible on mobile.

**Suggested fix:** Swap "Users" for "Ledger" (admins rarely manage users from mobile) or add a "More" overflow item.

---

### 3. Hardcoded Session Checker Thresholds
**File:** `backend/routers/sessions.py` (top of `session_checker_task`)

```python
STALE_THRESHOLD_HOURS = 48
REMINDER_COOLDOWN_HOURS = 24
LOW_STOCK_THRESHOLD = 5  # also in shop.py
```

These are buried as module-level constants. They should live in `config.py` / `.env` so ops can tune them without touching code.

---

### 4. Avatar Upload Is URL-Only (No File Upload Endpoint)
**File:** `frontend/src/components/UserSettingsModal.vue` (line ~126, comment says "mock")

The profile editor has a visual upload area that does nothing — the actual field is a plain text input for a URL. There's no `POST /users/{id}/avatar` endpoint to handle file uploads.

The model (`User.avatar_url`) and schema (`UserUpdate.avatar_url`) support it, but the file-upload pathway is missing. The `uploads/` directory exists and is used for session proofs — the same pattern could serve avatar uploads.

---

### 5. Payment List — No Pagination (Hardcoded limit: 500)
**File:** `backend/routers/payments.py` line 67, `frontend/src/stores/payments.ts`

`fetchPayments` fetches up to 500 records in one shot with no pagination UI. For a growing school this will become a slow page load. The activity log endpoint already has `skip`/`limit` and the ActivityLog.vue already implements client-side pagination — the payments store should mirror that pattern.

---

### 6. `console.error` Calls in Production Stores
**Files:** `frontend/src/stores/schedule.ts`, `shop.ts`, `interactions.ts`, `notification.ts`

Multiple catch blocks call `console.error(err)` in addition to toast notifications — this leaks internal error details to the browser console in production. Consider stripping or guarding these behind a `DEV` flag (`import.meta.env.DEV`).

---

### 7. No Rate Limiting on Profile Update Endpoint
**File:** `backend/routers/users.py` — `PUT /users/{user_id}`

The login endpoint is rate-limited via `slowapi`, but `updateUser` is not. A malicious authenticated user could hammer password changes or spam profile updates. Add `@limiter.limit("10/minute")` to the update endpoint.

---

### 8. `sessions_left` Counter Can Drift on Concurrent Completions
**File:** `backend/routers/sessions.py` — session completion logic (lines ~263–275)

`sessions_left` is decremented with a Python read-modify-write (`student.sessions_left -= 1`) without a `SELECT ... FOR UPDATE` or an atomic SQL update. Under concurrent requests (two admins completing two sessions for the same student simultaneously), both reads see the same starting value and one decrement is lost.

A `/sessions/{id}/recalculate-balance` endpoint already exists as a manual fix, but the root cause remains. Use an atomic SQL update here like the shop's stock deduction does.

---

## 💡 Minor Improvements

| Area | Suggestion |
|---|---|
| `backend/routers/shop.py` | `LOW_STOCK_THRESHOLD = 5` is a magic number — move to `config.py` |
| `frontend/src/views/admin/Instruments.vue` | Product editor doesn't validate that stock ≥ 0 before saving |
| `backend/routers/sessions.py` | `session_checker_task` logs nothing on successful overdue transitions — add an info log so ops can verify the checker ran |
| `frontend/src/stores/payments.ts` | No `updatePayment` optimistic update — the store re-fetches the whole list after each status change |
| `frontend/src/views/admin/ActivityLog.vue` | Action type filter is local-only (filters client-side from 500 records) — pass `action_type` param to backend for true server-side filtering |

---

## 🏗️ Suggested Next Sprint Priorities

1. **Fix naive DateTime → `DateTime(timezone=True)`** — blocking for any PostgreSQL migration
2. **Atomic `sessions_left` decrement** — data integrity issue
3. **Avatar file upload endpoint** — the UI already implies it works
4. **Mobile dock for admin** — Ledger/Activity are completely unreachable on mobile
5. **Rate limit `PUT /users/{id}`**

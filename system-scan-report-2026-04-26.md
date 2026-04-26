# SMC System Scan Report
**Date:** 2026-04-26  
**Branch:** `dev`  
**Scope:** Full codebase audit — backend (FastAPI/SQLAlchemy) + frontend (Vue 3/Pinia)

---

## What Was Done This Session

All items from `plans.md` were implemented:

1. **Confirmed complete (already done):** Alembic initialized, `pydantic-settings` config in place, `ALLOWED_ORIGINS` and `SECRET_KEY` reading from `.env`, all frontend entity IDs already typed as `number`.
2. **Built `AdminPayments.vue`** — Full ledger with KPI cards (total revenue, this month, pending), searchable/filterable table, and a "Record Payment" modal. Route `/admin/payments` registered.
3. **Enhanced payments backend** — Added `student_name` to the `Payment` schema response via eager `joinedload`. Bumped default `limit` to 200.
4. **Built `AdminActivityLog.vue`** — Timeline-style view with summary strip, filters by action type and search, and relative timestamps.
5. **Created `ActivityLog` model** — New `activity_logs` table with `action_type`, `actor_id/name`, `target_type/id`, `description`, `created_at`.
6. **Created `activity` router** with a `log_activity()` helper. Registered at `/activity-log`. Wired into `session_scheduled`, `session_completed`, `session_force_completed`, and `payment_created` events.
7. **Fixed Dashboard "View All Activity" button** — replaced the `toast.info(…)` placeholder with a `<RouterLink to="/admin/activity-log">`.
8. **Router audit** — confirmed all admin sidebar nav items (`Dashboard`, `Schedule`, `Students`, `Teachers`, `Ledger`, `Shop`) have explicit named routes with real components. No sidebar link falls through to `PlaceholderView`.
9. **Updated `payments.ts` store** — added `student_name`, `totalRevenue`, `pendingCount`, `completedCount` getters.

---

## Session 2 Updates (2026-04-26 — scheduled run)

10. **Alembic migration for `activity_logs`** — The `ActivityLog` model added in session 1 had no migration, so the table would never exist in a clean deployment. Created `backend/alembic/versions/f3a1b2c4d5e6_add_activity_logs_table.py` chaining off `ded95c6d7f14`.
11. **Bug fix: `read_student_payments` wrong filter column** — `backend/routers/payments.py` `/payments/student/{student_id}` was filtering on `Payment.id == student_id` instead of `Payment.student_id == student_id`. This meant the endpoint returned at most one record (the one whose PK happened to equal the student's ID). Fixed.
12. **Cleanup: redundant double `db.refresh()`** — `create_payment` called `db.refresh(db_payment)` twice before immediately re-querying with `joinedload`. Removed the first extra call.

---

## Bugs & Issues Found

### 🔴 Critical

**1. `record_past_session` doesn't update analytics**
- **File:** `backend/routers/sessions.py` ~line 92
- **Problem:** When an admin records a past session manually (status `completed`), it skips the `sessions_left` decrement and `enrollment.sessions_used` increment that `complete_session_as_admin` performs. Student counters will be out of sync.
- **Fix:** After `db.commit()`, add the same student/enrollment update block that exists in `complete_session_as_admin` (lines 577–586).

**2. No file type or size validation on proof/avatar uploads**
- **Files:** `backend/routers/sessions.py` ~line 688, `backend/routers/users.py`
- **Problem:** Any file type and any size is accepted. A user could upload a 500 MB file or a malicious `.exe`.
- **Fix:** Check `file.content_type in {"image/jpeg", "image/png", "image/webp"}` and read up to a max size (e.g. 10 MB), returning HTTP 400 otherwise.

---

### 🟠 High

**3. `sessions_left` on `User` and `Enrollment` can drift**
- **Files:** `backend/models.py`, `backend/routers/sessions.py`
- **Problem:** `sessions_left` is stored both on the `User` record and computed from `Enrollment.sessions_purchased - sessions_used`. These can diverge if enrollments are edited directly or if the decrement block is skipped (see bug #1). There's no single source of truth.
- **Fix:** Either remove `User.sessions_left` and derive it entirely from enrollments via a `@property`, or add a DB trigger / application-level validator that keeps them in sync.

**4. Default password `"password123"` used in production startup**
- **Files:** `backend/main.py` line 47, `backend/routers/users.py` line 71
- **Problem:** The auto-created admin and any teacher without a supplied password get `"password123"`. If this service is ever internet-facing, it's an easy takeover.
- **Fix:** Move default credentials to `.env` or generate a random password on first boot and log it once (then require change). At minimum, never use a well-known default in a web app.

**5. Missing `PATCH /payments/{id}` endpoint**
- **File:** `backend/routers/payments.py`
- **Problem:** The `payments.ts` store has an `updatePaymentStatus` action that calls `PATCH /payments/{id}`, but this endpoint doesn't exist. Calling it returns 404/405.
- **Fix:** Add the endpoint or remove the dead store action.

---

### 🟡 Medium

**6. N+1 query patterns in `sessions.py`**
- **File:** `backend/routers/sessions.py`
- **Problem:** Most session queries return raw `models.Session` objects, then `map_session()` accesses `.student`, `.teacher`, `.proofs`, `.homeworks`, `.instrument` — all lazy-loaded. On a list of 100 sessions, this is 500+ queries.
- **Fix:** Add `options(selectinload(models.Session.proofs), selectinload(models.Session.homeworks), joinedload(models.Session.instrument))` to the bulk fetch queries.

**7. `models.Base.metadata.create_all` still runs on every startup**
- **File:** `backend/main.py` line 18
- **Problem:** With Alembic managing migrations, `create_all` can silently create columns that Alembic doesn't know about, causing migration drift and missed `ALTER TABLE` operations.
- **Fix:** Remove `models.Base.metadata.create_all(bind=engine)` from `main.py`. Let Alembic be the sole DDL authority. Run `alembic upgrade head` as part of the startup script / Dockerfile.

**8. `alembic.ini` has placeholder DB URL**
- **File:** `backend/alembic.ini`
- **Problem:** `sqlalchemy.url = driver://user:pass@localhost/dbname` — the placeholder is never overridden by the real database URL in `env.py`, so Alembic CLI commands will fail.
- **Fix:** In `backend/alembic/env.py`, set `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL or "sqlite:///./sql_app.db")` to pull from the app settings.

**9. `record_past_session` not wired into activity log**
- **File:** `backend/routers/sessions.py`
- **Problem:** Manual session entries bypass the `log_activity()` call added to `create_session` and `complete_session_as_admin`, so they're invisible in the audit trail.
- **Fix:** Add `log_activity(db, "session_manual_entry", ...)` after the commit in `record_past_session`.

---

### 🔵 Low / Quality

**10. 30 `console.log` statements remain in frontend**
- **Scope:** `frontend/src/` — stores and views
- **Problem:** Development logs will appear in production builds, leaking internal state and cluttering DevTools.
- **Fix:** Do a pass with `grep -rn "console.log" src/` and remove or replace with proper error handling.

**11. Widespread `any` typing in stores and admin views (~113 instances)**
- **Scope:** `frontend/src/stores/*.ts`, `frontend/src/views/admin/*.vue`
- **Problem:** Heavy use of `: any` defeats TypeScript's value. Runtime shape mismatches get silently swallowed.
- **Fix:** Replace the most common `any` hits — particularly session objects in `Dashboard.vue` and `schedule.ts` — with the `Session` type already defined in `@types`.

**12. `.env` file is committed to the repo**
- **File:** `backend/.env`
- **Problem:** The `.env` containing `SECRET_KEY` is tracked in git. Rotating the key requires a commit.
- **Fix:** Add `backend/.env` to `.gitignore`, commit a `backend/.env.example` with placeholder values instead.

**13. Shop `fulfilled` status is not in the frontend state machine**
- **Files:** `frontend/src/views/admin/Instruments.vue`, `frontend/src/views/student/Shop.vue`
- **Problem:** The backend transitions orders to `fulfilled`, but the frontend color/label maps likely don't handle this status, causing orders to show as grey/unknown after fulfillment.
- **Fix:** Add `fulfilled` to the status badge/color maps in shop views.

**14. `sessionsLeft` update not triggered after session completion on the client**
- **File:** `frontend/src/stores/schedule.ts`, `frontend/src/stores/users.ts`
- **Problem:** When a session is completed in the UI, `_upsertSession` updates the session status reactively, but `usersStore` is not re-fetched, so the student's displayed `sessionsLeft` count stays stale until a full page refresh.
- **Fix:** After completing a session, call `usersStore.fetchUsers()` or update the student record in-place with `student.sessionsLeft--`.

---

## Summary Table

| # | Severity | Area | Issue |
|---|----------|------|-------|
| 1 | 🔴 Critical | Backend | `record_past_session` skips analytics update |
| 2 | 🔴 Critical | Backend | No file type/size validation on uploads |
| 3 | 🟠 High | Backend | `sessions_left` dual-source drift |
| 4 | 🟠 High | Backend | Hardcoded `"password123"` default |
| 5 | 🟠 High | Backend | Missing `PATCH /payments/{id}` endpoint |
| 6 | 🟡 Medium | Backend | N+1 queries in session list endpoints |
| 7 | 🟡 Medium | Backend | `create_all` runs alongside Alembic |
| 8 | 🟡 Medium | Backend | Alembic `alembic.ini` has placeholder URL |
| 9 | 🟡 Medium | Backend | `record_past_session` not activity-logged |
| 10 | 🔵 Low | Frontend | 30 `console.log` calls in production build |
| 11 | 🔵 Low | Frontend | ~113 `: any` usages weaken type safety |
| 12 | 🔵 Low | DevOps | `.env` committed to git |
| 13 | 🔵 Low | Frontend | `fulfilled` order status not styled |
| 14 | 🔵 Low | Frontend | `sessionsLeft` stale after client-side completion |

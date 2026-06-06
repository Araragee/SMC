# SMC Portal — Improvement Scan
**Date:** 2026-05-23  
**Branch:** `dev`  
**Scope:** Full-stack review after prior backlog items resolved

---

## ✅ Resolved This Session (from previous scan)

- `datetime.utcnow()` fully eliminated from all active router and dependency files
- `sessions_left` drift — admin recalculate endpoint added
- `DELETE /enrollments/{id}` with sessions_left rollback
- Receipt currency `$` → `₱` across all three occurrences
- `read_users` / `read_users_by_role` limit raised to 500
- `mapProduct` null category coerced to `null` (not `undefined`)
- Toast errors surfaced for `fetchProducts`, `fetchMyOrders`, `fetchAllOrders`
- Redundant `fetchProducts()` removed from `saveProduct` in Instruments.vue

---

## 🔍 New Issues Identified

### High Priority

**`datetime.utcnow()` still present in non-router files**  
The following files were not updated (they are scripts / model defaults, lower blast-radius, but still deprecated in Python 3.12):
- `backend/models.py` — all `default=datetime.datetime.utcnow` Column defaults (×14 occurrences). SQLAlchemy accepts a callable here; replacing with `lambda: datetime.now(timezone.utc)` would make these timezone-aware.
- `backend/dependencies.py` — now fixed.
- `backend/seed_data.py` / `backend/seed_comprehensive.py` — seeding scripts only (not runtime critical).
- `backend/routers/auth.py` line 325 — **fixed this session**.

**No token refresh flow — hard logout on expiry**  
`main.ts` catches 401s and immediately calls `auth.logout()` + redirects to `/login`. There is no refresh token endpoint wired up despite `build_token_pair` presumably returning one. Users mid-session get hard-kicked when their access token expires. A `POST /auth/refresh` endpoint + interceptor retry would fix this.

**`window.prompt` / `window.confirm` used for destructive actions**  
Six locations across admin views use native browser dialogs for proof rejection reasons and user deactivation confirmation. These are unstyled, block the JS thread, and cannot be dismissed with keyboard navigation. Should be replaced with proper modal components consistent with the rest of the UI.

### Medium Priority

**`recalculate-sessions` endpoint not wired to any frontend UI**  
The new `POST /students/{id}/recalculate-sessions` backend endpoint has no trigger in the admin UI. Should be added as a button (e.g. in `StudentRecords.vue` or the Students detail panel) so admins can use it without needing API access.

**`DELETE /enrollments/{id}` not wired to frontend**  
Same situation — endpoint exists but no UI exposes it. Enrollment deletion should appear in the student enrollment list in `StudentRecords.vue`.

**Order notification link is hard-coded to `/admin/instruments`**  
`backend/routers/shop.py` line 141: the admin notification for a new order links to `/admin/instruments`. If the orders tab is ever split into its own route this will silently be wrong. Should be a constant or derived from a config.

**`session_checker_task` queries run every 60 s unconditionally**  
The overdue/reminder queries fire regardless of whether any sessions exist. Low impact now, but adds unnecessary DB churn at scale. A simple `EXISTS` guard before the full query, or backing off to a longer interval during off-hours, would help.

**`backend/models.py` — `SessionThread` foreign keys not indexed**  
`SessionThread.session_id` and `SessionThread.conversation_id` are `unique=True` but do not have `index=True`. Unique constraints create an implicit index in most DBs, but being explicit is safer if the DB is ever swapped.

**`TeacherPayments.vue` — scope is students only, no totals row**  
Teacher payments view shows payments for linked students but has no aggregate row (total collected this month, etc.). The admin Ledger has these; teachers have a bare list. Low impact but a UX gap.

### Low Priority

**`backend/seed_data.py` / `seed_comprehensive.py` — `datetime.utcnow()` not updated**  
Only affects development/seeding workflows, not production runtime. Still worth updating to silence Python 3.12 deprecation warnings during `--reload` dev runs.

**`fetchUsers()` in `users.ts` sends no auth header**  
`GET /users/` requires `require_admin`. The store calls it without `{ headers: authHeaders() }`. This works because `axios` has a default `Authorization` header set at login time via `axios.defaults.headers.common`, but it's inconsistent with other calls in the same store that pass `authHeaders()` explicitly. Should be made explicit for clarity and resilience.

**`schedule.ts` — `console.error` present in 7 catch blocks**  
These blocks correctly set `this.error` (which views can render), so the pattern is better than `shop.ts` was. However, `this.error` is not actually displayed in most views that use the schedule store — they just show a blank list. A single error banner component wired to `scheduleStore.error` would surface failures to users.

**`RecurringSessionModal.vue` is untracked / unreferenced**  
`frontend/src/components/RecurringSessionModal.vue` exists in the working tree but is not imported anywhere. Either wire it up or remove it to avoid confusion.

**No `CONTRIBUTING.md` or dev-setup guide**  
The repo has `DOCKER.md` and `ACCOUNTS.md` but no guide covering: local dev without Docker, running migrations, seeding, and running tests. Low urgency but useful for onboarding.

---

## 🏗️ Structural Observations (No Change Required Now)

- **SQLite → Postgres migration readiness:** The codebase uses `Integer` PKs, `DateTime` (not `TIMESTAMP WITH TIME ZONE`), and no DB-specific SQL. A move to Postgres would require enabling timezone awareness on all datetime columns and re-running Alembic — feasible but not trivial.
- **No rate limiting on shop endpoints:** `slowapi` is set up on `/login` and `/refresh`, but shop order creation has no rate limit. A student could spam order creation.
- **Push subscription table exists but `push-sw.js` is untracked:** `backend/models.py` has a `PushSubscription` model and `backend/routers/push.py` exists, but `frontend/public/push-sw.js` is untracked and the push flow is not fully wired in the frontend stores. Either complete or remove the feature to avoid dead code.

---

## ✅ Verification Baseline

- All Python files in `backend/routers/` and `backend/dependencies.py` — AST-parse clean
- `npx vue-tsc --noEmit` — 0 errors
- No `datetime.utcnow()` in any active router or dependency file

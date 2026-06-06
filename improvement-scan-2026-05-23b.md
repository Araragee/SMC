# SMC Portal — Improvement Scan
**Date:** 2026-05-23 (Run 2)
**Branch:** `dev`
**Scope:** Full-stack review after second backlog pass

---

## ✅ Resolved This Session

- `datetime.utcnow()` eliminated from `backend/models.py` (18 occurrences → 0)
- `deleteEnrollment` and `recalculateSessions` wired to `StudentRecords.vue` (store + UI)
- `window.prompt` / `window.confirm` replaced across all 6 call sites with `useDialog()` composable + `AppDialogHost.vue`
- Token refresh flow: hard logout on 401 replaced with silent retry via `POST /auth/refresh`; concurrent-request queue pattern prevents duplicate refresh races

---

## 🔍 Remaining Issues

### High Priority

**`datetime.utcnow()` still in seeding scripts**
`backend/seed_data.py` and `backend/seed_comprehensive.py` each have 1 occurrence. Not runtime-critical but emits Python 3.12 deprecation warnings on `--reload` dev runs. Replace with `datetime.now(timezone.utc)`.

**`RecurringSessionModal.vue` is imported but never used outside `Schedule.vue`**
`frontend/src/views/admin/Schedule.vue` imports `RecurringSessionModal` but the component is neither referenced in its template nor the router. The `.vue` file itself is untracked. Either wire it into the schedule workflow or remove it to prevent dead-code confusion.

**`push-sw.js` is untracked and push feature is incomplete**
`frontend/public/push-sw.js` is untracked. `backend/models.py` has `PushSubscription`, `backend/routers/push.py` exists with subscribe/unsubscribe endpoints, but there is no frontend store action or UI to register a push subscription. The feature is ~60% implemented — either complete it (register SW, subscribe, call `/push/subscribe`) or stub it out behind a feature flag so the dead code doesn't mislead.

### Medium Priority

**`session_checker_task` queries run every 60 s unconditionally**
`backend/routers/sessions.py` line 125: `await asyncio.sleep(60)` runs overdue checks and reminder notifications regardless of whether any sessions exist or what time it is. At production scale (or during overnight off-hours) this creates unnecessary DB churn. Consider:
- An `EXISTS` guard before the full query
- Backing off to 5 min during 00:00–06:00 local time

**`TeacherPayments.vue` lacks aggregate totals**
The teacher payments view renders a bare list with no total-collected row, no monthly breakdown, and no export. The admin Ledger has these. Low usage impact now, but a gap that teachers notice.

**Order notification link hard-coded to `/admin/instruments`**
`backend/routers/shop.py` ~line 141: the admin notification for a new shop order links to `/admin/instruments`. If the orders tab is split into its own route, this will silently break. Should reference a config constant or settings value.

**`fetchUsers()` in `users.ts` inconsistently passes auth headers**
Most store actions pass `{ headers: authHeaders() }` explicitly. `GET /users/` does not because `axios.defaults.headers.common` carries the token globally — but the inconsistency is a maintenance hazard if the default header is ever cleared mid-session or the store is used in a context where it isn't set. Add explicit headers for consistency.

**No aggregate error banner for `scheduleStore.error`**
`schedule.ts` sets `this.error` in 7+ catch blocks, and views that use the store render blank lists on failure rather than surfacing the error. A single `<div v-if="scheduleStore.error">` banner in the shared layout (or per-view) would make failures visible to users.

### Low Priority

**`console.error` remains in `interactions.ts` (5 catch blocks)**
The newly added `deleteEnrollment` and `recalculateSessions` actions use `toast.error`, but the older actions (`fetchStudentEnrollments`, `createEnrollment`, `assignHomework`, `completeHomework`, `uploadImageProof`) still only call `console.error` or set `this.error` silently. Users see no feedback on failure for those actions. Add `toast.error` calls consistent with the newer actions.

**`schedule.ts` has 7 `console.error` catch blocks with no toast**
Same pattern — errors are swallowed or set to `this.error` but never surfaced as user-visible toasts.

**Seeding scripts emit `utcnow` deprecation warnings**
`backend/seed_data.py` and `backend/seed_comprehensive.py` (1 occurrence each). Only affects development workflow, not production.

**No `CONTRIBUTING.md` / dev setup guide**
Repo has `DOCKER.md` and `ACCOUNTS.md` but nothing covering: running without Docker, running Alembic migrations, seeding, running tests. Low urgency for solo development.

---

## 🏗️ Structural Observations

- **SQLite → Postgres readiness:** Codebase is portable — Integer PKs, no raw SQL, Alembic in place. Main migration work would be enabling timezone-aware DateTime columns. Feasible but not urgent.
- **No rate limiting on shop endpoints:** `slowapi` is wired for `/login` and `/auth/refresh` but not for `POST /orders/`. A student could spam order creation. Low risk in current school context.
- **`TOTP secret stored in plaintext:** `models.py` and `auth.py` both have `TODO: encrypt totp_secret at rest`. If the DB is ever leaked, all enrolled 2FA secrets are exposed. Fernet encryption via a `SECRET_KEY`-derived key is the recommended fix.

---

## ✅ Verification Baseline

- `npx vue-tsc --noEmit` — 0 errors
- `python3 -c "import ast; ast.parse(open('backend/models.py').read())"` — OK
- `grep -c 'utcnow' backend/models.py` — 0
- `grep -rn "window\.confirm\|window\.prompt" frontend/src/` — 0 active call sites

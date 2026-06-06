# SMC Codebase Scan Report
**Date:** 2026-06-04 | **Branch:** `dev`

---

## Plans.md Status

All items in `plans.md` are **already fully implemented** on the `dev` branch. No work needed there.

| Item | Status |
|---|---|
| Alembic migrations | ✅ Done — full version history in `backend/alembic/versions/` |
| `pydantic-settings` config | ✅ Done — `backend/config.py` with `.env` support |
| Frontend ID types as `number` | ✅ Done — all IDs in `frontend/src/types/api.ts` are `number` |
| `AdminPayments.vue` + `/admin/payments` route | ✅ Done |
| `ActivityLog.vue` + `/admin/activity-log` route | ✅ Done |
| "View All Activity" → RouterLink (not a toast) | ✅ Done — `Dashboard.vue` line 1011 |
| No `PlaceholderView.vue` references | ✅ Confirmed |
| `Base.metadata.create_all` removed from `main.py` | ✅ Done |
| Dashboard stats use live store data | ✅ Confirmed |

---

## Bugs Fixed This Run

### 1. Missing low-session notifications after admin session completion
**File:** `backend/routers/sessions.py` — `complete_session_as_admin`

`record_past_session` (manual entry) correctly notified students when sessions hit 0 or 1 remaining. `complete_session_as_admin` (both proof approval and force-complete paths) did not. Students would silently run out of sessions with no warning.

**Fix:** Added the same notification block to `complete_session_as_admin` after decrementing `sessions_left`.

---

### 2. `update_session` triggered lazy SQL queries on return
**File:** `backend/routers/sessions.py` — `update_session`

After commit + `db.refresh()`, `map_session()` accessed `.proofs` and `.homeworks` via lazy loads, causing 2 extra untracked queries per edit. Now re-fetches with `_session_eager_options()` (same pattern used in bulk list endpoints).

---

### 3. `payments` list endpoint had unconstrained `limit` parameter
**File:** `backend/routers/payments.py` — `read_payments`

`sessions.py` used `Query(default=500, le=1000)` but `payments.py` had bare `limit: int = 500` with no upper bound validation. A caller could pass `limit=999999` and dump the full table. Fixed to `Query(default=500, le=1000)` and `skip` to `Query(default=0, ge=0)`.

---

## Remaining Issues / Recommendations

### Medium Priority

**`delete_session` does not roll back `sessions_left`**
If an admin deletes a `completed` session, the student's `sessions_left` counter is not restored. The `POST /sessions/{id}/recalculate-sessions` endpoint exists as a manual fix, but there's no automatic rollback. Recommendation: add rollback logic inside `delete_session` (mirror the decrement logic in reverse), or at minimum document this as requiring a manual recalculate.

**`SessionEdit` schema allows setting any mutable field via `PUT /sessions/{id}` without status validation**
The admin edit endpoint applies `model_dump(exclude_unset=True)` to the DB object directly. Fields like `teacher_id`, `student_id`, and `instrument_id` can be changed on sessions in any status, including `completed` ones. The optimistic version lock is present but there's no guard on terminal statuses. Consider rejecting edits on `completed`, `cancelled`, or `rejected` sessions.

### Low Priority

**`map_session` exposes only the first proof URL in `proof_image_url`**
`session_dict['proof_image_url'] = db_session.proofs[0].image_url if db_session.proofs else None` returns only the first proof. This field is redundant since the full `proofs` array is already serialized — any consumer relying on `proof_image_url` alone would miss additional proofs. Safe to deprecate the field.

**`session_checker_task` bumps versions on reminder notifications**
`_bump_version(s)` is called when marking sessions as `notified_24h`/`notified_12h`. This increments the optimistic lock counter, which means a frontend tab open during that minute would get a stale-version 409 on the next user action. Consider a separate `notification_version` counter or skip `_bump_version` for notification-only updates.

**`/debug/users` endpoint visible in API docs when `DEBUG=False`**
The endpoint correctly returns 404 when `DEBUG` is off, but it still appears in the OpenAPI schema (`/docs`). If external API exposure matters, add `include_in_schema=settings.DEBUG` to the route decorator.

### Architecture Notes

**`sessions_left` counter drift is a known risk**
The counter is mutated in three places: `record_past_session`, `complete_session_as_admin`, and enrollment create/delete. The `recalculate_sessions_left` endpoint exists to fix drift but must be triggered manually. For correctness at scale, consider deriving `sessions_left` from `enrollment.sessions_purchased - enrollment.sessions_used` at query time rather than maintaining a denormalized counter.

**No frontend `delete session` UI**
`DELETE /sessions/{id}` exists on the backend (admin only) but no frontend component calls it. Sessions can only be cancelled/rejected, not hard-deleted, from the UI. This is likely intentional for audit trail, but the endpoint should be documented as admin-only internal use.

---

## TypeScript Build Note

`npm run build` fails in the sandbox due to a missing `rolldown-binding.linux-arm64-gnu.node` native binary — an ARM64 platform issue with the `rolldown` package. This is an environment issue, not a code issue. `npx vue-tsc --noEmit` exits 0 (no type errors).

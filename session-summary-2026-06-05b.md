# Scheduled Run Summary — 2026-06-05 (Run 2)

All `plans.md` items were already complete from prior runs. This run addressed the 12 issues identified in the `improvements_scan_2026-06-05.md` bug/improvement scan.

---

## Changes Made

### 🔴 Bugs Fixed

**Bug #2 — Student can propose sessions to any teacher**
`backend/routers/sessions.py` → `propose_session_as_student()`
Added a `TeacherStudent` assignment check before creating the session. Returns `HTTP 403` if no assignment exists.

**Bug #3 — No `sessions_left` gate on student proposals**
Same function. Added a guard that returns `HTTP 400` if `sessions_left` is not `None` and is ≤ 0.

### 🟡 Medium Fixes

**Fix #4 — Daily token purge added to background loop**
`backend/routers/sessions.py` → `session_checker_task()`
Added a 24-hour cadence token purge directly inside the checker loop (tracked via `_last_token_purge` global). Prevents unbounded growth of `RefreshToken`/`PasswordResetToken` rows between server restarts.

**Fix #5 — Activity Log server-side pagination**
`backend/routers/activity.py`: Added a `/count` endpoint and a `search` query parameter to the list endpoint. Default `limit` dropped from 500 → 25.
`frontend/src/views/admin/ActivityLog.vue`: Rewrote data fetching to use server-side pagination with debounced search. Both `action_type` filter and text search are now sent to the backend. Pagination footer uses ellipsis style for large page counts.

**Fix #7 — Redundant `status: 'scheduled'` removed from booking payload**
`frontend/src/stores/schedule.ts` → `bookSession()`. Field removed; backend enforces this anyway.

**Fix #8 — Token purge logs even when nothing is removed**
`backend/main.py` → `_purge_stale_tokens()`. Added `else` branch: `"Token purge completed: nothing to remove."` so startup confirmation is always visible.

### 🟢 Low / Quality-of-Life

**Fix #9 — Exception logging in session checker**
`backend/routers/sessions.py` → `session_checker_task()`. Replaced bare `print()` with `logger.error(..., exc_info=True)` for full stack traces.

**Fix #12 — Missing fulfilled notification in shop**
`backend/routers/shop.py` → `update_order_status()`. Added explicit `notify_users()` call on `approved → fulfilled` transition with pickup message.

---

## Verification

- `vue-tsc --noEmit`: no TypeScript errors
- `python3 -c "import ast; ast.parse(...)`: all 4 modified Python files parse cleanly
- Rolldown native binary unavailable in this ARM64 sandbox (existing environment constraint, not a code regression)

---

## Deferred (Not Implemented)

**Bug #1 / Fix #11 — `instrument_id` not sent in session proposals**
Requires a new instrument picker UI component in the session creation modal across three paths (admin-book, student-propose, teacher-propose). Deferred — needs UI design decision from Dave before implementing.

**Fix #6 — No enrollment check on admin session booking**
Adding hard enforcement would block legitimate admin overrides. Deferred pending guidance on whether this should be a hard block or a soft warning.

**Fix #10 — Activity Log CSV export**
Medium scope. Deferred to next run.

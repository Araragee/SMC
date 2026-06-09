# SMC Audit Implementation — Progress & Resume Guide

> **For the next session:** read this top-to-bottom. Sections 1-2 are reference (what's already shipped — don't redo it). Sections 3-7 are the queue of work; pick whichever phase the user names.

Companion docs in the same folder:
- `audit_2026-06-09.md` — the original audit report (problems and rationale).
- `implementation_plan_2026-06-09.md` — the six-phase rollout plan with decision points.

---

## 1. Status snapshot

| Phase | Theme | Status | Tests | Commit script |
|---|---|---|---|---|
| 1 | Foundation & safety net | **Done** | +16 (29 total) | `.phase1_commit.sh` |
| 2 | Privacy & auth hardening | **Done** | +21 (50 total) | `.phase2_commit.sh` |
| 3 | Unblock the user | Not started | — | — |
| 4 | Reliability & data integrity | Not started | — | — |
| 5 | UI/UX polish & accessibility | Not started | — | — |
| 6 | Stretch & nice-to-haves | Not started | — | — |

**Single Alembic head:** `k8l9m0n1o2p3` (Phase 2 migration). Fresh-DB `alembic upgrade head` and existing-prod stamp both succeed.

**To commit pending work to the user's machine** (sandbox can't write `.git/`):
```bash
cd "/Users/dex/Desktop/Essentials x Coding/SMC"
bash .phase1_commit.sh       # if not already committed
bash .phase2_commit.sh
```

---

## 2. What was done

### Phase 1 — Foundation & safety net

**Problem:** alembic had three independent heads — `alembic upgrade head` failed on fresh DBs. Pydantic schemas had no length caps anywhere. Session-window endpoints accepted past dates, 0-second sessions, and 12-hour sessions. No tests covered the session state machine. Several model columns had `MIGRATION NOTE: run alembic revision` comments and no actual migrations.

**What changed:**

*Migrations* (`backend/alembic/`)
- Rebased the legacy `e0c69a750bfa` chain onto `0001` baseline so alembic walks `0001` first (the comprehensive snapshot) on fresh installs.
- Wrapped every legacy migration in idempotency checks (`_has_table`, `_has_column`, `_has_index`) so they no-op when 0001 already created the schema.
- Added `phase1_helper` no-op revision and merge migration `j7k8l9m0n1o2_phase1_merge_and_indexes.py` (parents: `phase1_helper`, `d1e2f3a4b5c6`, `i6j7k8l9m0n1`).
- New indexes: `ix_sessions_status_end_time` (overdue-checker query), `ix_notifications_created_at` (planned 90-day purge).
- `env.py`: adds `versions/` to `sys.path` (kept for potential future imports).

*Schemas* (`backend/schemas.py`)
- Module-level length constants: `NAME_LEN`, `SHORT_NOTE_LEN`, `NOTE_LEN`, `LONG_NOTE_LEN`, `URL_LEN`, `EMAIL_LEN`, `USERNAME_LEN`, `PHONE_LEN`, `ADDRESS_LEN`, `TOKEN_LEN`, `LONG_TOKEN_LEN`.
- Annotated aliases: `NameStr`, `OptName`, `OptShortNote`, `OptNote`, `OptLongNote`, `OptUrl`, `OptPhone`, `OptAddress`, `OptDateStr`, `EmailStr`, `UsernameStr`.
- Applied `Field(max_length=…)` to every user-facing string in Session, Payment, User, Notification, Homework, Order, Message, Conversation, ActivityLog, push subscription, auth, refresh schemas.
- `BulkActionRequest.session_ids` capped at 100; `OrderCreate.items` at 100; `RecurringSessionCreate.skip_dates` at 52; age 0-150; price/stock bounded.
- Same treatment to `PaymentUpdate` in `routers/payments.py`.

*Session window validator* (`backend/routers/sessions.py`)
- `_validate_session_window(start, end, *, allow_past=False)` enforces: not in past (60 s clock-skew tolerance), end > start, duration 15-240 min.
- Wired into `record_past_session` (with `allow_past=True`), `create_recurring_sessions`, `create_session`, `propose_session_as_student`, `propose_session_as_teacher`, `counter_session_as_teacher`, `counter_session_as_student`, `update_session`.

*Docs*
- `_check_version` docstring expanded: spells out the no-bump-on-notification-only-updates contract (so new fields get put in the right bucket).

*Bug fix caught while testing*
- `complete_session_as_admin` and `bulk_session_action` compared SQLite-naive `end_time` to tz-aware `datetime.now(UTC)` — `TypeError`. Coerce to UTC before comparison.

*Tests* (`backend/test_session_state_machine.py`, 16 cases)
- Legal transitions (propose → approve, three-step negotiation → scheduled, admin reject).
- Illegal transitions return 409.
- Version conflicts.
- Overlap conflicts.
- Window validation (past, too-short, too-long, end ≤ start).
- Force-complete: 400 too early, succeeds after 24h with `sessions_left` decrement.
- Default end-time fill (start + 1h when omitted).
- `backend/conftest.py`: Python 3.10 shim for `datetime.UTC` (prod targets 3.11+; sandbox is 3.10).

### Phase 2 — Privacy & auth hardening

**Problem:** `/uploads/proofs/*` was wide open (any leaked URL = view any student's proof). Refresh token in `localStorage` (any XSS = takeover). Default-admin `.env` password could be used indefinitely. No "forgot password" UI even though the backend endpoints existed. `debug_users` was only hidden from OpenAPI, not actually disabled. `nudge` endpoint had no participant check. No security headers.

**What changed:**

*Auth-gated upload routes* (`backend/utils/signed_urls.py`, `backend/routers/uploads.py`)
- HMAC-SHA256 signed URLs with `?exp=` + `?sig=` (32-hex truncated, 1h TTL).
- Path bound into the HMAC so a sig for `/uploads/proofs/A.png` can't be replayed against `/uploads/proofs/B.png`.
- `GET /uploads/proofs/{filename}` and `GET /uploads/homework/{filename}` route handlers verify signature AND check the caller is admin OR a participant of the session/homework that owns the file.
- Strict 32-hex filename regex + `resolve()` containment check blocks path traversal.
- `main.py`: removed wide-open `/uploads` mount; only `/uploads/shop` (product images) is public via StaticFiles now.
- `sessions.py:map_session` signs proof URLs and (nested) homework URLs. `create_session_proof` and `upload_homework_file` return signed URLs in the response body. Same for homework GET/POST endpoints (helper `_serialize_homework`).
- 9 dedicated tests in `test_uploads_auth.py`.

*Refresh token in HttpOnly cookie*
- `config.py`: new `REFRESH_COOKIE_NAME` (`smc_rt`), `REFRESH_COOKIE_PATH` (`/auth` so cookie never accompanies API calls), `REFRESH_COOKIE_SECURE` (false in dev, **true in prod**), `REFRESH_COOKIE_SAMESITE` (`lax`).
- `routers/auth.py`: `_set_refresh_cookie`, `_clear_refresh_cookie`, `build_token_pair_with_cookie` helpers. `_read_refresh_token` — **body wins over cookie** (preserves replay-revoke chain for legacy clients; the security gain is that JS can't read HttpOnly cookies, not that JS can't choose to omit the body).
- All token-issuing endpoints (`/login`, `/users/`, `/auth/refresh`, `/auth/2fa/verify`) set the cookie via `build_token_pair_with_cookie`.
- `/auth/refresh` and `/auth/logout` accept the token via body OR cookie. `LogoutRequest` and `RefreshRequest` schemas now have `refresh_token: Optional`.
- `/auth/logout` always clears the cookie even on no-token logout.
- `frontend/src/main.ts`: `axios.defaults.withCredentials = true`.
- `frontend/src/stores/auth.ts`: login/2FA-verify no longer persist refresh_token to localStorage; legacy values are purged on next login/refresh; `refreshAccessToken` posts no body (cookie does the work); `logout` calls `/auth/logout` first.
- 5 tests in `test_refresh_cookie.py`.

*must_change_password gate*
- `models.py`: new boolean column (default false) on User.
- `0001_initial_schema.py` updated to include the column for fresh installs.
- `alembic/versions/k8l9m0n1o2p3_phase2_must_change_password.py` (idempotent) — adds column to existing prod DBs.
- `main.py:_seed_defaults` sets the flag true on the seeded admin so the `.env` temp password is single-use.
- `POST /auth/change-password` (new endpoint): verifies current password (`try/except` around `pwd_context.verify` so a None hash from tests returns 400 not 500), clears the flag, revokes all refresh tokens for the user, clears cookie, activity-logs.
- `/auth/reset-password` also clears the flag.
- `schemas.py`: User exposes `must_change_password`; new `ChangePasswordRequest` with `StrongPassword` validator.
- `frontend/src/views/ChangePassword.vue` (new) + `frontend/src/router/index.ts` redirect-gate: any authenticated user with the flag is redirected to `/change-password` before they can reach any role dashboard.
- `frontend/src/types/index.ts`: `User.mustChangePassword` field.
- `frontend/src/stores/auth.ts`: hydrates `mustChangePassword` from server response in both login and 2FA-verify paths.

*Forgot/Reset password UI*
- `frontend/src/views/ForgotPassword.vue` (new) — enumeration-resistant (same confirmation regardless of email existence).
- `frontend/src/views/ResetPassword.vue` (new) — client-side strength check mirrors backend `_validate_password_strength`.
- `frontend/src/views/Login.vue`: "Forgot your password?" link.
- `frontend/src/router/index.ts`: `/forgot-password` and `/reset-password` public routes (use `AuthLayout`).

*Security headers middleware* (`backend/main.py:SecurityHeadersMiddleware`)
- Adds on every response: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Strict-Transport-Security` (only on HTTPS), `Content-Security-Policy` (starter policy — keeps `unsafe-inline` on style/script because Vue runtime needs it; tighten later).
- 1 test pins the headers on `/health`.

*`/debug/users` actually disabled* (`backend/routers/users.py`)
- Route is now wrapped in `if settings.DEBUG:` — when False, the route is **not registered** (previously it was just hidden from OpenAPI).
- 1 test pins the 404 in the default (non-debug) test env.

*Nudge authorization* (`backend/routers/sessions.py:nudge_session`)
- Rejects callers who aren't admin or the teacher/student on the session.
- 2 tests (participant-allowed, outsider-rejected).

**Backend tests now run with sandbox Python 3.10** thanks to `backend/conftest.py` shim (`datetime.UTC`).

---

## 3. Phase 3 — Unblock the user (next phase)

**Goal:** close the "I'm stuck, please contact admin" workflows.

### Decisions to confirm before starting

The plan called these out as decision points. Sensible defaults are in **bold**.

1. **Cancel cutoff hours**: how close to start time can a student/teacher self-cancel before needing admin intervention? Plan default = **24 h**, configurable via `settings.CANCEL_CUTOFF_HOURS`.
2. **Counter-proposal cap**: how many back-and-forth volleys before the admin has to mediate? Plan default = **3**, configurable.
3. **Teacher proof: same single proof per role as student?** Yes — the audit found `request-approval` hardcoded to `uploader_role == 'student'` and rejected teacher-only proof; the fix is to accept either role.

### Tasks (in build order)

#### 3.1 Backend: session cancel endpoint

`POST /sessions/{id}/cancel` accepting student or teacher participant.

- Add `CANCEL_CUTOFF_HOURS: int = 24` to `backend/config.py`.
- New endpoint in `backend/routers/sessions.py`:
  - Caller must be admin or a participant.
  - Allowed source statuses: `scheduled`, `pending_teacher`, `pending_student`, `pending_admin`, `overdue`, `overdue_rejected`. Reject `completed`/`cancelled`/`rejected`/`pending_verification` with 409.
  - If not admin AND `start_time - now < CANCEL_CUTOFF_HOURS`, return 400 with "Sessions starting in less than X hours must be cancelled by an admin."
  - If source was `completed` (shouldn't reach here, but defensive): refund `sessions_left` like `delete_session` does.
  - Transition to `cancelled`, `_bump_version`, activity-log, notify the other party + admins.
- Reuse `schemas.SessionApproval` (already has optional `notes` for cancel reason + `version`).
- Tests: each role can cancel future session; admin can cancel even within cutoff; non-participant gets 403; cutoff guard fires at the right time; cancelling a `completed` session refunds sessions_left.

#### 3.2 Backend: fix `request-approval` to accept either role's proof

Current code in `sessions.py:1003`-ish:
```python
has_proof = any(p.uploader_role == 'student' for p in db_session.proofs)
```
Change to `p.uploader_role in ('student', 'teacher')`. Bump version, add test that a teacher-only proof advances overdue → pending_verification.

#### 3.3 Backend: counter-proposal cap

- Add `counter_count = Column(Integer, default=0, server_default="0")` on Session model.
- New migration `phase3_session_counter_count.py` (idempotent — pattern from Phase 2).
- In `counter_session_as_teacher` and `counter_session_as_student`: increment `counter_count` after `_bump_version`, then check `if db_session.counter_count >= settings.COUNTER_PROPOSAL_CAP: ...`. If at cap, force status to `pending_admin` regardless of who countered, notify admins with "Negotiation deadlock — please mediate."
- `settings.COUNTER_PROPOSAL_CAP: int = 3`.
- Expose `counter_count` in `schemas.Session` so the frontend can show "1/3 counter-proposals used".

#### 3.4 Backend: teacher proof upload visibility

The endpoint already exists (`POST /session-proofs/`) and already accepts teacher uploads. The frontend just doesn't call it for teachers. No backend change needed — handled in 3.5.

#### 3.5 Frontend: cancel + teacher proof upload UI

`frontend/src/components/SessionDetailModal.vue`:
- Add a "Cancel session" button visible to admin OR to the participant on `scheduled`/`pending_*`/`overdue`/`overdue_rejected` statuses. Disabled (with tooltip) for non-admins when within cancel cutoff. Confirms via `useDialog` before posting.
- Add an "Upload my proof" button visible to any participant who hasn't already uploaded on `scheduled`/`overdue`/`overdue_rejected`/`pending_verification`. Opens a file picker; posts to `/session-proofs/?session_id=N`; on success, refetch the session.
- New emit: `'cancel-session': [sessionId: number]` and `'upload-proof': [sessionId: number, file: File]`.
- Wire emits in all three Schedule views (admin, teacher, student) to call a new store action.

`frontend/src/stores/schedule.ts`:
- New `cancelSession(sessionId, notes?)` action — POST to `/sessions/{id}/cancel`, then `_upsertSession`.
- New `uploadSessionProof(sessionId, file)` action — multipart POST to `/session-proofs/?session_id={id}`, then re-fetch the session (proof URL response is already signed).

#### 3.6 Frontend: teacher Shop view

`frontend/src/views/teacher/Shop.vue` is currently a 7-line stub. Copy the student shop view (`views/student/Shop.vue`) — the same shop product list works for teachers (orders go via `/shop/orders` regardless of role). If teacher pricing differs in the future, hook a `pricingTier` query param later.

#### 3.7 Frontend: destructive-action confirmations

- `views/admin/Users.vue`: delete-user dialog now requires typing the user's name to confirm.
- `views/admin/Payments.vue`: delete-payment confirmation surfaces the amount and student name.
- `views/admin/Schedule.vue` bulk cancel: scan selection for any `completed` sessions; if present, warn "X of these are already completed and will be reverted (sessions_left will be refunded)" before proceeding.

#### 3.8 Tests

- Backend: state-machine tests for cancel (each transition + cutoff) and counter cap (volley until cap forces pending_admin).
- Backend: `request-approval` accepts teacher proof.
- Frontend: smoke tests aren't currently set up, so just verify in dev that the new buttons appear/disappear at the right statuses.

### Ship gate
Student can cancel a session in < 3 clicks. Teacher can upload proof. Teacher Shop view loads. Counter loop terminates after 3 volleys.

---

## 4. Phase 4 — Reliability & data integrity

**Goal:** prevent slow drift and silent corruption.

### Tasks

#### 4.1 Atomic enrollment counter

`backend/routers/sessions.py` — find every `enrollment.sessions_used += 1` (occurs in `complete_session_as_admin`, `record_past_session`, `bulk_session_action`) and convert to:
```python
db.execute(
    text("UPDATE enrollments SET sessions_used = sessions_used + 1 WHERE id = :eid"),
    {"eid": enrollment.id},
)
```
Mirror the pattern already used for the atomic `sessions_left` decrement. Same for the `-= 1` branches on session cancel/delete (refund).

#### 4.2 Stale reminders for `pending_*`

`session_checker_task` currently reminds only `pending_verification` and `overdue_rejected`. Extend the same `stale_cutoff` / `stale_reminded_at` / cooldown pattern to `pending_admin`, `pending_teacher`, `pending_student`. The reminder messages should target the role whose decision is awaited.

#### 4.3 Nightly drift recalc

In the daily-token-purge tick of `session_checker_task`, also iterate every student and run the body of `recalculate_student_sessions` (compare `students.sessions_left` vs `Σ(enrollments.purchased - used)`). If non-zero drift, fix it and write an `ActivityLog` entry + notify admins. Don't spam — only fire the notification if drift > 0 for at least one user.

#### 4.4 Enrollment delete guard

`DELETE /enrollments/{id}`: if `sessions_used > 0`, return 409 with "Enrollment has usage history. Use soft-delete or admin override." Add an `?force=true` query param admins can pass to override.

For the soft-delete path: add `Enrollment.is_active = Column(Boolean, default=True, server_default="1")` + migration. Soft-deleted enrollments are excluded from active counters.

#### 4.5 `delete_session` time guard

`DELETE /sessions/{id}` on completed sessions older than 30 days: return 409 with "Edit the audit log instead." Younger sessions refund against the most-recent enrollment (look up by `created_at DESC LIMIT 1`).

#### 4.6 90-day Notification purge

In the daily tick: `DELETE FROM notifications WHERE created_at < NOW() - INTERVAL 90 DAY`. The Phase 1 `ix_notifications_created_at` index already supports this query efficiently.

#### 4.7 Background task crash guard

`session_checker_task` wraps each iteration in `try/except`. Wrap the outer `while True` in another `try/except` that `logger.critical(...)` and `await asyncio.sleep(60)` then restarts the loop. Currently if the outer loop crashes (e.g. from a bug in the iteration code that escapes the inner try), the asyncio task dies silently and all reminders/transitions stop until app restart.

#### 4.8 Tests

- Concurrent completion (use threads pointing at the same SessionLocal) doesn't double-decrement.
- Drift-recalc tick fixes a manually-introduced mismatch.
- Enrollment delete with `sessions_used > 0` returns 409.
- Notification purge removes rows older than 90 days, keeps newer ones.

### Ship gate
Atomic counters under concurrent load. Nightly drift report runs. Deleting an enrollment with usage is rejected.

---

## 5. Phase 5 — UI/UX polish & accessibility

**Goal:** the product feels finished.

### Tasks (each is roughly independent — pick any order)

#### 5.1 Calendar view toggle

`frontend/src/components/BaseCalendar.vue` currently renders a fixed week strip. Add a `view: 'week' | 'month' | 'day'` prop (default 'week'). Build month and day templates as separate `<template v-if>` blocks in the same component. Persist the chosen view per-user in `localStorage` (`smc_calendar_view`). All three Schedule views pass through the prop and add a small toggle group above the calendar.

#### 5.2 Drag-and-drop reschedule (admin only)

In month/week views, make session pills draggable. On drop into a new day, call `scheduleStore.editSession(id, { startTime, endTime })` with the same duration on the new date. Use the native HTML5 DnD API (no extra dep), or `@vueuse/integrations/useDraggable`. Bail if the drop target is in the past or violates `_validate_session_window` (the backend will reject anyway; do a client-side guard so the toast is faster).

#### 5.3 Session overflow

When a day has more than N visible items (3 in week view, 4 in month view), render the first N and a "+K more" chip that opens a popover with the full list. Popover items are clickable into the detail modal.

#### 5.4 Session detail modal enhancements

`SessionDetailModal.vue`:
- **History tab.** New `<button>` group at the top — Overview / History. History panel calls a new endpoint `GET /activity-log/session/{id}` (filter `target_type=session AND target_id=N`) and lists entries with timestamps + actor names.
- **Copy session link.** Small icon button next to the close × — copies `${window.location.origin}${route_for_role}?session_id=${id}` to clipboard.
- **Live force-complete countdown.** Replace the static "available in 24h" text with a live one. Compute `Math.max(0, endTime + 24h - now)` in a `setInterval(1000)` and format as `Xh Ym`.
- **Proof lightbox arrow keys.** Track current index; bind ←/→ to step through proofs; show prev/next chevrons on hover.

#### 5.5 Notification UX

- Unread badge in `FloatingNavbar.vue` and `MobileDock.vue`: `notifStore.unreadCount` already exists; render a small pill on the bell icon when > 0.
- Filter pills in `NotificationsModal.vue`: All / Unread / Sessions / Shop / Payments / Auth. Filters apply against `notification.message` substring (or add a `category` field server-side — bigger change).
- Bulk "Mark all as read" button.
- Per-channel preferences (Settings → Notifications): boolean toggles for 24h-reminder, 12h-reminder, proof-rejected, nudge-received, payment-receipt. Store in `notification_preferences` table + new endpoints. Out of scope for first pass — call out in PR description, schedule for Phase 6 or later.

#### 5.6 Accessibility pass

- Every `<span class="material-symbols-outlined">…</span>` gets `aria-hidden="true"`. Mass find-replace then audit by hand.
- Status pills that rely on color only: add the text label inline on small screens too (currently labels are removed below a breakpoint).
- Consistent `focus-visible:ring-2 focus-visible:ring-primary/40` on every custom button. The base button in `BaseButton.vue` already does this; missing on the action buttons in `SessionDetailModal.vue`.
- Wrap modal transitions in `@media (prefers-reduced-motion: reduce) { transition: none; }`.

#### 5.7 Mobile fixes

- All page-root divs use `pb-28` consistently (some are `pb-24`, some have no safe-area). Pick `pb-[max(7rem,env(safe-area-inset-bottom))]`.
- Add `truncate` + `title` attribute on long name renderings so hover shows the full string.

### Ship gate
Lighthouse Accessibility ≥ 95; month view usable on a 1366×768 screen; reduced-motion respected.

---

## 6. Phase 6 — Stretch & nice-to-haves

Pick-and-choose; none are critical.

- **Messaging:** typing indicators (WebSocket payload `{ type: 'typing', conversation_id, user_id }` debounced 1 s on the client); image attachments in session threads (S3-style upload + signed URL like proofs); search across conversations (`GET /messages/search?q=…`).
- **Shop:** partial fulfillment — split an order into fulfilled/pending line items; low-stock-alert cooldown (24 h key per product in a new `low_stock_alerted_at` column or in-process dict); order history filter/search.
- **Image normalization on upload:** in `backend/utils/uploads.py:save_upload`, when ext is image, open with Pillow, downscale to max edge 2000 px, re-encode to WebP, write the WebP. Saves bandwidth and removes EXIF.
- **Web push notification preferences:** the infra is in `routers/push.py`; expose a settings page that registers/unregisters subscriptions and offers the same per-channel toggles as 5.5.
- **Working-hours config UI:** Phase 1 server-side enforces nothing about working hours yet (that was deferred to Phase 6). Add `settings.WORKING_HOURS_START/END` + an admin UI to edit them. Then enforce in `_validate_session_window` when the request comes from a non-admin caller.
- **Deep search across activity log + sessions** for admin: combined endpoint that does a `LIKE '%term%'` across descriptions and notes with pagination.

---

## 7. Key conventions / gotchas

Things the next session will trip on without these notes.

### 7.1 Python 3.11 codebase, sandbox 3.10
- `from datetime import UTC` is used in `routers/auth.py` and `routers/users.py`. **3.10 doesn't have this.**
- Workaround already in place: `backend/conftest.py` monkey-patches `datetime.UTC = datetime.timezone.utc` if missing.
- When running tests in the sandbox, paths like `/tmp/runtest` need conftest.py copied along.

### 7.2 Postgres in prod, SQLite in dev/tests
- Backend `.env` points `DATABASE_URL=postgresql+psycopg2://…`. In the sandbox (no psycopg2) you must override via env: `DATABASE_URL="sqlite:////tmp/x.db"`.
- SQLite returns naive datetimes even on `DateTime(timezone=True)` columns — see the `_validate_session_window` and `complete_session_as_admin` `tzinfo is None` checks.

### 7.3 Alembic migration topology
- Two roots: `0001` (fresh-install snapshot) and `e0c69a750bfa` (legacy stub chain).
- Both flow into `j7k8l9m0n1o2` (Phase 1 merge) → `k8l9m0n1o2p3` (Phase 2 column).
- **Every new migration must be idempotent** because both lineages run on a fresh DB. Use the `_has_table` / `_has_column` / `_has_index` inline-helper pattern (see any Phase 2 migration).
- `_idempotent.py` is a no-op revision script in `versions/`. Alembic loads every `*.py` in there as a script, so the file declares `revision = "phase1_helper"` and `down_revision = "0001"`. Don't delete it.
- After every migration: `DATABASE_URL=sqlite:////tmp/check.db SECRET_KEY=test alembic -c backend/alembic.ini upgrade head` should complete cleanly from empty.

### 7.4 Optimistic locking contract
- See `_check_version` docstring in `backend/routers/sessions.py`.
- **Bump version** on every user-visible state transition (status, time, parties, proof verdict).
- **Don't bump version** on background-only updates (`notified_24h`, `stale_reminded_at`) — bumping causes spurious 409s on active frontend tabs.
- When adding a new field, decide which bucket it belongs in and document it at the call site.

### 7.5 Refresh-token auth contract
- HttpOnly cookie `smc_rt` at path `/auth`.
- `_read_refresh_token` reads body-first, cookie-fallback. **Don't switch to cookie-first** — it breaks the replay-revoke chain for legacy tests.
- `axios.defaults.withCredentials = true` is set in `frontend/src/main.ts` AND `frontend/src/stores/auth.ts`. Either is enough; both are belt-and-suspenders.
- In prod, set `REFRESH_COOKIE_SECURE=true` in `.env`. In dev it must stay false because the cookie won't ride on plain HTTP.

### 7.6 Signed-URL contract
- HMAC-SHA256 of `f"{path}|{exp}"` truncated to 32 hex chars. Key derived from `settings.SECRET_KEY` via SHA-256 with the `smc-signed-url-v1::` tag.
- Path is bound into the signature — `?sig=…` doesn't transplant.
- The `map_session` helper signs proofs and homework URLs inline. Any new endpoint returning a `SessionProof` or `Homework` shape **must** also call `_signed_or_passthrough` on the URLs, or the frontend will get 403s.

### 7.7 Test setup quirks
- `backend/test_main.py` defines `as_admin`, `as_teacher`, `as_student` fixtures. Only `as_admin` overrides every role dep — use it as the base whenever you need to seed users via the admin-gated endpoints, then call `_swap_to_student`/`_swap_to_teacher` from `test_session_state_machine.py` to act as that role.
- `_seed_users` reads role IDs from the create response — don't hard-code `role_id=1/2/3`.
- The user-create response is wrapped by `build_token_pair` — the user lives in `body["user"]`, not at the top level.

### 7.8 File-sharing surface
The user opens the SMC repo on their Mac at `/Users/dex/Desktop/Essentials x Coding/SMC`. In the sandbox the same files are visible at `/sessions/determined-peaceful-galileo/mnt/SMC`. **The sandbox cannot write to `.git/`.** Commits are prepared as shell scripts (`.phaseN_commit.sh`) that the user runs from their terminal.

---

## 8. Quick-start for the next session

Open this file. The user will name a phase (e.g. "do phase 3"). Then:

1. Re-read section 2 for that phase's neighbors (what's already wired in).
2. Re-read section 7 for gotchas relevant to the planned work.
3. Use the section for that phase as the implementation checklist.
4. At the end, write a `.phaseN_commit.sh` mirroring the structure of `.phase1_commit.sh` / `.phase2_commit.sh` and ask the user to run it.
5. Update this file's section 1 status table and section 2 "what was done" with a new subsection.

# SMC Implementation Plan — Phased

Six phases, ordered so each one ships independently and de-risks the next. Phase 1 is the safety net; everything after it depends on having migrations and tests in place.

---

## Strategy in one paragraph

Lock down the existing system first (migrations + tests + input validation), then close the privacy/auth holes that have CVE-shaped risk, then unblock the users who are currently stuck ("I can't cancel my own session"), then harden reliability under load, then polish UX and accessibility, then layer on stretch features. Each phase is shippable to prod on its own — if you stop after Phase 3, the system is already meaningfully safer and friendlier than today.

---

## Phase 1 — Foundation & safety net

**Goal:** make it safe to ship the next four phases without regressions.

**Deliverables**
1. Generate + commit Alembic migrations for the columns that already exist in `models.py` but have "MIGRATION NOTE" comments (`failed_login_count`, `locked_until`, `email_verified`, `email_verification_token_hash`, `totp_*`, `version`, `is_force_completed`, `stale_reminded_at`).
2. Add `Field(max_length=...)` to every user-facing string in `schemas.py` (notes, justification, rejection_reason, homework description, order notes, payment notes).
3. Add `_validate_session_window(start, end)` helper enforcing: not in past, end > start, duration ≥15min ≤240min. Call it on every `create/propose/counter/edit` endpoint.
4. Add backend tests for the full session state machine: every valid transition, every illegal transition, version conflict, overlap conflict, force-complete 24h window, complete with proof, complete without proof.
5. Add the missing DB indexes: `(status, end_time)` on Session, `created_at` on Notification.
6. Document the no-version-bump-on-notification-only-updates contract in `_check_version`'s docstring.

**Why first:** migrations missing = broken first deploy on fresh DB. Tests missing = every later phase is a regression risk.

**Ship gate:** all existing endpoints still pass; new tests green; fresh `alembic upgrade head` from empty creates the current schema.

---

## Phase 2 — Privacy & auth hardening

**Goal:** close the security holes the audit flagged.

**Deliverables**
1. Auth-gate `/uploads/proofs/*` (and any other private subdir). Either signed short-lived URLs or a `GET /uploads/proofs/{name}` endpoint that checks the requester is admin or a participant of the linked session.
2. Move refresh token from `localStorage` to an HttpOnly + Secure + SameSite=Lax cookie. Update `auth.ts` and `main.ts` interceptor.
3. Force-change-password on default admin: add `must_change_password` boolean on `User`, set it true in `_seed_defaults`, gate the dashboard router with a redirect to `/change-password` when true.
4. Add the missing "Forgot password" UI: link on Login, `/forgot-password` page, `/reset-password?token=...` page.
5. Add `mcp__cowork`-style security headers middleware (CSP, X-Content-Type-Options, Referrer-Policy, HSTS).
6. Skip `debug_users` route registration entirely when `not DEBUG` (don't just hide from OpenAPI).
7. Add participant-or-admin authorization to `POST /sessions/{id}/nudge`.
8. Decide & wire the `email_verified` story: either gate sensitive actions on it or drop the field. Recommend gating profile-edit and payment endpoints on verified-email.

**Why second:** these are latent security debts; better to land them before the surface grows in Phase 3.

**Ship gate:** signed-URL test (curl an `/uploads/proofs/x.png` without auth → 403). Refresh-cookie test passes a manual login + 16-min idle + page reload.

---

## Phase 3 — Unblock the user (highest UX impact)

**Goal:** close the "I'm stuck, please contact admin" workflows.

**Deliverables**
1. `POST /sessions/{id}/cancel` accepting student or teacher participant; require admin if `< X` hours before start (configurable, default 24h); status → `cancelled`; activity-logged; notifies the other party.
2. Teacher proof upload UI: add an "Upload my proof" button to `SessionDetailModal` for any participant on `scheduled / overdue / overdue_rejected / pending_verification` who hasn't already uploaded.
3. Fix `request-approval` to accept either teacher or student proof (or document the rule clearly in the UI with a disabled button + tooltip).
4. Implement `views/teacher/Shop.vue` (currently a 7-line stub) — copy the student shop view and gate by teacher-pricing if applicable.
5. Counter-proposal cap: add `counter_count` column on Session; after 3 volleys, both buttons disable and the UI shows "Admin will mediate" (notify admin).
6. Confirmation-pattern upgrade on destructive admin actions: bulk cancel warns about completed-session refunds; delete user requires typing the name; delete payment shows the amount and student.

**Why third:** the foundations + auth work makes this safe; this is the highest user-perceived value.

**Ship gate:** student can cancel a session in < 3 clicks; teacher can upload proof; teacher Shop view loads.

---

## Phase 4 — Reliability & data integrity

**Goal:** prevent slow drift and silent corruption.

**Deliverables**
1. Convert `enrollment.sessions_used += 1` to atomic SQL `UPDATE enrollments SET sessions_used = sessions_used + 1 WHERE id = :eid` everywhere it appears (`complete_session_as_admin`, `record_past_session`, `bulk_session_action`).
2. Add stale-reminder coverage for `pending_admin`, `pending_teacher`, `pending_student` — mirror the existing `pending_verification` reminder pattern in `session_checker_task`.
3. Nightly drift recalc: in the daily-purge tick of `session_checker_task`, run `recalculate_student_sessions` for every student; if old ≠ new, fix it and notify admin with a one-line activity-log entry.
4. Enrollment delete guard: refuse with 409 if `sessions_used > 0`; offer soft-delete via `is_active` flag.
5. `delete_session` on completed sessions older than 30 days returns 409 with "use the audit log to correct this"; younger ones refund to the most-recent enrollment.
6. 90-day Notification purge in the daily tick.
7. `session_checker_task` outer-loop crash guard: wrap `while True` in a try/except that `logger.critical`s and restarts after backoff.

**Why fourth:** these are silent failure modes — they don't break anything today, but they will eventually. Worth doing once the surface above is stable.

**Ship gate:** simulated concurrent completions don't double-decrement; nightly drift report runs; deleting an enrollment with usage is rejected.

---

## Phase 5 — UI/UX polish & accessibility

**Goal:** the product feels finished.

**Deliverables**
1. Calendar view toggle: Week / Month / Day in `BaseCalendar.vue`. Month view especially needed for admin overview.
2. Drag-and-drop reschedule for admin on Week/Day views (vue-draggable or native DnD). On drop → call `editSession` with new times.
3. Session-overflow handling: when a day has more than N visible items, render "+K more" with a popover.
4. Session detail modal upgrades:
   - "History" tab showing `ActivityLog` entries filtered to this session.
   - "Copy session link" button → clipboard.
   - Live countdown on "Force Complete (available in 4h 12m)".
   - Lightbox arrow-key navigation between proofs.
5. Notification UX:
   - Unread badge in `FloatingNavbar` and `MobileDock`.
   - Filter by type + "show only unread" + bulk mark-as-read.
   - Per-channel preferences page (Settings → Notifications).
6. Accessibility pass:
   - `aria-hidden="true"` on every Material Symbols `<span>`.
   - Status labels everywhere color is the only differentiator (not just in modal).
   - Consistent `focus-visible:ring` on every custom button.
   - `@media (prefers-reduced-motion: reduce)` killing modal/transition animations.
7. Mobile fixes: safe-area + `pb-28` consistency, name truncation tooltips.

**Why fifth:** none of these block anyone today, but together they're the difference between "works" and "feels nice." Polish lands faster on top of the stabilized core from Phases 1-4.

**Ship gate:** Lighthouse accessibility ≥ 95; calendar month view usable on a 1366×768 screen; reduced-motion respected.

---

## Phase 6 — Stretch & nice-to-haves

**Goal:** layer in delight where time allows.

**Deliverables (pick & choose)**
- Messaging: typing indicators, image attachments in session threads, full-text search.
- Shop: partial fulfillment, low-stock-alert cooldown (don't re-alert in 24h), order history filter/search.
- Image normalization: downscale uploads to max edge 2000px, convert to WebP server-side.
- Web push notification preferences (already have the infra in `routers/push.py`).
- Working-hours config UI for admin (Phase 1 enforces it server-side; this exposes the settings panel).
- Optional: deep search across activity log + sessions for admin.

**Why last:** none are critical, all are additive. Defer until 1-5 are solid.

---

## Cross-phase notes

- **Each phase ships independently to production.** Don't batch.
- **Phase 1 must land before any other PR that modifies state-machine code.**
- **Tests added in Phase 1 become the safety net every later phase relies on.**
- **Each phase carries ~5-7 days of work for a single developer, ~2-3 days for a pair.**

---

## Decision points for you

Before starting Phase 1, two things to decide:

1. **HttpOnly cookie vs. localStorage refresh token (Phase 2).** Cookie means CSRF protection (SameSite + double-submit token); localStorage means XSS-vulnerable but simpler. Recommend cookie.
2. **Force-complete window (currently 24h hardcoded).** Move to a settings value so you can shorten in dev. 24h is sensible default.
3. **Counter-proposal cap (Phase 3).** Default to 3; configurable.

Tell me which phase to start and any of the above you want to override.

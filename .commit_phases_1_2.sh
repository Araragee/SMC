#!/usr/bin/env bash
# Commit Phases 1 and 2 in one shot.
# Use this if you haven't run .phase1_commit.sh yet — it will stage and
# commit both phases as two separate commits in the right order.
#
# If Phase 1 was already committed, this script's first git commit will
# be empty and skipped; the script continues to Phase 2.
set -e
cd "$(dirname "$0")"

# Clear any stale lock the sandbox might have left.
rm -f .git/index.lock

# ── Phase 1 ────────────────────────────────────────────────────────────────
PHASE1_FILES=(
  "audit_2026-06-09.md"
  "implementation_plan_2026-06-09.md"
  "backend/conftest.py"
  "backend/test_session_state_machine.py"
  "backend/alembic/env.py"
  "backend/alembic/versions/_idempotent.py"
  "backend/alembic/versions/0001_initial_schema.py"
  "backend/alembic/versions/a7b9c2d4e8f1_indexes_and_session_version.py"
  "backend/alembic/versions/b8c1e3f4d6a2_auth_overhaul.py"
  "backend/alembic/versions/c9d2f5a7e8b3_push_subscriptions.py"
  "backend/alembic/versions/d1e2f3a4b5c6_session_timestamps.py"
  "backend/alembic/versions/ded95c6d7f14_add_instrument_shop_v2.py"
  "backend/alembic/versions/e0c69a750bfa_initial_migration.py"
  "backend/alembic/versions/f3a1b2c4d5e6_add_activity_logs_table.py"
  "backend/alembic/versions/g4h5i6j7k8l9_notification_composite_index.py"
  "backend/alembic/versions/h5i6j7k8l9m0_session_stale_reminded_at.py"
  "backend/alembic/versions/i6j7k8l9m0n1_sessions_compound_index.py"
  "backend/alembic/versions/j7k8l9m0n1o2_phase1_merge_and_indexes.py"
  "backend/models.py"
  "backend/schemas.py"
  "backend/routers/payments.py"
  "backend/routers/sessions.py"
)

git add -- "${PHASE1_FILES[@]}" 2>/dev/null || true
if git diff --cached --quiet; then
  echo "Phase 1: nothing to commit (already up-to-date)."
else
  git commit -m "phase 1: foundation & safety net

Backend audit found three independent Alembic heads (0001, d1e2f3a4b5c6,
i6j7k8l9m0n1) — fresh-DB \`alembic upgrade head\` was failing outright.
This commit ships Phase 1 of the audit's implementation plan:

Migrations
- Rebase the legacy e0c69a750bfa chain onto the 0001 baseline so chain
  ordering is deterministic
- Wrap every legacy migration's DDL in idempotency checks
  (_has_table, _has_column, _has_index)
- Add merge migration j7k8l9m0n1o2 that converges all heads and adds
  ix_sessions_status_end_time + ix_notifications_created_at
- Single head verified on fresh DB and existing-prod simulation

Schemas
- Centralize length caps as module constants + Annotated aliases
- Apply Field(max_length=...) to every user-facing string in Session,
  Payment, User, Notification, Homework, Order, Message, Conversation,
  ActivityLog, push subscription, auth, refresh schemas
- Cap BulkActionRequest.session_ids / OrderCreate.items at 100;
  RecurringSessionCreate.skip_dates at 52; age 0-150; price/stock bounded
- Same treatment to PaymentUpdate in routers/payments.py

Session window validation
- New _validate_session_window helper enforces: not in past (60s skew),
  end > start, duration 15-240 min
- Wired into record_past_session (allow_past=True), recurring,
  create_session, propose_student, propose_teacher, counter_teacher,
  counter_student, update_session

Indexes (models.py)
- Declare ix_sessions_status_end_time and ix_notifications_created_at

Documentation
- Expand _check_version docstring with the no-bump-on-notification-only
  contract

Bug fix (caught by tests)
- complete_session_as_admin and bulk_session_action compared SQLite-naive
  datetime against tz-aware datetime.now(UTC). Coerce end_time to UTC.

Tests
- backend/test_session_state_machine.py: 16 cases for state transitions,
  version conflicts, overlap, window validation, force-complete window
- backend/conftest.py: Python 3.10 shim for datetime.UTC

Verification
- 29 tests pass (13 pre-existing + 16 new)
- alembic upgrade head succeeds from fresh DB and from prod stamp
"
  echo "Phase 1 committed."
fi

# ── Phase 2 ────────────────────────────────────────────────────────────────
PHASE2_FILES=(
  "backend/alembic/versions/k8l9m0n1o2p3_phase2_must_change_password.py"
  "backend/config.py"
  "backend/main.py"
  "backend/models.py"
  "backend/routers/auth.py"
  "backend/routers/sessions.py"
  "backend/routers/uploads.py"
  "backend/routers/users.py"
  "backend/schemas.py"
  "backend/test_phase2_misc.py"
  "backend/test_refresh_cookie.py"
  "backend/test_uploads_auth.py"
  "backend/utils/signed_urls.py"
  "frontend/src/main.ts"
  "frontend/src/router/index.ts"
  "frontend/src/stores/auth.ts"
  "frontend/src/types/index.ts"
  "frontend/src/views/ChangePassword.vue"
  "frontend/src/views/ForgotPassword.vue"
  "frontend/src/views/Login.vue"
  "frontend/src/views/ResetPassword.vue"
)

git add -- "${PHASE2_FILES[@]}" 2>/dev/null || true
if git diff --cached --quiet; then
  echo "Phase 2: nothing to commit (already up-to-date)."
else
  git commit -m "phase 2: privacy & auth hardening

Closes the four highest-risk audit findings: leakable proofs,
XSS-exploitable refresh token, no forced rotation on default admin,
missing forgot-password flow. Adds security headers and locks down
debug endpoints.

Auth-gated upload routes
- backend/routers/uploads.py serves /uploads/proofs/* and
  /uploads/homework/* with HMAC signature + expiry (utils/signed_urls.py)
  AND a participant/admin authorization check
- main.py: removes wide-open StaticFiles('/uploads'); only
  /uploads/shop (product images) stays public
- map_session signs proof + homework URLs inline so the frontend
  renders <img src> unchanged
- 9 tests covering signature roundtrip, forgery, expiry, traversal,
  authz matrix

HttpOnly refresh-token cookie
- build_token_pair_with_cookie helper in routers/auth.py
- /login, /users/, /auth/2fa/verify, /auth/refresh set the cookie
- /auth/refresh + /auth/logout read body-first / cookie-fallback so
  replay-revoke chain stays intact for legacy clients
- /auth/logout always clears the cookie + revokes the token
- config.py: REFRESH_COOKIE_* settings; Path scoped to /auth
- schemas.py: RefreshRequest/LogoutRequest.refresh_token now Optional
- frontend: axios withCredentials=true; logins no longer persist
  refresh_token to localStorage; legacy values purged on next refresh
- 5 cookie-specific tests

must_change_password gate
- models.py: new boolean column + 0001 baseline + idempotent migration
- main.py:_seed_defaults sets flag true on default admin
- POST /auth/change-password verifies current pw, clears flag, revokes
  refresh chain, clears cookie, activity-logs
- /auth/reset-password also clears the flag
- schemas: User exposes must_change_password; ChangePasswordRequest
- frontend: ChangePassword.vue + router redirect-gate

Forgot/Reset password UI
- ForgotPassword.vue (enumeration-resistant)
- ResetPassword.vue (client-side strength check mirrors backend)
- Login.vue: 'Forgot your password?' link
- New public routes /forgot-password and /reset-password

Security headers middleware
- backend/main.py:SecurityHeadersMiddleware adds X-Content-Type-Options,
  X-Frame-Options, Referrer-Policy, HSTS (HTTPS only), CSP
- Test pins headers on /health

Lockdown: debug_users route
- Conditionally REGISTERED on settings.DEBUG (previously only hidden
  from OpenAPI). Direct curl now returns 404 in production.

Nudge authorization
- POST /sessions/{id}/nudge now rejects callers who aren't admin or
  a participant. Closes the 'enumerate IDs and spam all teachers' hole.

Test totals
- 50 backend tests pass (29 from phase 1, 21 new this phase)
- alembic upgrade head clean on fresh DB and on prod stamp; single head

Deploy notes
- Set REFRESH_COOKIE_SECURE=true in prod .env (cookie only over HTTPS)
- DEFAULT_ADMIN_PASSWORD in .env is now ALWAYS a temporary credential;
  the admin is forced through /change-password on first sign-in
"
  echo "Phase 2 committed."
fi

# ── Progress doc commit ────────────────────────────────────────────────────
if [ -f PHASE_PROGRESS.md ]; then
  git add PHASE_PROGRESS.md .phase1_commit.sh .phase2_commit.sh .commit_phases_1_2.sh 2>/dev/null || true
  if ! git diff --cached --quiet; then
    git commit -m "docs: phase progress + resume guide

Tracks what's been shipped (phases 1 and 2) and documents the
remaining four phases with enough context for a fresh session to
pick up cleanly. Includes per-phase task lists, decision points,
gotchas (Python 3.11 vs sandbox 3.10, alembic migration topology,
optimistic locking contract, signed URLs, refresh cookie semantics)
and a test-setup quick-reference.

Companion commit scripts (.phaseN_commit.sh) prepared by the
sandbox session so each phase can be landed via a single shell
command on the host machine.
"
    echo "Progress doc committed."
  else
    echo "Progress doc: nothing to commit."
  fi
fi

echo
echo "==== All done ===="
git log --oneline -5

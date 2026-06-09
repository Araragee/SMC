#!/usr/bin/env bash
# One-shot commit for Phase 1. Run from the repo root.
set -e

cd "$(dirname "$0")"

# Clear any stale lock from the sandbox.
rm -f .git/index.lock

git add -A
git commit -m "phase 1: foundation & safety net

Backend audit found three independent Alembic heads (0001, d1e2f3a4b5c6,
i6j7k8l9m0n1) — fresh-DB \`alembic upgrade head\` was failing outright.
This commit ships Phase 1 of the audit's implementation plan:

Migrations
- Rebase the legacy e0c69a750bfa chain onto the 0001 baseline so chain
  ordering is deterministic
- Wrap every legacy migration's DDL in idempotency checks
  (_has_table, _has_column, _has_index) so it skips work already done
  by 0001 on fresh installs
- Add merge migration j7k8l9m0n1o2 that converges all heads and adds
  ix_sessions_status_end_time (overdue-checker query) +
  ix_notifications_created_at (planned 90-day purge)
- Single head verified on both fresh DB and existing-prod simulation

Schemas
- Centralize length caps as module constants and Annotated aliases in
  schemas.py (NAME_LEN, NOTE_LEN, URL_LEN, etc.)
- Apply Field(max_length=...) to every user-facing string field across
  Session, Payment, User, Notification, Homework, Order, Message,
  Conversation, ActivityLog, push subscription, auth, refresh schemas
- Cap BulkActionRequest.session_ids / OrderCreate.items at 100;
  RecurringSessionCreate.skip_dates at 52; age 0-150; price/stock bounded
- Same treatment to PaymentUpdate in routers/payments.py

Session window validation
- New _validate_session_window helper in routers/sessions.py enforces:
  not in past (60s skew tolerance), end > start, duration 15-240 min
- Wired into record_past_session (allow_past=True), recurring,
  create_session, propose_student, propose_teacher, counter_teacher,
  counter_student, update_session

Indexes (models.py)
- Declare ix_sessions_status_end_time
- Declare ix_notifications_created_at

Documentation
- Expand _check_version docstring to spell out the no-bump-on-
  notification-only-updates contract so new fields are added to the
  right bucket

Bug fix (caught by tests)
- complete_session_as_admin and bulk_session_action compared SQLite's
  naive datetime against tz-aware datetime.now(UTC), raising TypeError.
  Coerce end_time to UTC before the 24h check

Tests
- New backend/test_session_state_machine.py: 16 cases covering legal
  transitions (propose -> approve, three-step negotiation -> scheduled,
  admin reject), illegal transitions (409), version conflicts,
  overlap detection, window validation (past/short/long/inverted),
  force-complete window (400 too early, succeeds after 24h with
  sessions_left decrement), default end-time fill
- backend/conftest.py: Python 3.10 shim for datetime.UTC import so the
  suite runs on older dev envs (prod targets 3.11+)

Verification
- 29 tests pass (13 pre-existing + 16 new)
- alembic upgrade head succeeds from fresh DB and from prod state
  stamped at i6j7k8l9m0n1
- Single head (j7k8l9m0n1o2) confirmed

Docs:
- audit_2026-06-09.md
- implementation_plan_2026-06-09.md
"
echo
echo "Phase 1 committed. Latest log:"
git log --oneline -3

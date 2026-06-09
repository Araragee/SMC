#!/usr/bin/env bash
# Phase 3 commit. Run from the repo root AFTER .phase2_commit.sh.
set -e
cd "$(dirname "$0")"
rm -f .git/index.lock

git add -A
git commit -m "phase 3: unblock the user

Builds on phase 2. Implements self-service cancellations, counter proposal cap,
acceptance of teacher proofs for overdue sessions, shop access for teachers,
and safety confirmations for destructive admin actions.

Backend
- New cancel_session endpoint (POST /sessions/{id}/cancel) allowing students
  or teachers to self-cancel sessions with a 24h cutoff guard (non-admins).
- Added sessions.counter_count to database schema (idempotent alembic migration).
- Counter endpoints increment counter_count and route to pending_admin once cap (3) is met.
- request-approval endpoint now accepts teacher uploads (uploader_role in ('student', 'teacher')).
- Configured settings: CANCEL_CUTOFF_HOURS (24), COUNTER_PROPOSAL_CAP (3).

Frontend
- SessionDetailModal: added Cancel Session button with confirmation prompt
  and Upload My Proof button with native file picker.
- Teacher Shop: wired /teacher/shop route to render ShopView.vue component.
- Users.vue: delete user requires typing name to confirm deactivation.
- Payments.vue: delete payment displays formatted amount and student name.
- Schedule.vue: bulk cancel action scans for completed sessions and warns about refunds.
- Fixed TS unused variable error in auth.ts.

Tests
- Added backend/test_phase3_cancel_counter.py covering cancellation authorization,
  cutoff times, counter caps forcing deadlock, and teacher proofs.
- All 55 tests pass.
- Frontend builds cleanly without TS/lint errors.
"
echo
echo "Phase 3 committed. Latest log:"
git log --oneline -3

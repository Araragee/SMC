# SMC Portal — Run Summary

_Scheduled task `automated-smc-portal`, run of 2026-06-21. Code is **not** pushed (per task instructions)._

This run **continued and completed** the plan in `plans.md` (a prior run of the same
task had been interrupted mid-execution), then added new functionality and re-verified
the whole change set.

## What was already done by the previous (interrupted) run — now verified

- **Backend correctness + lint debt** across 26 files: dead-import removal, `raise … from`
  (B904) fixes, `== True/False/None` → `.is_(…)` SQLAlchemy idioms, `datetime.timezone.utc`
  → `datetime.UTC`, import sorting, and the `sessions.py` logger/import reordering.
- **Backend test suite restored** under `backend/tests/` (signed URLs, uploads, security
  helpers, config, import smoke) — the safety net deleted in commit `09ff30e`.

I re-ran everything and confirmed: **36 prior tests green**, pyflakes clean, the
`.is_()` conversions and `raise … from` fixes are behaviour-preserving, and **no
`datetime.UTC` (3.11+) rewrite leaked into the Alembic migrations** (which run outside
the pytest 3.10 shim, so that would have broken `alembic upgrade` on 3.10).

## What this run finished and added

**1. Completed the stale-component cleanup (plan step 4, unfinished)**

- Deleted `frontend/src/components/PlaceholderView.vue` and `frontend/src/mock/index.ts`
  (the two files the plan flagged as dead).
- Found and removed **3 more genuinely-dead components** — `FloatingNavbar.vue`,
  `BaseChip.vue`, `TopNavbar.vue` (311 lines) — zero references in the whole frontend
  (PascalCase + kebab-case + dynamic-path checks), not globally registered.
- Removed a stray duplicate test file (`backend/test_imports_smoke_tmp.py`) left by the
  prior run.
- `vue-tsc --noEmit` re-confirmed clean after every deletion.

**2. Added a password-strength policy (new functionality)**

Real gap: the only constraint on a new password was the 72-byte bcrypt ceiling, so a
user could set a 1-character password via `change-password` / `reset-password`.

- New module `backend/utils/passwords.py`:
  - `validate_password_strength()` — pure, returns a list of failure reasons.
  - `enforce_password_strength()` — raises `HTTPException(400)` for route handlers.
  - Policy is **NIST SP 800-63B-aligned**: length-first (min 8, configurable) + a
    72-byte ceiling + rejection of single-character repetition + a small weak-password
    block-list. No rigid composition rules, so strong passphrases still pass.
- New setting `PASSWORD_MIN_LENGTH` (default `8`) in `config.py`, overridable via `.env`.
- Wired into the two **user-chosen** password flows (`/auth/change-password`,
  `/auth/reset-password`). **Deliberately not** wired into admin user-create/update —
  the auto-generated default passwords (e.g. the `password123` fallback) would fail the
  policy; that is tracked as a follow-up in `IMPROVEMENTS_SCAN.md` instead.
- New tests `backend/tests/test_passwords.py` (14 cases incl. empty/whitespace, length
  floor, multi-byte byte-counting, repetition, weak-list, custom min length, wrapper 400).

## Verification (all green)

| Check | Tool | Result |
|------|------|--------|
| Backend tests | `pytest backend/tests/` | ✅ **50 passed** (was 36; +14 password tests) |
| Dead code / undefined names | `pyflakes` (all app code) | ✅ clean |
| Frontend types | `vue-tsc --noEmit` | ✅ 0 errors |
| App boot | `import backend.main` | ✅ app constructs, policy wired |

Note: `ruff` itself could not run in the sandbox (the 10.8 MB wheel exceeded the
network/proxy limits of an unattended run). `pyflakes` + the repo's existing conventions
were used as a stand-in; CI (`ci.yml`) still runs the full `ruff check .` on push.

## Change set (uncommitted, not pushed)

- **28 modified** · **5 deleted** · new: `backend/utils/passwords.py`,
  `backend/tests/` (6 test files), `plans.md`.

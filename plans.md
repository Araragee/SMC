# SMC Portal — Audit & Improvement Plan

_Generated automatically on 2026-06-21 (scheduled task: `automated-smc-portal`)._
_No `plans.md` existed, so the app was audited and this plan was produced, then executed._

## Context

- **Backend:** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + Alembic (SQLite dev / Postgres prod).
- **Frontend:** Vue 3 (Composition API) + Vite + TypeScript + Pinia + Tailwind.
- The codebase is mature (6 development phases) and well commented. Most issues are
  **stale debt** rather than broken behavior.

## Audit Snapshot

| Area | Tool | Result |
|------|------|--------|
| Frontend types | `vue-tsc --noEmit` | ✅ 0 errors |
| Backend lint | `ruff check` | ⚠️ 156 issues (110 auto-fixable) |
| Backend tests | `pytest` | ❌ No test files (suite deleted; `conftest.py` orphaned) |
| Frontend lint | `eslint` | ⚠️ cannot run — `node_modules` stale (missing `vue-eslint-parser`) |

### Findings (prioritized)

**P1 — Correctness / dead code (real)**
1. `routers/users.py` — unused imports `File`, `UploadFile`, and a dead late import `save_upload`.
2. `dependencies.py:43` & `utils/uploads.py:81` — `raise` inside `except` without `from` (B904); loses error chain.
3. Backend test suite was removed in commit `09ff30e` (cleanup). `conftest.py` + `dev-requirements`
   (pytest, pytest-asyncio, pytest-cov) remain, and `.pytest_cache` still references a deleted
   `test_schedule_visibility.py`. No regression safety net exists.

**P2 — Lint debt (mechanical, low risk)**
4. 16× `== True/False` and 1× `== None` inside SQLAlchemy `.filter()` — functionally correct but
   flagged (E712/E711). Convert to the idiomatic `.is_(...)` form (zero behavior change, clears lint).
5. `routers/sessions.py` — a `logger = …` statement sits above the import block, cascading 14× E402.
   `models.py` / `routers/activity.py` define classes / late-import mid-file (E402).
6. 47× `datetime.timezone.utc` → `datetime.UTC` (UP017), 34× trailing-whitespace blank lines (W293),
   import sorting (I001), and a few `List`→`list` / encoding-arg modernizations.

**P3 — Stale frontend components (dead)**
7. `components/PlaceholderView.vue` — zero references (router uses `NotFoundView`); contains
   leftover "under construction" branding copy.
8. `mock/index.ts` — zero references; superseded by Pinia stores + live API.

**P4 — Noted, not auto-executed (need product direction)**
9. `frontend/node_modules` is stale vs `package.json` (eslint broken). Needs `npm install`.
10. Teacher-side homework assignment UI: `Homework` model exists and students have a homework route,
    but there is no teacher homework management view. Candidate feature.

## Execution Plan (this run)

1. **plans.md** — this file. ✅
2. **Backend correctness + dead code + lint** — items 1, 2, 4, 5, 6 above. Guard `conftest.py` against
   the self-referential UP017 rewrite; apply only safe, behavior-preserving fixes.
3. **Backend tests** — write `backend/tests/` covering signed URLs (HMAC sign/verify, expiry, path
   binding), upload validation (magic bytes, size cap, extensions), auth/security helpers (JWT
   create/decode, role guards), config, and an import smoke test. Restores the deleted safety net.
4. **Frontend dead-code removal** — delete items 7, 8. Re-confirm `vue-tsc` clean.
5. **Verify** — `ruff check` (app code clean), `pytest` (green), `vue-tsc` (clean).
6. **Docs** — write a plain-md summary of work done and a second-pass improvements scan.

### Explicitly out of scope (this run)
- `git push` (task says do not push).
- Speculative features (item 10) and dependency reinstall (item 9) — documented in the improvements
  scan instead of executed, to avoid unreviewed product/behavior changes in an unattended run.

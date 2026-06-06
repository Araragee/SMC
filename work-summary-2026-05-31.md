# Work Summary — 2026-05-31 (scheduled run)

Branch: `dev` (changes left **uncommitted / not pushed**, as instructed).

## Context
`plans.md` was present on `dev` and read. The remediation roadmap it describes
(Alembic migrations, `pydantic-settings` config, env-based secrets/CORS, removal
of manual `create_all`/seeding from `main.py`, Activity Log, Admin Payments/Ledger,
router↔sidebar audit, no `PlaceholderView` links) was **already implemented** by
prior runs and sitting in the working tree. So this run focused on **verifying that
work and fixing what was actually broken**.

## Bug fixed (app-startup crash)
`backend/routers/auth.py` began with `from __future__ import annotations`.
Combined with the `slowapi` `@_limiter.limit(...)` decorator on `forgot_password`
and `reset_password`, this turned the route signatures into string annotations that
FastAPI/pydantic could not resolve (`PydanticUndefinedAnnotation: name 'schemas'
is not defined`). The result: **`import backend.main` failed — the app would not
start at all.**

Fix: removed the `from __future__ import annotations` line so annotations stay as
real objects. After the fix the app imports cleanly and all routes register.

## Minor cleanups (same file)
- Re-sorted the import block (ruff `I001`).
- Added `... from None` to two `HTTPException` raises in `two_fa_verify`
  (ruff `B904`, cleaner exception chaining).
- `ruff check routers/auth.py` → **All checks passed.**

## Verification performed
- **Backend tests:** `pytest backend/test_main.py` → **13 passed.**
  (Had to run from a local copy: SQLite throws "disk I/O error" on the mounted
  filesystem — environment quirk, not a code issue.)
- **Backend import:** `import backend.main` → OK (was failing before the fix).
- **Frontend type check:** `vue-tsc -b` → **exit 0, no type errors**
  (this is the plans.md verification criterion).
- **Frontend `vite build`:** could not complete in this sandbox — `rolldown`'s
  native binary in `node_modules` was installed for macOS, not Linux
  (`MODULE_NOT_FOUND` on the platform binding). Platform mismatch, **not** a code
  problem; type checking already passed.

## plans.md roadmap status (spot-checked, all confirmed done)
- `main.py` has **no** `create_all` / manual `ALTER TABLE` (explicit comment notes
  Alembic owns schema).
- CORS uses `settings.ALLOWED_ORIGINS`; JWT secret read from settings — no
  hardcoded values.
- No remaining `PlaceholderView` references in `router/index.ts` or `SidebarNav.vue`.
- No other router still using `from __future__ import annotations`.

## Note / environment caveats
- This sandbox runs Python 3.10; the project targets 3.11 (`datetime.UTC` is used,
  which is 3.11+). A 3.10 shim was used only to run the tests here — no code was
  changed for it. On the real 3.11 deployment target the code is correct as-is.

## Recommendation for next run
- Run `npm run build` on a Linux host with a fresh `npm install` (or `npm rebuild`)
  to confirm the production bundle builds with the correct native `rolldown` binary.
- Consider committing the verified working-tree changes once the build is confirmed
  on a matching platform.

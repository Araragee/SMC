# Improvement Scan — 2026-05-31 (run 2)

A fresh sweep of the SMC backend + frontend for bugs, debt, and security gaps beyond
what plans.md already covers. Sandbox disk wedged mid-run, so this is a static scan.

## Severity legend
🔴 fix soon · 🟡 worth doing · 🟢 nice-to-have

---

## 🔴 / fixed this run — deploy bypassed Alembic
`entrypoint.sh` called `Base.metadata.create_all()` on container boot, bypassing the
Alembic migration chain that the rest of the project now depends on. **Fixed** →
container now runs `alembic upgrade head`. (See work-summary-2026-05-31-run2.md.)

## 🟡 seed.py creates tables itself
`backend/seed.py` calls `create_all` before inserting seed rows. For consistency with
the Alembic-owns-schema model, it should assume migrations already ran (or invoke
`alembic upgrade head` first) rather than creating tables directly. Low impact since
it's a manual/standalone script.

## 🟢 `from __future__ import annotations` in services/scripts
Present in `services/notifier.py`, `services/push.py`, `scripts/gen_vapid.py`, one
migration, and `test_main.py`. None of these combine the import with FastAPI route
decorators (the pattern that crashed `auth.py`), so they're currently safe — but worth
keeping in mind: never add that import to a router module with `slowapi`/Pydantic
signatures.

## 🟢 debug `print` / `console.log` statements
~24 `print(`/`console.log` calls across app code. Harmless but noisy; consider routing
backend output through `logging` and stripping stray frontend `console.log`s before a
production cut.

## Things checked and found healthy ✅
- **CORS**: scoped origins (localhost defaults, env-overridable), explicit method/header
  allowlists, `allow_credentials=True` paired with non-wildcard origins — no
  credentials+wildcard misconfiguration.
- **Secrets**: JWT secret and origins read from `settings` (pydantic-settings); no
  hardcoded `SECRET_KEY` / `allow_origins=[...]` literals in source.
- **Schema ownership**: `main.py` no longer creates tables or runs manual `ALTER TABLE`.
- **Frontend types**: domain entity IDs are numeric; no stray `id: string` leakage
  (only client-side toast IDs use strings, correctly).
- **Routing**: no `PlaceholderView` links remain in router or sidebar.
- **No bare `except:` blocks** in backend app code.

## Suggested next priorities (no code change made)
1. Confirm `npm run build` on a matching (Linux) platform with fresh deps.
2. Migrate-then-seed ordering in `seed.py`.
3. Introduce structured logging to replace ad-hoc prints.

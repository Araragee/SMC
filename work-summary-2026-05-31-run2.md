# Work Summary — 2026-05-31 (scheduled run 2)

Branch: `dev`. Changes left **uncommitted / not pushed**, per the task instructions.

## Context
`plans.md` is present on `dev` and was read/internalized. Its remediation roadmap
(Alembic migrations, `pydantic-settings` config, env-based secrets/CORS, removal of
manual `create_all`/seeding from `main.py`, Activity Log, Admin Ledger, router↔sidebar
audit, numeric entity IDs) was **already implemented and verified by prior runs** and
is sitting in the working tree. This run re-verified that work and then did a fresh
scan, fixing one real inconsistency.

## Verification of plans.md roadmap (all confirmed)
- `backend/main.py` — no `create_all` / manual `ALTER TABLE`; explicit comment notes
  Alembic owns the schema.
- CORS: `allow_origins=settings.ALLOWED_ORIGINS` with scoped methods/headers; defaults
  are localhost-only (no wildcard-with-credentials bug). JWT secret read from settings.
- No `PlaceholderView` references remain in `frontend/src` (router or sidebar).
- Entity IDs: no stray `id: string` on domain types — only `toast.ts` uses string IDs,
  which is correct (client-generated toast keys).
- No app router still uses `from __future__ import annotations` (the prior auth.py
  startup-crash fix holds). The remaining 5 occurrences are in services/scripts/tests,
  none of which combine it with FastAPI route decorators, so they're safe.

## Fix applied this run
**`backend/entrypoint.sh` bypassed Alembic.** On container start it ran
`models.Base.metadata.create_all(bind=engine)`, which directly contradicts the
plans.md goal that Alembic own the schema (and would silently mask pending/failed
migrations in deployment). Replaced it with:

```bash
(cd /app/backend && alembic upgrade head)
```

so the deployed container now applies versioned migrations on boot instead of
side-stepping them. Low risk, aligns deploy behaviour with Phase 1 of plans.md.

## Remaining note (not changed)
- `backend/seed.py` still calls `create_all` before seeding. Acceptable for a
  standalone seeding script, but ideally it should run after `alembic upgrade head`
  rather than create tables itself. Left as-is to avoid touching seed behaviour.

## Environment caveat
The Linux sandbox's disk filled during an attempted copy of the backend into `/tmp`
to run a live import test, which wedged the shell for the rest of the run. All
verification above was therefore done statically via file/grep tooling rather than by
importing the app. Prior run already confirmed `import backend.main` succeeds,
`pytest backend/test_main.py` → 13 passed, and `vue-tsc -b` → 0 type errors.

## Recommendation for next run
- On a Linux host with a fresh `npm install`, run `npm run build` to confirm the
  production bundle (rolldown native binary was macOS-only in the working tree).
- Once build is confirmed, consider committing the verified working-tree changes.
- Optionally reorder `seed.py` to migrate-then-seed for full Alembic consistency.

# SMC Improvement Scan — 2026-05-30 (run 2)

A targeted re-scan focused on areas not fully closed by `plans.md`. Severity: 🔴 high, 🟡 medium, 🟢 low/polish.

## 1. Repository hygiene
- 🔴 **Large uncommitted working tree.** `dev` is ahead of `origin/dev` and has ~60 modified + many untracked files (new routers, services, utils, migrations, composables, components). This is risky: a single bad run could lose hours of work. Recommend committing in small, themed commits (auth, push, shop, recurring, messaging) so progress is recoverable.
- 🟡 **Tracked DB/journal artifacts.** `backend/sql_app.db`, `backend/test.db`, and a deleted `sql_app.db-journal` appear in status. SQLite files should be in `.gitignore`, not tracked — they cause noisy diffs and merge pain.
- 🟢 **Scan/summary sprawl.** ~25 `improvement-scan-*`, `session-summary-*`, `system-scan-*` MDs now live at repo root. Consider moving them under a `docs/runs/` folder to declutter.

## 2. Backend
- 🟡 **Seeding still runs in-process on startup.** `_seed_defaults()` executes on every boot via lifespan. Fine for dev, but for prod this should be an idempotent one-shot script/migration so app start stays side-effect-free. `plans.md` item 4 ("move seeding to standalone scripts") is only partially met — standalone seed scripts exist (`seed.py`, `seed_comprehensive.py`, `seed_data.py`) but the lifespan still seeds.
- 🟡 **Default admin credentials from env.** `_seed_defaults` creates an admin from `DEFAULT_ADMIN_PASSWORD`. Confirm `.env` is not committed and that prod forces a password rotation on first login.
- 🟢 **`Payment.amount` unit ambiguity.** Model comment says "cents or smallest currency unit" while shop uses explicit `price_cents`. Standardize payments on `_cents` naming to remove ambiguity.
- 🟢 **Token purge only at startup.** `_purge_stale_tokens()` runs once per boot. Long-running instances won't purge until restart; consider folding it into the existing `session_checker_task` loop on a daily cadence.

## 3. Frontend
- 🟡 **ID type standardization (plans.md item 1).** Verify no `id: string` remain in `src/types/*.ts` and that stores cast API ids to `number` consistently. This was a named plan goal; worth a final grep + build to confirm zero type errors.
- 🟢 **Router ↔ Sidebar 1:1 audit.** Confirm every `SidebarNav.vue` entry resolves to a real route (no `PlaceholderView` fallbacks) for all three roles, especially Teacher Payments and Student sub-views called out in `plans.md`.
- 🟢 **`Payment.status` surfacing.** Now that payments carry `pending|completed|failed`, ensure the admin Ledger and student Payments views render status badges + a printable receipt (plans.md Phase 3.2).

## 4. Testing & CI
- 🔴 **Verification not reproducibly captured.** There is a `.github/` dir (CI) and `backend/test_main.py` (219 lines). Make each scheduled run write `pytest` and `npm run build` output to a file in-repo so health is auditable even when terminal output is flaky.
- 🟡 **No visible frontend unit tests.** Backend has tests; consider a minimal Vitest smoke test for the critical `SessionDetailModal.vue` state machine, given its centrality (per CLAUDE.md).

## 5. Quick wins for next run
1. `echo backend/*.db >> .gitignore` and `git rm --cached backend/*.db backend/*.db-journal`.
2. Commit the working tree in themed commits.
3. Run and capture `pytest -q` + `npm run build`; fix any failures.
4. Final grep for `id: string` in `src/types` and resolve.
5. Move startup seeding behind an explicit `--seed` script/flag for prod.

_Generated autonomously. No code changes or pushes were made this run._

# SMC Portal — Second-Pass Improvements & Bug-Fix Scan

_Generated 2026-06-21 by scheduled task `automated-smc-portal`, after this run's work
(`RUN_SUMMARY.md`) was complete and verified. Nothing here is executed yet — it is the
backlog for the next run / a human review. Items are ordered by value-over-risk._

## How to read this

Each item is tagged **[safe-auto]** (behaviour-preserving, a future unattended run can
just do it), **[needs-review]** (a product or behaviour decision), or **[ops]**
(environment / pipeline, not code).

---

## P1 — Security & correctness

**1. Predictable, weak default passwords on user creation — [needs-review]**
`routers/users.py:135-140` generates `"{first_name}{age}SMC"` for students and falls
back to the literal `"password123"`. Both are guessable, and `password123` is on the new
weak-password block-list — i.e. the system mints credentials it would reject from a user.
Because the admin create/update path is intentionally *not* gated by the new policy
(it would reject its own defaults), the gap is currently unguarded.
_Fix:_ generate a random secret (`secrets.token_urlsafe(12)`), always set
`must_change_password=True`, and deliver it via the existing welcome notifier. Then the
admin path can also call `enforce_password_strength` safely.

**2. `reset-password` allows reusing the current password — [needs-review]**
`change-password` rejects a no-op change (`new == current`, `routers/auth.py:290`) but
`reset-password` does not. A reset flow should arguably enforce the same "must differ"
rule (it can't read the plaintext old password, but it can compare against the stored
hash with `pwd_context.verify`).

**3. Broad `except Exception` audit — [needs-review]**
14 `except Exception` / bare handlers across `routers/`, `services/`, `utils/`. Several
are deliberate (uniform "incorrect password", notifier best-effort), but a pass to ensure
none silently swallow programming errors — and that all log at `warning`/`error` — would
tighten reliability. Start with the notifier and the upload/image paths.

## P2 — Consistency & maintainability

**4. `print()` instead of logging for lifecycle messages — [safe-auto]**
`main.py:63,92,94` use `print(...)` for startup / token-purge output; the rest of the app
uses `logging`. Convert to `logger.info(...)` for consistent, capturable logs. (The
`print` in `services/notifier.py:35` is the *console* notifier backend and is fine.)

**5. Centralise UTC handling to retire the 3.10/3.11 split — [safe-auto]**
The codebase imports `datetime.UTC` (3.11+) and carries a `conftest.py` shim so the
suite imports on 3.10. A tiny `utils/time.py` exposing `utcnow()` / `UTC`, used
everywhere, would remove the version sensitivity and the need for the shim, and give one
place to enforce naive-vs-aware consistency (several routers already juggle
`_naive(...)` / `.replace(tzinfo=UTC)`).

**6. Optional: strengthen the password policy with a breach check — [needs-review]**
The new block-list (`utils/passwords.py`) is intentionally tiny. A future enhancement is
an opt-in HIBP k-anonymity range check (one hashed-prefix HTTPS call) behind a setting,
giving real breached-password coverage without storing any corpus.

## P3 — Features (carried from `plans.md`, still open)

**7. Teacher-side homework management — [needs-review]**
The `Homework` model exists and students have a homework route, but there is no teacher
view to create/assign/grade homework. This is the largest genuine product gap; it spans
backend endpoints + a new frontend view and needs product direction before building.

## P4 — Ops / pipeline (not code)

**8. Reinstall the frontend toolchain — [ops]**
`frontend/node_modules` is stale vs `package.json`: `eslint` can't run (missing
`vue-eslint-parser`). A clean `npm install` restores lint. (`vue-tsc` works, so types are
still checked.)

**9. CI is now repaired by this run — confirm it — [ops]**
`.github/workflows/ci.yml` runs `ruff check .` and `pytest -v`. With the suite deleted,
the `pytest` step was collecting zero tests (exit 5 = failure). Restoring `backend/tests/`
turns that step green again. Recommend: (a) confirm the next CI run passes end-to-end,
and (b) add a `vue-tsc --noEmit` step so the frontend type-check that this task relies on
is also gated in CI.

---

## Suggested order for the next unattended run

1. **[safe-auto]** Items 4 (print→logging) and 5 (`utils/time.py`) — pure refactors with
   tests, zero behaviour change.
2. **[needs-review]** Item 1 (random default passwords) — high security value; flag the
   behaviour change for the owner.
3. **[needs-review]** Item 2 (reset-password reuse guard) — small, security-positive.
4. Leave items 3, 6, 7 for human direction; items 8–9 are environment, not code.

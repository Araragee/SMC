# SMC Portal — Improvement Scan
**Date:** 2026-05-23 (Run 3)
**Branch:** `dev`
**Scope:** Full-stack review after third backlog pass

---

## ✅ Resolved This Session

- `datetime.utcnow()` cleared from `seed_data.py` and `seed_comprehensive.py` (0 deprecation warnings remain in any active file)
- Hard-coded `/admin/instruments` route in `shop.py` extracted to `_ADMIN_SHOP_ROUTE` constant
- Toast errors wired to all silent `console.error` catch blocks in `interactions.ts` (4 actions) and `schedule.ts` (7 actions, including new `useToastStore` import)
- `session_checker_task`: added EXISTS short-circuit guard + off-hours back-off (300 s between 00:00–06:00 UTC, 60 s otherwise); `sleep_interval` moved before `try` block to prevent possible `NameError`
- `TeacherPayments.vue`: three stat cards (Collected / Pending / All-Time Total) replace single aggregate; monthly breakdown table added below the ledger

---

## 🔍 Remaining Issues

### High Priority

**Push notification UI is never mounted**
`frontend/src/composables/usePushNotifications.ts` is a complete, well-written composable (service worker registration, VAPID subscribe/unsubscribe, backend call). `frontend/public/push-sw.js` is a working service worker. The backend `POST /push/subscribe` and `DELETE /push/unsubscribe` endpoints exist. However `usePushNotifications` is not imported or called *anywhere* in the frontend. The feature is 100% built but silently inactive — users will never opt in and the backend will never send any web pushes.

To complete: add a toggle button (profile page or notification bell in the AppBar) that calls `subscribe()` / `unsubscribe()` from the composable.

**TOTP secret stored in plaintext**
`backend/models.py` line 77 and `backend/routers/auth.py` line 262 both carry a `TODO: encrypt totp_secret at rest`. If the SQLite file is ever leaked (backup, accidental `git add`, etc.) all enrolled 2FA secrets are exposed. Fix: derive a 32-byte Fernet key from `settings.SECRET_KEY` + a static salt via `hashlib.pbkdf2_hmac`, wrap/unwrap secret on write/read in the auth router.

### Medium Priority

**Email flows stub out to console — password reset and email verification are non-functional**
`backend/routers/auth.py`:
- `POST /auth/forgot-password` issues a reset token but the email is only printed to the console (`TODO(email): wire to backend.services.notifier`).
- `POST /auth/verify-email` same pattern.
Users who trigger "forgot password" will receive no email and can never reset unless an admin intervenes manually. `backend/services/notifier.py` already has the `send_password_reset` stub ready — wire it to `smtplib` / `aiosmtplib` or a provider SDK (Resend, SendGrid).

**`POST /orders/` has no rate limit**
`slowapi` is wired globally and applied to `POST /login` (10/min). The shop order endpoint has no `@limiter.limit(…)` decorator. A student or compromised account could spam order creation, inflating inventory counts and generating excessive admin notifications. Add `@limiter.limit("5/minute")` to `create_order`.

**`TeacherPayments.vue` has no CSV export**
Monthly breakdown and totals are now visible, but there is no way to export the ledger data. The admin `Payments.vue` has a receipt/print path. Add a simple CSV download button (client-side, using `Blob` + `URL.createObjectURL`) so teachers can hand the data to their accounting contact.

### Low Priority

**`console.error` calls remain in both stores (by design)**
All catch blocks now fire `toast.error` AND `console.error`. The `console.error` is retained intentionally for devtools debugging, but consider gating it behind `import.meta.env.DEV` so production builds are silent:
```ts
if (import.meta.env.DEV) console.error(err)
```

**`auth.py` still uses legacy `/users/login` endpoint alongside new `/auth/*` routes**
`backend/routers/users.py` has a `POST /login` endpoint; `backend/routers/auth.py` exposes `POST /auth/login` (with 2FA, lockout, TOTP). Both are mounted and reachable. The legacy `/login` path lacks 2FA and account-lockout logic. It should either be removed or proxied to the new route to prevent authentication bypass.

**No CONTRIBUTING.md / dev setup guide**
Repo has `DOCKER.md` and `ACCOUNTS.md` but nothing covering: running without Docker, running Alembic migrations, seeding, running tests, generating VAPID keys (`backend/scripts/gen_vapid.py` exists). Low urgency for solo development.

**`improvement-scan-2026-05-22.md`, `improvement-scan-2026-05-23.md`, `improvement-scan-2026-05-23b.md` are untracked**
These files live in the repo root but are untracked. Either add them to `.gitignore` or stage them — leaving untracked session files in the root creates noise in `git status`.

---

## 🏗️ Structural Observations

- **SQLite → Postgres readiness:** Still portable. Alembic in place. No blockers.
- **`session-summary-*` files** accumulating in root — same `.gitignore` note as scan files above.
- **`usePushNotifications` VAPID key sourcing:** The composable correctly fetches the public key from `GET /push/public-key` rather than hardcoding it; the pattern is clean and ready to go once the UI toggle is added.

---

## ✅ Verification Baseline

- `npx vue-tsc --noEmit` — 0 errors
- `python3 -c "import ast; ast.parse(…)"` on all changed Python files — OK
- `grep -c utcnow backend/seed_data.py backend/seed_comprehensive.py` — 0 / 0
- `grep -rn "window\.confirm|window\.prompt" frontend/src/` — 0 active call sites
- `grep -c console.error frontend/src/stores/schedule.ts` — 7 (kept for devtools; now all paired with `toast.error`)

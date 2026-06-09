#!/usr/bin/env bash
# Phase 2 commit. Run from the repo root AFTER .phase1_commit.sh (or just
# after Phase 1 is committed manually).
set -e
cd "$(dirname "$0")"
rm -f .git/index.lock

git add -A
git commit -m "phase 2: privacy & auth hardening

Builds on phase 1's foundation. Closes the four highest-risk audit
findings: leakable proofs, XSS-exploitable refresh token, no forced
rotation on the default admin, and missing forgot-password flow.

Auth-gated upload routes
- New backend/routers/uploads.py serves /uploads/proofs/* and
  /uploads/homework/* with two gates: (1) HMAC signature + expiry
  via backend/utils/signed_urls.py, (2) caller must be admin or a
  participant of the session/homework owning the file
- main.py: replaces the wide-open StaticFiles('/uploads') mount with
  /uploads/shop only (product images stay public)
- map_session and the homework/proof upload endpoints sign URLs
  inline so the frontend renders <img src> unchanged
- Path-traversal safety: strict 32-hex filename regex + resolve()
  containment check
- Tests: 9 cases (sig roundtrip, forge/expire/missing-params,
  admin/participant/outsider authz, traversal, missing file)

HttpOnly refresh-token cookie
- New cookie helpers + build_token_pair_with_cookie in routers/auth.py
- /login, /users/, /auth/2fa/verify, /auth/refresh all SET the cookie
- /auth/refresh and /auth/logout READ from body OR cookie (body wins
  for backward-compat + replay-detection semantics) — see
  _read_refresh_token docstring
- /auth/logout always CLEARS the cookie + revokes the token
- config.py: REFRESH_COOKIE_NAME / PATH / SECURE / SAMESITE settings;
  Path scoped to /auth so the cookie never accompanies API calls
- schemas.py: RefreshRequest.refresh_token and LogoutRequest are now
  Optional so cookie-only callers can omit them
- main.ts + stores/auth.ts: axios withCredentials=true; new logins no
  longer persist refresh_token in localStorage; legacy values are
  purged on next login/refresh
- Tests: 5 cases (cookie set + attributes, cookie-only refresh, body
  wins, logout clears, no creds -> 401)

must_change_password gate
- models.py: new boolean column on User
- alembic: idempotent migration k8l9m0n1o2p3 + 0001 baseline update
- main.py: _seed_defaults sets the flag on the default admin so the
  .env temp password cannot be used as the long-term credential
- routers/auth.py: new POST /auth/change-password endpoint verifies
  current password, clears the flag, revokes refresh tokens, clears
  cookie, logs activity. Reset-password also clears the flag.
- schemas.py: User exposes must_change_password; new ChangePasswordRequest
- frontend: new ChangePassword.vue view + router gate redirects any
  authenticated user with the flag to /change-password before they can
  reach a role dashboard

Forgot/Reset password UI
- New ForgotPassword.vue + ResetPassword.vue views wired to existing
  backend endpoints
- Login.vue: 'Forgot your password?' link
- router/index.ts: /forgot-password and /reset-password routes
- Enumeration-resistant UX: forgot view shows the same confirmation
  regardless of whether the email exists

Security headers middleware
- main.py: SecurityHeadersMiddleware adds X-Content-Type-Options,
  X-Frame-Options, Referrer-Policy, Strict-Transport-Security
  (HTTPS only), and a starter Content-Security-Policy
- Test pins the headers on /health

Lockdown: debug_users route
- routers/users.py: route is now conditionally REGISTERED based on
  settings.DEBUG. Previously it was always registered and just hidden
  from OpenAPI, so a direct curl still returned 401/404 with the
  endpoint live. Now it 404s because no route is mounted.
- Test pins the 404 in the default (non-debug) test env.

Nudge authorization
- routers/sessions.py: nudge_session now rejects callers who aren't
  admin or the teacher/student on the session. Before, any
  authenticated user could enumerate session IDs and spam every
  teacher in the school.
- Tests: participant-allowed, outsider-rejected

Test totals
- 50 backend tests pass (29 from phase 1, 21 new this phase)
- alembic upgrade head clean on fresh DB and on prod stamp; single head

Notes for deploy
- Set REFRESH_COOKIE_SECURE=true in production .env so the cookie only
  rides on HTTPS
- The DEFAULT_ADMIN_PASSWORD in .env is now ALWAYS a temporary boot
  credential — the admin is forced through /change-password on first
  sign-in
"
echo
echo "Phase 2 committed. Latest log:"
git log --oneline -3

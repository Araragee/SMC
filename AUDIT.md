# Hostability Audit — Sernan's Music Clinic

Audited against `dev` (56 commits ahead of `main`). Scope: what this app needs
to be hosted safely and run reliably, focused on **API**, **stability** and
**UI**. Deployment platform is deliberately not assumed.

This complements `IMPROVEMENTS_SCAN.md` rather than repeating it: that file is
a forward-looking backlog, this one records what was verified, what was fixed
in this pass, and what still blocks a real deployment.

---

## 1. Summary

`dev` is in far better shape than `main`. Alembic migrations, a Docker build,
a router/service split, rate limiting, a password policy, signed upload URLs,
HttpOnly refresh tokens and a 69-test suite are all already in place, and the
endpoints that were once fully unauthenticated (`POST /users/`, `/roles/`,
`/notifications/`, `GET /debug/users`) are now guarded.

Three things were found still open, and all three are fixed here:

1. **Object-level authorization was missing** on every user-scoped read. The
   role guards answered "what kind of user is this?" but nothing checked
   *whose* record was being requested — any authenticated account could read
   another user's schedule, lesson history, enrollments and notifications by
   changing an id in the path.
2. **The frontend could not be installed or built** from a clean checkout.
3. **The UI was still built on translucency and absolute colors**, which
   caused unreadable screens in the light theme.

---

## 2. API and security

### Fixed in this pass

Five endpoints took a user id in the path and never verified the caller's
relationship to it:

| Endpoint | Before |
|---|---|
| `GET /notifications/user/{user_id}` | Any authenticated user could read anyone's notifications. |
| `GET /sessions/user/{user_id}` | Any authenticated user could read anyone's schedule. |
| `GET /enrollments/student/{student_id}` | Any authenticated user could read anyone's enrollments. |
| `GET /teacher-students/teacher/{teacher_id}` | Any authenticated user could enumerate any teacher's roster. |
| `GET /sessions/student/{student_id}/records` | Blocked students only — every *teacher* could read the full lesson history of any student in the school. |

Two helpers were added to `dependencies.py` and applied at each call site:

- `require_self_or_admin(current_user, user_id)` — the user themselves, or an
  admin.
- `require_can_view_user(db, current_user, user_id)` — additionally allows a
  teacher/student pair with a real relationship: an explicit `TeacherStudent`
  assignment, or at least one shared session. A teacher legitimately needs
  their own students' records and no one else's.

Also fixed: `PUT /users/{user_id}` allows self-edits, and `UserUpdate` exposes
`sessions_left` / `sessions_enrolled`, so **a student could top up their own
lesson balance**. Both fields are now stripped for non-admins.

`backend/tests/test_object_authorization.py` covers each boundary (16 tests,
including that a teacher gets no blanket access by role alone). Full suite:
**85 passing**, ruff clean on every touched file.

### Verified as already handled on dev

Unauthenticated endpoints closed; `/debug/users` now only registered when
`DEBUG` is on *and* admin-guarded; login rate limiting and account lockout;
password strength policy; HMAC-signed upload URLs; HttpOnly refresh cookies;
forced password change on first login; Alembic migrations; query `limit`
bounds. The `datetime.timedelta` crash in admin force-completion that existed
on `main` is already gone here.

---

## 3. Stability

### Fixed in this pass

**A clean checkout could not build the frontend.** `vite-plugin-pwa@1.2.0`
declares a peer range of vite `^3–^7` while the project is on vite `^8`, so
both `npm install` and `npm ci` fail with `ERESOLVE`. This also breaks the
Docker frontend build and any CI job. Bumped to `^1.3.0`, which adds vite 8 to
its peer range; install, typecheck and build all pass afterwards.

### Open, by design of the current architecture

- **WebSockets are per-process.** `ConnectionManager` keeps sockets in a
  process-local dict, so with more than one worker or replica a message only
  reaches viewers connected to the same process. `entrypoint.sh` correctly
  runs a single uvicorn worker, which makes this safe *today* — but it also
  means the app cannot be scaled horizontally without a Redis (or equivalent)
  pub/sub fan-out. Worth a comment at the class so nobody adds `--workers 4`.
- **The reminder sweep runs unconditionally** (`asyncio.create_task` in the
  lifespan). Every replica would run it, duplicating reminders. Same single-
  instance caveat; an `ENABLE_SESSION_CHECKER`-style flag or a real scheduler
  is the fix before scaling.

---

## 4. Hostability

### Blocker

**Uploads are on local disk at a hardcoded relative path.**
`utils/uploads.py` writes to `Path("uploads")/subdir` — relative to the
process working directory, with no setting to override it. `docker-compose`
bind-mounts `./uploads`, so local development persists, but:

- on a host with an ephemeral filesystem every proof image is lost on each
  deploy or restart;
- with more than one replica, a file written by instance A is a 404 from
  instance B;
- the path breaks entirely if the process is ever started from another
  directory.

Make it configurable (`UPLOAD_DIR`, resolved absolute at startup) as the
minimum, and move to object storage (S3 / R2 / Supabase Storage) storing the
object key before running more than one instance. The signed-URL layer already
in place gives a clean seam to do this behind.

### Recommended

1. **Pin `vite-plugin-pwa` and friends more tightly**, or add a CI job that
   runs `npm ci` on a clean cache. The break above would have been caught
   immediately by one.
2. **Add CI** for `pytest`, `ruff` and `vue-tsc`. Ten pre-existing ruff
   findings sit in `main.py`, `seed.py` and two test modules; the suite and
   typecheck are otherwise clean, so this is cheap to turn on now and keep
   green.
3. **Self-host the fonts.** Plus Jakarta Sans and Material Symbols are fetched
   from Google at runtime; if `fonts.googleapis.com` is slow or blocked the UI
   degrades badly, and every visitor's IP goes to a third party — which
   matters for a school handling minors' data.
4. **Weak generated passwords** — already item 1 of `IMPROVEMENTS_SCAN.md`,
   and worth doing before real users: `{firstname}{age}SMC` is derivable from
   the student's own profile page.
5. **Retire `scripts/`** (`fix_*.js`, `test_db.py`, `debug_db.py`, …) and the
   committed `backend.log` / `frontend.log`.

---

## 5. UI / UX

The whole liquid-glass system was still in place on `dev`: 8 `backdrop-filter`
rules, ~490 hardcoded orange utilities and ~1200 absolute `white`/`black`
utilities across 48 components. Replaced with a pastel token system.

- **Surfaces are opaque.** `backdrop-filter` forces the compositor to re-blur
  a full-page region on every scroll and animation frame, and stacked panels
  (modal over card over nav) compounded it. More importantly, translucency
  makes text contrast depend on the content behind a panel, so no colour pair
  can be guaranteed readable. Elevation now reads through the surface ramp and
  a hairline border. The `.glass*` class names are kept so every view picks up
  the change without touching 48 files.
- **Pastel palette.** Soft tinted containers carry the colour; text and
  interactive fills use a deeper value of the same hue, so contrast never
  depends on the pastel itself. Every foreground/background pair is verified
  at WCAG AA in both themes (≥4.5:1 text, ≥3:1 non-text).
- **Removed the generic-AI signatures**: gradient-filled buttons, gradient
  headline text, neon glow shadows, blurred decorative orbs, and the five
  animated background blobs (background animation on every route costs
  battery, lowers effective contrast, and is a motion-sensitivity trigger).
- **Fixed real light-theme bugs.** Several modals rendered white text on white
  surfaces and were simply unreadable. Full-bleed saturated hero panels used a
  white-ish foreground that measures ~1.9:1 in the dark theme, where primary
  is a light apricot; they are now pastel containers with a checked
  foreground.
- **Accessibility**: global `:focus-visible` ring (components were setting
  `focus:outline-none` with no substitute, so the app was not keyboard-
  navigable); `prefers-reduced-motion` and `prefers-contrast` honoured.
- **Type scale**: root font-size back to the browser default. It was pinned at
  18px, which scaled every rem-based size *and all spacing* by 12.5% and
  overrode the user's own font-size preference. Density steps up only at
  ≥1280px. The PWA safe-area and iOS scroll-containment rules are preserved
  unchanged.

Deliberately left alone: the status hues (teal / amber / violet / rose /
emerald) encode session state and need to stay mutually distinguishable, so
they are not folded into the primary ramp.

### Follow-up

Rename the `.glass*` classes — they now describe the opposite of what they do.
Kept as-is here to keep this change reviewable; a mechanical rename to
`.surface` / `.surface-raised` is a good next step.

---

## 6. Verification performed

- `pytest backend/tests` — 85 passing (69 pre-existing + 16 new).
- `ruff check` — clean on every file touched; the 10 remaining findings are
  pre-existing in files not modified here.
- `alembic upgrade head` — clean against a fresh SQLite database.
- `npm install`, `vue-tsc -b`, `npm run build` — all succeed (they did not
  before the plugin bump).
- Backend booted and exercised: login, forced password-change gate, health.
- Both themes rendered in a real browser at 1440×950 (login, password gate,
  admin dashboard) and inspected for contrast, layout and leftover glass.

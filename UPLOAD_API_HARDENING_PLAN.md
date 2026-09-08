# Upload Reliability, API Security & Speed — Execution Plan

_Branch: `claude/upload-api-security-tech-debt-dpe2hf`, cut from `dev` (the latest
branch; `main` is far behind and is not the working line)._

Scope: make proof/homework uploads stop failing, tighten the API surface, remove
avoidable latency, and clear the open backlog recorded in `AUDIT.md`,
`IMPROVEMENTS_SCAN.md` and `plans.md`.

---

## What is actually broken

Findings from reading the upload path end to end (`frontend/src/stores/*.ts` →
`routers/sessions.py` / `routers/shop.py` → `utils/uploads.py` → `utils/storage.py`
→ `routers/uploads.py`).

### Upload failures

| # | Problem | Where | Effect |
|---|---|---|---|
| U1 | `Pillow` is not in `requirements.txt` — every image upload depends on it, but it arrives only as a transitive extra of `qrcode[pil]` | `backend/requirements.txt` | Any change to the qrcode dependency silently breaks all uploads with a 500 |
| U2 | Extension allowlist is `jpg/jpeg/png/webp` only | `utils/uploads.py` | An iPhone photo (HEIC) — the single most likely proof a student submits — is rejected outright with "Unsupported file type" |
| U3 | The client hard-sets `Content-Type: multipart/form-data` | `stores/schedule.ts`, `stores/interactions.ts` | Suppresses the browser-generated MIME boundary; fragile by construction and a classic source of intermittent 422s |
| U4 | Size cap is checked *after* `file.file.read()` buffers the whole body | `utils/uploads.py:60` | A 500 MB body is fully read into RAM before being refused — a trivial memory-exhaustion lever |
| U5 | EXIF orientation is discarded on re-encode | `utils/uploads.py` | Phone photos are stored sideways; users re-upload repeatedly thinking it failed |
| U6 | No decompression-bomb guard, no `RGBA`/`P`/animated handling before `save(format="WEBP")` | `utils/uploads.py` | Crafted images can exhaust memory; palette/animated inputs raise and surface as "Invalid image file: …" |
| U7 | Everything returns `400`; the raw Pillow exception is echoed to the client | `utils/uploads.py:86` | No `413`/`415` for clients to branch on, and internal error text leaks |
| U8 | No client-side validation | all three upload stores | The user uploads for 30 s over school wifi to be told "no" |
| U9 | `uploadImageProof` / shop upload report `err.message` | `stores/interactions.ts:240`, `stores/shop.ts:127` | The user sees "Request failed with status code 400" instead of the server's actual reason |
| U10 | `uploadHomeworkFile` fetches **every session** to find one homework id | `stores/interactions.ts:337` | Slow, and it fails outright when the session list is paginated or the row is missing |
| U11 | `storage.get`/`put` use module-level `httpx` calls with no retry | `utils/storage.py` | A new TLS handshake per file, and one transient blip renders a broken image permanently |

### API security

| # | Problem | Where |
|---|---|---|
| S1 | `GET /homework/user/{user_id}` and `POST /homework/{id}/upload` guard students only — **any teacher can read or overwrite any student's homework** | `routers/sessions.py:2002`, `:2011` |
| S2 | Upload endpoints have no rate limit, unlike login and the other write paths | `routers/sessions.py`, `routers/shop.py` |
| S3 | Stored files are served without `Content-Disposition` or a per-response sandbox policy | `routers/uploads.py:_serve` |
| S4 | Default passwords are `{firstname}{age}SMC`, falling back to the literal `password123` — derivable from the student's own profile, and on the app's own weak-password blocklist | `routers/users.py:160-172` (`IMPROVEMENTS_SCAN` #1) |
| S5 | `reset-password` permits reusing the current password; `change-password` rejects it | `routers/auth.py:311` (`IMPROVEMENTS_SCAN` #2) |
| S6 | Broad `except Exception` blocks swallow programming errors in the upload/image and notifier paths | (`IMPROVEMENTS_SCAN` #3) |

### Speed

| # | Problem |
|---|---|
| P1 | No `ETag`/`If-None-Match` on `/uploads/*` — every modal re-open re-transfers every proof, even within the `max-age` window, on any revalidating client |
| P2 | Remote reads pull the whole object through the API process on every request, with no connection reuse and no hot cache |
| P3 | `_user_can_see_proof` / `_user_can_see_homework` issue two sequential queries where one join suffices — on the request path of every image render |
| P4 | The homework-id lookup described in U10 |

### Open backlog (carried, not re-derived)

`ENABLE_SESSION_CHECKER` flag and the horizontal-scaling caveats (`AUDIT.md` §3),
`utils/time.py` to retire the 3.10 `conftest` shim (`IMPROVEMENTS_SCAN` #5),
`print` → `logging` (#4), retire `scripts/fix_*.js` and the debug scripts
(`AUDIT.md` §4.5), and a `vue-tsc` gate in CI (#9b).

---

## Phases

### Phase 0 — Shared foundations
- `backend/utils/time.py` exposing `utcnow()` / `UTC`; adopt it and drop the 3.10
  shim from `conftest.py`.
- Consolidate error formatting onto the existing `frontend/src/utils/apiError.ts`
  and delete the weaker `errMsg` copy in `stores/schedule.ts`, so every store
  reports the server's real message. (The plan first called for a *new* module;
  `apiError.ts` already did the job better, so it absorbed the callers instead.)
- `frontend/src/utils/upload.ts` — one client-side validator (type + size) shared
  by all three upload call sites.

### Phase 1 — Upload reliability *(U1–U11)*
- Pin `Pillow` explicitly; add `pillow-heif` and accept HEIC/HEIF.
- Read the body in bounded chunks and refuse at the cap (`413`) before buffering.
- `ImageOps.exif_transpose` for orientation; strip remaining metadata (GPS) on
  re-encode; flatten palette/alpha/animated inputs; cap total pixels.
- Distinct status codes (`413` too large, `415` unsupported) and no internal
  exception text in responses.
- Frontend: drop the manual `Content-Type`, pre-validate, surface real errors,
  and resolve the homework id from a dedicated endpoint instead of the full
  session list.
- `utils/storage.py`: one pooled `httpx.Client`, bounded retry on transient
  failures.

### Phase 2 — API security *(S1–S6)*
- Apply `require_can_view_user` to the homework read and upload paths.
- Rate-limit the three upload endpoints.
- Serve uploads with `Content-Disposition: inline` and a sandboxing CSP.
- Random per-user default passwords (`secrets.token_urlsafe`) with
  `must_change_password` always set, delivered through the existing notifier.
- Enforce "must differ" on `reset-password`.
- Narrow the broad exception handlers on the upload/image path.

### Phase 3 — Speed *(P1–P4)*
- `ETag` + `304 Not Modified` on `/uploads/*` (both storage backends).
- Reuse the pooled client from Phase 1. **No object cache was added**: the
  planned in-process LRU would hold other people's proof images in memory, and
  with the ETag path in place a warm client re-fetches nothing anyway. The
  privacy cost was not worth a saving that conditional requests already deliver.
- Collapse the two authorization queries into one join.

### Phase 4 — Tech debt
- `ENABLE_SESSION_CHECKER` setting plus the scaling caveat comment on
  `ConnectionManager`.
- Sweep any remaining `print` lifecycle logging.
- Delete `scripts/fix_*.js`, `scripts/test_*.py`, `scripts/debug_db.py`.
- Add the frontend type-check gate to CI.

### Phase 5 — Verification
`pytest` (with new tests for every behaviour above), `ruff check`, `vue-tsc`,
`npm run build`, and a fresh `alembic upgrade head`.

---

## Deliberately out of scope

- **Teacher-side homework management** (`IMPROVEMENTS_SCAN` #7) — a genuine
  product gap, but it needs product direction, not an unattended build.
- **Renaming the `.glass*` classes** (`AUDIT.md` §5) — a 48-file mechanical
  rename that would bury this diff.
- **Self-hosting the Google fonts** (`AUDIT.md` §4.3) — worth doing, but it means
  committing binary font assets and is unrelated to the three themes above.

---

## Execution record

All five phases were completed. Verification at the end of the run:

| Check | Before | After |
|---|---|---|
| `pytest backend/tests` | 94 passed, **1 failed** | **149 passed** |
| `ruff check backend` | **13 findings** | **clean** |
| `alembic upgrade head` (fresh SQLite) | **fails** — `ALTER COLUMN` is not SQLite syntax | **applies** |
| `vue-tsc --noEmit` | clean | clean |
| `eslint src/` | **4 errors**, 318 warnings | **0 errors**, 316 warnings |
| `npm run build` | passes | passes |

All three of CI's gating steps (ruff, migrations, pytest) were red on `dev`
before this branch. That was not a goal of the task; it surfaced while
verifying, and the fixes are included.

### Found while working, beyond the original list

Three problems the read-through turned up that were not in any backlog:

1. **`POST /users/` handed the admin the new user's session.** The route ended
   by minting the created user's token pair and setting *their* HttpOnly
   refresh cookie on the response — which goes to the admin who made the call.
   The admin's own refresh cookie was silently replaced, so their next
   `/auth/refresh` returned a session as the student they had just created.
   Creating an account is not logging into it; the route now issues no
   credentials at all.
2. **`PUT /homework/{id}` had no object-level check whatsoever.** Any
   authenticated account could mark any homework in the school complete or
   incomplete by guessing an id — and completion is what a teacher grades
   against.
3. **`Pillow` was not a declared dependency.** Every image upload used it, but
   it arrived only as a transitive extra of `qrcode[pil]`.

### Behaviour changes worth knowing about

- **Admin-created accounts get a random password**, shown once in the create
  dialog and never recoverable, with `must_change_password` set. The old
  `{firstname}{age}SMC` / `password123` defaults are gone from both the server
  and the client, which was generating and sending the same formula.
- **`POST /users/` returns `{user, temp_password}`** instead of a token pair.
- **`reset-password` refuses the current password**, matching `change-password`.
- **Uploads answer 413 and 415** where everything used to be a 400.
- **Images are stored stripped of metadata** — including EXIF GPS — and
  upright, and HEIC is accepted.

# Improvement Scan — 2026-05-23f

Full-system scan of `dev` branch. Issues ranked by severity. Items marked ✅ were fixed this session or a prior one.

---

## ✅ Fixed This Session

| # | Issue | File |
|---|-------|------|
| 1 | `NameError: List not defined` crash on import | `backend/schemas.py` |
| 2 | `cancelMyOrder` → 403 for all non-admin users | `backend/routers/shop.py` + `frontend/src/stores/shop.ts` |
| 3 | N+1 queries on order list/detail endpoints | `backend/routers/shop.py` |

---

## 🟠 High

### 1. `/nudge` endpoint has no server-side rate limiting
**File:** `backend/routers/sessions.py:727`  
The nudge endpoint enforces a client-side cooldown via `localStorage` (`nudge_last_{sessionId}`), but the server has no throttle at all. Any authenticated user can bypass the client gate and spam `POST /sessions/{id}/nudge` in a loop, flooding the target's notification inbox.  
**Fix:** Add `@_limiter.limit("3/minute")` (or similar) to the nudge endpoint using the same `slowapi` pattern already used in `auth.py` and `users.py`. Also consider a per-`(user_id, session_id)` key instead of per-IP so the limit follows the actor, not the network address.

### 2. `update_order_status` re-checks stock under no lock (race condition)
**File:** `backend/routers/shop.py:234`  
When approving an order the backend re-queries each `item.product.stock` and deducts it. Under concurrent approvals of two orders for the same low-stock product, both requests can read the pre-deduction stock value, both pass the sufficiency check, and both deduct — leaving stock negative. SQLite's default locking is coarse-grained so this is lower risk today, but it's a latent bug that will surface if the app moves to Postgres.  
**Fix:** Either use `SELECT ... FOR UPDATE` (Postgres) or wrap the stock-check and deduction in a single `UPDATE instrument_products SET stock = stock - ? WHERE id = ? AND stock >= ?` and check `rowcount` to detect under-stock atomically.

---

## 🟡 Medium

### 3. TOTP secret stored unencrypted in DB
**File:** `backend/models.py:77`, `backend/routers/auth.py:262`  
Both files carry a `# TODO: encrypt totp_secret at rest` note. If the SQLite file is ever read directly, all enrolled TOTP secrets are exposed. The Fernet symmetric cipher (keyed off a derived bytes of `settings.SECRET_KEY`) would fix this with a one-time migration.  
**Fix:** On `totp_secret` write, `Fernet(derived_key).encrypt(secret.encode())`. On read, decrypt before passing to `pyotp.TOTP(...)`. Add an Alembic migration to encrypt existing rows at deploy time.

### 4. `create_session_proof` allows any authenticated user to attach proofs to any session
**File:** `backend/routers/sessions.py:1010`  
The endpoint checks that the session exists but does NOT verify that `current_user` is the teacher or student on that session. Any authenticated user could upload a proof for a session they're not party to.  
**Fix:** Add an ownership check:
```python
if current_user.role.name != "admin" and current_user.id not in (db_session.teacher_id, db_session.student_id):
    raise HTTPException(status_code=403, detail="Not authorized to upload proof for this session")
```

### 5. `/auth/2fa/verify` has no rate limiting
**File:** `backend/routers/auth.py:335`  
The login endpoint (`users.py`) is rate-limited at 10/minute. But a valid `challenge_token` from a successful first-factor login can be used to brute-force the 6-digit TOTP against `POST /auth/2fa/verify` with no throttle. 10^6 guesses / unlimited rate = a real window, especially since the TOTP window allows ±1 step.  
**Fix:** Add `@_limiter.limit("5/minute")` to the `two_fa_verify` function (same pattern as `forgot_password`).

### 6. Sessions list endpoint loads all sessions with no pagination
**File:** `backend/routers/sessions.py` — `GET /sessions/` and related list endpoints  
The session queries return `.all()` with no `limit`/`offset`. As session count grows this will become slow and memory-intensive. The frontend already pages results client-side (`PAGE_SIZE` constant), but the backend still materialises every row.  
**Fix:** Add optional `skip: int = 0` and `limit: int = Query(default=200, le=1000)` parameters to the main sessions list route. The frontend fetches all at once today, so a high default (200-500) avoids breaking changes while establishing a ceiling.

### 7. Shop `get_products` eager-loads nothing (N+1 on category)
**File:** `backend/routers/shop.py:23`  
`InstrumentProduct` has a `category` relationship (`category_id` → `Instrument`). The product list endpoint returns all products with no `.options(joinedload(...))`, so serialising `product.category` triggers one extra query per product.  
**Fix:** Add `.options(joinedload(models.InstrumentProduct.category))` to the `get_products` query.

---

## 🟢 Low / Polish

### 8. `ICS` summary line uses `↔` which may break some calendar clients
**File:** `backend/routers/sessions.py:1086`  
`f"{instrument}: {teacher} ↔ {student}"` — the `↔` (U+2194) is valid UTF-8 but some legacy `.ics` parsers (Outlook 2016 desktop) do not handle non-ASCII in `SUMMARY` lines correctly. RFC 5545 strongly recommends keeping `SUMMARY` printable ASCII.  
**Fix:** Replace `↔` with `vs` or `-`.

### 9. Missing `authHeaders` on `shop.ts` `placeOrder` — redundant but fragile
**File:** `frontend/src/stores/shop.ts:158`  
The store relies on `axios.defaults.headers.common['Authorization']` being pre-set by `auth.ts`. This works, but if the interceptor hasn't run (e.g., in tests or SSR), the order POST goes unauthenticated. The pattern in `schedule.ts` and `payments.ts` is to pass explicit `authHeaders()` per request — `shop.ts` is the odd one out.  
**Fix:** Low priority since the axios default is set on app init, but aligning to the explicit-header pattern improves test-ability.

### 10. No `updated_at` timestamp on `Session` model
**File:** `backend/models.py` — `Session` class  
`Order` has both `created_at` and `updated_at` (with `onupdate`). `Session` only has `start_time` / `end_time`. Audit trail queries that want to know when a session's status last changed must fall back to `ActivityLog`, which isn't always populated for every transition (e.g., counter-proposals don't log).  
**Fix:** Add `updated_at = Column(DateTime, default=..., onupdate=...)` to the `Session` model with a corresponding Alembic migration.

### 11. `RecurringSessionModal` only available to admins
**File:** `frontend/src/views/admin/Schedule.vue` — only place `RecurringSessionModal` is imported  
Teachers who manage their own scheduling must create recurring sessions one-by-one. The modal component is already built; it just needs to be wired into `TeacherSchedule.vue`.

---

## Summary Table

| # | Severity | Area | File(s) |
|---|----------|------|---------|
| 1 | 🟠 High | Security — nudge spam | `backend/routers/sessions.py` |
| 2 | 🟠 High | Race condition — stock deduction | `backend/routers/shop.py` |
| 3 | 🟡 Medium | Security — TOTP at rest | `backend/models.py`, `routers/auth.py` |
| 4 | 🟡 Medium | Security — proof upload authz | `backend/routers/sessions.py:1010` |
| 5 | 🟡 Medium | Security — 2FA brute force | `backend/routers/auth.py:335` |
| 6 | 🟡 Medium | Performance — no pagination | `backend/routers/sessions.py` |
| 7 | 🟡 Medium | Performance — N+1 on products | `backend/routers/shop.py:23` |
| 8 | 🟢 Low | Compatibility — ICS summary char | `backend/routers/sessions.py` |
| 9 | 🟢 Low | Consistency — shop auth headers | `frontend/src/stores/shop.ts` |
| 10 | 🟢 Low | Data model — missing updated_at | `backend/models.py` |
| 11 | 🟢 Low | UX gap — RecurringSession for teachers | `frontend/src/views/teacher/Schedule.vue` |

# Improvement Scan — 2026-05-23g

Full-system scan of `dev` branch. Issues ranked by severity.
Items marked ✅ were fixed this session or a prior one.

---

## ✅ Fixed This Session

| # | Issue | File |
|---|-------|------|
| 1 | TOTP secret stored plain-text in DB | `backend/utils/totp_crypt.py` (new), `backend/routers/auth.py` |
| 2 | Session list endpoints had hard limit of 100 with no configurable ceiling | `backend/routers/sessions.py` |

---

## 🟠 High

### 1. `POST /notifications/` endpoint is unauthenticated
**File:** `backend/routers/notifications.py:33`

The `create_notification` route has no auth dependency — any request (including unauthenticated ones) can call it to insert an arbitrary notification for any `user_id`. Since notification messages render in the sidebar with links, this is a stored-content injection vector.

**Fix:** Add `current_user: models.User = Depends(require_admin)` (only admins should create notifications directly; the `notify_users` helper is for internal use and never hits this endpoint).

---

## 🟡 Medium

### 2. Revoked/expired tokens never purged — unbounded table growth
**File:** `backend/models.py` — `refresh_tokens`, `password_reset_tokens` tables

Both tables accumulate rows indefinitely. Every login creates a new `RefreshToken`; expired and revoked rows are checked against but never deleted. In a school with daily logins this will become a performance drag within months on SQLite.

**Fix:** Add a periodic cleanup call (can be run as a FastAPI startup background task or cron via the existing scheduler pattern):
```python
db.query(RefreshToken).filter(
    (RefreshToken.revoked == True) | (RefreshToken.expires_at < utcnow())
).delete()
db.query(PasswordResetToken).filter(PasswordResetToken.expires_at < utcnow()).delete()
db.commit()
```
A daily prune keeping only the last 30 days of revoked tokens is sufficient.

### 3. Pydantic v2 deprecation: `.dict()` still used in `notifications.py`
**File:** `backend/routers/notifications.py:35`

```python
db_notification = models.Notification(**notification.dict())
```

Pydantic v2 deprecated `.dict()` in favour of `.model_dump()`. This raises a `PydanticDeprecatedSince20` warning at runtime and will become an error in a future Pydantic release.

**Fix:** `notification.model_dump()` — one-line change.

### 4. No composite index on `(user_id, is_read)` for Notification table
**File:** `backend/models.py` — `Notification` class

The unread-count query (`WHERE user_id = ? AND is_read = false`) runs on every page load for every active user. The table has a single-column index on `user_id` but not the composite index needed to cover the `is_read` predicate efficiently. As notification volume grows this query will table-scan the per-user partition.

**Fix:**
```python
__table_args__ = (
    Index("ix_notifications_user_unread", "user_id", "is_read"),
)
```
With a corresponding Alembic migration.

---

## 🟢 Low / Polish

### 5. `PlaceholderView` wildcard catch-all still present for all three roles
**File:** `frontend/src/router/index.ts:71,86,100`

```js
{ path: ':module', component: PlaceholderView }
```

Any mistyped nav path (or future sidebar link added without a matching route) silently renders a placeholder page instead of a proper 404. A user who bookmarks a URL that later gets renamed will see a blank placeholder with no error or redirect.

**Fix:** Replace with a named `NotFound` or `ErrorView` component that shows a clear message and a "back to dashboard" button, or remove the catch-all and let the global 404 guard handle it.

### 6. `notify_users` uses a fragile dual-signature positional argument pattern
**File:** `backend/routers/notifications.py:10`

The function detects whether it was called as `notify_users(db, ids, message)` or `notify_users(db, ids, title, message, link)` by checking whether `link is not None`. This means `link=None` (an explicit no-link call in the shop style) silently falls through to the session-style path. It works today because all shop calls pass a real link string, but it is easy to break and hard to read.

**Fix:** Split into two explicit helpers or use keyword-only arguments:
```python
def notify_users(db, user_ids, message, *, title=None, link=None): ...
```

### 7. Cart persisted in `localStorage` keyed without user scope
**File:** `frontend/src/stores/shop.ts:155`

```js
localStorage.setItem('smc_cart', JSON.stringify(this.cart))
```

The cart key is global — if two users share a browser (common in a school lab), the second user inherits the first user's cart after login. Auth tokens are cleared on logout, but `smc_cart` is not.

**Fix:** Key the cart by user ID: `smc_cart_${userId}` and clear the key on logout in `auth.ts`.

### 8. `[DEV]` password reset / email verify tokens printed to stdout unconditionally
**File:** `backend/routers/auth.py:171,227`

```python
print(f"[DEV] Password reset token for {user.email}: {raw}")
```

These `print` statements were added as a development convenience (no email transport). They remain in place with no `settings.DEBUG` guard, so token values appear in production server logs. If logs are shipped to a log aggregator this leaks valid reset tokens.

**Fix:** Wrap in `if settings.DEBUG:` or, better, route through the `notifier.py` `console` backend which already has a debug gate.

---

## Summary Table

| # | Severity | Area | File(s) |
|---|----------|------|---------|
| 1 | 🟠 High | Security — unauthenticated notification injection | `backend/routers/notifications.py` |
| 2 | 🟡 Medium | Performance — unbounded token table growth | `backend/models.py`, `backend/routers/auth.py` |
| 3 | 🟡 Medium | Compatibility — Pydantic v2 `.dict()` deprecation | `backend/routers/notifications.py` |
| 4 | 🟡 Medium | Performance — missing composite index on notifications | `backend/models.py` |
| 5 | 🟢 Low | UX — PlaceholderView catch-all hides routing errors | `frontend/src/router/index.ts` |
| 6 | 🟢 Low | Code quality — fragile dual-signature `notify_users` | `backend/routers/notifications.py` |
| 7 | 🟢 Low | Privacy — cart bleeds between users on shared browser | `frontend/src/stores/shop.ts`, `frontend/src/stores/auth.ts` |
| 8 | 🟢 Low | Security — dev tokens printed to stdout unconditionally | `backend/routers/auth.py` |

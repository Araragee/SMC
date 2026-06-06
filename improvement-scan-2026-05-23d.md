# Improvement Scan — 2026-05-23d

Full-system scan of `dev` branch. Issues ranked by severity.

---

## 🔴 Critical (already fixed)

### 1. `_ADMIN_SHOP_ROUTE` self-reference — `backend/routers/shop.py:18`
`_ADMIN_SHOP_ROUTE = _ADMIN_SHOP_ROUTE` causes `NameError` at import, crashing the entire backend on startup.
**Fixed this session** → `_ADMIN_SHOP_ROUTE = "/admin/instruments"`

---

## 🟠 High

### 2. Product stock not refreshed in frontend after order approval
**File:** `frontend/src/views/admin/Instruments.vue` → `updateOrderStatus()`  
**Problem:** When an admin approves an order, the backend deducts stock from the product. The frontend `updateOrderStatus` action in `shop.ts` only updates the order record in local state — it does not call `fetchProducts()`. The admin shop grid continues to display the old (pre-deduction) stock number until the page is manually reloaded.  
**Fix:** After a successful `PATCH /shop/orders/{id}/status` in `shop.ts`, call `await this.fetchProducts()` when the new status is `approved`, `cancelled`, or `fulfilled` (any transition that touches stock).

```ts
// In shop.ts updateOrderStatus(), after updating local state:
if (['approved', 'cancelled', 'fulfilled'].includes(status)) {
  await this.fetchProducts()
}
```

### 3. Overdue auto-transition not logged to ActivityLog
**File:** `backend/routers/sessions.py` → `session_checker_task()` (~line 128)  
**Problem:** When the background task marks a session as `overdue`, it calls `notify_users` but never calls `log_activity`. Admin activity log therefore shows no record of automatic overdue transitions — making audits harder.  
**Fix:** Add `log_activity` call inside the loop:

```python
for s in overdue_sessions:
    dt_str = format_dt(s.start_time)
    s.status = "overdue"
    _bump_version(s)
    notify_users(db, [s.teacher_id, s.student_id], f"Action Required: Session from {dt_str} is overdue...")
    log_activity(db, action_type="session_overdue",
                 description=f"Session #{s.id} on {dt_str} automatically marked overdue.",
                 target_type="session", target_id=s.id)
```

---

## 🟡 Medium

### 4. `updateOrderStatus` in `Instruments.vue` accepts `any` for status
**File:** `frontend/src/views/admin/Instruments.vue:111`  
`const updateOrderStatus = async function(id: number, status: any)` — loses type safety.  
**Fix:** Import `OrderStatus` from `@types` and type the param: `status: OrderStatus`.

### 5. `/debug/users` endpoint should be removed before production
**File:** `backend/routers/users.py:28`  
The endpoint is admin-gated so it isn't a security hole, but it's a dead-code smell that leaks internal user structure. Should be removed or gated behind a `settings.DEBUG` flag before shipping to prod.

### 6. TOTP secret stored unencrypted
**File:** `backend/models.py:77` and `backend/routers/auth.py:262`  
Both files carry a `TODO: encrypt totp_secret at rest` note. Currently the TOTP secret is stored as plaintext in the `users` table. If the database is ever read directly, all 2FA secrets are exposed.  
**Fix:** Use Fernet (symmetric encryption keyed off `settings.SECRET_KEY`) to encrypt before write and decrypt before use. A migration is needed to encrypt existing rows.

### 7. `session_checker_task` short-circuits on "no scheduled sessions" but misses already-overdue ones
**File:** `backend/routers/sessions.py:85`  
`has_work` only checks for `status == "scheduled"`. If somehow a session ends up stuck in `overdue` with no `scheduled` sessions active, the checker skips the entire loop — but this is fine since the overdue filter also requires `status == "scheduled"`. However, the short-circuit comment is misleading: it says "skip if no scheduled sessions" but the check itself only gates further scheduled-status queries, not any future `pending_verification` or other cleanup logic that may be added later. Worth a comment clarification.

---

## 🟢 Low / Polish

### 8. Toast import inconsistency in stores
Some stores import `useToastStore` and call `toast.error(title, msg)` while others swallow errors silently with only `console.error`. Specifically `frontend/src/stores/payments.ts` sets `this.error` but never surfaces a toast on fetch failure. Standardize to always call `useToastStore().error()` on failed fetches.

### 9. `notify_users` signature overloaded — fragile two-mode API
**File:** `backend/routers/notifications.py:11`  
The function handles two call signatures (2-arg and 5-arg) with an internal `if link is not None` branch. This works but is confusing and has already caused call-site mismatches in earlier branches. Consider splitting into `notify_simple(db, ids, message, link=None)` and `notify_titled(db, ids, title, message, link)` with the old name as a deprecated alias.

### 10. `ICS export` does not include pending sessions
**File:** `backend/routers/sessions.py:1055`  
The `.ics` export filters `status.in_(["scheduled", "pending_verification", "completed"])`. Sessions in `pending_teacher`, `pending_student`, or `pending_admin` are excluded, so a user exporting their calendar misses sessions they're actively negotiating. Consider including all non-cancelled, non-rejected statuses and marking them `STATUS:TENTATIVE`.

### 11. `RecurringSessionModal` not available to teachers
**File:** `frontend/src/views/admin/Schedule.vue` only imports `RecurringSessionModal`.  
Teachers who manage their own scheduling cannot bulk-create recurring sessions — they must create them one by one. Low priority but a UX gap.

---

## Summary Table

| # | Severity | Area | File |
|---|----------|------|------|
| 1 | 🔴 Fixed | Backend startup crash | `backend/routers/shop.py` |
| 2 | 🟠 High | Frontend stale stock display | `frontend/src/stores/shop.ts` |
| 3 | 🟠 High | Missing activity log entries | `backend/routers/sessions.py` |
| 4 | 🟡 Medium | Type safety | `frontend/src/views/admin/Instruments.vue` |
| 5 | 🟡 Medium | Dead code / prod hygiene | `backend/routers/users.py` |
| 6 | 🟡 Medium | Security — TOTP at rest | `backend/models.py`, `backend/routers/auth.py` |
| 7 | 🟡 Medium | Code clarity | `backend/routers/sessions.py` |
| 8 | 🟢 Low | UX consistency | `frontend/src/stores/payments.ts` |
| 9 | 🟢 Low | API design | `backend/routers/notifications.py` |
| 10 | 🟢 Low | Feature gap | `backend/routers/sessions.py` |
| 11 | 🟢 Low | UX gap | Teacher Schedule view |

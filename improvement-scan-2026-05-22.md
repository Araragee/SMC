# SMC Portal — Improvement Scan
**Date:** 2026-05-22  
**Branch:** `dev`  
**Scope:** Full-stack review after `plans.md` implementation

---

## ✅ What Was Implemented This Session

### From `plans.md`
All tasks in the remediation plan were already completed in a prior session. On entry, the codebase had:
- Alembic migrations fully initialized with 5 migration versions
- `pydantic-settings` config with no hardcoded secrets
- `AdminPayments.vue` (`/admin/payments`) live and functional
- `ActivityLog.vue` (`/admin/activity-log`) fully wired to the backend
- Admin Dashboard "View All Activity" correctly linked via `<RouterLink>` (not a toast)
- All entity IDs typed as `number` in TypeScript interfaces
- `log_activity` calls in sessions, payments, auth, and users (create) routers

### New Fixes Applied This Session

**Backend — `backend/routers/shop.py`**  
Added `log_activity` calls to all mutating endpoints that were missing them:
- `create_product` → `product_created`
- `update_product` → `product_updated`
- `delete_product` → `product_deactivated`
- `create_order` → `order_placed`
- `update_order_status` → `order_approved / order_fulfilled / order_rejected / order_cancelled`

**Backend — `backend/routers/users.py`**  
Added missing `log_activity` calls:
- `update_user` (admin-initiated only) → `user_updated`
- `delete_user` → `user_deactivated` or `user_deleted`
- `assign_teacher_student` → `student_assigned`
- `unassign_teacher_student` → `student_unassigned`

**Backend — `backend/routers/sessions.py`**  
- Fixed `create_enrollment`: now syncs `sessions_left` on the `User` record when a new enrollment is created (the counter was never incremented on enrollment, only decremented on session completion — causing a permanent mismatch for new students)
- Added `log_activity` call to `create_enrollment` → `enrollment_created`
- Fixed `session_checker_task`: moved `db.close()` into a `finally` block and added `db.rollback()` in the `except` branch so DB connections are always released even when the background loop throws

**Backend — `backend/routers/users.py`**  
- `read_users` and `read_users_by_role` now filter out inactive (soft-deleted) users by default. Both endpoints accept an optional `include_inactive=true` query param for admin use-cases that need the full list.

**Frontend — `frontend/src/views/admin/Payments.vue`**  
- Added a **Print Receipt** button (receipt icon) to every payment row. Uses axios to fetch the backend's `/payments/{id}/receipt.html` with the Bearer token, creates a blob URL, and opens it in a new tab. The blob URL is revoked after 10 s to free memory.
- Adjusted grid column widths (`40px → 72px`) to accommodate the two-button action cell.

---

## 🔍 Further Issues Identified (Not Yet Fixed)

### High Priority

**`sessions_left` counter drift (structural)**  
`sessions_left` on the `User` model and `sessions_purchased - sessions_used` on `Enrollment` are two independent counters. Session completions decrement the User counter only if `> 0`, but there is no endpoint to reconcile them if they diverge (e.g. after a manual DB edit or a failed transaction). Consider adding an admin `/students/{id}/recalculate-sessions` endpoint that resets `sessions_left` from the sum of enrollment balances.

**`datetime.utcnow()` deprecation**  
Python 3.12 deprecated `datetime.utcnow()` (produces naive datetimes). The codebase mixes naive UTC (`datetime.utcnow()` in `sessions.py`, `shop.py`, `messaging.py`) with aware UTC (`datetime.now(UTC)` in `auth.py`, `users.py`). The overdue-checker in `session_checker_task` compares naive datetimes from the DB against a naive `now`, which works today but will silently break if SQLite is ever replaced with a timezone-aware DB. Standardise on `datetime.now(timezone.utc)` throughout.

### Medium Priority

**No DELETE endpoint for Enrollments**  
Admins can create enrollments but cannot remove or adjust them via the API. A `DELETE /enrollments/{id}` endpoint with a corresponding `sessions_left` rollback on the student would complete the CRUD surface.

**Receipt currency symbol inconsistency**  
The printable HTML receipt (`/payments/{id}/receipt.html`) displays amounts with a `$` symbol. The rest of the application (order notifications, the ledger view) uses `PHP`. The receipt template should use `₱` or `PHP`.

**`read_users` has no pagination in the frontend**  
The `fetchUsers()` call in `users.ts` hits `GET /users/` with the backend default `limit=100`. Schools with more than 100 users will silently receive a truncated list. Either raise the backend default to a safe ceiling (e.g. 500) or implement cursor/page-based fetching in the store.

**Shop store `mapProduct` not handling `null` category gracefully**  
If a product has `category_id` but its `category` relation is `null` (e.g. category was deleted), `mapProduct` passes `undefined` for `category`. The `ProductCard.vue` component renders `product.category?.name` which silently shows nothing. A backend `GET /shop/products` should eager-load or omit the `category` key when the relation is broken.

### Low Priority

**`session_checker_task` runs every 60 s unconditionally**  
The overdue / reminder queries run whether or not any sessions exist. At scale this adds unnecessary DB load. A simple optimisation is to skip the overdue query during hours when no sessions are expected, or to use a conditional `EXISTS` check before running the full query.

**`console.error` not surfaced as user toasts in some stores**  
`shop.ts` `fetchProducts` and `fetchAllOrders` swallow errors silently (only `console.error`). Users see a blank list with no explanation. Should surface a toast or set an `error` state for these actions, consistent with how `schedule.ts` and `payments.ts` already behave.

**`create_product` and `update_product` in the admin instruments view call `fetchProducts()` after save**  
This is a full re-fetch. Should use the returned product to upsert the local store list instead, saving a round-trip. The `updateProduct` action already does an in-place update in the store but `saveProduct` in `Instruments.vue` calls `fetchProducts()` anyway, negating it.

**Notification link for order placed points to `/admin/instruments` (hard-coded)**  
The `create_order` endpoint notifies admins with a link to `/admin/instruments`. This is correct today, but if the orders tab is ever moved to a separate route the string will be stale. Extract the URL to a constant or derive it from the router.

---

## ✅ Verification

- `python3 -c "import ast; ast.parse(open(f).read())"` passed for all modified Python files
- `npx vue-tsc --noEmit` returned 0 errors after all frontend changes

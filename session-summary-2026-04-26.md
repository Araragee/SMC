# Scheduled Run Summary — 2026-04-26

## What Was Done

`plans.md` was present on `dev`. All items were confirmed implemented or completed.

### Fixes applied this run

**1. Alembic migration for `activity_logs` table**  
File: `backend/alembic/versions/f3a1b2c4d5e6_add_activity_logs_table.py`  
The `ActivityLog` model had no migration. Without this, a fresh deployment would never create the `activity_logs` table even though the ORM model and router existed. Migration chains off the shop v2 migration (`ded95c6d7f14`) and creates the table with indexes on `action_type` and `created_at`.

**2. Bug fix — `read_student_payments` filtered on wrong column**  
File: `backend/routers/payments.py` (line 116)  
The `/payments/student/{student_id}` endpoint was doing `.filter(models.Payment.id == student_id)` instead of `.filter(models.Payment.student_id == student_id)`. This caused the endpoint to return at most one wrong payment record. Fixed.

**3. Cleanup — double `db.refresh()` in `create_payment`**  
File: `backend/routers/payments.py`  
`create_payment` called `db.refresh(db_payment)` twice in a row before immediately re-querying the record with `joinedload`. Removed the redundant first refresh.

### Everything from `plans.md` verified complete

- `AdminPayments.vue` + `/admin/payments` route — done  
- `AdminActivityLog.vue` + `/admin/activity-log` route — done  
- "View All Activity" button → real `RouterLink` — done  
- `ActivityLog` model, schema, router, `log_activity` helper — done  
- `log_activity` wired into session and payment events — done  
- `pydantic-settings` config — already in place  
- Alembic initialized — already in place  
- All frontend IDs typed as `number` — already correct  
- No dead sidebar links — confirmed, all routes map to real views  

## Nothing was pushed. Code is uncommitted on `dev`.

## See `system-scan-report-2026-04-26.md` for the full bug/improvement backlog.

# SMC Improvement Scan — 2026-06-05

Full system scan performed after confirming all `plans.md` items are complete.
Findings are grouped by severity.

---

## 🔴 Bugs

### 1. `instrument_id` never sent when booking a session
**File:** `frontend/src/stores/schedule.ts` → `bookSession()`

The `bookSession` payload omits `instrument_id`, so every admin-created session is stored with `instrument_id = null`. The backend schema supports it (`instrument_id: int | None`), but the frontend never sends it. The admin Schedule view also has no instrument picker in the session creation form.

**Fix:** Add an instrument selector to the session creation modal; include `instrument_id` in the `bookSession` and `proposeSession` payloads.

---

### 2. `propose_session_as_student` doesn't validate teacher–student assignment
**File:** `backend/routers/sessions.py` → `propose_session_as_student()`

A student can propose a session with *any* teacher — there's no check that a `TeacherStudent` record exists linking them. This means a student could spam proposals to teachers they've never been assigned to.

**Fix:** Query `TeacherStudent` before creating the session and raise `403` if no assignment exists.

```python
assignment = db.query(models.TeacherStudent).filter_by(
    teacher_id=proposal.teacher_id,
    student_id=current_user.id
).first()
if not assignment:
    raise HTTPException(403, "You are not assigned to this teacher")
```

---

### 3. `propose_session_as_student` doesn't check `sessions_left`
**File:** `backend/routers/sessions.py` → `propose_session_as_student()`

A student with `sessions_left = 0` can still propose sessions. Sessions are not blocked at proposal time. While `sessions_left` is decremented on *completion*, students shouldn't be able to queue up new sessions they have no remaining quota for.

**Fix:** Add a guard before session creation:

```python
if current_user.sessions_left is not None and current_user.sessions_left <= 0:
    raise HTTPException(400, "No sessions remaining. Please contact admin to enroll in more.")
```

---

## 🟡 Medium Improvements

### 4. Stale-token purge only runs once at startup
**File:** `backend/main.py` → `lifespan()`

`_purge_stale_tokens()` is called once when the server starts. Between restarts, expired/revoked `RefreshToken` and `PasswordResetToken` rows accumulate indefinitely. On high-traffic instances this table grows unbounded.

**Fix:** Call `_purge_stale_tokens()` inside the `session_checker_task()` loop on a daily cadence (e.g., run once per 24h iteration).

---

### 5. Activity log fetches up to 500 entries in one shot
**File:** `frontend/src/views/admin/ActivityLog.vue`

The frontend requests `limit=500` from `/activity-log/`. As the log grows, this becomes a large payload sent and rendered all at once. Client-side pagination is applied after the full fetch.

**Fix:** Switch to server-side pagination — pass `skip` and `limit` based on current page, and add a `GET /activity-log/count` endpoint (or include `X-Total-Count` in the response header) so the frontend knows total pages without fetching everything.

---

### 6. No enrollment check before admin-direct session booking
**File:** `backend/routers/sessions.py` → `create_session()` (admin endpoint)

When an admin directly books a session (`POST /sessions/`), there is no check that the student is enrolled with that teacher. `sessions_left` is also not decremented at booking time, only at completion — but an admin could book sessions for student/teacher pairs with no active enrollment. This creates orphaned sessions that affect `sessions_used` counters on unrelated enrollments (the completion logic finds the *first* enrollment for that student/teacher pair, which may not exist).

**Fix:** Add a warning (or optional enforcement) that checks for an active `Enrollment` record before confirming the booking.

---

### 7. `bookSession` in schedule store sends `status: 'scheduled'` from frontend
**File:** `frontend/src/stores/schedule.ts` → `bookSession()`

The payload explicitly includes `status: 'scheduled'`. The backend `SessionCreate` schema accepts `status` but the admin endpoint forcibly sets it to `'scheduled'` regardless. Sending it from the frontend is redundant and could be confusing if the schema changes. Minor, but worth cleaning up.

**Fix:** Remove `status` from the `bookSession` payload.

---

### 8. `_purge_stale_tokens` has no logging guard for zero-deletion runs
**File:** `backend/main.py`

The purge only prints when tokens are deleted. If it runs on startup and deletes nothing, there's no confirmation it ran at all. Makes debugging startup issues harder.

**Fix:** Add a `print("Token purge completed: nothing to remove.")` branch, or move to a proper logger.

---

## 🟢 Low / Quality-of-Life

### 9. Session checker catches all exceptions silently
**File:** `backend/routers/sessions.py` → `session_checker_task()`

The `except Exception as e: print(...)` block swallows all errors inside the loop body. If a recurring exception hits (e.g., DB schema mismatch after a migration), it will silently spam stdout with no alerting.

**Fix:** Log to `logging.getLogger` at `ERROR` level, and consider emitting an in-app admin notification after N consecutive failures.

---

### 10. No CSV/PDF export for Activity Log
**File:** `frontend/src/views/admin/ActivityLog.vue`

The activity log is admin-only and audit-critical, but there's no way to export it. The payments view has printable receipts — the activity log should have a similar export option.

**Fix:** Add a `GET /activity-log/export.csv` endpoint and an "Export" button in the UI.

---

### 11. `bookSession` and `proposeSession` flows don't pass `instrument_id`
Covered in Bug #1 above, but worth noting that teacher-initiated proposals (`propose/teacher`) also omit instrument. A consistent fix should cover all three paths: admin-book, student-propose, teacher-propose.

---

### 12. Shop order fulfillment doesn't notify student
**File:** `backend/routers/shop.py` → `update_order_status()`

When status transitions `approved → fulfilled`, no notification is sent to the student. The `approved` and `cancelled` transitions do send notifications, but `fulfilled` is missing one.

**Fix:**
```python
elif old_status == "approved" and new_status == "fulfilled":
    notify_users(db, [order.user_id],
        f"✅ Your order #{order.id} has been fulfilled and is ready for pickup!")
```

---

## Summary Table

| # | Severity | Area | Fix Complexity |
|---|---|---|---|
| 1 | 🔴 Bug | instrument_id not sent | Medium |
| 2 | 🔴 Bug | Student can propose to any teacher | Easy |
| 3 | 🔴 Bug | No sessions_left gate on proposal | Easy |
| 4 | 🟡 Medium | Token purge only at startup | Easy |
| 5 | 🟡 Medium | Activity log fetches 500 rows | Medium |
| 6 | 🟡 Medium | No enrollment check on admin booking | Medium |
| 7 | 🟡 Medium | Redundant `status` in booking payload | Trivial |
| 8 | 🟡 Medium | Silent purge logging | Trivial |
| 9 | 🟢 Low | Silent exception logging in checker | Easy |
| 10 | 🟢 Low | No activity log export | Medium |
| 11 | 🟢 Low | propose flows also missing instrument_id | Medium |
| 12 | 🟢 Low | No fulfilled notification in shop | Trivial |

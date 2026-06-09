import asyncio
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload, selectinload

from .. import models, schemas
from ..config import settings
from ..database import SessionLocal, get_db
from ..dependencies import get_current_active_user, require_admin, require_student, require_teacher
from ..services.notifier import safe_notify
from ..utils.signed_urls import sign_url
from ..utils.uploads import save_upload

router = APIRouter()

# Per-(IP, session_id) rate-limit key for nudge — scopes the limit per session so
# a user cannot spam one session's participants while still being able to nudge others.
def _nudge_key(request: Request) -> str:
    ip = get_remote_address(request)
    session_id = request.path_params.get("session_id", "unknown")
    return f"nudge:{ip}:{session_id}"

_limiter = Limiter(key_func=_nudge_key)

# --- Helpers ---

def format_dt(dt: datetime) -> str:
    return dt.strftime("%b %d at %I:%M %p") if dt else "Unknown"

from .activity import log_activity
from .notifications import notify_users


def _check_version(db_session: models.Session, expected: int | None) -> None:
    """Reject the request with 409 if the caller's view of the session is stale.

    Pass ``expected`` from the client request body. ``None`` means the caller
    opted out of optimistic locking (legacy clients) and we let it through —
    this keeps the change backwards-compatible while new clients get safety.

    Contract: every endpoint that meaningfully transitions a session's state
    (status change, time change, party change, proof verdict) MUST call
    ``_check_version`` before mutating and ``_bump_version`` before commit.
    Background-only updates that do NOT change observable session state for
    the user (e.g. setting ``notified_24h=True`` in the checker task, or
    setting ``stale_reminded_at`` after a reminder send) intentionally
    SKIP the bump. That avoids gratuitous 409s on active frontend tabs whose
    cached version would otherwise drift behind the server every loop tick.
    When you add a new field, decide which bucket it falls into and document
    that at the call site.
    """
    if expected is None:
        return
    if db_session.version != expected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Session was modified by someone else "
                f"(expected version {expected}, got {db_session.version}). "
                "Reload and try again."
            ),
        )


def _bump_version(db_session: models.Session) -> None:
    """Increment session version. Call before commit on every status transition.
    Also clears stale_reminded_at so the reminder clock restarts after any action.

    Do NOT call this for notification-only updates (see ``_check_version``
    docstring) — the version is part of the user-visible state contract.
    """
    db_session.version = (db_session.version or 0) + 1
    db_session.stale_reminded_at = None


# ── Session-time validation ─────────────────────────────────────────────────
# Centralized so every create/propose/counter/edit path enforces the same
# rules. Conservative defaults; widen if a real use case shows up.
_MIN_SESSION_MINUTES = 15
_MAX_SESSION_MINUTES = 240
# Small clock-skew tolerance so a client submitting "now" doesn't get rejected
# if the server clock is ~1 minute ahead.
_PAST_CLOCK_SKEW_SECONDS = 60


def _validate_session_window(
    start: datetime,
    end: datetime | None,
    *,
    allow_past: bool = False,
    is_admin: bool = False,
) -> datetime:
    """Validate a (start, end) window. Returns the resolved ``end`` time.

    Rules:
      - Naive datetimes are coerced to UTC (SQLite hands them back naive).
      - ``end`` defaults to ``start + 1h`` if omitted.
      - ``end`` must be strictly greater than ``start``.
      - Duration must be in [_MIN_SESSION_MINUTES, _MAX_SESSION_MINUTES].
      - ``start`` must not be in the past (modulo clock-skew tolerance),
        unless ``allow_past=True`` — used by admin manual-entry endpoints
        that record historic sessions.
      - Non-admin sessions must fall within school working hours.

    Raises HTTPException(400) on any violation; never silently coerces.
    """
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end is None:
        end = start + timedelta(hours=1)
    elif end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    if end <= start:
        raise HTTPException(
            status_code=400,
            detail="Session end time must be after start time.",
        )

    duration_minutes = (end - start).total_seconds() / 60
    if duration_minutes < _MIN_SESSION_MINUTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Session is too short ({int(duration_minutes)} min). "
                f"Minimum allowed is {_MIN_SESSION_MINUTES} minutes."
            ),
        )
    if duration_minutes > _MAX_SESSION_MINUTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Session is too long ({int(duration_minutes)} min). "
                f"Maximum allowed is {_MAX_SESSION_MINUTES} minutes."
            ),
        )

    if not allow_past:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=_PAST_CLOCK_SKEW_SECONDS)
        if start < cutoff:
            raise HTTPException(
                status_code=400,
                detail="Cannot schedule a session in the past.",
            )

    if not is_admin:
        if start.date() != end.date():
            raise HTTPException(
                status_code=400,
                detail="Session cannot span across multiple days.",
            )
        start_hour_val = start.hour + start.minute / 60.0 + start.second / 3600.0
        end_hour_val = end.hour + end.minute / 60.0 + end.second / 3600.0
        if start_hour_val < settings.WORKING_HOURS_START or end_hour_val > settings.WORKING_HOURS_END:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Session must fall within school working hours "
                    f"({settings.WORKING_HOURS_START}:00 to {settings.WORKING_HOURS_END}:00)."
                ),
            )

    return end



def get_admin_ids(db) -> list:
    """Return all admin user IDs."""
    admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
    if not admin_role:
        return []
    admins = db.query(models.User).filter(models.User.role_id == admin_role.id).all()
    return [a.id for a in admins]


_OVERLAP_ACTIVE_STATUSES = [
    "scheduled", "pending_teacher", "pending_student", "pending_admin",
    "overdue", "pending_verification", "overdue_rejected",
]

def _check_overlap(db, teacher_id: int, student_id: int, start: datetime, end: datetime, exclude_session_id: int | None = None) -> None:
    """Raise 409 if either participant already has an active session that overlaps [start, end)."""
    q = db.query(models.Session).filter(
        models.Session.status.in_(_OVERLAP_ACTIVE_STATUSES),
        models.Session.start_time < end,
        models.Session.end_time > start,
        (
            (models.Session.teacher_id == teacher_id) |
            (models.Session.student_id == student_id)
        ),
    )
    if exclude_session_id is not None:
        q = q.filter(models.Session.id != exclude_session_id)
    conflict = q.first()
    if conflict:
        role = "teacher" if conflict.teacher_id == teacher_id else "student"
        raise HTTPException(
            status_code=409,
            detail=f"Scheduling conflict: the {role} already has an active session overlapping this time slot (Session #{conflict.id}).",
        )

def _signed_or_passthrough(url: str | None) -> str | None:
    """Sign internal upload URLs; leave anything else (including absolute
    URLs to external CDNs or already-signed URLs) untouched."""
    if not url:
        return url
    if url.startswith(("/uploads/proofs/", "/uploads/homework/")):
        return sign_url(url)
    return url


def get_session_conflict_id(db, session: models.Session) -> int | None:
    """Return the ID of an overlapping scheduled session if one exists."""
    if session.status not in _OVERLAP_ACTIVE_STATUSES:
        return None
    conflict = db.query(models.Session).filter(
        models.Session.id != session.id,
        models.Session.status == "scheduled",
        models.Session.start_time < session.end_time,
        models.Session.end_time > session.start_time,
        (
            (models.Session.teacher_id == session.teacher_id) |
            (models.Session.student_id == session.student_id)
        )
    ).first()
    return conflict.id if conflict else None


def map_session(db_session: models.Session) -> dict:
    from sqlalchemy.orm import object_session
    session_dict = schemas.Session.model_validate(db_session).model_dump()
    db = object_session(db_session)
    if db:
        session_dict['conflict_session_id'] = get_session_conflict_id(db, db_session)
    else:
        session_dict['conflict_session_id'] = None

    # Sign all proof URLs (top-level and nested) so the frontend can
    # render <img src> directly without needing to attach auth headers.
    session_dict['proof_image_url'] = (
        _signed_or_passthrough(db_session.proofs[0].image_url)
        if db_session.proofs else None
    )
    for proof in session_dict.get('proofs') or []:
        proof['image_url'] = _signed_or_passthrough(proof.get('image_url'))
    session_dict['homework_assigned'] = db_session.homeworks[0].description if db_session.homeworks else None
    session_dict['homework_completed'] = db_session.homeworks[0].is_completed if db_session.homeworks else False
    # Sign homework file URLs if exposed in the nested list.
    for hw in session_dict.get('homeworks') or []:
        hw['file_url'] = _signed_or_passthrough(hw.get('file_url'))
    return session_dict



def _session_eager_options():
    """Return a consistent set of eager-load options to prevent N+1 queries on bulk session fetches."""
    return [
        selectinload(models.Session.proofs),
        selectinload(models.Session.homeworks),
        joinedload(models.Session.instrument),
    ]

_last_token_purge: datetime | None = None

async def session_checker_task():
    global _last_token_purge
    while True:
        try:
            # Off-hours back-off: 00:00–06:00 UTC → 5 min intervals to reduce DB churn.
            _hour = datetime.now(timezone.utc).hour
            sleep_interval = 300 if _hour < 6 else 60

            db = SessionLocal()
            try:
                now = datetime.now(timezone.utc)

                # ── Daily token and notification purge, and drift recalculation ──────────────────
                if _last_token_purge is None or (now - _last_token_purge).total_seconds() >= 86400:
                    from .. import models as _m
                    deleted_refresh = (
                        db.query(_m.RefreshToken)
                        .filter((_m.RefreshToken.revoked == True) | (_m.RefreshToken.expires_at < now))
                        .delete(synchronize_session=False)
                    )
                    deleted_reset = (
                        db.query(_m.PasswordResetToken)
                        .filter(_m.PasswordResetToken.expires_at < now)
                        .delete(synchronize_session=False)
                    )
                    
                    # 90-day Notification purge
                    deleted_notifications = (
                        db.query(_m.Notification)
                        .filter(_m.Notification.created_at < now - timedelta(days=90))
                        .delete(synchronize_session=False)
                    )

                    # Nightly drift recalculation
                    students = db.query(_m.User).join(_m.Role).filter(_m.Role.name.ilike("student")).all()
                    drift_detected = False
                    for student in students:
                        enrollments = db.query(_m.Enrollment).filter(_m.Enrollment.student_id == student.id, _m.Enrollment.is_active == True).all()
                        recalculated = sum(max(0, e.sessions_purchased - e.sessions_used) for e in enrollments)
                        old_value = student.sessions_left or 0
                        if old_value != recalculated:
                            student.sessions_left = recalculated
                            drift_detected = True
                            log_activity(
                                db,
                                action_type="sessions_recalculated",
                                description=f"System nightly cleanup recalculated sessions_left for {student.name}: {old_value} → {recalculated}",
                                target_type="user",
                                target_id=student.id,
                            )
                    
                    db.commit()
                    _last_token_purge = now
                    
                    if deleted_refresh or deleted_reset or deleted_notifications:
                        logger.info("Daily token purge: removed %d refresh, %d reset token(s), %d notifications.", deleted_refresh, deleted_reset, deleted_notifications)
                    else:
                        logger.info("Daily token purge: nothing to remove.")
                        
                    if drift_detected:
                        notify_users(db, get_admin_ids(db), "⚠️ Nightly cleanup detected and resolved session credit drift for one or more students.")

                # ── Stale-state reminders ─────────────────────────────────────────
                # Always run, regardless of whether any "scheduled" sessions exist,
                # because pending_verification / overdue_rejected sessions are
                # independent of the scheduled-only gate below.
                STALE_THRESHOLD_HOURS = settings.STALE_THRESHOLD_HOURS
                stale_cutoff = now - timedelta(hours=STALE_THRESHOLD_HOURS)
                REMINDER_COOLDOWN_HOURS = settings.REMINDER_COOLDOWN_HOURS

                stale_sessions = db.query(models.Session).filter(
                    models.Session.status.in_(["pending_verification", "overdue_rejected", "pending_teacher", "pending_student", "pending_admin"]),
                    models.Session.updated_at < stale_cutoff,
                    # Only send if we haven't reminded within the cooldown window
                    (
                        (models.Session.stale_reminded_at == None) |
                        (models.Session.stale_reminded_at < now - timedelta(hours=REMINDER_COOLDOWN_HOURS))
                    ),
                ).all()

                for s in stale_sessions:
                    dt_str = format_dt(s.start_time)
                    if s.status == "pending_verification":
                        notify_users(
                            db,
                            [s.teacher_id, s.student_id],
                            f"Reminder: Session proof for {dt_str} has been waiting for admin review for over {STALE_THRESHOLD_HOURS}h. An admin will action it soon.",
                        )
                        # Also ping admins so they know a proof is waiting
                        notify_users(
                            db,
                            get_admin_ids(db),
                            f"Action Required: Session #{s.id} ({dt_str}) proof has been pending your review for over {STALE_THRESHOLD_HOURS}h.",
                        )
                    elif s.status == "overdue_rejected":
                        notify_users(
                            db,
                            [s.teacher_id, s.student_id],
                            f"Reminder: Session proof for {dt_str} was rejected over {STALE_THRESHOLD_HOURS}h ago. Please re-upload your proof.",
                        )
                    elif s.status == "pending_teacher":
                        notify_users(
                            db,
                            [s.teacher_id],
                            f"Reminder: Session request with student for {dt_str} is pending your approval for over {STALE_THRESHOLD_HOURS}h.",
                        )
                    elif s.status == "pending_student":
                        notify_users(
                            db,
                            [s.student_id],
                            f"Reminder: Counter-proposal for session on {dt_str} is pending your response for over {STALE_THRESHOLD_HOURS}h.",
                        )
                    elif s.status == "pending_admin":
                        notify_users(
                            db,
                            get_admin_ids(db),
                            f"Reminder: Session #{s.id} for {dt_str} is pending admin approval for over {STALE_THRESHOLD_HOURS}h.",
                        )

                    s.stale_reminded_at = now

                if stale_sessions:
                    db.commit()

                # ── Scheduled-session reminders & overdue transition ──────────────
                # Short-circuit: skip these queries when there are no "scheduled"
                # sessions — avoids unnecessary DB load when the calendar is empty.
                has_scheduled = db.query(
                    db.query(models.Session).filter(
                        models.Session.status == "scheduled"
                    ).exists()
                ).scalar()

                if has_scheduled:
                    # Check for 24h notifications
                    target_24h = now + timedelta(hours=24)
                    sessions_24h = db.query(models.Session).filter(
                        models.Session.status == "scheduled",
                        models.Session.start_time <= target_24h,
                        models.Session.start_time > now,
                        models.Session.notified_24h == False
                    ).all()
                    for s in sessions_24h:
                        dt_str = format_dt(s.start_time)
                        notify_users(db, [s.teacher_id, s.student_id], f"Reminder: Session scheduled in ~24h on {dt_str}.")
                        s.notified_24h = True

                    # Check for 12h notifications
                    target_12h = now + timedelta(hours=12)
                    sessions_12h = db.query(models.Session).filter(
                        models.Session.status == "scheduled",
                        models.Session.start_time <= target_12h,
                        models.Session.start_time > now,
                        models.Session.notified_12h == False
                    ).all()
                    for s in sessions_12h:
                        dt_str = format_dt(s.start_time)
                        notify_users(db, [s.teacher_id, s.student_id], f"Reminder: Session schedule nearing! ~12h left for {dt_str}.")
                        s.notified_12h = True

                    # Check for overdue sessions (end_time in the past)
                    overdue_sessions = db.query(models.Session).filter(
                        models.Session.status == "scheduled",
                        models.Session.end_time < now
                    ).all()
                    for s in overdue_sessions:
                        dt_str = format_dt(s.start_time)
                        s.status = "overdue"
                        _bump_version(s)
                        notify_users(db, [s.teacher_id, s.student_id], f"Action Required: Session from {dt_str} is overdue. Please upload proofs or mark complete.")
                        log_activity(
                            db,
                            action_type="session_overdue",
                            description=f"Session #{s.id} on {dt_str} automatically marked overdue.",
                            target_type="session",
                            target_id=s.id,
                        )

                    db.commit()

            except Exception as e:
                logger.error("Error in session_checker_task iteration: %s", e, exc_info=True)
                db.rollback()
            finally:
                db.close()
            await asyncio.sleep(sleep_interval)
        except Exception as outer_e:
            logger.critical("CRITICAL: session_checker_task crashed: %s. Restarting in 60s.", outer_e, exc_info=True)
            await asyncio.sleep(60)

# --- Endpoints ---

@router.post("/sessions/record", response_model=schemas.Session)
def record_past_session(session: schemas.SessionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Admin creates a manual past session directly."""
    student = db.query(models.User).filter(models.User.id == session.student_id).first()
    teacher = db.query(models.User).filter(models.User.id == session.teacher_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Past sessions are explicitly allowed here (this endpoint records history),
    # but duration sanity still applies.
    end_time = _validate_session_window(session.start_time, session.end_time, allow_past=True, is_admin=True)

    db_session = models.Session(
        teacher_id=session.teacher_id,
        student_id=session.student_id,
        start_time=session.start_time,
        end_time=end_time,
        status="completed",
        notes=session.notes,
        proposed_by=current_user.id,
        is_manual_entry=True,
        instrument_id=session.instrument_id,
        session_number=session.session_number
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    # Update analytics — atomic decrement to prevent going negative
    db.execute(
        text(
            "UPDATE users SET sessions_left = sessions_left - 1 "
            "WHERE id = :uid AND sessions_left IS NOT NULL AND sessions_left > 0"
        ),
        {"uid": db_session.student_id},
    )
    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == db_session.student_id,
        models.Enrollment.teacher_id == db_session.teacher_id,
        models.Enrollment.is_active == True
    ).order_by(models.Enrollment.id.desc()).first()
    if enrollment:
        db.execute(
            text(
                "UPDATE enrollments SET sessions_used = sessions_used + 1 "
                "WHERE id = :eid"
            ),
            {"eid": enrollment.id},
        )
        db.expire(enrollment, ["sessions_used"])
    db.commit()
    # Re-query student so sessions_left reflects the DB value after the raw UPDATE
    student = db.query(models.User).filter(models.User.id == db_session.student_id).first()

    # Notify student if sessions are running low
    if student and student.sessions_left is not None:
        if student.sessions_left == 0:
            notify_users(db, [student.id],
                         "You have no sessions left. Please contact admin to top up your sessions.",
                         title="⚠️ No Sessions Remaining", link="/student/dashboard")
            notify_users(db, get_admin_ids(db),
                         f"{student.name} has used all their sessions. Consider scheduling a renewal.",
                         title="⚠️ Student Out of Sessions", link="/admin/students")
        elif student.sessions_left == 1:
            notify_users(db, [student.id],
                         "You have only 1 session left. Contact admin to book more sessions soon.",
                         title="⚠️ Last Session Remaining", link="/student/dashboard")

    dt_str = format_dt(db_session.start_time)
    log_activity(db, action_type="session_manual_entry",
                 description=f"Manual session entry for {student.name} with {teacher.name} on {dt_str}",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="session", target_id=db_session.id)

    # Reload with eager options so map_session can access proofs/homeworks
    db.refresh(db_session)
    db_session = (
        db.query(models.Session)
        .options(*_session_eager_options())
        .filter(models.Session.id == db_session.id)
        .first()
    )
    return map_session(db_session)

@router.get("/sessions/student/{student_id}/records", response_model=list[schemas.Session])
def get_student_records(student_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if current_user.role.name.lower() == "student" and current_user.id != student_id:
         raise HTTPException(status_code=403, detail="Not authorized")
    sessions = (
        db.query(models.Session)
        .options(*_session_eager_options())
        .filter(models.Session.student_id == student_id)
        .order_by(models.Session.start_time.desc())
        .all()
    )
    return [map_session(s) for s in sessions]

@router.post("/sessions/recurring", response_model=schemas.RecurringSessionResult)
def create_recurring_sessions(
    payload: schemas.RecurringSessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Generate a series of scheduled sessions from a single template."""
    student = db.query(models.User).filter(models.User.id == payload.student_id).first()
    teacher = db.query(models.User).filter(models.User.id == payload.teacher_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Validate the template window; recurring sessions are future-only.
    _validate_session_window(payload.start_time, payload.end_time, is_admin=True)

    duration = payload.end_time - payload.start_time
    step = {
        "weekly": timedelta(weeks=1),
        "biweekly": timedelta(weeks=2),
        "monthly": timedelta(days=28),
    }[payload.cadence]

    skip_set = {d.replace(microsecond=0) for d in payload.skip_dates}
    created_ids: list[int] = []
    skipped = 0
    occurrence_start = payload.start_time

    for _ in range(payload.occurrences):
        if occurrence_start.replace(microsecond=0) in skip_set:
            skipped += 1
        else:
            occurrence_end = occurrence_start + duration
            # Check for scheduling conflicts on each occurrence individually so
            # the admin sees a clear error rather than silently double-booking.
            _check_overlap(db, payload.teacher_id, payload.student_id, occurrence_start, occurrence_end)
            db_session = models.Session(
                teacher_id=payload.teacher_id,
                student_id=payload.student_id,
                start_time=occurrence_start,
                end_time=occurrence_end,
                status="scheduled",
                proposed_by=current_user.id,
                notes=payload.notes,
                instrument_id=payload.instrument_id,
            )
            db.add(db_session)
            db.flush()
            created_ids.append(db_session.id)
        occurrence_start = occurrence_start + step

    db.commit()

    log_activity(
        db, action_type="recurring_series_created",
        description=f"Admin {current_user.name} created {len(created_ids)} recurring sessions ({payload.cadence}) for {student.name} with {teacher.name}",
        actor_id=current_user.id, actor_name=current_user.name,
        target_type="session", target_id=created_ids[0] if created_ids else None,
    )
    if student:
        safe_notify("send_session_confirmed", student, type("S", (), {"id": created_ids[0] if created_ids else 0, "start_time": payload.start_time}))
    return schemas.RecurringSessionResult(
        created_count=len(created_ids),
        skipped_count=skipped,
        session_ids=created_ids,
    )


@router.post("/sessions/", response_model=schemas.Session)
def create_session(session: schemas.SessionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Admin creates a session directly — immediately scheduled."""
    student = db.query(models.User).filter(models.User.id == session.student_id).first()
    teacher = db.query(models.User).filter(models.User.id == session.teacher_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    end_time = _validate_session_window(session.start_time, session.end_time, is_admin=True)
    _check_overlap(db, session.teacher_id, session.student_id, session.start_time, end_time)

    db_session = models.Session(
        teacher_id=session.teacher_id,
        student_id=session.student_id,
        start_time=session.start_time,
        end_time=end_time,
        status="scheduled",
        proposed_by=current_user.id,
        notes=session.notes
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    notify_users(db, [db_session.teacher_id], f"📅 Admin has scheduled a session with {student.name} on {dt_str}.")
    notify_users(db, [db_session.student_id], f"✅ A session has been scheduled for you on {dt_str} with {teacher.name}.")
    log_activity(db, action_type="session_scheduled",
                 description=f"Session scheduled for {student.name} with {teacher.name} on {dt_str}",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="session", target_id=db_session.id)

    return map_session(db_session)

@router.get("/sessions/pending", response_model=list[schemas.Session])
def read_pending_sessions(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Admin: get all sessions awaiting approval."""
    sessions = (
        db.query(models.Session)
        .options(*_session_eager_options())
        .filter(models.Session.status.in_(["pending_teacher", "pending_admin"]))
        .all()
    )
    return [map_session(s) for s in sessions]

@router.get("/sessions/", response_model=list[schemas.Session])
def read_sessions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    sessions = (
        db.query(models.Session)
        .options(*_session_eager_options())
        .order_by(models.Session.start_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [map_session(s) for s in sessions]

@router.get("/sessions/user/{user_id}", response_model=list[schemas.Session])
def read_user_sessions(
    user_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    sessions = (
        db.query(models.Session)
        .options(*_session_eager_options())
        .filter((models.Session.teacher_id == user_id) | (models.Session.student_id == user_id))
        .order_by(models.Session.start_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [map_session(s) for s in sessions]


@router.get("/sessions/teacher/{teacher_id}/public", response_model=list[schemas.PublicBusySlot])
def read_teacher_public_sessions(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Fetch sanitized busy time slots for a specific teacher's active sessions."""
    if current_user.role.name == "student":
        assignment = db.query(models.TeacherStudent).filter_by(
            teacher_id=teacher_id,
            student_id=current_user.id
        ).first()
        if not assignment:
            raise HTTPException(status_code=403, detail="You are not assigned to this teacher")

    sessions = (
        db.query(models.Session)
        .filter(
            models.Session.teacher_id == teacher_id,
            models.Session.status.in_(_OVERLAP_ACTIVE_STATUSES)
        )
        .all()
    )
    return [schemas.PublicBusySlot(start_time=s.start_time, end_time=s.end_time) for s in sessions]


TERMINAL_STATUSES = {"completed", "cancelled", "rejected"}

@router.put("/sessions/{session_id}", response_model=schemas.Session)
def update_session(session_id: int, session: schemas.SessionEdit, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Admin edits a session."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot edit a session in terminal status '{db_session.status}'."
        )

    update_data = session.model_dump(exclude_unset=True)
    expected_version = update_data.pop("version", None)
    _check_version(db_session, expected_version)

    # If start/end time changes, validate the new window and reset notification
    # flags so the user gets fresh reminders for the rescheduled slot.
    time_fields = {"start_time", "end_time"}
    if time_fields & update_data.keys():
        new_start = update_data.get("start_time", db_session.start_time)
        new_end = update_data.get("end_time", db_session.end_time)
        # Admin edits are allowed on past sessions (e.g. fixing a typo on a
        # completed session before this guard rejects edits of terminal
        # statuses above). For non-terminal statuses we still don't want
        # the admin scheduling into the past — they have manual entry for that.
        update_data["end_time"] = _validate_session_window(
            new_start, new_end, allow_past=False, is_admin=True
        )
        update_data["notified_24h"] = False
        update_data["notified_12h"] = False

    changed_fields = list(update_data.keys())
    for key, value in update_data.items():
        setattr(db_session, key, value)
    _bump_version(db_session)

    db.commit()
    # Re-fetch with eager loads so map_session can access proofs/homeworks without lazy queries
    db_session = (
        db.query(models.Session)
        .options(*_session_eager_options())
        .filter(models.Session.id == session_id)
        .first()
    )

    dt_str = format_dt(db_session.start_time)
    log_activity(
        db,
        action_type="session_updated",
        description=f"Admin {current_user.name} edited session #{session_id} ({dt_str}); changed: {', '.join(changed_fields)}",
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="session",
        target_id=session_id,
    )

    return map_session(db_session)

@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Roll back sessions_left and enrollment counter if deleting a completed session
    student_name = db_session.student.name if db_session.student else f"student #{db_session.student_id}"
    teacher_name = db_session.teacher.name if db_session.teacher else f"teacher #{db_session.teacher_id}"
    dt_str = format_dt(db_session.start_time)

    if db_session.status == "completed":
        now = datetime.now(timezone.utc)
        start_time = db_session.start_time
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if (now - start_time).days >= 30:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete completed session older than 30 days. Edit the audit log instead.",
            )

        student = db.query(models.User).filter(models.User.id == db_session.student_id).first()
        if student and student.sessions_left is not None:
            student.sessions_left += 1

        enrollment = db.query(models.Enrollment).filter(
            models.Enrollment.student_id == db_session.student_id,
            models.Enrollment.teacher_id == db_session.teacher_id
        ).order_by(models.Enrollment.id.desc()).first()
        if enrollment and enrollment.sessions_used > 0:
            db.execute(
                text(
                    "UPDATE enrollments SET sessions_used = sessions_used - 1 "
                    "WHERE id = :eid AND sessions_used > 0"
                ),
                {"eid": enrollment.id},
            )
            db.expire(enrollment, ["sessions_used"])

    log_activity(
        db,
        action_type="session_deleted",
        description=f"Admin {current_user.name} deleted session #{session_id} ({dt_str}) between {student_name} and {teacher_name} [status was '{db_session.status}']",
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="session",
        target_id=session_id,
    )

    db.delete(db_session)
    db.commit()
    return {"message": "Session deleted successfully"}

@router.post("/sessions/{session_id}/cancel", response_model=schemas.Session)
def cancel_session(
    session_id: int,
    approval: schemas.SessionApproval = schemas.SessionApproval(),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    is_admin = current_user.role and current_user.role.name.lower() == "admin"
    is_participant = current_user.id in (db_session.student_id, db_session.teacher_id)
    if not (is_admin or is_participant):
        raise HTTPException(status_code=403, detail="You are not authorized to cancel this session")

    # Allowed source statuses: scheduled, pending_teacher, pending_student, pending_admin, overdue, overdue_rejected
    # Reject completed, cancelled, rejected, pending_verification with 409
    if db_session.status in ("completed", "cancelled", "rejected", "pending_verification"):
        raise HTTPException(status_code=409, detail=f"Cannot cancel a session in '{db_session.status}' status")

    _check_version(db_session, approval.version)

    # Cutoff check: if not admin, cannot cancel within CANCEL_CUTOFF_HOURS
    start_time = db_session.start_time
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    if not is_admin:
        cutoff_time = start_time - timedelta(hours=settings.CANCEL_CUTOFF_HOURS)
        if datetime.now(timezone.utc) >= cutoff_time:
            raise HTTPException(
                status_code=400,
                detail=f"Sessions starting in less than {settings.CANCEL_CUTOFF_HOURS} hours must be cancelled by an admin."
            )

    old_status = db_session.status
    db_session.status = "cancelled"
    if approval.notes:
        db_session.notes = approval.notes
    _bump_version(db_session)
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    log_activity(
        db,
        action_type="session_cancelled",
        description=f"User {current_user.name} cancelled session #{session_id} on {dt_str} [old status was '{old_status}']",
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="session",
        target_id=session_id,
    )

    notify_ids = set()
    for uid in (db_session.student_id, db_session.teacher_id):
        if uid != current_user.id:
            notify_ids.add(uid)
    
    notify_reason = f" Reason: {approval.notes}" if approval.notes else ""
    if notify_ids:
        notify_users(db, list(notify_ids), f"❌ Session on {dt_str} has been cancelled by {current_user.name}.{notify_reason}")
    notify_users(db, get_admin_ids(db), f"❌ Session #{db_session.id} on {dt_str} was cancelled by {current_user.name}.{notify_reason}")

    return map_session(db_session)

@router.post("/sessions/propose/student", response_model=schemas.Session)
def propose_session_as_student(
    proposal: schemas.SessionPropose,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_student)
):
    """Student proposes a session → pending_teacher."""
    teacher = db.query(models.User).filter(models.User.id == proposal.teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Guard: student must be assigned to this teacher
    assignment = db.query(models.TeacherStudent).filter_by(
        teacher_id=proposal.teacher_id,
        student_id=current_user.id
    ).first()
    if not assignment:
        raise HTTPException(status_code=403, detail="You are not assigned to this teacher")

    # Guard: student must have remaining sessions
    if current_user.sessions_left is not None and current_user.sessions_left <= 0:
        raise HTTPException(
            status_code=400,
            detail="No sessions remaining. Please contact admin to enroll in more."
        )

    end_time = _validate_session_window(proposal.start_time, proposal.end_time, is_admin=(current_user.role.name == "admin"))
    _check_overlap(db, proposal.teacher_id, current_user.id, proposal.start_time, end_time)

    db_session = models.Session(
        teacher_id=proposal.teacher_id,
        student_id=current_user.id,
        start_time=proposal.start_time,
        end_time=end_time,
        status="pending_teacher",
        proposed_by=current_user.id,
        notes=proposal.notes,
        instrument_id=proposal.instrument_id,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    log_activity(
        db,
        action_type="session_proposed",
        description=f"Student {current_user.name} proposed a session with {teacher.name} on {dt_str}",
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="session",
        target_id=db_session.id,
    )
    notify_users(db, [proposal.teacher_id],
        f"📅 {current_user.name} has requested a session on {dt_str}. Please review and approve or decline.")
    notify_users(db, get_admin_ids(db),
        f"📋 Student {current_user.name} proposed a session with {teacher.name} on {dt_str} (Student ID: {current_user.id}). Awaiting teacher review.")

    return map_session(db_session)

@router.post("/sessions/propose/teacher", response_model=schemas.Session)
def propose_session_as_teacher(
    proposal: schemas.SessionPropose,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """Teacher proposes a session → pending_admin."""
    student = db.query(models.User).filter(models.User.id == proposal.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    end_time = _validate_session_window(proposal.start_time, proposal.end_time, is_admin=(current_user.role.name == "admin"))
    _check_overlap(db, current_user.id, proposal.student_id, proposal.start_time, end_time)

    db_session = models.Session(
        teacher_id=current_user.id,
        student_id=proposal.student_id,
        start_time=proposal.start_time,
        end_time=end_time,
        status="pending_admin",
        proposed_by=current_user.id,
        notes=proposal.notes,
        instrument_id=proposal.instrument_id,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    log_activity(
        db,
        action_type="session_proposed",
        description=f"Teacher {current_user.name} proposed a session with {student.name} on {dt_str}",
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="session",
        target_id=db_session.id,
    )
    notify_users(db, [proposal.student_id],
        f"📅 Your teacher {current_user.name} proposed a session on {dt_str}. It is awaiting admin approval.")
    notify_users(db, get_admin_ids(db),
        f"📋 Teacher {current_user.name} proposed a session with {student.name} on {dt_str}. Awaiting your approval.")

    return map_session(db_session)

@router.post("/sessions/{session_id}/approve/teacher", response_model=schemas.Session)
def approve_session_as_teacher(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """Teacher approves a student proposal → pending_admin."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_teacher":
        raise HTTPException(status_code=409, detail="Session is not awaiting teacher approval")
    if db_session.teacher_id != current_user.id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="You can only approve sessions assigned to you")

    db_session.status = "pending_admin"
    _bump_version(db_session)
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    log_activity(db, action_type="session_teacher_approved",
                 description=f"Teacher {current_user.name} approved session with {db_session.student.name} on {dt_str}",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="session", target_id=db_session.id)

    notify_users(db, get_admin_ids(db),
        f"✅ {current_user.name} approved a session request from {db_session.student.name} on {dt_str}. Awaiting your final approval.")

    return map_session(db_session)

@router.post("/sessions/{session_id}/reject/teacher", response_model=schemas.Session)
def reject_session_as_teacher(
    session_id: int,
    approval: schemas.SessionApproval = schemas.SessionApproval(),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """Teacher rejects a student proposal → rejected."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_teacher":
        raise HTTPException(status_code=409, detail="Session is not awaiting teacher approval")
    if db_session.teacher_id != current_user.id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="You can only reject sessions assigned to you")

    _check_version(db_session, approval.version)
    db_session.status = "rejected"
    if approval.notes:
        db_session.notes = approval.notes
    _bump_version(db_session)
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    log_activity(db, action_type="session_teacher_rejected",
                 description=f"Teacher {current_user.name} rejected session with {db_session.student.name} on {dt_str}",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="session", target_id=db_session.id)

    dt_str = format_dt(db_session.start_time)
    reason = f" Reason: {approval.notes}" if approval.notes else ""
    notify_users(db, [db_session.student_id],
        f"❌ Your session request on {dt_str} was declined by {current_user.name}.{reason}")

    return map_session(db_session)

@router.post("/sessions/{session_id}/counter/teacher", response_model=schemas.Session)
def counter_session_as_teacher(
    session_id: int,
    counter: schemas.SessionCounter,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """Teacher proposes an alternative time → pending_student (or pending_admin if resolving conflict)."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if this session has a conflict with an active scheduled session
    has_conflict_before = get_session_conflict_id(db, db_session) is not None
    
    if db_session.status != "pending_teacher" and not (db_session.status == "scheduled" and has_conflict_before):
        raise HTTPException(status_code=409, detail="Only pending_teacher or conflicting scheduled sessions can be countered by teacher")
    if db_session.teacher_id != current_user.id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="You can only counter sessions assigned to you")

    _check_version(db_session, counter.version)
    counter_end = _validate_session_window(counter.start_time, counter.end_time, is_admin=(current_user.role.name == "admin"))
    _check_overlap(db, db_session.teacher_id, db_session.student_id, counter.start_time, counter_end, exclude_session_id=session_id)
    db_session.start_time = counter.start_time
    db_session.end_time = counter_end
    db_session.proposed_by = current_user.id
    if counter.notes:
        db_session.notes = counter.notes
    db_session.counter_count = (db_session.counter_count or 0) + 1
    
    # If resolving a conflict, bypass student approval and send straight to admin approval
    if has_conflict_before or db_session.counter_count >= settings.COUNTER_PROPOSAL_CAP:
        db_session.status = "pending_admin"
    else:
        db_session.status = "pending_student"
        
    _bump_version(db_session)

    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    if db_session.status == "pending_admin":
        notify_users(db, get_admin_ids(db), f"⚠️ Teacher resolved conflict on session #{db_session.id} - counter cap or conflict resolution reached. Admin approval required.")
        notify_users(db, [db_session.student_id], f"🔄 Session #{db_session.id} has been countered by teacher to resolve conflict and awaits admin approval.")
    else:
        notify_users(db, [db_session.student_id], f"🔄 Teacher {current_user.name} proposed a different time for your session: {dt_str}. Please review.")
        notify_users(db, get_admin_ids(db), f"📋 Session countered by {current_user.name} with a new time: {dt_str}.")

    return map_session(db_session)

@router.post("/sessions/{session_id}/counter/student", response_model=schemas.Session)
def counter_session_as_student(
    session_id: int,
    counter: schemas.SessionCounter,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_student)
):
    """Student proposes an alternative time → pending_teacher."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_student":
        raise HTTPException(status_code=409, detail="Only pending_student sessions can be countered by student")
    if db_session.student_id != current_user.id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="You can only counter sessions assigned to you")

    _check_version(db_session, counter.version)
    counter_end = _validate_session_window(counter.start_time, counter.end_time, is_admin=(current_user.role.name == "admin"))
    _check_overlap(db, db_session.teacher_id, db_session.student_id, counter.start_time, counter_end, exclude_session_id=session_id)
    db_session.start_time = counter.start_time
    db_session.end_time = counter_end
    db_session.proposed_by = current_user.id
    if counter.notes:
        db_session.notes = counter.notes
    db_session.counter_count = (db_session.counter_count or 0) + 1
    
    if db_session.counter_count >= settings.COUNTER_PROPOSAL_CAP:
        db_session.status = "pending_admin"
    else:
        db_session.status = "pending_teacher"
        
    _bump_version(db_session)

    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    if db_session.counter_count >= settings.COUNTER_PROPOSAL_CAP:
        notify_users(db, get_admin_ids(db), f"⚠️ Negotiation deadlock on session #{db_session.id} - counter cap reached. Admin mediation required.")
        notify_users(db, [db_session.teacher_id], f"🔄 Session #{db_session.id} has reached the counter-proposal limit. Awaiting admin mediation.")
    else:
        notify_users(db, [db_session.teacher_id], f"🔄 Student {current_user.name} proposed a different time for your session: {dt_str}. Please review.")

    return map_session(db_session)

@router.post("/sessions/{session_id}/approve/student", response_model=schemas.Session)
def approve_session_as_student(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_student)
):
    """Student approves a teacher's counter-proposal → pending_admin."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_student":
        raise HTTPException(status_code=409, detail="Session is not awaiting student approval")
    if db_session.student_id != current_user.id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="You can only approve sessions assigned to you")

    db_session.status = "pending_admin"
    _bump_version(db_session)
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    log_activity(
        db,
        action_type="session_student_approved",
        description=f"Student {current_user.name} accepted counter-proposal for session on {dt_str}",
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="session",
        target_id=session_id,
    )
    notify_users(db, get_admin_ids(db), f"✅ Student {current_user.name} accepted the counter-proposal for {dt_str}. Awaiting your final approval.")

    return map_session(db_session)

@router.post("/sessions/{session_id}/reject/student", response_model=schemas.Session)
def reject_session_as_student(
    session_id: int,
    approval: schemas.SessionApproval = schemas.SessionApproval(),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_student)
):
    """Student declines a teacher's counter-proposal → rejected."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_student":
        raise HTTPException(status_code=409, detail="Session is not awaiting student decision")
    if db_session.student_id != current_user.id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="You can only reject sessions assigned to you")

    _check_version(db_session, approval.version)
    db_session.status = "rejected"
    if approval.notes:
        db_session.notes = approval.notes
    _bump_version(db_session)
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    reason = f" Reason: {approval.notes}" if approval.notes else ""
    log_activity(db, action_type="session_student_rejected",
                 description=f"Student {current_user.name} declined counter-proposal for session on {dt_str}",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="session", target_id=db_session.id)
    notify_users(db, [db_session.teacher_id],
        f"❌ Student {current_user.name} declined your counter-proposal for {dt_str}.{reason}")
    notify_users(db, get_admin_ids(db),
        f"❌ Session #{db_session.id} was declined by student {current_user.name} after counter-proposal on {dt_str}.")

    return map_session(db_session)

@router.post("/sessions/{session_id}/approve/admin", response_model=schemas.Session)
def approve_session_as_admin(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Admin approves a session → scheduled."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_admin":
        raise HTTPException(status_code=409, detail="Session is not awaiting admin approval")

    db_session.status = "scheduled"
    _bump_version(db_session)
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    log_activity(db, action_type="session_approved",
                 description=f"Admin {current_user.name} approved session with {db_session.student.name} and {db_session.teacher.name} on {dt_str}",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="session", target_id=db_session.id)

    dt_str = format_dt(db_session.start_time)
    notify_users(db, [db_session.teacher_id],
        f"✅ Session on {dt_str} with {db_session.student.name} has been approved and confirmed.")
    notify_users(db, [db_session.student_id],
        f"🎵 Great news! Your session on {dt_str} with {db_session.teacher.name} is confirmed.")

    return map_session(db_session)

@router.post("/sessions/{session_id}/reject/admin", response_model=schemas.Session)
def reject_session_as_admin(
    session_id: int,
    approval: schemas.SessionApproval = schemas.SessionApproval(),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Admin rejects a session → rejected."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status not in ["pending_admin", "pending_teacher"]:
        raise HTTPException(status_code=409, detail="Session is not pending approval")

    _check_version(db_session, approval.version)
    db_session.status = "rejected"
    if approval.notes:
        db_session.notes = approval.notes
    _bump_version(db_session)
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    log_activity(db, action_type="session_rejected",
                 description=f"Admin {current_user.name} rejected session with {db_session.student.name} and {db_session.teacher.name} on {dt_str}",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="session", target_id=db_session.id)

    dt_str = format_dt(db_session.start_time)
    reason = f" Reason: {approval.notes}" if approval.notes else ""

    notify_ids = set()
    if db_session.proposed_by:
        notify_ids.add(db_session.proposed_by)
    notify_ids.add(db_session.teacher_id)
    notify_ids.add(db_session.student_id)

    for uid in notify_ids:
        notify_users(db, [uid],
            f"❌ The session proposal for {dt_str} was not approved by admin.{reason}")

    return map_session(db_session)

@router.post("/sessions/{session_id}/request-approval", response_model=schemas.Session)
def request_session_approval(
    session_id: int,
    approval_req: schemas.SessionRequestApproval,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Student requests approval for an uploaded overdue session proof."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status not in ["overdue", "overdue_rejected"]:
        raise HTTPException(status_code=409, detail="Only overdue sessions can request approval")

    has_proof = any(p.uploader_role in ("student", "teacher") for p in db_session.proofs)
    if not has_proof:
        raise HTTPException(status_code=400, detail="Must upload proof before requesting approval")

    _check_version(db_session, approval_req.version)
    db_session.status = "pending_verification"
    if approval_req.justification:
        db_session.proof_justification = approval_req.justification
    _bump_version(db_session)

    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    log_activity(db, action_type="proof_submitted",
                 description=f"Student {current_user.name} submitted proof for session on {dt_str}",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="session", target_id=db_session.id)

    dt_str = format_dt(db_session.start_time)

    notify_users(db, [db_session.teacher_id], f"🔔 {current_user.name} has submitted proof for the overdue session on {dt_str} and requested approval.", link="/teacher/dashboard")

    admin_ids = get_admin_ids(db)
    if admin_ids:
        notify_users(db, admin_ids, f"🔔 Proof submitted by {current_user.name} for overdue session on {dt_str} requires verification.", link=f"/admin/schedule?session_id={db_session.id}")

    return map_session(db_session)

@router.post("/sessions/{session_id}/nudge", response_model=schemas.Session)
@_limiter.limit("3/minute")
def nudge_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Notify relevant party to upload proof or finalize a session."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Authorization (added Phase 2): only admins or actual participants of
    # this session can nudge. Previously any authenticated user could
    # enumerate session IDs and spam every teacher in the school.
    is_admin = bool(current_user.role and current_user.role.name.lower() == "admin")
    is_party = current_user.id in (db_session.teacher_id, db_session.student_id)
    if not (is_admin or is_party):
        raise HTTPException(
            status_code=403,
            detail="Only session participants or admins can nudge.",
        )

    dt_str = format_dt(db_session.start_time)
    teacher_proof = any(p.uploader_role == 'teacher' for p in db_session.proofs)
    student_proof = any(p.uploader_role == 'student' for p in db_session.proofs)

    if not student_proof:
        notify_users(db, [db_session.student_id], f"🔔 Reminder from {current_user.name}: Please upload your proof for the session on {dt_str}.")
    elif not teacher_proof:
        notify_users(db, [db_session.teacher_id], f"🔔 Reminder from {current_user.name}: Please upload your proof for the session on {dt_str}.")
    else:
        notify_users(db, get_admin_ids(db), f"🔔 Reminder from {current_user.name}: Session on {dt_str} is ready for final approval. All proofs are in.")

    return map_session(db_session)

@router.post("/sessions/{session_id}/reject-proof", response_model=schemas.Session)
def reject_session_proof(
    session_id: int,
    rejection: schemas.SessionRejectProof,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Admin rejects the uploaded session proof."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_verification":
        raise HTTPException(status_code=409, detail="Session is not pending verification")

    _check_version(db_session, rejection.version)
    db_session.status = "overdue_rejected"
    db_session.rejection_reason = rejection.reason
    _bump_version(db_session)

    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    log_activity(db, action_type="proof_rejected",
                 description=f"Admin {current_user.name} rejected proof for session on {dt_str}. Reason: {rejection.reason}",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="session", target_id=db_session.id)

    dt_str = format_dt(db_session.start_time)
    notify_users(db, [db_session.student_id, db_session.teacher_id], f"❌ The proof submitted for the session on {dt_str} was rejected. Reason: {rejection.reason}. Please review and re-submit.")

    if db_session.student:
        safe_notify("send_proof_rejected", db_session.student, db_session, rejection.reason)
    if db_session.teacher:
        safe_notify("send_proof_rejected", db_session.teacher, db_session, rejection.reason)

    return map_session(db_session)

@router.post("/sessions/{session_id}/complete", response_model=schemas.Session)
def complete_session_as_admin(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Admin completes a session overriding proof requirements."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status not in ["scheduled", "overdue", "overdue_rejected", "pending_verification"]:
        raise HTTPException(status_code=409, detail="Only scheduled, overdue, overdue_rejected, or pending_verification sessions can be completed")

    is_force = False
    if db_session.status != "pending_verification":
        # SQLite hands back naive datetimes even when the column is tz-aware,
        # which makes the comparison below blow up with
        # "can't compare offset-naive and offset-aware". Coerce to UTC.
        end_time = db_session.end_time
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        target_time = end_time + timedelta(hours=24)
        if datetime.now(timezone.utc) < target_time:
            raise HTTPException(status_code=400, detail="Cannot force complete a session until 24 hours after its end time.")
        is_force = True
        db_session.is_force_completed = True

    db_session.status = "completed"
    _bump_version(db_session)

    # Atomic decrement: only subtract if sessions_left > 0 to prevent going
    # negative under concurrent completion requests (race condition guard).
    db.execute(
        text(
            "UPDATE users SET sessions_left = sessions_left - 1 "
            "WHERE id = :uid AND sessions_left IS NOT NULL AND sessions_left > 0"
        ),
        {"uid": db_session.student_id},
    )

    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == db_session.student_id,
        models.Enrollment.teacher_id == db_session.teacher_id,
        models.Enrollment.is_active == True
    ).order_by(models.Enrollment.id.desc()).first()
    if enrollment:
        db.execute(
            text(
                "UPDATE enrollments SET sessions_used = sessions_used + 1 "
                "WHERE id = :eid"
            ),
            {"eid": enrollment.id},
        )
        db.expire(enrollment, ["sessions_used"])

    db.commit()
    # Refresh student after the raw UPDATE so ORM object reflects DB value
    student = db.query(models.User).filter(models.User.id == db_session.student_id).first()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    msg = f"✅ Session from {dt_str} has been marked complete by admin."
    if is_force:
        msg = f"⚠️ Session from {dt_str} has been force completed by admin."
    notify_users(db, [db_session.teacher_id, db_session.student_id], msg)

    # Notify student if sessions are running low (mirrors record_past_session logic)
    if student and student.sessions_left is not None:
        if student.sessions_left == 0:
            notify_users(db, [student.id],
                         "You have no sessions left. Please contact admin to top up your sessions.",
                         title="⚠️ No Sessions Remaining", link="/student/dashboard")
            notify_users(db, get_admin_ids(db),
                         f"{student.name} has used all their sessions. Consider scheduling a renewal.",
                         title="⚠️ Student Out of Sessions", link="/admin/students")
        elif student.sessions_left == 1:
            notify_users(db, [student.id],
                         "You have only 1 session left. Contact admin to book more sessions soon.",
                         title="⚠️ Last Session Remaining", link="/student/dashboard")
    action = "session_force_completed" if is_force else "session_completed"
    log_activity(db, action_type=action,
                 description=msg.replace("✅ ", "").replace("⚠️ ", ""),
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="session", target_id=session_id)

    return map_session(db_session)

# --- Enrollments ---

@router.post("/enrollments/", response_model=schemas.Enrollment)
def create_enrollment(enrollment: schemas.EnrollmentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    db_enrollment = models.Enrollment(**enrollment.model_dump())
    db.add(db_enrollment)
    db.commit()
    db.refresh(db_enrollment)

    # Sync sessions_left on the User record so the dashboard counter stays accurate
    student = db.query(models.User).filter(models.User.id == enrollment.student_id).first()
    teacher = db.query(models.User).filter(models.User.id == enrollment.teacher_id).first()
    if student is not None:
        current_left = student.sessions_left or 0
        student.sessions_left = current_left + enrollment.sessions_purchased
        db.commit()

    log_activity(
        db,
        action_type="enrollment_created",
        description=(
            f"Admin {current_user.name} enrolled student "
            f"{student.name if student else enrollment.student_id} "
            f"with teacher {teacher.name if teacher else enrollment.teacher_id} "
            f"({enrollment.sessions_purchased} sessions)"
        ),
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="enrollment",
        target_id=db_enrollment.id,
    )

    return db_enrollment

@router.get("/enrollments/student/{student_id}", response_model=list[schemas.Enrollment])
def read_student_enrollments(student_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.student_id == student_id).all()
    return enrollments

@router.delete("/enrollments/{enrollment_id}", status_code=204)
def delete_enrollment(
    enrollment_id: int,
    force: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Admin removes an enrollment and rolls back sessions_left on the student."""
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    if enrollment.sessions_used > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete enrollment with active usage history. Use force=true to soft-delete."
        )

    remaining = max(0, enrollment.sessions_purchased - enrollment.sessions_used)
    student = db.query(models.User).filter(models.User.id == enrollment.student_id).first()
    teacher = db.query(models.User).filter(models.User.id == enrollment.teacher_id).first()

    if student is not None and remaining > 0:
        student.sessions_left = max(0, (student.sessions_left or 0) - remaining)

    log_activity(
        db,
        action_type="enrollment_deleted",
        description=(
            f"Admin {current_user.name} {'soft-' if enrollment.sessions_used > 0 else ''}removed enrollment #{enrollment_id} "
            f"for student {student.name if student else enrollment.student_id} "
            f"with teacher {teacher.name if teacher else enrollment.teacher_id} "
            f"({remaining} unused sessions rolled back)"
        ),
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="enrollment",
        target_id=enrollment_id,
    )

    if enrollment.sessions_used > 0:
        enrollment.is_active = False
    else:
        db.delete(enrollment)
    db.commit()
    return None

@router.post("/students/{student_id}/recalculate-sessions", response_model=dict)
def recalculate_student_sessions(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Recompute a student's sessions_left from enrollment balances to fix counter drift."""
    student = db.query(models.User).filter(models.User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    enrollments = db.query(models.Enrollment).filter(models.Enrollment.student_id == student_id, models.Enrollment.is_active == True).all()
    recalculated = sum(
        max(0, e.sessions_purchased - e.sessions_used) for e in enrollments
    )
    old_value = student.sessions_left or 0
    student.sessions_left = recalculated

    log_activity(
        db,
        action_type="sessions_recalculated",
        description=(
            f"Admin {current_user.name} recalculated sessions_left for {student.name}: "
            f"{old_value} → {recalculated}"
        ),
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="user",
        target_id=student_id,
    )

    db.commit()
    return {"student_id": student_id, "old_sessions_left": old_value, "new_sessions_left": recalculated}

# --- Homework ---

def _serialize_homework(db_homework: models.Homework) -> dict:
    """Pydantic-validate a Homework row and sign its file_url for safe rendering."""
    out = schemas.Homework.model_validate(db_homework).model_dump()
    out["file_url"] = _signed_or_passthrough(out.get("file_url"))
    return out


@router.post("/homework/", response_model=schemas.Homework)
def create_homework(session_id: int, homework: schemas.HomeworkCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_teacher)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    db_homework = models.Homework(**homework.model_dump(), session_id=session_id)
    db.add(db_homework)
    db.commit()
    db.refresh(db_homework)
    return _serialize_homework(db_homework)

@router.put("/homework/{homework_id}", response_model=schemas.Homework)
def update_homework(homework_id: int, is_completed: bool, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_homework = db.query(models.Homework).filter(models.Homework.id == homework_id).first()
    if not db_homework:
        raise HTTPException(status_code=404, detail="Homework not found")

    db_homework.is_completed = is_completed
    db.commit()
    db.refresh(db_homework)
    return _serialize_homework(db_homework)

@router.get("/homework/user/{user_id}", response_model=list[schemas.Homework])
def get_user_homework(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """Fetch all homework assigned to a student."""
    if current_user.role.name.lower() == "student" and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    rows = db.query(models.Homework).join(models.Session).filter(models.Session.student_id == user_id).all()
    return [_serialize_homework(hw) for hw in rows]

@router.post("/homework/{homework_id}/upload", response_model=schemas.Homework)
def upload_homework_file(
    homework_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Students upload proof of completed homework."""
    db_homework = db.query(models.Homework).filter(models.Homework.id == homework_id).first()
    if not db_homework:
        raise HTTPException(status_code=404, detail="Homework not found")

    # Check if student is the owner
    session = db.query(models.Session).filter(models.Session.id == db_homework.session_id).first()
    if current_user.role.name.lower() == "student" and session.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    public_url, _ = save_upload(file, "homework", {"jpg", "jpeg", "png", "webp"})

    db_homework.file_url = public_url
    db_homework.is_completed = True
    db.commit()
    db.refresh(db_homework)
    # Return a copy with the URL signed so the frontend can render it
    # immediately without a separate sign step.
    out = schemas.Homework.model_validate(db_homework).model_dump()
    out["file_url"] = _signed_or_passthrough(out.get("file_url"))
    return out

# --- Session Proofs ---

@router.post("/session-proofs/", response_model=schemas.SessionProof)
def create_session_proof(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Only the teacher or student on this session (or an admin) may upload proof.
    is_admin = current_user.role and current_user.role.name == "admin"
    is_party = current_user.id in (db_session.teacher_id, db_session.student_id)
    if not is_admin and not is_party:
        raise HTTPException(
            status_code=403,
            detail="You are not a participant of this session and cannot upload proof.",
        )

    image_url, _ = save_upload(file, "proofs", {"jpg", "jpeg", "png", "webp"})

    db_proof = models.SessionProof(
        session_id=session_id,
        image_url=image_url,
        uploader_id=current_user.id,
        uploader_role=current_user.role.name if current_user.role else None
    )
    db.add(db_proof)
    db.commit()
    db.refresh(db_proof)
    # Return with the URL signed (route ``GET /uploads/proofs/<name>``
    # rejects unsigned requests).
    out = schemas.SessionProof.model_validate(db_proof).model_dump()
    out["image_url"] = _signed_or_passthrough(out.get("image_url"))
    return out


# ── ICS calendar export ──────────────────────────────────────────────────────

def _ics_escape(s: str) -> str:
    """Escape per RFC 5545 §3.3.11."""
    return (
        s.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def _ics_dt(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


@router.get("/sessions/export.ics")
def export_sessions_ics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Returns a .ics calendar of the user's relevant sessions."""
    q = db.query(models.Session).options(
        joinedload(models.Session.teacher),
        joinedload(models.Session.student),
        joinedload(models.Session.instrument),
    ).filter(
        # Include all active/negotiation statuses; exclude only terminal cancelled/rejected states
        models.Session.status.in_([
            "scheduled",
            "pending_teacher",
            "pending_student",
            "pending_admin",
            "overdue",
            "pending_verification",
            "overdue_rejected",
            "completed",
        ])
    )
    role = (current_user.role.name.lower() if current_user.role else "")
    if role == "teacher":
        q = q.filter(models.Session.teacher_id == current_user.id)
    elif role == "student":
        q = q.filter(models.Session.student_id == current_user.id)
    # admin: all sessions

    now_stamp = _ics_dt(datetime.now(timezone.utc))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SMC//Music School//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:SMC Schedule ({_ics_escape(current_user.name or current_user.email)})",
    ]
    for s in q.all():
        if not s.start_time or not s.end_time:
            continue
        instrument = s.instrument.name if s.instrument else "Lesson"
        teacher = s.teacher.name if s.teacher else "?"
        student = s.student.name if s.student else "?"
        summary = f"{instrument}: {teacher} vs {student}"
        desc = f"Status: {s.status}. Teacher: {teacher}. Student: {student}."
        if s.notes:
            desc += f" Notes: {s.notes}"
        lines += [
            "BEGIN:VEVENT",
            f"UID:session-{s.id}@smc",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART:{_ics_dt(s.start_time)}",
            f"DTEND:{_ics_dt(s.end_time)}",
            f"SUMMARY:{_ics_escape(summary)}",
            f"DESCRIPTION:{_ics_escape(desc)}",
            f"STATUS:{'COMPLETED' if s.status == 'completed' else 'CONFIRMED' if s.status == 'scheduled' else 'TENTATIVE'}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    body = "\r\n".join(lines) + "\r\n"
    return Response(
        content=body,
        media_type="text/calendar",
        headers={
            "Content-Disposition": 'attachment; filename="smc-schedule.ics"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )


# ── Bulk Session Action & Stats ───────────────────────────────────────────────

@router.post("/sessions/bulk-action", response_model=list[schemas.Session])
def bulk_session_action(
    req: schemas.BulkActionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Admin performs a bulk action (approve, cancel, complete) on multiple sessions."""
    sessions = db.query(models.Session).filter(models.Session.id.in_(req.session_ids)).all()
    if len(sessions) != len(req.session_ids):
        found_ids = {s.id for s in sessions}
        missing_ids = set(req.session_ids) - found_ids
        raise HTTPException(status_code=404, detail=f"Sessions not found: {list(missing_ids)}")
    
    updated_sessions = []
    
    for s in sessions:
        if req.action == "approve":
            if s.status != "pending_admin":
                raise HTTPException(status_code=409, detail=f"Session #{s.id} is not pending admin approval (status is '{s.status}')")
            s.status = "scheduled"
            _bump_version(s)
            
            dt_str = format_dt(s.start_time)
            log_activity(db, action_type="session_approved",
                         description=f"Admin {current_user.name} approved session #{s.id} with {s.student.name} and {s.teacher.name} on {dt_str} (bulk)",
                         actor_id=current_user.id, actor_name=current_user.name,
                         target_type="session", target_id=s.id)
            notify_users(db, [s.teacher_id], f"✅ Session on {dt_str} with {s.student.name} has been approved and confirmed.")
            notify_users(db, [s.student_id], f"🎵 Great news! Your session on {dt_str} with {s.teacher.name} is confirmed.")
            
        elif req.action == "complete":
            if s.status not in ["scheduled", "overdue", "overdue_rejected", "pending_verification"]:
                raise HTTPException(status_code=409, detail=f"Session #{s.id} cannot be completed from status '{s.status}'")
            
            is_force = False
            if s.status != "pending_verification":
                end_time = s.end_time
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)
                target_time = end_time + timedelta(hours=24)
                if datetime.now(timezone.utc) < target_time:
                    raise HTTPException(status_code=400, detail=f"Cannot force complete session #{s.id} until 24 hours after its end time.")
                is_force = True
                s.is_force_completed = True
            
            s.status = "completed"
            _bump_version(s)
            
            db.execute(
                text(
                    "UPDATE users SET sessions_left = sessions_left - 1 "
                    "WHERE id = :uid AND sessions_left IS NOT NULL AND sessions_left > 0"
                ),
                {"uid": s.student_id},
            )
            
            enrollment = db.query(models.Enrollment).filter(
                models.Enrollment.student_id == s.student_id,
                models.Enrollment.teacher_id == s.teacher_id,
                models.Enrollment.is_active == True
            ).order_by(models.Enrollment.id.desc()).first()
            if enrollment:
                db.execute(
                    text(
                        "UPDATE enrollments SET sessions_used = sessions_used + 1 "
                        "WHERE id = :eid"
                    ),
                    {"eid": enrollment.id},
                )
                db.expire(enrollment, ["sessions_used"])
            
            dt_str = format_dt(s.start_time)
            msg = f"Session from {dt_str} has been marked complete by admin."
            if is_force:
                msg = f"Session from {dt_str} has been force completed by admin."
            notify_users(db, [s.teacher_id, s.student_id], ("✅ " if not is_force else "⚠️ ") + msg)
            
            # Notify student if low sessions
            student = db.query(models.User).filter(models.User.id == s.student_id).first()
            if student and student.sessions_left is not None:
                if student.sessions_left == 0:
                    notify_users(db, [student.id], "You have no sessions left. Please contact admin to top up your sessions.", title="⚠️ No Sessions Remaining", link="/student/dashboard")
                    notify_users(db, get_admin_ids(db), f"{student.name} has used all their sessions. Consider scheduling a renewal.", title="⚠️ Student Out of Sessions", link="/admin/students")
                elif student.sessions_left == 1:
                    notify_users(db, [student.id], "You have only 1 session left. Contact admin to book more sessions soon.", title="⚠️ Last Session Remaining", link="/student/dashboard")
            
            action = "session_force_completed" if is_force else "session_completed"
            log_activity(db, action_type=action,
                         description=msg,
                         actor_id=current_user.id, actor_name=current_user.name,
                         target_type="session", target_id=s.id)
                         
        elif req.action == "cancel":
            if s.status in TERMINAL_STATUSES and s.status != "completed":
                raise HTTPException(status_code=409, detail=f"Session #{s.id} is already in terminal status '{s.status}'")
            
            if s.status == "completed":
                student = db.query(models.User).filter(models.User.id == s.student_id).first()
                if student and student.sessions_left is not None:
                    student.sessions_left += 1
                enrollment = db.query(models.Enrollment).filter(
                    models.Enrollment.student_id == s.student_id,
                    models.Enrollment.teacher_id == s.teacher_id
                ).order_by(models.Enrollment.id.desc()).first()
                if enrollment and enrollment.sessions_used > 0:
                    db.execute(
                        text(
                            "UPDATE enrollments SET sessions_used = sessions_used - 1 "
                            "WHERE id = :eid AND sessions_used > 0"
                        ),
                        {"eid": enrollment.id},
                    )
                    db.expire(enrollment, ["sessions_used"])
            
            s.status = "cancelled"
            _bump_version(s)
            
            dt_str = format_dt(s.start_time)
            log_activity(db, action_type="session_cancelled",
                         description=f"Admin {current_user.name} cancelled session #{s.id} ({dt_str}) (bulk)",
                         actor_id=current_user.id, actor_name=current_user.name,
                         target_type="session", target_id=s.id)
            notify_users(db, [s.teacher_id, s.student_id], f"❌ Session on {dt_str} has been cancelled by admin.")
        
        updated_sessions.append(s)
    
    db.commit()
    return [map_session(s) for s in updated_sessions]


@router.get("/sessions/stats", response_model=schemas.SessionStatsResponse)
def get_sessions_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Get aggregated session status counts and rate for the dashboard."""
    total = db.query(models.Session).count()
    completed = db.query(models.Session).filter(models.Session.status == "completed").count()
    scheduled = db.query(models.Session).filter(models.Session.status == "scheduled").count()
    overdue = db.query(models.Session).filter(models.Session.status.in_(["overdue", "overdue_rejected"])).count()
    
    pending_statuses = ["pending_teacher", "pending_student", "pending_admin", "pending_verification"]
    pending = db.query(models.Session).filter(models.Session.status.in_(pending_statuses)).count()
    
    awaiting_admin = db.query(models.Session).filter(models.Session.status.in_(["pending_admin", "pending_verification"])).count()
    
    rate = round((completed / total) * 100) if total > 0 else 0
    
    return schemas.SessionStatsResponse(
        total_sessions=total,
        scheduled_sessions=scheduled,
        completed_sessions=completed,
        completion_rate=rate,
        overdue_sessions=overdue,
        pending_sessions=pending,
        awaiting_admin=awaiting_admin
    )



import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_active_user, require_admin

router = APIRouter()


def log_activity(
    db: Session,
    action_type: str,
    description: str,
    actor_id: int | None = None,
    actor_name: str | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
):
    """Helper to write an ActivityLog entry. Call this inside any router action."""
    entry = models.ActivityLog(
        action_type=action_type,
        actor_id=actor_id,
        actor_name=actor_name,
        target_type=target_type,
        target_id=target_id,
        description=description,
    )
    db.add(entry)
    db.commit()
    return entry


def _build_log_query(db: Session, action_type: str | None, search: str | None):
    """Shared filter builder for list and count endpoints."""
    q = db.query(models.ActivityLog)
    if action_type:
        q = q.filter(models.ActivityLog.action_type == action_type)
    if search:
        term = f"%{search}%"
        q = q.filter(
            models.ActivityLog.description.ilike(term)
            | models.ActivityLog.actor_name.ilike(term)
            | models.ActivityLog.target_type.ilike(term)
        )
    return q


@router.get("/count")
def get_activity_log_count(
    action_type: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Return total count of matching activity log entries. Admin only."""
    return {"count": _build_log_query(db, action_type, search).count()}


@router.get("/export.csv")
def export_activity_log_csv(
    action_type: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Export all matching activity log entries as a CSV file. Admin only."""
    rows = (
        _build_log_query(db, action_type, search)
        .order_by(models.ActivityLog.created_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "timestamp", "action_type", "actor", "actor_id", "target_type", "target_id", "description"])
    for row in rows:
        writer.writerow([
            row.id,
            row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
            row.action_type,
            row.actor_name or "",
            row.actor_id or "",
            row.target_type or "",
            row.target_id or "",
            row.description,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=activity-log.csv"},
    )


@router.get("/", response_model=list[schemas.ActivityLogEntry])
def get_activity_log(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, le=100),
    action_type: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Return paginated activity log entries, newest first. Admin only."""
    return (
        _build_log_query(db, action_type, search)
        .order_by(models.ActivityLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/session/{session_id}", response_model=list[schemas.ActivityLogEntry])
def get_session_activity_log(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Return activity log entries for a specific session. Admins and participants only."""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    is_admin = current_user.role and current_user.role.name.lower() == "admin"
    is_participant = current_user.id in (session.student_id, session.teacher_id)
    if not (is_admin or is_participant):
        raise HTTPException(status_code=403, detail="Not authorized to view this session's history")

    return (
        db.query(models.ActivityLog)
        .filter(models.ActivityLog.target_type == "session", models.ActivityLog.target_id == session_id)
        .order_by(models.ActivityLog.created_at.desc())
        .all()
    )

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas
from ..database import get_db
from ..dependencies import require_admin

router = APIRouter()


def log_activity(
    db: Session,
    action_type: str,
    description: str,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
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


@router.get("/", response_model=List[schemas.ActivityLogEntry])
def get_activity_log(
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    action_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Return recent activity log entries, newest first. Admin only."""
    q = db.query(models.ActivityLog)
    if action_type:
        q = q.filter(models.ActivityLog.action_type == action_type)
    return (
        q.order_by(models.ActivityLog.created_at.desc()).offset(skip).limit(limit).all()
    )

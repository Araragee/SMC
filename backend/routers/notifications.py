from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_active_user
from typing import List, Optional

router = APIRouter()

def notify_users(db: Session, user_ids: List[int], title_or_message: str, message_or_link: Optional[str] = None, link: Optional[str] = None):
    """
    Flexible notification helper.
    - notify_users(db, user_ids, message, link=None)
    - notify_users(db, user_ids, title, message, link)
    """
    if link is not None:
        # Shop style: (db, ids, title, message, link)
        title = title_or_message
        message = message_or_link
        full_message = f"**{title}**\n{message}"
        final_link = link
    else:
        # Session style: (db, ids, message, link=None)
        full_message = title_or_message
        final_link = message_or_link

    for uid in user_ids:
        if uid:
            db.add(models.Notification(user_id=uid, message=full_message, link=final_link, is_read=False))
    db.commit()

@router.post("/notifications/", response_model=schemas.Notification)
def create_notification(notification: schemas.NotificationCreate, db: Session = Depends(get_db)):
    db_notification = models.Notification(**notification.dict())
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

@router.get("/notifications/user/{user_id}", response_model=list[schemas.Notification])
def read_user_notifications(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == user_id
    ).order_by(models.Notification.created_at.desc()).offset(skip).limit(limit).all()
    return notifications

@router.patch("/notifications/{notification_id}/read", response_model=schemas.Notification)
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_notif = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not db_notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if db_notif.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db_notif.is_read = True
    db.commit()
    db.refresh(db_notif)
    return db_notif

@router.patch("/notifications/user/{user_id}/read-all")
def mark_all_notifications_read(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if current_user.id != user_id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}

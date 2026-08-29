"""Web push subscription endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..dependencies import get_current_active_user

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/public-key")
def get_public_key():
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="Push not configured")
    return {"key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe", response_model=schemas.SimpleOK)
def subscribe(
    sub: schemas.PushSubscriptionIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    existing = db.query(models.PushSubscription).filter(
        models.PushSubscription.endpoint == sub.endpoint
    ).first()
    if existing:
        existing.user_id = current_user.id
        existing.keys_p256dh = sub.keys_p256dh
        existing.keys_auth = sub.keys_auth
        existing.user_agent = sub.user_agent
    else:
        db.add(models.PushSubscription(
            user_id=current_user.id,
            endpoint=sub.endpoint,
            keys_p256dh=sub.keys_p256dh,
            keys_auth=sub.keys_auth,
            user_agent=sub.user_agent,
        ))
    db.commit()
    return schemas.SimpleOK(detail="subscribed")


@router.post("/unsubscribe", response_model=schemas.SimpleOK)
def unsubscribe(
    sub: schemas.PushSubscriptionIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    db.query(models.PushSubscription).filter(
        models.PushSubscription.endpoint == sub.endpoint,
        models.PushSubscription.user_id == current_user.id,
    ).delete(synchronize_session=False)
    db.commit()
    return schemas.SimpleOK(detail="unsubscribed")

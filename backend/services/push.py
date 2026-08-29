"""Web Push helper. Requires `pywebpush` + VAPID keys in settings.

If pywebpush isn't installed or VAPID keys aren't configured, send_push is a
no-op so dev doesn't break.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from .. import models
from ..config import settings

logger = logging.getLogger(__name__)

try:
    from pywebpush import WebPushException, webpush  # type: ignore
    _HAS_PYWEBPUSH = True
except Exception:  # pragma: no cover
    _HAS_PYWEBPUSH = False


def push_enabled() -> bool:
    return bool(_HAS_PYWEBPUSH and settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY)


def send_push_to_user(db: Session, user_id: int, title: str, body: str, url: str | None = None) -> int:
    """Send web push to every active subscription for the user.

    Returns number of successfully-sent pushes. Stale (410/404) subscriptions
    are deleted. All other errors are logged and swallowed.
    """
    if not push_enabled():
        return 0
    subs = db.query(models.PushSubscription).filter(
        models.PushSubscription.user_id == user_id
    ).all()
    if not subs:
        return 0
    payload = json.dumps({"title": title, "body": body, "url": url or "/"})
    sent = 0
    stale: list[int] = []
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.keys_p256dh, "auth": sub.keys_auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
            )
            sent += 1
        except WebPushException as exc:  # pragma: no cover
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):
                stale.append(sub.id)
            else:
                logger.warning("webpush send failed: %s", exc)
        except Exception as exc:  # noqa: BLE001  # pragma: no cover
            logger.warning("webpush send error: %s", exc)
    if stale:
        db.query(models.PushSubscription).filter(
            models.PushSubscription.id.in_(stale)
        ).delete(synchronize_session=False)
        db.commit()
    return sent

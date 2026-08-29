"""Auth-gated routes for private uploads (session proofs, homework files).

Until Phase 2 these lived under a wide-open ``StaticFiles("/uploads")``
mount: any unauthenticated client with a URL could view any student's
proof. This router replaces that with two routes that require a valid
HMAC signature (see ``backend/utils/signed_urls``) AND a valid auth
token, so a leaked signed URL alone is not enough — the recipient must
also be logged in as the admin or as a participant of the relevant session.

Path-traversal safety: ``filename`` is validated against a strict
character set before being joined to the upload directory, and the
final resolved path is checked to lie inside the expected base.

Public uploads (shop product images) remain mounted via StaticFiles in
``main.py`` under ``/uploads/shop`` — those are intentionally public.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from ..database import get_db
from ..dependencies import get_current_active_user
from ..utils import storage
from ..utils.signed_urls import verify_sig

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Anchored to the same ``uploads/`` directory the rest of the app writes to
# (created on app boot in main.py). Using ``resolve()`` makes the
# traversal check below symlink-safe.
_UPLOADS_ROOT = Path(settings.UPLOADS_DIR).resolve()

# Filenames are generated server-side as ``token_hex(16).<ext>`` — strict
# enough that we can reject anything else outright. This blocks path
# traversal (``..``, ``/``) and weird hidden-file games (``.htaccess``).
_SAFE_FILENAME = re.compile(r"^[A-Fa-f0-9]{32}\.(?:jpg|jpeg|png|webp|pdf)$")


def _safe_path(subdir: str, filename: str) -> Path:
    """Resolve ``uploads/<subdir>/<filename>`` and make sure the result
    stays inside the uploads tree. Raises 400 on a bad filename and 404
    if the file does not exist.

    The double-check (regex + ``is_relative_to``) is deliberate belt-and-
    suspenders: the regex prevents almost everything, but if a future
    subdir uses a different naming scheme we still don't escape.
    """
    if not _SAFE_FILENAME.match(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    candidate = (_UPLOADS_ROOT / subdir / filename).resolve()
    try:
        candidate.relative_to(_UPLOADS_ROOT / subdir)
    except ValueError:
        # Means resolve() escaped the expected directory — refuse.
        raise HTTPException(status_code=400, detail="Invalid filename") from None
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return candidate


def _is_admin(user: models.User) -> bool:
    return bool(user.role and user.role.name.lower() == "admin")


def _user_can_see_proof(db: Session, user: models.User, image_url: str) -> bool:
    """True iff ``user`` is admin OR a teacher/student on a session whose
    ``SessionProof.image_url`` equals ``image_url``.

    We match on the stored URL rather than the filename alone so a future
    rename of the upload subdir doesn't accidentally widen access.
    """
    if _is_admin(user):
        return True
    proof = (
        db.query(models.SessionProof)
        .filter(models.SessionProof.image_url == image_url)
        .first()
    )
    if not proof:
        # No row points at this file. Could be orphan or just-uploaded;
        # only admins are allowed to fetch it.
        return False
    session = (
        db.query(models.Session)
        .filter(models.Session.id == proof.session_id)
        .first()
    )
    if not session:
        return False
    return user.id in (session.teacher_id, session.student_id)


def _user_can_see_homework(db: Session, user: models.User, file_url: str) -> bool:
    """Same shape as ``_user_can_see_proof`` but for Homework.file_url."""
    if _is_admin(user):
        return True
    hw = (
        db.query(models.Homework)
        .filter(models.Homework.file_url == file_url)
        .first()
    )
    if not hw:
        return False
    session = (
        db.query(models.Session)
        .filter(models.Session.id == hw.session_id)
        .first()
    )
    if not session:
        return False
    return user.id in (session.teacher_id, session.student_id)


def _serve(subdir: str, filename: str):
    """Return the stored file, whichever backend holds it.

    Local disk keeps using FileResponse (sendfile, no buffering). Object
    storage is fetched and returned inline — uploads are capped at 10 MB, so
    holding one in memory briefly is cheaper than the streaming plumbing.
    """
    if not _SAFE_FILENAME.match(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not storage.is_remote():
        return FileResponse(_safe_path(subdir, filename))

    found = storage.get(subdir, filename)
    if found is None:
        raise HTTPException(status_code=404, detail="File not found")
    data, content_type = found
    return Response(content=data, media_type=content_type)


@router.get("/proofs/{filename}")
def get_proof(
    filename: str,
    exp: int | None = Query(default=None),
    sig: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Serve a session proof if the caller is allowed AND the URL signature
    is fresh.

    Two checks must pass:
      1. HMAC signature on the URL is valid and unexpired.
      2. Caller is admin OR a participant on the session that owns the proof.
    """
    path_for_sig = f"/uploads/proofs/{filename}"
    if not verify_sig(path_for_sig, exp, sig):
        raise HTTPException(status_code=403, detail="Invalid or expired signature")

    if not _user_can_see_proof(db, current_user, path_for_sig):
        raise HTTPException(status_code=403, detail="Not authorized to view this proof")

    return _serve("proofs", filename)


@router.get("/homework/{filename}")
def get_homework(
    filename: str,
    exp: int | None = Query(default=None),
    sig: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Serve a homework file if the caller is allowed AND the URL signature
    is fresh. Same model as ``get_proof`` but resolves against Homework."""
    path_for_sig = f"/uploads/homework/{filename}"
    if not verify_sig(path_for_sig, exp, sig):
        raise HTTPException(status_code=403, detail="Invalid or expired signature")

    if not _user_can_see_homework(db, current_user, path_for_sig):
        raise HTTPException(status_code=403, detail="Not authorized to view this file")

    return _serve("homework", filename)


@router.get("/shop/{filename}")
def get_shop_image(filename: str):
    """Public product images.

    Only registered when object storage is in use — on local disk these are
    served by the StaticFiles mount in main.py, which is faster.
    """
    return _serve("shop", filename)

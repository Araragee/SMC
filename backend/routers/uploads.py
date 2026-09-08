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

import hashlib
import re
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query
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
# jpg/jpeg/png stay on the list for files stored before every raster upload
# was normalised to WebP.
_SAFE_FILENAME = re.compile(r"^[A-Fa-f0-9]{32}\.(?:jpg|jpeg|png|webp|pdf)$")

# An upload never changes under its own filename, and the signed URL that
# reaches it expires in an hour anyway — so let the browser hold it for
# exactly that long, privately. Without this every render of a proof or
# homework thumbnail is a fresh round trip.
_CACHE_CONTROL = "private, max-age=3600"

# Served files are user-supplied content on our own origin, so they are given
# the narrowest possible execution context: no scripts, no plugins, no
# same-origin privileges. A stored payload that gets past the image decoder
# then still has nothing to reach.
_SANDBOX_CSP = "default-src 'none'; img-src 'self'; sandbox"


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


def _participates_in(db: Session, user: models.User, model, url_column, url: str) -> bool:
    """True iff ``user`` is a teacher or student on the session that owns the
    row of ``model`` whose ``url_column`` equals ``url``.

    One join rather than two sequential queries: this runs on the request path
    of every proof and homework thumbnail the UI renders, so a saved round trip
    to the database is multiplied by every image on the screen.

    We match on the stored URL rather than the filename alone so a future
    rename of the upload subdir doesn't accidentally widen access.
    """
    row = (
        db.query(models.Session.teacher_id, models.Session.student_id)
        .join(model, model.session_id == models.Session.id)
        .filter(url_column == url)
        .first()
    )
    # No row points at this file, or it points at a session that no longer
    # exists. Either way it is an orphan, and only admins may fetch it.
    if row is None:
        return False
    # An unassigned teacher_id is NULL, and ``None in (None, 2)`` is True, so a
    # caller with an unresolved id must not fall into an empty slot.
    return user.id is not None and user.id in (row.teacher_id, row.student_id)


def _user_can_see_proof(db: Session, user: models.User, image_url: str) -> bool:
    """True iff ``user`` is admin OR a participant on the proof's session."""
    if _is_admin(user):
        return True
    return _participates_in(db, user, models.SessionProof, models.SessionProof.image_url, image_url)


def _user_can_see_homework(db: Session, user: models.User, file_url: str) -> bool:
    """Same shape as ``_user_can_see_proof`` but for Homework.file_url."""
    if _is_admin(user):
        return True
    return _participates_in(db, user, models.Homework, models.Homework.file_url, file_url)


def _headers_for(etag: str) -> dict[str, str]:
    return {
        "Cache-Control": _CACHE_CONTROL,
        "ETag": etag,
        # Render in place (these are thumbnails in a modal), but pin the name
        # so a browser that does decide to save one cannot be steered into
        # writing an executable extension.
        "Content-Disposition": "inline",
        "Content-Security-Policy": _SANDBOX_CSP,
        "X-Content-Type-Options": "nosniff",
    }


def _etag_for(subdir: str, filename: str, size: int | None = None) -> str:
    """A strong validator for a stored object.

    Filenames are random and content never changes under one, so the name
    alone identifies the bytes; the size is folded in where it is free so a
    truncated write cannot validate against the complete file. Hashed rather
    than used raw so the header does not restate the (signed, private) storage
    key back to any intermediary.
    """
    material = f"{subdir}/{filename}:{size if size is not None else ''}"
    return '"' + hashlib.sha256(material.encode()).hexdigest()[:32] + '"'


def _not_modified(etag: str) -> Response:
    """A 304 must repeat the validator and the caching policy, and carry no body."""
    return Response(
        status_code=304,
        headers={"ETag": etag, "Cache-Control": _CACHE_CONTROL},
    )


def _serve(subdir: str, filename: str, if_none_match: str | None = None):
    """Return the stored file, whichever backend holds it.

    Local disk keeps using FileResponse (sendfile, no buffering). Object
    storage is fetched and returned inline — uploads are capped at 10 MB, so
    holding one in memory briefly is cheaper than the streaming plumbing.

    Both backends answer a matching ``If-None-Match`` with a 304 before any
    bytes are read. On the remote backend that also skips the round trip to
    the bucket, which is the expensive part.
    """
    if not _SAFE_FILENAME.match(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not storage.is_remote():
        path = _safe_path(subdir, filename)
        etag = _etag_for(subdir, filename, path.stat().st_size)
        if _matches_etag(if_none_match, etag):
            return _not_modified(etag)
        return FileResponse(path, headers=_headers_for(etag))

    # Remote: the size is not known until the object is fetched, so the
    # validator is computed from the name alone. Names are single-use and
    # random, so this is still a strong validator.
    etag = _etag_for(subdir, filename)
    if _matches_etag(if_none_match, etag):
        return _not_modified(etag)

    found = storage.get(subdir, filename)
    if found is None:
        raise HTTPException(status_code=404, detail="File not found")
    data, content_type = found
    return Response(content=data, media_type=content_type, headers=_headers_for(etag))


def _matches_etag(if_none_match: str | None, etag: str) -> bool:
    """Per RFC 9110 §13.1.2: ``*`` matches anything, otherwise any member of
    the comma-separated list matches, and a ``W/`` prefix is ignored for this
    comparison."""
    if not if_none_match:
        return False
    candidates = [c.strip() for c in if_none_match.split(",")]
    if "*" in candidates:
        return True
    return any(c.removeprefix("W/") == etag for c in candidates)


@router.get("/proofs/{filename}")
def get_proof(
    filename: str,
    exp: int | None = Query(default=None),
    sig: str | None = Query(default=None),
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Serve a session proof if the caller is allowed AND the URL signature
    is fresh.

    Two checks must pass:
      1. HMAC signature on the URL is valid and unexpired.
      2. Caller is admin OR a participant on the session that owns the proof.

    Both run before the conditional-request shortcut: a 304 confirms the file
    exists, so it must not be reachable by anyone who could not fetch the body.
    """
    path_for_sig = f"/uploads/proofs/{filename}"
    if not verify_sig(path_for_sig, exp, sig):
        raise HTTPException(status_code=403, detail="Invalid or expired signature")

    if not _user_can_see_proof(db, current_user, path_for_sig):
        raise HTTPException(status_code=403, detail="Not authorized to view this proof")

    return _serve("proofs", filename, if_none_match)


@router.get("/homework/{filename}")
def get_homework(
    filename: str,
    exp: int | None = Query(default=None),
    sig: str | None = Query(default=None),
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
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

    return _serve("homework", filename, if_none_match)


@router.get("/shop/{filename}")
def get_shop_image(
    filename: str,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
):
    """Public product images.

    Only registered when object storage is in use — on local disk these are
    served by the StaticFiles mount in main.py, which is faster.
    """
    return _serve("shop", filename, if_none_match)

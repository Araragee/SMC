"""Where uploaded files physically live.

Two backends behind one small interface:

- **local disk** (default) — files under ``settings.UPLOADS_DIR``. What dev and
  a single-VM deployment with a mounted volume use.
- **Supabase Storage** — used when ``SUPABASE_URL``, ``SUPABASE_SERVICE_KEY``
  and ``SUPABASE_BUCKET`` are all set. Required on hosts with an ephemeral
  filesystem (Render's free tier, and anything running more than one replica),
  where local files disappear on the next deploy and 404 across instances.

The bucket is private. Nothing here hands out Supabase URLs: files are still
served through this app's auth-gated, HMAC-signed ``/uploads/*`` routes, so the
access rules do not change with the backend.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Uploads are small (10 MB cap, images recompressed to WebP), so a plain
# request with a generous timeout beats streaming machinery here.
_TIMEOUT = httpx.Timeout(30.0)


def is_remote() -> bool:
    """True when object storage is configured and should be used."""
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY and settings.SUPABASE_BUCKET)


def _object_url(key: str) -> str:
    base = settings.SUPABASE_URL.rstrip("/")
    return f"{base}/storage/v1/object/{settings.SUPABASE_BUCKET}/{key}"


def _headers() -> dict[str, str]:
    # The service key bypasses row-level security, which is why it must never
    # reach the browser — only this server talks to the bucket.
    return {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_KEY,
    }


def local_path(subdir: str, filename: str) -> Path:
    return Path(settings.UPLOADS_DIR) / subdir / filename


def put(subdir: str, filename: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Store ``data`` and return the storage key (``<subdir>/<filename>``)."""
    key = f"{subdir}/{filename}"

    if not is_remote():
        dest = local_path(subdir, filename)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return key

    response = httpx.post(
        _object_url(key),
        content=data,
        headers={**_headers(), "Content-Type": content_type, "x-upsert": "true"},
        timeout=_TIMEOUT,
    )
    if response.status_code >= 400:
        logger.error("Supabase Storage upload failed (%s): %s", response.status_code, response.text[:300])
        raise RuntimeError("Upload storage rejected the file")
    return key


def get(subdir: str, filename: str) -> tuple[bytes, str] | None:
    """Return ``(data, content_type)`` for a stored object, or None if missing."""
    if not is_remote():
        path = local_path(subdir, filename)
        if not path.is_file():
            return None
        return path.read_bytes(), _guess_type(filename)

    response = httpx.get(_object_url(f"{subdir}/{filename}"), headers=_headers(), timeout=_TIMEOUT)
    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        logger.error("Supabase Storage read failed (%s): %s", response.status_code, response.text[:300])
        return None
    return response.content, response.headers.get("content-type", _guess_type(filename))


_TYPES = {
    ".webp": "image/webp",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
}


def _guess_type(filename: str) -> str:
    return _TYPES.get(Path(filename).suffix.lower(), "application/octet-stream")

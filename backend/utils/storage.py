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

Two things make the remote path survive real networks:

- **One pooled client** rather than a fresh connection per call. Every proof
  thumbnail is a request; without pooling each one paid a full TLS handshake
  to the bucket before a byte moved.
- **A bounded retry.** A single dropped connection used to mean a permanently
  broken image in the UI, because nothing ever asked again. Retries cover only
  transport errors and 5xx — never a 404, and never a write that may have
  already landed in a way a repeat would corrupt (uploads are content-addressed
  by a random name and idempotent, so a repeated PUT is safe).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Uploads are small (10 MB cap, images recompressed to WebP), so a plain
# request with a generous timeout beats streaming machinery here. The connect
# timeout is deliberately much shorter than the read timeout: a bucket that is
# not answering at all should fail fast enough to retry inside the request.
_TIMEOUT = httpx.Timeout(30.0, connect=5.0)

# Sized for a single uvicorn worker serving a school. Keeping connections warm
# is the point; the ceiling just stops a burst of thumbnail requests from
# opening an unbounded number of sockets to the bucket.
_LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)

_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = (0.2, 0.6)  # one entry per retry after the first attempt

_client: httpx.Client | None = None


def is_remote() -> bool:
    """True when object storage is configured and should be used."""
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY and settings.SUPABASE_BUCKET)


def _get_client() -> httpx.Client:
    """The process-wide pooled client, created on first use.

    Built lazily rather than at import so that importing this module never
    opens sockets — the test suite and the Alembic env import it freely.
    """
    global _client
    if _client is None:
        _client = httpx.Client(timeout=_TIMEOUT, limits=_LIMITS)
    return _client


def close_client() -> None:
    """Release pooled connections. Called from the app's shutdown path."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


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


def _request_with_retry(method: str, url: str, **kwargs) -> httpx.Response:
    """Issue a request, retrying transport failures and 5xx responses.

    A 4xx is returned as-is: the caller distinguishes "missing" (404) from
    "misconfigured" (401/403), and repeating either would only add latency to a
    verdict that will not change.
    """
    client = _get_client()
    last_error: Exception | None = None

    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = client.request(method, url, **kwargs)
            if response.status_code < 500:
                return response
            last_error = None
            logger.warning(
                "Object storage %s returned %s (attempt %d/%d)",
                method, response.status_code, attempt + 1, _MAX_ATTEMPTS,
            )
            if attempt == _MAX_ATTEMPTS - 1:
                return response
        except httpx.HTTPError as err:
            last_error = err
            logger.warning(
                "Object storage %s failed (attempt %d/%d): %s",
                method, attempt + 1, _MAX_ATTEMPTS, err,
            )
            if attempt == _MAX_ATTEMPTS - 1:
                raise

        time.sleep(_BACKOFF_SECONDS[attempt])

    # Unreachable: the loop either returns or raises on its final attempt.
    raise last_error or RuntimeError("Object storage request failed")


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

    response = _request_with_retry(
        "POST",
        _object_url(key),
        content=data,
        headers={**_headers(), "Content-Type": content_type, "x-upsert": "true"},
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

    try:
        response = _request_with_retry("GET", _object_url(f"{subdir}/{filename}"), headers=_headers())
    except httpx.HTTPError:
        # Already logged per attempt. None reads as "not available", which the
        # route turns into a 404 — the client retries by reloading the image.
        return None
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

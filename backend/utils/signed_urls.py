"""HMAC-signed short-lived URLs for private uploads.

Why: ``/uploads/proofs/*`` and ``/uploads/homework/*`` contain personally
identifiable images (proofs of attendance, student homework). Until Phase 2
they were served via FastAPI's ``StaticFiles`` mount with no auth check —
anyone with a leaked URL could view any student's proof.

This module attaches an HMAC signature and expiry to every URL the API
emits for those files. The matching backend route handler (see
``routers/uploads.py``) rejects requests with missing / expired / forged
signatures with 403.

The signing key is derived from ``settings.SECRET_KEY`` so it rotates
with the rest of the app's signing material. Signatures use HMAC-SHA256
truncated to the first 32 hex chars — long enough that brute force is
infeasible and short enough that the URL stays readable.

URL shape::

    /uploads/proofs/abc123.png?exp=1717948800&sig=deadbeef...

``exp`` is a Unix UTC timestamp (seconds). After it, the route returns 403.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

from ..config import settings

# 1 hour: long enough for a user to keep the session-detail modal open and
# inspect proofs without re-fetching, short enough that a leaked URL stops
# being useful within a day. Configurable if a real use case shows up.
DEFAULT_TTL_SECONDS = 3600

# Truncating HMAC to 32 hex chars (~128 bits) keeps the URL short while
# still being well above the brute-force threshold for a short-lived token.
_SIG_LEN = 32


def _signing_key() -> bytes:
    """Derive an HMAC key from the app secret. Tagged with a context label
    so this signer can't be confused with JWT / refresh-token signers if
    those ever share a key path."""
    return hashlib.sha256(
        b"smc-signed-url-v1::" + settings.SECRET_KEY.encode("utf-8")
    ).digest()


def _compute_sig(path: str, exp: int) -> str:
    """Sign the *path + exp* pair. The path is included so a signature
    for ``/uploads/proofs/A.png`` cannot be replayed against
    ``/uploads/proofs/B.png`` simply by editing the URL."""
    msg = f"{path}|{exp}".encode("utf-8")
    return hmac.new(_signing_key(), msg, hashlib.sha256).hexdigest()[:_SIG_LEN]


def sign_url(path: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Return ``path`` with ``?exp=...&sig=...`` appended.

    ``path`` should be the URL path portion only (e.g.
    ``/uploads/proofs/abc.png``). The function does not add a host; callers
    that need an absolute URL must prefix it themselves.

    If ``path`` already has a query string we extend it; otherwise we add one.
    """
    exp = int(time.time()) + ttl_seconds
    sig = _compute_sig(path, exp)
    qs = urlencode({"exp": exp, "sig": sig})
    sep = "&" if "?" in path else "?"
    return f"{path}{sep}{qs}"


def verify_sig(path: str, exp: str | int | None, sig: str | None) -> bool:
    """Verify the signature on ``path``. Returns False on any error
    (missing params, expired, bad signature). Use ``hmac.compare_digest``
    to avoid timing leaks."""
    if not exp or not sig:
        return False
    try:
        exp_int = int(exp)
    except (TypeError, ValueError):
        return False
    if exp_int < int(time.time()):
        return False
    expected = _compute_sig(path, exp_int)
    return hmac.compare_digest(expected, str(sig))

"""Password-strength validation for user-chosen credentials.

Why: until now the only constraint on a new password was the 72-byte bcrypt
ceiling (see ``routers/auth.py`` / ``routers/users.py``). A user could set a
one-character password on ``/auth/change-password`` or ``/auth/reset-password``
and the API would happily hash and store it. This module adds a single,
testable place that defines what counts as an acceptable password.

The policy is deliberately **NIST-aligned** (SP 800-63B): favour length and a
block-list of obviously-weak secrets over rigid composition rules. We do *not*
force "1 upper + 1 digit + 1 symbol", because that rejects strong passphrases
(``correct horse battery staple``) while still admitting weak-but-compliant
ones (``Password1!``). Instead we require a sensible minimum length, reject
single-character repetition, and block a small set of notorious passwords.

Two entry points:

* :func:`validate_password_strength` — pure; returns a list of human-readable
  failure reasons (empty list ⇒ the password is acceptable). Easy to unit test.
* :func:`enforce_password_strength` — thin wrapper that raises
  ``HTTPException(400)`` with the joined reasons, for use inside route handlers.
"""
from __future__ import annotations

from fastapi import HTTPException

from ..config import settings

# bcrypt silently truncates anything past 72 *bytes*; a longer password would
# have an unverified tail, so we reject it outright rather than store a value
# whose suffix never matters. Mirrors the inline checks already in the routers.
MAX_PASSWORD_BYTES = 72

# Small block-list of secrets that show up at the top of every breach corpus.
# Compared case-insensitively. Kept short on purpose — this is a guardrail
# against the laziest choices, not a substitute for a breached-password service.
COMMON_WEAK_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "password123",
        "12345678",
        "123456789",
        "1234567890",
        "qwerty",
        "qwertyuiop",
        "letmein",
        "iloveyou",
        "admin",
        "welcome",
        "changeme",
        "passw0rd",
        "abc12345",
    }
)


def validate_password_strength(
    password: str, min_length: int | None = None
) -> list[str]:
    """Return a list of reasons ``password`` is unacceptable (empty ⇒ OK).

    ``min_length`` defaults to ``settings.PASSWORD_MIN_LENGTH``. Returning the
    reasons (rather than raising) keeps this function pure and lets callers
    decide how to surface them; see :func:`enforce_password_strength`.
    """
    if min_length is None:
        min_length = settings.PASSWORD_MIN_LENGTH

    reasons: list[str] = []

    # Empty / whitespace-only. Checked first so the messages below stay relevant.
    if not password or not password.strip():
        reasons.append("Password must not be empty.")
        return reasons

    if len(password) < min_length:
        reasons.append(f"Password must be at least {min_length} characters long.")

    # Measured in bytes because that is what bcrypt truncates on.
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        reasons.append(f"Password must be at most {MAX_PASSWORD_BYTES} bytes long.")

    # "aaaaaaaa" / "00000000" clear a length check but carry almost no entropy.
    if len(set(password)) == 1:
        reasons.append("Password must not be a single repeated character.")

    if password.lower() in COMMON_WEAK_PASSWORDS:
        reasons.append("Password is too common; choose something less guessable.")

    return reasons


def enforce_password_strength(
    password: str, min_length: int | None = None
) -> None:
    """Raise ``HTTPException(400)`` if ``password`` fails the policy.

    Convenience wrapper for route handlers: the joined reasons become the
    error ``detail`` so the client can show every problem at once.
    """
    reasons = validate_password_strength(password, min_length=min_length)
    if reasons:
        raise HTTPException(status_code=400, detail=" ".join(reasons))

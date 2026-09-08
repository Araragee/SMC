"""Credentials the system issues to itself.

Passwords a user chooses are covered by ``test_passwords.py``. This covers the
ones nobody chooses: the temporary password an admin-created account starts
with. That used to be ``{firstname}{age}SMC`` for students and the literal
``password123`` for everyone else — the first derivable from the student's own
profile page, the second on this app's own weak-password blocklist. The system
was minting credentials it would have refused from a user.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from backend.routers.users import _generate_temp_password  # noqa: E402
from backend.utils.passwords import (  # noqa: E402
    MAX_PASSWORD_BYTES,
    validate_password_strength,
)


def test_a_generated_password_passes_the_policy_it_would_be_judged_by():
    """The old defaults did not — ``password123`` is on the blocklist the same
    app applies at change-password time."""
    for _ in range(50):
        assert validate_password_strength(_generate_temp_password()) == []


def test_generated_passwords_are_unique():
    """Derived defaults collided by construction: two students with the same
    first name and age shared a password."""
    generated = {_generate_temp_password() for _ in range(500)}
    assert len(generated) == 500


def test_a_generated_password_fits_bcrypt_without_truncation():
    """Anything past 72 bytes is silently dropped by bcrypt, which would make
    the tail of the password decorative."""
    assert len(_generate_temp_password().encode()) <= MAX_PASSWORD_BYTES


def test_a_generated_password_is_url_safe_and_transcribable():
    """It is read off a screen and typed in by hand once, so it must survive
    being copied out of a chat message or written on a slip of paper."""
    password = _generate_temp_password()
    assert password.isascii()
    assert not any(c.isspace() for c in password)
    assert all(c.isalnum() or c in "-_" for c in password)


def test_a_generated_password_carries_real_entropy():
    """token_urlsafe(12) is 96 bits over a 64-character alphabet: 16 chars."""
    assert len(_generate_temp_password()) >= 16


@pytest.mark.parametrize("name,age", [("Maria", 12), ("jose", 9), ("Ana", None)])
def test_a_generated_password_is_not_derivable_from_the_profile(name, age):
    """The specific old formula, asserted dead: knowing a student's first name
    and age must no longer be enough to know their password."""
    old_formula = f"{name.split(' ')[0].lower()}{age if age else ''}SMC"
    assert _generate_temp_password() != old_formula
    assert name.lower() not in _generate_temp_password().lower()

"""Tests for the password-strength policy (``backend.utils.passwords``).

Locks in the contract used by ``/auth/change-password`` and
``/auth/reset-password``: a sensible length floor, a 72-byte ceiling (bcrypt),
rejection of single-character repetition and notorious weak passwords, and the
``enforce_*`` wrapper's 400 behaviour. The policy is intentionally length-first
(NIST SP 800-63B), so strong passphrases must pass.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi import HTTPException  # noqa: E402

from backend.utils.passwords import (  # noqa: E402
    MAX_PASSWORD_BYTES,
    enforce_password_strength,
    validate_password_strength,
)


# ── validate_password_strength: accepts ───────────────────────────────────────

def test_strong_password_has_no_reasons():
    assert validate_password_strength("Tr0mbone!Slide") == []


def test_long_passphrase_passes_without_composition_rules():
    # All-lowercase + spaces: only one "character class" but plenty of length.
    assert validate_password_strength("correct horse battery staple") == []


def test_exactly_minimum_length_is_accepted():
    assert validate_password_strength("abcdefgh", min_length=8) == []


# ── validate_password_strength: rejects ───────────────────────────────────────

def test_empty_password_rejected():
    assert validate_password_strength("") != []


def test_whitespace_only_rejected():
    reasons = validate_password_strength("        ")
    assert any("empty" in r.lower() for r in reasons)


def test_too_short_rejected_with_helpful_reason():
    reasons = validate_password_strength("ab12", min_length=8)
    assert any("at least 8" in r for r in reasons)


def test_single_repeated_character_rejected_even_if_long():
    reasons = validate_password_strength("aaaaaaaaaaaa")
    assert any("repeated character" in r for r in reasons)


def test_common_password_rejected_case_insensitively():
    for candidate in ("password", "PASSWORD123", "QwErTy", "letmein"):
        reasons = validate_password_strength(candidate)
        assert any("too common" in r for r in reasons), candidate


def test_over_72_bytes_rejected():
    # Varied chars (not a single repeat) so the byte-ceiling rule is isolated.
    varied = "".join(chr(33 + (i % 90)) for i in range(MAX_PASSWORD_BYTES + 1))
    reasons = validate_password_strength(varied)
    assert any("at most" in r and "bytes" in r for r in reasons)


def test_multibyte_chars_count_as_bytes_not_codepoints():
    # 'é' is 2 bytes in UTF-8; 40 of them = 80 bytes > 72 even though len()==40.
    pwd = "é" * 40
    assert len(pwd) == 40
    reasons = validate_password_strength(pwd)
    assert any("bytes" in r for r in reasons)


def test_custom_min_length_is_respected():
    assert validate_password_strength("abcdefghij", min_length=12) != []
    assert validate_password_strength("abcdefghijkl", min_length=12) == []


# ── enforce_password_strength wrapper ─────────────────────────────────────────

def test_enforce_raises_400_on_weak_password():
    with pytest.raises(HTTPException) as exc:
        enforce_password_strength("short")
    assert exc.value.status_code == 400
    assert exc.value.detail  # a human-readable reason is attached


def test_enforce_is_silent_on_strong_password():
    # Should simply return None without raising.
    assert enforce_password_strength("Tr0mbone!Slide") is None


def test_enforce_joins_multiple_reasons():
    # "a" is both too short and a single repeated character ⇒ two reasons joined.
    with pytest.raises(HTTPException) as exc:
        enforce_password_strength("a")
    assert "at least" in exc.value.detail
    assert "repeated character" in exc.value.detail

"""Tests for HMAC-signed private-upload URLs (``backend.utils.signed_urls``).

These guard the access-control contract for ``/uploads/proofs/*`` and
``/uploads/homework/*``: a signature is bound to *both* the path and an
expiry, must be rejected when tampered, expired, or missing, and must be
verified in constant time.
"""
from __future__ import annotations

import time
from urllib.parse import parse_qs, urlparse

from backend.utils.signed_urls import (
    DEFAULT_TTL_SECONDS,
    _SIG_LEN,
    _compute_sig,
    sign_url,
    verify_sig,
)

PROOF = "/uploads/proofs/abc123.png"


def _split(signed: str) -> tuple[str, str, str]:
    """Return (path, exp, sig) parsed out of a signed URL."""
    parsed = urlparse(signed)
    qs = parse_qs(parsed.query)
    return parsed.path, qs["exp"][0], qs["sig"][0]


def test_sign_url_appends_exp_and_sig():
    signed = sign_url(PROOF)
    path, exp, sig = _split(signed)
    assert path == PROOF
    assert exp.isdigit()
    assert len(sig) == _SIG_LEN


def test_round_trip_verifies():
    path, exp, sig = _split(sign_url(PROOF))
    assert verify_sig(path, exp, sig) is True


def test_path_binding_rejects_replay_on_other_file():
    # A signature minted for one proof must not validate another path.
    _, exp, sig = _split(sign_url(PROOF))
    assert verify_sig("/uploads/proofs/other.png", exp, sig) is False


def test_tampered_signature_rejected():
    path, exp, sig = _split(sign_url(PROOF))
    forged = ("0" * _SIG_LEN) if sig != "0" * _SIG_LEN else ("1" * _SIG_LEN)
    assert verify_sig(path, exp, forged) is False


def test_expired_signature_rejected():
    # TTL of -1s ⇒ exp is already in the past at verification time.
    path, exp, sig = _split(sign_url(PROOF, ttl_seconds=-1))
    assert verify_sig(path, exp, sig) is False


def test_missing_params_rejected():
    assert verify_sig(PROOF, None, "deadbeef") is False
    assert verify_sig(PROOF, "123", None) is False
    assert verify_sig(PROOF, "", "") is False


def test_non_integer_exp_rejected():
    path, _, sig = _split(sign_url(PROOF))
    assert verify_sig(path, "not-a-number", sig) is False


def test_tampered_exp_rejected():
    # Extending the expiry without re-signing must fail (exp is signed too).
    path, exp, sig = _split(sign_url(PROOF))
    assert verify_sig(path, str(int(exp) + 10_000), sig) is False


def test_default_ttl_is_roughly_one_hour():
    before = int(time.time())
    _, exp, _ = _split(sign_url(PROOF))
    delta = int(exp) - before
    # Allow a couple of seconds of slack for slow CI.
    assert DEFAULT_TTL_SECONDS - 2 <= delta <= DEFAULT_TTL_SECONDS + 2


def test_existing_query_string_is_extended_not_clobbered():
    signed = sign_url("/uploads/proofs/x.png?v=2")
    assert "v=2" in signed
    assert "exp=" in signed and "sig=" in signed


def test_compute_sig_is_deterministic_and_truncated():
    a = _compute_sig(PROOF, 1_717_000_000)
    b = _compute_sig(PROOF, 1_717_000_000)
    assert a == b
    assert len(a) == _SIG_LEN


def test_distinct_paths_produce_distinct_signatures():
    exp = 1_717_000_000
    assert _compute_sig("/uploads/proofs/a.png", exp) != _compute_sig(
        "/uploads/proofs/b.png", exp
    )

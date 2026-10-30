"""A password reset must not accept the password already on the account.

``change-password`` has always refused a no-op change. ``reset-password`` is
the flow people reach *because* a credential is suspect — forgotten, shared,
or possibly stolen — so quietly re-setting that same credential is the worst
place to allow it. There is no plaintext old password in this flow, but the
stored hash answers the question.

The guard exists; these tests are here so it cannot quietly disappear.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from backend import models, schemas  # noqa: E402
from backend.dependencies import pwd_context  # noqa: E402
from backend.routers.auth import _hash_token, _naive, _utcnow, reset_password  # noqa: E402

# The handler carries a slowapi rate-limit decorator that wants a real
# Request. The limiter is not what is under test, so call the function it
# wrapped and leave `request` unused.
_reset = reset_password.__wrapped__

CURRENT = "the-current-passphrase-9134"
REPLACEMENT = "a-genuinely-different-one-7725"


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    models.Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _user_with_reset_token(db, *, password: str | None = CURRENT, raw_token="tok-abc"):
    user = models.User(
        name="Student", username="student", email="s@smc.com",
        hashed_password=pwd_context.hash(password) if password else None,
        must_change_password=True,
    )
    db.add(user)
    db.flush()

    prt = models.PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=_naive(_utcnow() + timedelta(hours=1)),
    )
    db.add(prt)
    db.commit()
    return user, prt, raw_token


def test_resetting_to_the_current_password_is_rejected(db):
    user, prt, raw = _user_with_reset_token(db)

    with pytest.raises(HTTPException) as exc:
        _reset(None, schemas.ResetPasswordRequest(token=raw, new_password=CURRENT), db=db)

    assert exc.value.status_code == 400
    assert "different" in str(exc.value.detail).lower()
    # The token must survive a rejected attempt, or one slip would burn it and
    # strand the user with no way to finish the reset.
    db.refresh(prt)
    assert prt.used_at is None


def test_a_genuinely_new_password_is_accepted(db):
    user, prt, raw = _user_with_reset_token(db)

    _reset(None, schemas.ResetPasswordRequest(token=raw, new_password=REPLACEMENT), db=db)

    db.refresh(user)
    db.refresh(prt)
    assert pwd_context.verify(REPLACEMENT, user.hashed_password)
    assert prt.used_at is not None, "the reset token must be consumed"
    assert user.must_change_password is False


def test_an_unusable_stored_hash_does_not_block_the_reset(db):
    """The fallback that matters: a malformed or missing hash cannot answer
    "is this the same password?", and refusing there would lock the user out
    of the one flow that would replace the unusable hash."""
    user, prt, raw = _user_with_reset_token(db, password=None)
    user.hashed_password = "not-a-bcrypt-hash"
    db.commit()

    _reset(None, schemas.ResetPasswordRequest(token=raw, new_password=REPLACEMENT), db=db)

    db.refresh(user)
    assert pwd_context.verify(REPLACEMENT, user.hashed_password)

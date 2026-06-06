import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import models

# Load .env from the backend directory
from .config import settings
from .database import SessionLocal
from .routers import activity, auth, messaging, notifications, payments, push, sessions, shop, users
from .routers.sessions import session_checker_task

# Rate limiter shared with routers (e.g. login endpoint).
limiter = Limiter(key_func=get_remote_address)

# NOTE: Table creation is managed by Alembic migrations.
# Run `alembic upgrade head` before starting the app.
# Do NOT call models.Base.metadata.create_all() here — it bypasses Alembic versioning.


def _seed_defaults() -> None:
    """Seed required roles, instruments, and a default admin on first boot."""
    db = SessionLocal()
    try:
        for role_name in ["admin", "teacher", "student"]:
            if not db.query(models.Role).filter(models.Role.name == role_name).first():
                db.add(models.Role(name=role_name))
        db.commit()

        for instrument_name in ["Guitar", "Bass", "Voice", "Drum", "Flute", "Violin", "Keyboard", "Ukulele"]:
            if not db.query(models.Instrument).filter(models.Instrument.name == instrument_name).first():
                db.add(models.Instrument(name=instrument_name))
        db.commit()

        admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
        admin_user = db.query(models.User).filter(
            (models.User.email == settings.DEFAULT_ADMIN_EMAIL) |
            (models.User.username == settings.DEFAULT_ADMIN_USERNAME)
        ).first()
        if not admin_user and admin_role:
            from .dependencies import pwd_context
            hashed_password = pwd_context.hash(settings.DEFAULT_ADMIN_PASSWORD)
            db.add(models.User(
                email=settings.DEFAULT_ADMIN_EMAIL,
                username=settings.DEFAULT_ADMIN_USERNAME,
                name="System Admin",
                hashed_password=hashed_password,
                role_id=admin_role.id,
                is_active=True,
            ))
            db.commit()
            print(f"Default admin user created: {settings.DEFAULT_ADMIN_USERNAME} / [see DEFAULT_ADMIN_PASSWORD in .env]")
        elif admin_user and not admin_user.username:
            admin_user.username = settings.DEFAULT_ADMIN_USERNAME
            db.commit()
    finally:
        db.close()


def _purge_stale_tokens() -> None:
    """Delete expired and revoked auth tokens to prevent unbounded table growth."""
    import datetime
    from datetime import timezone
    db = SessionLocal()
    try:
        now = datetime.datetime.now(timezone.utc)
        deleted_refresh = (
            db.query(models.RefreshToken)
            .filter(
                (models.RefreshToken.revoked == True)
                | (models.RefreshToken.expires_at < now)
            )
            .delete(synchronize_session=False)
        )
        deleted_reset = (
            db.query(models.PasswordResetToken)
            .filter(models.PasswordResetToken.expires_at < now)
            .delete(synchronize_session=False)
        )
        db.commit()
        if deleted_refresh or deleted_reset:
            print(f"Token purge: removed {deleted_refresh} refresh token(s), {deleted_reset} reset token(s).")
        else:
            print("Token purge completed: nothing to remove.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: seed DB on startup, clean up on shutdown."""
    _seed_defaults()
    _purge_stale_tokens()
    checker = asyncio.create_task(session_checker_task())
    yield
    checker.cancel()
    try:
        await checker
    except asyncio.CancelledError:
        pass

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Include routers
app.include_router(users.router)
app.include_router(sessions.router)
app.include_router(notifications.router)
app.include_router(messaging.router)
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(shop.router, prefix="/shop", tags=["shop"])
app.include_router(activity.router, prefix="/activity-log", tags=["activity"])
app.include_router(auth.router)
app.include_router(push.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Music School API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

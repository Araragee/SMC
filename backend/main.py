from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import os
import pathlib
import asyncio

# Load .env from the backend directory
from .config import settings

from . import models, schemas
from .database import engine, SessionLocal
from .routers import users, sessions, notifications, messaging, payments, shop, activity
from .routers.sessions import session_checker_task

# NOTE: Table creation is managed by Alembic migrations.
# Run `alembic upgrade head` before starting the app.
# Do NOT call models.Base.metadata.create_all() here — it bypasses Alembic versioning.

app = FastAPI(title=settings.PROJECT_NAME)

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        # Create default roles if they don't exist
        for role_name in ["admin", "teacher", "student"]:
            role = db.query(models.Role).filter(models.Role.name == role_name).first()
            if not role:
                db.add(models.Role(name=role_name))
        db.commit()

        # Seed instruments
        for instrument_name in ["Guitar", "Bass", "Voice", "Drum", "Flute", "Violin", "Keyboard", "Ukulele"]:
            instrument = db.query(models.Instrument).filter(models.Instrument.name == instrument_name).first()
            if not instrument:
                new_instrument = models.Instrument(name=instrument_name)
                db.add(new_instrument)
        db.commit()

        # Create default admin if none exists
        admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
        admin_user = db.query(models.User).filter(
            (models.User.email == settings.DEFAULT_ADMIN_EMAIL) |
            (models.User.username == settings.DEFAULT_ADMIN_USERNAME)
        ).first()
        if not admin_user and admin_role:
            from .dependencies import pwd_context
            hashed_password = pwd_context.hash(settings.DEFAULT_ADMIN_PASSWORD)
            new_admin = models.User(
                email=settings.DEFAULT_ADMIN_EMAIL,
                username=settings.DEFAULT_ADMIN_USERNAME,
                name="System Admin",
                hashed_password=hashed_password,
                role_id=admin_role.id,
                is_active=True
            )
            db.add(new_admin)
            db.commit()
            print(f"Default admin user created: {settings.DEFAULT_ADMIN_USERNAME} / [see DEFAULT_ADMIN_PASSWORD in .env]")
        elif admin_user and not admin_user.username:
            admin_user.username = "admin"
            db.commit()
    finally:
        db.close()

    # Start the background task
    asyncio.create_task(session_checker_task())

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router)
app.include_router(sessions.router)
app.include_router(notifications.router)
app.include_router(messaging.router)
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(shop.router, prefix="/shop", tags=["shop"])
app.include_router(activity.router, prefix="/activity-log", tags=["activity"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Music School API"}

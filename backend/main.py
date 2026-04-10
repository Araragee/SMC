from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import os
import pathlib
import asyncio

# Load .env from the backend directory
load_dotenv_path = pathlib.Path(__file__).parent / ".env"
from dotenv import load_dotenv
load_dotenv(load_dotenv_path)

from . import models, schemas
from .database import engine, SessionLocal
from .routers import users, sessions, notifications, messaging, payments
from .routers.sessions import session_checker_task

# Ensure Base metadata creates all tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Music School API")

@app.on_event("startup")
def startup_event():
    db = SessionLocal()

    # Run SQLite migration: Add new columns if they don't exist
    columns = [
        ("users", "username", "VARCHAR"),
        ("users", "contact_number", "VARCHAR"),
        ("users", "home_address", "VARCHAR"),
        ("users", "birthday", "VARCHAR"),
        ("users", "age", "INTEGER"),
        ("users", "school", "VARCHAR"),
        ("users", "parent_name", "VARCHAR"),
        ("users", "parent_contact", "VARCHAR"),
        ("users", "sessions_enrolled", "INTEGER"),
        ("sessions", "instrument_id", "INTEGER REFERENCES instruments(id)"),
        ("sessions", "is_manual_entry", "BOOLEAN DEFAULT 0"),
        ("sessions", "session_number", "INTEGER"),
        ("sessions", "notified_24h", "BOOLEAN DEFAULT 0"),
        ("sessions", "notified_12h", "BOOLEAN DEFAULT 0"),
        ("sessions", "proof_justification", "VARCHAR"),
        ("sessions", "rejection_reason", "VARCHAR"),
        ("sessions", "is_force_completed", "BOOLEAN DEFAULT 0"),
        ("homework", "file_url", "VARCHAR"),
        ("session_proofs", "uploader_id", "INTEGER REFERENCES users(id)"),
        ("session_proofs", "uploader_role", "VARCHAR")
    ]
    
    for table, col, col_type in columns:
        try:
            db.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
            db.commit()
        except Exception:
            db.rollback() # Ignore errors if columns already exist

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
        admin_user = db.query(models.User).filter((models.User.email == "admin@smc.edu") | (models.User.username == "admin")).first()
        if not admin_user and admin_role:
            # We need to import pwd_context here for the initial admin
            from .dependencies import pwd_context
            hashed_password = pwd_context.hash("password123")
            new_admin = models.User(
                email="admin@smc.edu",
                username="admin",
                name="System Admin",
                hashed_password=hashed_password,
                role_id=admin_role.id,
                is_active=True
            )
            db.add(new_admin)
            db.commit()
            print("Default admin user created: admin / password123")
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
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
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

@app.get("/")
def read_root():
    return {"message": "Welcome to the Music School API"}

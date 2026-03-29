from fastapi import Depends, FastAPI, HTTPException, status, UploadFile, File, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import os
import passlib.hash
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pathlib
import json
from typing import Dict, List as TList
import asyncio

# Load .env from the backend directory
load_dotenv(pathlib.Path(__file__).parent / ".env")

from . import models, schemas
from .database import engine, get_db, SessionLocal

pwd_context = passlib.hash.bcrypt

SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-key-change-me")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
    user = db.query(models.User).filter(
        (models.User.username == username) | (models.User.email == username)
    ).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_admin(current_user: models.User = Depends(get_current_active_user)):
    if current_user.role is None or current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires admin role")
    return current_user

def require_teacher(current_user: models.User = Depends(get_current_active_user)):
    if current_user.role is None or current_user.role.name.lower() not in ["teacher", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires teacher or admin role")
    return current_user

def require_student(current_user: models.User = Depends(get_current_active_user)):
    if current_user.role is None or current_user.role.name.lower() != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires student role")
    return current_user

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
        admin_user = db.query(models.User).filter(models.User.email == "admin@example.com").first()
        if not admin_user and admin_role:
            hashed_password = pwd_context.hash("password123")
            new_admin = models.User(
                email="admin@example.com",
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

# --- Helpers ---

def format_dt(dt: datetime) -> str:
    return dt.strftime("%b %d at %I:%M %p") if dt else "Unknown"

def notify_users(db, user_ids: list, message: str):
    """Create notifications for a list of user IDs."""
    for uid in user_ids:
        if uid:
            db.add(models.Notification(user_id=uid, message=message, is_read=False))
    db.commit()

def get_admin_ids(db) -> list:
    """Return all admin user IDs."""
    admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
    if not admin_role:
        return []
    admins = db.query(models.User).filter(models.User.role_id == admin_role.id).all()
    return [a.id for a in admins]

def map_session(db_session: models.Session) -> dict:
    session_dict = schemas.Session.model_validate(db_session).model_dump()
    session_dict['proof_image_url'] = db_session.proofs[0].image_url if db_session.proofs else None
    session_dict['homework_assigned'] = db_session.homeworks[0].description if db_session.homeworks else None
    session_dict['homework_completed'] = db_session.homeworks[0].is_completed if db_session.homeworks else False
    return session_dict

async def session_checker_task():
    while True:
        try:
            db = SessionLocal()
            now = datetime.utcnow()
            
            # Check for 24h notifications
            target_24h = now + timedelta(hours=24)
            sessions_24h = db.query(models.Session).filter(
                models.Session.status == "scheduled",
                models.Session.start_time <= target_24h,
                models.Session.start_time > now,
                models.Session.notified_24h == False
            ).all()
            for s in sessions_24h:
                dt_str = format_dt(s.start_time)
                notify_users(db, [s.teacher_id, s.student_id], f"Reminder: Session scheduled in ~24h on {dt_str}.")
                s.notified_24h = True
            
            # Check for 12h notifications
            target_12h = now + timedelta(hours=12)
            sessions_12h = db.query(models.Session).filter(
                models.Session.status == "scheduled",
                models.Session.start_time <= target_12h,
                models.Session.start_time > now,
                models.Session.notified_12h == False
            ).all()
            for s in sessions_12h:
                dt_str = format_dt(s.start_time)
                notify_users(db, [s.teacher_id, s.student_id], f"Reminder: Session schedule nearing! ~12h left for {dt_str}.")
                s.notified_12h = True
                
            # Check for overdue sessions (end_time in the past)
            overdue_sessions = db.query(models.Session).filter(
                models.Session.status == "scheduled",
                models.Session.end_time < now
            ).all()
            for s in overdue_sessions:
                dt_str = format_dt(s.start_time)
                s.status = "overdue"
                notify_users(db, [s.teacher_id, s.student_id], f"Action Required: Session from {dt_str} is overdue. Please upload proofs or mark complete.")
                
            db.commit()
            db.close()
        except Exception as e:
            print(f"Error in background task: {e}")
        await asyncio.sleep(60)

# --- Root ---

@app.get("/")
def read_root():
    return {"message": "Welcome to the Music School API"}

@app.get("/debug/users")
def debug_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return [{"email": u.email, "role": u.role.name if u.role else None} for u in users]

# --- Auth ---
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Try searching by username first, then fallback to email (for transition)
    user = db.query(models.User).filter(
        (models.User.username == form_data.username) | 
        (models.User.email == form_data.username)
    ).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    is_valid_hash = False
    try:
        is_valid_hash = pwd_context.verify(form_data.password[:72], user.hashed_password)
    except Exception:
        pass

    if not is_valid_hash and user.hashed_password != (form_data.password + "notreallyhashed"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username or user.email, "user_id": user.id}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer", "user": schemas.User.model_validate(user)}

# --- Users ---

@app.post("/users/")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user_email = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    role = db.query(models.Role).filter(models.Role.id == user.role_id).first()

    # Generate default username if not provided
    username = user.username
    if not username:
        # Use first part of email or name as base
        base = user.email.split("@")[0] if user.email else user.name.replace(" ", "").lower()
        # Verify uniqueness
        username = base
        counter = 1
        while db.query(models.User).filter(models.User.username == username).first():
            username = f"{base}{counter}"
            counter += 1

    password = user.password
    if not password and role and role.name.lower() == "student":
        first_name = user.name.split(" ")[0].lower()
        age_str = str(user.age) if user.age else ""
        password = f"{first_name}{age_str}SMC"
    elif not password:
        password = "password123" # Fallback

    hashed_password = pwd_context.hash(password[:72])

    user_data = user.dict(exclude={"password", "instrument_ids", "username"})
    user_data["hashed_password"] = hashed_password
    user_data["username"] = username

    db_user = models.User(**user_data)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    if user.instrument_ids:
        for instrument_id in user.instrument_ids:
            db_user_instrument = models.UserInstrument(user_id=db_user.id, instrument_id=instrument_id)
            db.add(db_user_instrument)
        db.commit()
        db.refresh(db_user)

    # Automatically generate token for the response to allow "automatic login"
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.username, "user_id": db_user.id}, 
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": schemas.User.model_validate(db_user)
    }

@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    # Authorization: User can update themselves, or Admin can update anyone
    if current_user.id != user_id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update this user")

    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = pwd_context.hash(update_data.pop("password")[:72])

    instrument_ids = update_data.pop("instrument_ids", None)

    for key, value in update_data.items():
        setattr(db_user, key, value)

    if instrument_ids is not None:
        db.query(models.UserInstrument).filter(models.UserInstrument.user_id == user_id).delete()
        for instrument_id in instrument_ids:
            db.add(models.UserInstrument(user_id=user_id, instrument_id=instrument_id))

    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}

@app.get("/users/role/{role_name}", response_model=list[schemas.User])
def read_users_by_role(role_name: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    users = db.query(models.User).filter(models.User.role_id == role.id).offset(skip).limit(limit).all()
    return users

@app.get("/users/", response_model=list[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

# --- Instruments ---

@app.get("/instruments/", response_model=list[schemas.Instrument])
def get_instruments(db: Session = Depends(get_db)):
    instruments = db.query(models.Instrument).all()
    return instruments

# --- Teacher-Students ---

@app.post("/teacher-students/", response_model=schemas.TeacherStudent)
def assign_teacher_student(assignment: schemas.TeacherStudentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    existing = db.query(models.TeacherStudent).filter(
        models.TeacherStudent.teacher_id == assignment.teacher_id,
        models.TeacherStudent.student_id == assignment.student_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Student is already assigned to this teacher")

    new_assignment = models.TeacherStudent(
        teacher_id=assignment.teacher_id,
        student_id=assignment.student_id
    )
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    return new_assignment

@app.get("/teacher-students/teacher/{teacher_id}", response_model=list[schemas.TeacherStudent])
def get_students_for_teacher(teacher_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    assignments = db.query(models.TeacherStudent).filter(models.TeacherStudent.teacher_id == teacher_id).all()
    return assignments

@app.delete("/teacher-students/{assignment_id}")
def unassign_teacher_student(assignment_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    assignment = db.query(models.TeacherStudent).filter(models.TeacherStudent.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()
    return {"message": "Assignment deleted successfully"}


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# --- Sessions (Admin direct) ---

@app.post("/sessions/record", response_model=schemas.Session)
def record_past_session(session: schemas.SessionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Admin creates a manual past session directly."""
    student = db.query(models.User).filter(models.User.id == session.student_id).first()
    teacher = db.query(models.User).filter(models.User.id == session.teacher_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    db_session = models.Session(
        teacher_id=session.teacher_id,
        student_id=session.student_id,
        start_time=session.start_time,
        end_time=session.end_time,
        status="completed", # Typically past records are marked completed
        notes=session.notes,
        proposed_by=current_user.id,
        is_manual_entry=True,
        instrument_id=session.instrument_id,
        session_number=session.session_number
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    return db_session


@app.get("/sessions/student/{student_id}/records", response_model=list[schemas.Session])
def get_student_records(student_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    # Authorization logic
    if current_user.role.name.lower() == "student" and current_user.id != student_id:
         raise HTTPException(status_code=403, detail="Not authorized")

    sessions = db.query(models.Session).filter(models.Session.student_id == student_id).order_by(models.Session.start_time.desc()).all()
    return sessions

@app.post("/sessions/", response_model=schemas.Session)
def create_session(session: schemas.SessionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Admin creates a session directly — immediately scheduled."""
    student = db.query(models.User).filter(models.User.id == session.student_id).first()
    teacher = db.query(models.User).filter(models.User.id == session.teacher_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    db_session = models.Session(
        teacher_id=session.teacher_id,
        student_id=session.student_id,
        start_time=session.start_time,
        end_time=session.end_time,
        status="scheduled",
        proposed_by=current_user.id,
        notes=session.notes
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    notify_users(db, [db_session.teacher_id], f"📅 Admin has scheduled a session with {student.name} on {dt_str}.")
    notify_users(db, [db_session.student_id], f"✅ A session has been scheduled for you on {dt_str} with {teacher.name}.")

    return map_session(db_session)

@app.get("/sessions/pending", response_model=list[schemas.Session])
def read_pending_sessions(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Admin: get all sessions awaiting approval."""
    sessions = db.query(models.Session).filter(
        models.Session.status.in_(["pending_teacher", "pending_admin"])
    ).all()
    return [map_session(s) for s in sessions]

@app.get("/sessions/", response_model=list[schemas.Session])
def read_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    sessions = db.query(models.Session).offset(skip).limit(limit).all()
    return [map_session(s) for s in sessions]

@app.get("/sessions/user/{user_id}", response_model=list[schemas.Session])
def read_user_sessions(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    sessions = db.query(models.Session).filter(
        (models.Session.teacher_id == user_id) | (models.Session.student_id == user_id)
    ).offset(skip).limit(limit).all()
    return [map_session(s) for s in sessions]

@app.put("/sessions/{session_id}", response_model=schemas.Session)
def update_session(session_id: int, session: schemas.SessionEdit, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Admin edits a session."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    update_data = session.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_session, key, value)

    db.commit()
    db.refresh(db_session)
    return map_session(db_session)

@app.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(db_session)
    db.commit()
    return {"message": "Session deleted successfully"}

# --- Session Approval Workflow ---

@app.post("/sessions/propose/student", response_model=schemas.Session)
def propose_session_as_student(
    proposal: schemas.SessionPropose,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_student)
):
    """Student proposes a session → pending_teacher."""
    teacher = db.query(models.User).filter(models.User.id == proposal.teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    end_time = proposal.end_time or (proposal.start_time + timedelta(hours=1))
    db_session = models.Session(
        teacher_id=proposal.teacher_id,
        student_id=current_user.id,
        start_time=proposal.start_time,
        end_time=end_time,
        status="pending_teacher",
        proposed_by=current_user.id,
        notes=proposal.notes
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    notify_users(db, [proposal.teacher_id],
        f"📅 {current_user.name} has requested a session on {dt_str}. Please review and approve or decline.")
    notify_users(db, get_admin_ids(db),
        f"📋 Student {current_user.name} proposed a session with {teacher.name} on {dt_str}. Awaiting teacher review.")

    return map_session(db_session)

@app.post("/sessions/propose/teacher", response_model=schemas.Session)
def propose_session_as_teacher(
    proposal: schemas.SessionPropose,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """Teacher proposes a session → pending_admin."""
    student = db.query(models.User).filter(models.User.id == proposal.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    end_time = proposal.end_time or (proposal.start_time + timedelta(hours=1))
    db_session = models.Session(
        teacher_id=current_user.id,
        student_id=proposal.student_id,
        start_time=proposal.start_time,
        end_time=end_time,
        status="pending_admin",
        proposed_by=current_user.id,
        notes=proposal.notes
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    notify_users(db, [proposal.student_id],
        f"📅 Your teacher {current_user.name} proposed a session on {dt_str}. It is awaiting admin approval.")
    notify_users(db, get_admin_ids(db),
        f"📋 Teacher {current_user.name} proposed a session with {student.name} on {dt_str}. Awaiting your approval.")

    return map_session(db_session)

@app.post("/sessions/{session_id}/approve/teacher", response_model=schemas.Session)
def approve_session_as_teacher(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """Teacher approves a student proposal → pending_admin."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_teacher":
        raise HTTPException(status_code=409, detail="Session is not awaiting teacher approval")
    if db_session.teacher_id != current_user.id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="You can only approve sessions assigned to you")

    db_session.status = "pending_admin"
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    notify_users(db, get_admin_ids(db),
        f"✅ {current_user.name} approved a session request from {db_session.student.name} on {dt_str}. Awaiting your final approval.")

    return map_session(db_session)

@app.post("/sessions/{session_id}/reject/teacher", response_model=schemas.Session)
def reject_session_as_teacher(
    session_id: int,
    approval: schemas.SessionApproval = schemas.SessionApproval(),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """Teacher rejects a student proposal → rejected."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_teacher":
        raise HTTPException(status_code=409, detail="Session is not awaiting teacher approval")
    if db_session.teacher_id != current_user.id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="You can only reject sessions assigned to you")

    db_session.status = "rejected"
    if approval.notes:
        db_session.notes = approval.notes
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    reason = f" Reason: {approval.notes}" if approval.notes else ""
    notify_users(db, [db_session.student_id],
        f"❌ Your session request on {dt_str} was declined by {current_user.name}.{reason}")

    return map_session(db_session)

@app.post("/sessions/{session_id}/counter/teacher", response_model=schemas.Session)
def counter_session_as_teacher(
    session_id: int,
    counter: schemas.SessionCounter,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    """Teacher proposes an alternative time → pending_student."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_teacher":
        raise HTTPException(status_code=409, detail="Only pending_teacher sessions can be countered by teacher")
    
    db_session.start_time = counter.start_time
    db_session.end_time = counter.end_time
    db_session.status = "pending_student"
    db_session.proposed_by = current_user.id
    if counter.notes:
        db_session.notes = counter.notes
        
    db.commit()
    db.refresh(db_session)
    
    dt_str = format_dt(db_session.start_time)
    notify_users(db, [db_session.student_id], f"🔄 Teacher {current_user.name} proposed a different time for your session: {dt_str}. Please review.")
    notify_users(db, get_admin_ids(db), f"📋 Session countered by {current_user.name} with a new time: {dt_str}.")
    
    return map_session(db_session)

@app.post("/sessions/{session_id}/counter/student", response_model=schemas.Session)
def counter_session_as_student(
    session_id: int,
    counter: schemas.SessionCounter,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_student)
):
    """Student proposes an alternative time → pending_teacher."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_student":
        raise HTTPException(status_code=409, detail="Only pending_student sessions can be countered by student")
    
    db_session.start_time = counter.start_time
    db_session.end_time = counter.end_time
    db_session.status = "pending_teacher"
    db_session.proposed_by = current_user.id
    if counter.notes:
        db_session.notes = counter.notes
        
    db.commit()
    db.refresh(db_session)
    
    dt_str = format_dt(db_session.start_time)
    notify_users(db, [db_session.teacher_id], f"🔄 Student {current_user.name} proposed a different time for your session: {dt_str}. Please review.")
    
    return map_session(db_session)

@app.post("/sessions/{session_id}/approve/student", response_model=schemas.Session)
def approve_session_as_student(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_student)
):
    """Student approves a teacher's counter-proposal → pending_admin."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_student":
        raise HTTPException(status_code=409, detail="Session is not awaiting student approval")
    
    db_session.status = "pending_admin"
    db.commit()
    db.refresh(db_session)
    
    dt_str = format_dt(db_session.start_time)
    notify_users(db, get_admin_ids(db), f"✅ Student {current_user.name} accepted the counter-proposal for {dt_str}. Awaiting your final approval.")
    
    return map_session(db_session)

@app.post("/sessions/{session_id}/approve/admin", response_model=schemas.Session)
def approve_session_as_admin(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Admin approves a session → scheduled."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_admin":
        raise HTTPException(status_code=409, detail="Session is not awaiting admin approval")

    db_session.status = "scheduled"
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    notify_users(db, [db_session.teacher_id],
        f"✅ Session on {dt_str} with {db_session.student.name} has been approved and confirmed.")
    notify_users(db, [db_session.student_id],
        f"🎵 Great news! Your session on {dt_str} with {db_session.teacher.name} is confirmed.")

    return map_session(db_session)

@app.post("/sessions/{session_id}/reject/admin", response_model=schemas.Session)
def reject_session_as_admin(
    session_id: int,
    approval: schemas.SessionApproval = schemas.SessionApproval(),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Admin rejects a session → rejected."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status not in ["pending_admin", "pending_teacher"]:
        raise HTTPException(status_code=409, detail="Session is not pending approval")

    db_session.status = "rejected"
    if approval.notes:
        db_session.notes = approval.notes
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    reason = f" Reason: {approval.notes}" if approval.notes else ""

    # Notify the proposer and relevant parties
    notify_ids = set()
    if db_session.proposed_by:
        notify_ids.add(db_session.proposed_by)
    notify_ids.add(db_session.teacher_id)
    notify_ids.add(db_session.student_id)

    for uid in notify_ids:
        notify_users(db, [uid],
            f"❌ The session proposal for {dt_str} was not approved by admin.{reason}")

    return map_session(db_session)

@app.post("/sessions/{session_id}/request-approval", response_model=schemas.Session)
def request_session_approval(
    session_id: int,
    approval_req: schemas.SessionRequestApproval,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Student requests approval for an uploaded overdue session proof."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status not in ["overdue", "overdue_rejected"]:
        raise HTTPException(status_code=409, detail="Only overdue sessions can request approval")
    
    # Ensure student has uploaded proof
    has_proof = any(p.uploader_role == 'student' for p in db_session.proofs)
    if not has_proof:
        raise HTTPException(status_code=400, detail="Must upload proof before requesting approval")

    db_session.status = "pending_verification"
    if approval_req.justification:
        db_session.proof_justification = approval_req.justification
    
    db.commit()
    db.refresh(db_session)
    
    dt_str = format_dt(db_session.start_time)
    
    notify_users(db, [db_session.teacher_id], f"🔔 {current_user.name} has submitted proof for the overdue session on {dt_str} and requested approval.")
    
    admin_users = db.query(models.User).join(models.Role).filter(models.Role.name == "admin").all()
    if admin_users:
        notify_users(db, [admin.id for admin in admin_users], f"🔔 Proof submitted by {current_user.name} for overdue session on {dt_str} requires verification.")

    return map_session(db_session)


@app.post("/sessions/{session_id}/reject-proof", response_model=schemas.Session)
def reject_session_proof(
    session_id: int,
    rejection: schemas.SessionRejectProof,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Admin rejects the uploaded session proof."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status != "pending_verification":
        raise HTTPException(status_code=409, detail="Session is not pending verification")

    db_session.status = "overdue_rejected"
    db_session.rejection_reason = rejection.reason
    
    db.commit()
    db.refresh(db_session)
    
    dt_str = format_dt(db_session.start_time)
    notify_users(db, [db_session.student_id, db_session.teacher_id], f"❌ The proof submitted for the session on {dt_str} was rejected. Reason: {rejection.reason}. Please review and re-submit.")

    return map_session(db_session)


@app.post("/sessions/{session_id}/complete", response_model=schemas.Session)
def complete_session_as_admin(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Admin completes a session overriding proof requirements."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status not in ["scheduled", "overdue", "pending_verification"]:
        raise HTTPException(status_code=409, detail="Only scheduled, overdue, or pending_verification sessions can be completed")

    db_session.status = "completed"
    
    # Analytics logic
    student = db.query(models.User).filter(models.User.id == db_session.student_id).first()
    if student and student.sessions_left is not None and student.sessions_left > 0:
        student.sessions_left -= 1
        
    enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == db_session.student_id,
        models.Enrollment.teacher_id == db_session.teacher_id
    ).first()
    if enrollment:
        enrollment.sessions_used += 1

    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    notify_users(db, [db_session.teacher_id, db_session.student_id],
        f"✅ Session from {dt_str} has been marked complete by admin.")

    return map_session(db_session)

# --- Enrollments ---

@app.post("/enrollments/", response_model=schemas.Enrollment)
def create_enrollment(enrollment: schemas.EnrollmentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    db_enrollment = models.Enrollment(**enrollment.dict())
    db.add(db_enrollment)
    db.commit()
    db.refresh(db_enrollment)
    return db_enrollment

@app.get("/enrollments/student/{student_id}", response_model=list[schemas.Enrollment])
def read_student_enrollments(student_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.student_id == student_id).all()
    return enrollments

# --- Homework ---

@app.post("/homework/", response_model=schemas.Homework)
def create_homework(session_id: int, homework: schemas.HomeworkCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_teacher)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    db_homework = models.Homework(**homework.dict(), session_id=session_id)
    db.add(db_homework)
    db.commit()
    db.refresh(db_homework)
    return db_homework

@app.put("/homework/{homework_id}", response_model=schemas.Homework)
def update_homework(homework_id: int, is_completed: bool, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_homework = db.query(models.Homework).filter(models.Homework.id == homework_id).first()
    if not db_homework:
        raise HTTPException(status_code=404, detail="Homework not found")

    db_homework.is_completed = is_completed
    db.commit()
    db.refresh(db_homework)
    return db_homework

# --- Session Proofs ---

@app.post("/session-proofs/", response_model=schemas.SessionProof)
def create_session_proof(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    file_extension = file.filename.split(".")[-1]
    file_name = f"session_{session_id}_{int(datetime.utcnow().timestamp())}.{file_extension}"
    file_path = f"uploads/{file_name}"

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    image_url = f"http://localhost:8000/uploads/{file_name}"

    db_proof = models.SessionProof(
        session_id=session_id, 
        image_url=image_url,
        uploader_id=current_user.id,
        uploader_role=current_user.role.name if current_user.role else None
    )
    db.add(db_proof)
    db.commit()
    db.refresh(db_proof)
    return db_proof

# --- Roles ---

@app.post("/roles/", response_model=schemas.Role)
def create_role(role: schemas.RoleCreate, db: Session = Depends(get_db)):
    db_role = models.Role(name=role.name)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

@app.get("/roles/", response_model=list[schemas.Role])
def read_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    roles = db.query(models.Role).offset(skip).limit(limit).all()
    return roles

# --- Notifications ---

@app.post("/notifications/", response_model=schemas.Notification)
def create_notification(notification: schemas.NotificationCreate, db: Session = Depends(get_db)):
    db_notification = models.Notification(**notification.dict())
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

@app.get("/notifications/user/{user_id}", response_model=list[schemas.Notification])
def read_user_notifications(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == user_id
    ).order_by(models.Notification.created_at.desc()).offset(skip).limit(limit).all()
    return notifications

@app.patch("/notifications/{notification_id}/read", response_model=schemas.Notification)
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_notif = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not db_notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if db_notif.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db_notif.is_read = True
    db.commit()
    db.refresh(db_notif)
    return db_notif

@app.patch("/notifications/user/{user_id}/read-all")
def mark_all_notifications_read(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if current_user.id != user_id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}


# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGING — WebSocket + REST
# ═══════════════════════════════════════════════════════════════════════════════

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, TList[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        conns = self.active_connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, payload: dict):
        dead = []
        for ws in list(self.active_connections.get(user_id, [])):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def broadcast_to_conversation(self, db, conversation_id: int, payload: dict, exclude_user_id: int = None):
        participants = db.query(models.ConversationParticipant).filter(
            models.ConversationParticipant.conversation_id == conversation_id
        ).all()
        for p in participants:
            if p.user_id == exclude_user_id:
                continue
            await self.send_to_user(p.user_id, payload)


ws_manager = ConnectionManager()


# ── WebSocket Helpers ──────────────────────────────────────────────────────────

def _msg_dict(msg: models.Message) -> dict:
    return {
        "id":              msg.id,
        "conversation_id": msg.conversation_id,
        "sender_id":       msg.sender_id,
        "sender_name":     msg.sender.name if msg.sender else None,
        "body":            msg.body if not msg.is_deleted else "[deleted]",
        "created_at":      msg.created_at.isoformat(),
        "is_deleted":      msg.is_deleted,
    }


def _unread_count(db, conversation_id: int, participant: models.ConversationParticipant) -> int:
    q = db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id,
        models.Message.is_deleted == False,
    )
    if participant.last_read_at:
        q = q.filter(models.Message.created_at > participant.last_read_at)
    return q.count()


def _build_conversation_out(db, conv: models.Conversation, current_user_id: int) -> dict:
    participants = []
    for p in conv.participants:
        participants.append({
            "user_id":      p.user_id,
            "joined_at":    p.joined_at.isoformat(),
            "last_read_at": p.last_read_at.isoformat() if p.last_read_at else None,
            "name":         p.user.name if p.user else None,
        })

    last_msg = db.query(models.Message).filter(
        models.Message.conversation_id == conv.id,
        models.Message.is_deleted == False,
    ).order_by(models.Message.created_at.desc()).first()

    my_part = next((p for p in conv.participants if p.user_id == current_user_id), None)
    unread = _unread_count(db, conv.id, my_part) if my_part else 0

    return {
        "id":           conv.id,
        "type":         conv.type,
        "name":         conv.name,
        "created_at":   conv.created_at.isoformat(),
        "participants": participants,
        "last_message": _msg_dict(last_msg) if last_msg else None,
        "unread_count": unread,
    }


async def _ws_handle_send_message(sender_id: int, data: dict, db):
    conv_id = int(data.get("conversation_id", 0))
    body = str(data.get("body", "")).strip()
    if not body:
        return
    part = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conv_id,
        models.ConversationParticipant.user_id == sender_id,
    ).first()
    if not part:
        return
    msg = models.Message(conversation_id=conv_id, sender_id=sender_id, body=body)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    # reload sender relation
    db.refresh(msg)
    payload = {"type": "new_message", "message": _msg_dict(msg)}
    await ws_manager.broadcast_to_conversation(db, conv_id, payload)
    # push unread_update to everyone except sender
    for p in db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conv_id,
        models.ConversationParticipant.user_id != sender_id,
    ).all():
        count = _unread_count(db, conv_id, p)
        await ws_manager.send_to_user(p.user_id, {
            "type": "unread_update", "conversation_id": conv_id, "count": count,
        })


async def _ws_handle_mark_read(user_id: int, data: dict, db):
    conv_id = int(data.get("conversation_id", 0))
    part = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conv_id,
        models.ConversationParticipant.user_id == user_id,
    ).first()
    if not part:
        return
    part.last_read_at = datetime.utcnow()
    db.commit()
    await ws_manager.send_to_user(user_id, {
        "type": "unread_update", "conversation_id": conv_id, "count": 0,
    })


async def _ws_handle_typing(user_id: int, data: dict, db):
    conv_id = int(data.get("conversation_id", 0))
    part = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conv_id,
        models.ConversationParticipant.user_id == user_id,
    ).first()
    if not part:
        return
    await ws_manager.broadcast_to_conversation(db, conv_id, {
        "type": "typing", "conversation_id": conv_id, "user_id": user_id,
    }, exclude_user_id=user_id)


# ── WebSocket Endpoint ─────────────────────────────────────────────────────────

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(user_id: int, websocket: WebSocket, token: str = Query(...)):
    # Authenticate
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_user_id: int = payload.get("user_id")
        if token_user_id != user_id:
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await ws_manager.connect(user_id, websocket)
    print(f"✅ WebSocket connected for user {user_id}")
    db = SessionLocal()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                continue
            msg_type = data.get("type")
            if msg_type == "send_message":
                await _ws_handle_send_message(user_id, data, db)
            elif msg_type == "mark_read":
                await _ws_handle_mark_read(user_id, data, db)
            elif msg_type == "typing":
                await _ws_handle_typing(user_id, data, db)
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(user_id, websocket)
        db.close()


# ── Messaging REST Endpoints ───────────────────────────────────────────────────

@app.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    memberships = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.user_id == current_user.id
    ).all()
    results = []
    for m in memberships:
        conv = db.query(models.Conversation).filter(models.Conversation.id == m.conversation_id).first()
        if conv:
            results.append(_build_conversation_out(db, conv, current_user.id))
    results.sort(key=lambda c: c["last_message"]["created_at"] if c["last_message"] else c["created_at"], reverse=True)
    return results


@app.post("/conversations/dm")
def create_or_get_dm(
    body: schemas.CreateDMRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    other_user = db.query(models.User).filter(models.User.id == body.other_user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    # Look for existing DM between these two users
    my_convs = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.user_id == current_user.id
    ).all()
    for m in my_convs:
        conv = db.query(models.Conversation).filter(
            models.Conversation.id == m.conversation_id,
            models.Conversation.type == "dm",
        ).first()
        if not conv:
            continue
        if len(conv.participants) == 2:
            ids = {p.user_id for p in conv.participants}
            if ids == {current_user.id, body.other_user_id}:
                return _build_conversation_out(db, conv, current_user.id)
    # Create new DM
    conv = models.Conversation(type="dm")
    db.add(conv)
    db.flush()
    db.add(models.ConversationParticipant(conversation_id=conv.id, user_id=current_user.id))
    db.add(models.ConversationParticipant(conversation_id=conv.id, user_id=body.other_user_id))
    db.commit()
    db.refresh(conv)
    return _build_conversation_out(db, conv, current_user.id)


@app.post("/conversations/group")
def create_group(
    body: schemas.CreateGroupRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    conv = models.Conversation(type="group", name=body.name)
    db.add(conv)
    db.flush()
    seen = set()
    for uid in [current_user.id] + body.participant_ids:
        if uid not in seen:
            seen.add(uid)
            db.add(models.ConversationParticipant(conversation_id=conv.id, user_id=uid))
    db.commit()
    db.refresh(conv)
    return _build_conversation_out(db, conv, current_user.id)


@app.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    cursor: int = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    # Admin can read any conversation; others must be participants
    is_admin = current_user.role and current_user.role.name.lower() == "admin"
    if not is_admin:
        part = db.query(models.ConversationParticipant).filter(
            models.ConversationParticipant.conversation_id == conversation_id,
            models.ConversationParticipant.user_id == current_user.id,
        ).first()
        if not part:
            raise HTTPException(status_code=403, detail="Not a participant")
    q = db.query(models.Message).filter(models.Message.conversation_id == conversation_id)
    if cursor:
        q = q.filter(models.Message.id < cursor)
    msgs = q.order_by(models.Message.id.desc()).limit(limit).all()
    msgs_asc = list(reversed(msgs))
    next_cursor = msgs_asc[0].id if len(msgs) == limit else None
    return {
        "messages": [_msg_dict(m) for m in msgs_asc],
        "next_cursor": next_cursor,
    }

@app.post("/conversations/{conversation_id}/messages")
async def send_message_rest(
    conversation_id: int,
    body: schemas.CreateMessageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    # Verify participation
    part = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conversation_id,
        models.ConversationParticipant.user_id == current_user.id,
    ).first()
    if not part:
        raise HTTPException(status_code=403, detail="Not a participant")

    msg = models.Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        body=body.body
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # Broadcast to other users via WebSocket
    payload = {"type": "new_message", "message": _msg_dict(msg)}
    await ws_manager.broadcast_to_conversation(db, conversation_id, payload)
    
    # Update unread counts for others
    for p in db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conversation_id,
        models.ConversationParticipant.user_id != current_user.id,
    ).all():
        count = _unread_count(db, conversation_id, p)
        await ws_manager.send_to_user(p.user_id, {
            "type": "unread_update", "conversation_id": conversation_id, "count": count,
        })

    return _msg_dict(msg)


@app.get("/sessions/{session_id}/thread")
def get_or_create_session_thread(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    is_admin = current_user.role and current_user.role.name.lower() == "admin"
    if not is_admin and current_user.id not in (session.teacher_id, session.student_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    # Check existing thread
    thread = db.query(models.SessionThread).filter(models.SessionThread.session_id == session_id).first()
    if thread:
        conv = db.query(models.Conversation).filter(models.Conversation.id == thread.conversation_id).first()
        return _build_conversation_out(db, conv, current_user.id)
    # Build label
    teacher = db.query(models.User).filter(models.User.id == session.teacher_id).first()
    student = db.query(models.User).filter(models.User.id == session.student_id).first()
    label = f"Session #{session.id}: {teacher.name if teacher else '?'} + {student.name if student else '?'}"
    conv = models.Conversation(type="session_thread", name=label)
    db.add(conv)
    db.flush()
    seen = set()
    for uid in [session.teacher_id, session.student_id]:
        if uid and uid not in seen:
            seen.add(uid)
            db.add(models.ConversationParticipant(conversation_id=conv.id, user_id=uid))
    db.add(models.SessionThread(session_id=session_id, conversation_id=conv.id))
    db.commit()
    db.refresh(conv)
    return _build_conversation_out(db, conv, current_user.id)


@app.post("/conversations/{conversation_id}/participants")
def add_participant(
    conversation_id: int,
    body: schemas.AddParticipantRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not conv or conv.type != "group":
        raise HTTPException(status_code=400, detail="Only group conversations can have participants added")
    caller_part = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conversation_id,
        models.ConversationParticipant.user_id == current_user.id,
    ).first()
    if not caller_part:
        raise HTTPException(status_code=403, detail="Not a participant")
    existing = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conversation_id,
        models.ConversationParticipant.user_id == body.user_id,
    ).first()
    if not existing:
        db.add(models.ConversationParticipant(conversation_id=conversation_id, user_id=body.user_id))
        db.commit()
    db.refresh(conv)
    return _build_conversation_out(db, conv, current_user.id)


@app.patch("/conversations/{conversation_id}/read")
def mark_conversation_read(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    part = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conversation_id,
        models.ConversationParticipant.user_id == current_user.id,
    ).first()
    if not part:
        raise HTTPException(status_code=403, detail="Not a participant")
    part.last_read_at = datetime.utcnow()
    db.commit()
    return {"unread_count": 0}

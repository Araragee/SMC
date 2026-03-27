from fastapi import Depends, FastAPI, HTTPException, status, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import os
import passlib.hash
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pathlib

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
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.email == email).first()
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
    try:
        db.execute("ALTER TABLE users ADD COLUMN username VARCHAR")
        db.execute("ALTER TABLE users ADD COLUMN contact_number VARCHAR")
        db.execute("ALTER TABLE users ADD COLUMN home_address VARCHAR")
        db.execute("ALTER TABLE users ADD COLUMN birthday VARCHAR")
        db.execute("ALTER TABLE users ADD COLUMN age INTEGER")
        db.execute("ALTER TABLE users ADD COLUMN school VARCHAR")
        db.execute("ALTER TABLE users ADD COLUMN parent_name VARCHAR")
        db.execute("ALTER TABLE users ADD COLUMN parent_contact VARCHAR")
        db.execute("ALTER TABLE users ADD COLUMN sessions_enrolled INTEGER")
    except Exception:
        pass # Ignore errors if columns already exist

    try:
        db.execute("ALTER TABLE sessions ADD COLUMN instrument_id INTEGER REFERENCES instruments(id)")
        db.execute("ALTER TABLE sessions ADD COLUMN is_manual_entry BOOLEAN DEFAULT 0")
        db.execute("ALTER TABLE sessions ADD COLUMN session_number INTEGER")
    except Exception:
        pass # Ignore errors if columns already exist
    db.commit()

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
                name="System Admin",
                hashed_password=hashed_password,
                role_id=admin_role.id,
                is_active=True
            )
            db.add(new_admin)
            db.commit()
            print("Default admin user created: admin@example.com / password123")
    finally:
        db.close()

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
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
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
        data={"sub": user.email, "user_id": user.id}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer", "user": schemas.User.model_validate(user)}

# --- Users ---

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    role = db.query(models.Role).filter(models.Role.id == user.role_id).first()

    password = user.password
    if not password and role and role.name.lower() == "student":
        first_name = user.name.split(" ")[0].lower()
        age_str = str(user.age) if user.age else ""
        password = f"{first_name}{age_str}SMC"
    elif not password:
        password = "password123" # Fallback

    hashed_password = pwd_context.hash(password[:72])

    user_data = user.dict(exclude={"password", "instrument_ids"})
    user_data["hashed_password"] = hashed_password

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

    return db_user

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

    db_proof = models.SessionProof(session_id=session_id, image_url=image_url)
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

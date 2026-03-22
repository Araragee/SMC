from typing import List
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import passlib.hash
import jwt
from datetime import datetime, timedelta

from . import models, schemas
from .database import engine, get_db

pwd_context = passlib.hash.bcrypt

SECRET_KEY = "dummy-secret-key-for-music-school-phase-1"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Music School API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Music School API"}

# --- Auth ---
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    # Try verifying the hash. Also try the fake hash for backward compatibility with mock users if any
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

    # Limit password length to avoid bcrypt ValueError and hash it
    hashed_password = pwd_context.hash(user.password[:72])

    db_user = models.User(
        email=user.email,
        name=user.name,
        hashed_password=hashed_password,
        role_id=user.role_id,
        avatar_url=user.avatar_url,
        sessions_left=user.sessions_left

    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user: schemas.UserBase, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in user.dict(exclude_unset=True).items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}

@app.get("/users/role/{role_name}", response_model=List[schemas.User])
def read_users_by_role(role_name: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    users = db.query(models.User).filter(models.User.role_id == role.id).offset(skip).limit(limit).all()
    return users

@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# Mapping utility
def map_session(db_session: models.Session) -> dict:
    session_dict = schemas.Session.model_validate(db_session).model_dump()
    session_dict['proof_image_url'] = db_session.proofs[0].image_url if db_session.proofs else None
    session_dict['homework_assigned'] = db_session.homeworks[0].description if db_session.homeworks else None
    session_dict['homework_completed'] = db_session.homeworks[0].is_completed if db_session.homeworks else False
    return session_dict

# --- Sessions ---

@app.post("/sessions/", response_model=schemas.Session)
def create_session(session: schemas.SessionCreate, db: Session = Depends(get_db)):
    student = db.query(models.User).filter(models.User.id == session.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    db_session = models.Session(**session.dict())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return map_session(db_session)

@app.get("/sessions/", response_model=List[schemas.Session])
def read_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    sessions = db.query(models.Session).offset(skip).limit(limit).all()
    return [map_session(s) for s in sessions]

@app.get("/sessions/user/{user_id}", response_model=List[schemas.Session])
def read_user_sessions(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    sessions = db.query(models.Session).filter(
        (models.Session.teacher_id == user_id) | (models.Session.student_id == user_id)
    ).offset(skip).limit(limit).all()
    return [map_session(s) for s in sessions]

@app.put("/sessions/{session_id}", response_model=schemas.Session)
def update_session(session_id: int, session: schemas.SessionBase, db: Session = Depends(get_db)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    for key, value in session.dict(exclude_unset=True).items():
        setattr(db_session, key, value)

    db.commit()
    db.refresh(db_session)
    return map_session(db_session)

@app.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(db_session)
    db.commit()
    return {"message": "Session deleted successfully"}


# --- Enrollments ---

@app.post("/enrollments/", response_model=schemas.Enrollment)
def create_enrollment(enrollment: schemas.EnrollmentCreate, db: Session = Depends(get_db)):
    db_enrollment = models.Enrollment(**enrollment.dict())
    db.add(db_enrollment)
    db.commit()
    db.refresh(db_enrollment)
    return db_enrollment

@app.get("/enrollments/student/{student_id}", response_model=List[schemas.Enrollment])
def read_student_enrollments(student_id: int, db: Session = Depends(get_db)):
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.student_id == student_id).all()
    return enrollments

# --- Homework ---

@app.post("/homework/", response_model=schemas.Homework)
def create_homework(session_id: int, homework: schemas.HomeworkCreate, db: Session = Depends(get_db)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    db_homework = models.Homework(**homework.dict(), session_id=session_id)
    db.add(db_homework)
    db.commit()
    db.refresh(db_homework)
    return db_homework

@app.put("/homework/{homework_id}", response_model=schemas.Homework)
def update_homework(homework_id: int, is_completed: bool, db: Session = Depends(get_db)):
    db_homework = db.query(models.Homework).filter(models.Homework.id == homework_id).first()
    if not db_homework:
        raise HTTPException(status_code=404, detail="Homework not found")

    db_homework.is_completed = is_completed
    db.commit()
    db.refresh(db_homework)
    return db_homework

# --- Session Proofs ---

@app.post("/session-proofs/", response_model=schemas.SessionProof)
def create_session_proof(session_id: int, proof: schemas.SessionProofCreate, db: Session = Depends(get_db)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    db_proof = models.SessionProof(**proof.dict(), session_id=session_id)
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

@app.get("/roles/", response_model=List[schemas.Role])
def read_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
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

@app.get("/notifications/user/{user_id}", response_model=List[schemas.Notification])
def read_user_notifications(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    notifications = db.query(models.Notification).filter(models.Notification.user_id == user_id).offset(skip).limit(limit).all()
    return notifications

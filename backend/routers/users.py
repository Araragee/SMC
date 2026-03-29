from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from .. import models, schemas
from ..database import get_db
from ..dependencies import (
    pwd_context,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_active_user,
    require_admin
)

router = APIRouter()

@router.get("/debug/users")
def debug_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return [{"email": u.email, "role": u.role.name if u.role else None} for u in users]

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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

@router.post("/users/")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user_email = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    role = db.query(models.Role).filter(models.Role.id == user.role_id).first()

    username = user.username
    if not username:
        base = user.email.split("@")[0] if user.email else user.name.replace(" ", "").lower()
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
        password = "password123"

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

@router.put("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
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

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}

@router.get("/users/role/{role_name}", response_model=list[schemas.User])
def read_users_by_role(role_name: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    users = db.query(models.User).filter(models.User.role_id == role.id).offset(skip).limit(limit).all()
    return users

@router.get("/users/", response_model=list[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@router.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/instruments/", response_model=list[schemas.Instrument])
def get_instruments(db: Session = Depends(get_db)):
    instruments = db.query(models.Instrument).all()
    return instruments

@router.post("/teacher-students/", response_model=schemas.TeacherStudent)
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

@router.get("/teacher-students/teacher/{teacher_id}", response_model=list[schemas.TeacherStudent])
def get_students_for_teacher(teacher_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    assignments = db.query(models.TeacherStudent).filter(models.TeacherStudent.teacher_id == teacher_id).all()
    return assignments

@router.delete("/teacher-students/{assignment_id}")
def unassign_teacher_student(assignment_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    assignment = db.query(models.TeacherStudent).filter(models.TeacherStudent.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()
    return {"message": "Assignment deleted successfully"}

@router.post("/roles/", response_model=schemas.Role)
def create_role(role: schemas.RoleCreate, db: Session = Depends(get_db)):
    db_role = models.Role(name=role.name)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

@router.get("/roles/", response_model=list[schemas.Role])
def read_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    roles = db.query(models.Role).offset(skip).limit(limit).all()
    return roles

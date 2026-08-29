from datetime import UTC, datetime, timedelta

import jwt
import passlib.hash
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import get_db

pwd_context = passlib.hash.bcrypt

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
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
    except jwt.InvalidTokenError as err:
        raise credentials_exception from err
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
    if current_user.role is None or current_user.role.name.lower() not in ["student", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires student or admin role")
    return current_user


# ── Object-level authorization ────────────────────────────────────────────────
# The guards above answer "what kind of user is this?". These answer "may this
# user see *this* record?" — without them, an endpoint that takes a user id in
# the path is readable by any authenticated account that changes the number.

def is_admin(user: models.User | None) -> bool:
    return bool(user and user.role and user.role.name.lower() == "admin")


def require_self_or_admin(current_user: models.User, user_id: int) -> None:
    """Allow only the user themselves, or an admin."""
    if current_user.id != user_id and not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


def require_can_view_user(db: Session, current_user: models.User, user_id: int) -> None:
    """Allow reading another user's schedule, records or enrollments.

    Permitted for the user themselves, any admin, or a teacher/student pair
    with a real relationship — either an explicit assignment or at least one
    shared session. A teacher legitimately needs their own students' history;
    they have no business reading a student they have never taught.
    """
    if current_user.id == user_id or is_admin(current_user):
        return

    linked = db.query(models.TeacherStudent).filter(
        ((models.TeacherStudent.teacher_id == current_user.id)
         & (models.TeacherStudent.student_id == user_id))
        | ((models.TeacherStudent.student_id == current_user.id)
           & (models.TeacherStudent.teacher_id == user_id))
    ).first()
    if linked:
        return

    enrolled = db.query(models.Enrollment).filter(
        ((models.Enrollment.teacher_id == current_user.id)
         & (models.Enrollment.student_id == user_id))
        | ((models.Enrollment.student_id == current_user.id)
           & (models.Enrollment.teacher_id == user_id))
    ).first()
    if enrolled:
        return

    shared = db.query(models.Session).filter(
        ((models.Session.teacher_id == current_user.id)
         & (models.Session.student_id == user_id))
        | ((models.Session.student_id == current_user.id)
           & (models.Session.teacher_id == user_id))
    ).first()
    if shared:
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


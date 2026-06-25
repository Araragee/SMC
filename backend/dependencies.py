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

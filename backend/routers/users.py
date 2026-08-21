from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..dependencies import (
    get_current_active_user,
    is_admin,
    pwd_context,
    require_admin,
    require_self_or_admin,
)
from ..services.notifier import safe_notify
from .activity import log_activity

router = APIRouter()

# Local Limiter handle for decorator use. The same key_func is configured on the
# app-level limiter in main.py; slowapi keys by remote address regardless.
limiter = Limiter(key_func=get_remote_address)

# Account lockout policy: after N consecutive failures, lock for LOCKOUT_MINUTES.
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15

# NOTE: ``/debug/users`` is conditionally registered below — when DEBUG is
# False the route never enters the FastAPI routing table at all (used to
# just be hidden from OpenAPI, which left a working curl-able endpoint).
if settings.DEBUG:
    @router.get("/debug/users")
    def debug_users(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(require_admin),
    ):
        users = db.query(models.User).all()
        return [{"email": u.email, "role": u.role.name if u.role else None} for u in users]

@router.post("/login")
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(
        (models.User.username == form_data.username) |
        (models.User.email == form_data.username)
    ).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    now = datetime.now(UTC)

    # Reject early if the account is currently locked.
    if user.locked_until is not None:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=UTC)
        if locked_until > now:
            retry_after = max(1, int((locked_until - now).total_seconds()))
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to too many failed login attempts",
                headers={"Retry-After": str(retry_after)},
            )

    is_valid_hash = False
    try:
        is_valid_hash = pwd_context.verify(form_data.password[:72], user.hashed_password)
    except Exception:
        pass

    if not is_valid_hash:
        # Track failed attempt and possibly lock the account.
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            db.commit()
            retry_after = LOCKOUT_MINUTES * 60
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to too many failed login attempts",
                headers={"Retry-After": str(retry_after)},
            )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    # Success: clear lockout state.
    if user.failed_login_count or user.locked_until is not None:
        user.failed_login_count = 0
        user.locked_until = None
        db.commit()

    # If 2FA enabled, return challenge instead of full tokens.
    if user.totp_enabled:
        from .auth import issue_2fa_challenge
        return {"requires_2fa": True, "challenge_token": issue_2fa_challenge(user.id)}

    # Note: build_token_pair_with_cookie sets the HttpOnly refresh cookie on
    # ``response`` AND returns the token in the body. The body copy remains
    # for non-browser clients; new browser tabs use the cookie automatically.
    from .auth import build_token_pair_with_cookie
    pair = build_token_pair_with_cookie(db, user, response)
    return pair.model_dump()


@router.post("/users/")
def create_user(
    user: schemas.UserCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
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

    if len(password.encode()) > 72:
        raise HTTPException(status_code=400, detail="Password too long (max 72 bytes)")

    hashed_password = pwd_context.hash(password[:72])

    user_data = user.model_dump(exclude={"password", "instrument_ids", "username"})
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

    log_activity(db, action_type="user_created",
                 description=f"Admin {current_user.name} created user {db_user.name} ({role.name if role else 'No Role'})",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="user", target_id=db_user.id)

    safe_notify("send_welcome", db_user, password)

    # New users get the HttpOnly cookie immediately so the SPA never has to
    # touch the refresh token directly.
    from .auth import build_token_pair_with_cookie
    return build_token_pair_with_cookie(db, db_user, response).model_dump()

@router.put("/users/{user_id}", response_model=schemas.User)
@limiter.limit("10/minute")
def update_user(request: Request, user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if current_user.id != user_id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update this user")

    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user.model_dump(exclude_unset=True)

    # Lesson balances decide what the student is owed. Self-service edits here
    # let a student top up their own account, so only an admin may set them.
    if not is_admin(current_user):
        for privileged in ("sessions_left", "sessions_enrolled"):
            update_data.pop(privileged, None)

    if "password" in update_data:
        pwd = update_data.pop("password")
        if len(pwd.encode()) > 72:
            raise HTTPException(status_code=400, detail="Password too long (max 72 bytes)")
        update_data["hashed_password"] = pwd_context.hash(pwd[:72])

    instrument_ids = update_data.pop("instrument_ids", None)

    for key, value in update_data.items():
        setattr(db_user, key, value)

    if instrument_ids is not None:
        db.query(models.UserInstrument).filter(models.UserInstrument.user_id == user_id).delete()
        for instrument_id in instrument_ids:
            db.add(models.UserInstrument(user_id=user_id, instrument_id=instrument_id))

    db.commit()
    db.refresh(db_user)

    if current_user.role.name.lower() == "admin" and current_user.id != user_id:
        log_activity(db, action_type="user_updated",
                     description=f"Admin {current_user.name} updated profile for {db_user.name}",
                     actor_id=current_user.id, actor_name=current_user.name,
                     target_type="user", target_id=db_user.id)

    return db_user

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user is linked to sessions or enrollments
    has_sessions = db.query(models.Session).filter(
        (models.Session.teacher_id == user_id) | (models.Session.student_id == user_id)
    ).first()

    has_enrollments = db.query(models.Enrollment).filter(
        (models.Enrollment.teacher_id == user_id) | (models.Enrollment.student_id == user_id)
    ).first()

    def deactivate(reason: str) -> dict:
        db_user.is_active = False
        db.commit()
        log_activity(db, action_type="user_deactivated",
                     description=f"Admin {current_user.name} deactivated user {db_user.name} ({reason})",
                     actor_id=current_user.id, actor_name=current_user.name,
                     target_type="user", target_id=db_user.id)
        return {"message": f"User was deactivated instead of deleted ({reason})"}

    # Credentials die with the account on either path: an account that is gone
    # or disabled must not keep a usable refresh token or push channel.
    db.query(models.RefreshToken).filter(models.RefreshToken.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(models.PushSubscription).filter(models.PushSubscription.user_id == user_id).delete(
        synchronize_session=False
    )
    db.commit()

    if has_sessions or has_enrollments:
        return deactivate("has linked records")

    user_name = db_user.name
    try:
        db.delete(db_user)
        db.commit()
    except IntegrityError:
        # Some other table still references this user (payments, orders, roster
        # entries, messages...). Enumerating them all would rot the moment a
        # table is added, so let the database be the authority and fall back to
        # deactivation.
        db.rollback()
        return deactivate("still referenced by other records")

    log_activity(db, action_type="user_deleted",
                 description=f"Admin {current_user.name} permanently deleted user {user_name}",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="user", target_id=user_id)
    return {"message": "User deleted successfully"}

@router.get("/users/role/{role_name}", response_model=list[schemas.User])
def read_users_by_role(
    role_name: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, le=1000),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    role = db.query(models.Role).filter(models.Role.name == role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    q = db.query(models.User).filter(models.User.role_id == role.id)
    if not include_inactive:
        q = q.filter(models.User.is_active.is_(True))
    return q.offset(skip).limit(limit).all()

@router.get("/users/", response_model=list[schemas.User])
def read_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, le=1000),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    q = db.query(models.User)
    if not include_inactive:
        q = q.filter(models.User.is_active.is_(True))
    return q.offset(skip).limit(limit).all()

@router.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/instruments/", response_model=list[schemas.Instrument])
def get_instruments(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
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

    teacher = db.query(models.User).filter(models.User.id == assignment.teacher_id).first()
    student = db.query(models.User).filter(models.User.id == assignment.student_id).first()
    log_activity(db, action_type="student_assigned",
                 description=f"Admin {current_user.name} assigned student {student.name if student else assignment.student_id} to teacher {teacher.name if teacher else assignment.teacher_id}",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="teacher_student", target_id=new_assignment.id)

    return new_assignment

@router.get("/teacher-students/", response_model=list[schemas.TeacherStudent])
def get_all_teacher_students(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Full teacher-student roster. Admin-only: it exposes the whole school's
    assignment graph, which a single teacher has no business reading."""
    return db.query(models.TeacherStudent).all()

@router.get("/teacher-students/teacher/{teacher_id}", response_model=list[schemas.TeacherStudent])
def get_students_for_teacher(teacher_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    require_self_or_admin(current_user, teacher_id)
    assignments = db.query(models.TeacherStudent).filter(models.TeacherStudent.teacher_id == teacher_id).all()
    return assignments

@router.delete("/teacher-students/{assignment_id}")
def unassign_teacher_student(assignment_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    assignment = db.query(models.TeacherStudent).filter(models.TeacherStudent.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    teacher = db.query(models.User).filter(models.User.id == assignment.teacher_id).first()
    student = db.query(models.User).filter(models.User.id == assignment.student_id).first()
    db.delete(assignment)
    db.commit()
    log_activity(db, action_type="student_unassigned",
                 description=f"Admin {current_user.name} unassigned student {student.name if student else '?'} from teacher {teacher.name if teacher else '?'}",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="teacher_student", target_id=assignment_id)
    return {"message": "Assignment deleted successfully"}

@router.post("/roles/", response_model=schemas.Role)
def create_role(role: schemas.RoleCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    db_role = models.Role(name=role.name)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

@router.get("/roles/", response_model=list[schemas.Role])
def read_roles(skip: int = Query(default=0, ge=0), limit: int = Query(default=100, le=500), db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    roles = db.query(models.Role).offset(skip).limit(limit).all()
    return roles

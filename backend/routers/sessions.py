from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import asyncio
import os

from .. import models, schemas
from ..database import get_db, SessionLocal
from ..dependencies import (
    get_current_active_user,
    require_admin,
    require_teacher,
    require_student
)

router = APIRouter()

# --- Helpers ---

def format_dt(dt: datetime) -> str:
    return dt.strftime("%b %d at %I:%M %p") if dt else "Unknown"

def notify_users(db, user_ids: list, message: str, link: str = None):
    """Create notifications for a list of user IDs."""
    for uid in user_ids:
        if uid:
            db.add(models.Notification(user_id=uid, message=message, link=link, is_read=False))
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

# --- Endpoints ---

@router.post("/sessions/record", response_model=schemas.Session)
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
        status="completed",
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

@router.get("/sessions/student/{student_id}/records", response_model=list[schemas.Session])
def get_student_records(student_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if current_user.role.name.lower() == "student" and current_user.id != student_id:
         raise HTTPException(status_code=403, detail="Not authorized")
    sessions = db.query(models.Session).filter(models.Session.student_id == student_id).order_by(models.Session.start_time.desc()).all()
    return sessions

@router.post("/sessions/", response_model=schemas.Session)
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

@router.get("/sessions/pending", response_model=list[schemas.Session])
def read_pending_sessions(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Admin: get all sessions awaiting approval."""
    sessions = db.query(models.Session).filter(
        models.Session.status.in_(["pending_teacher", "pending_admin"])
    ).all()
    return [map_session(s) for s in sessions]

@router.get("/sessions/", response_model=list[schemas.Session])
def read_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    sessions = db.query(models.Session).offset(skip).limit(limit).all()
    return [map_session(s) for s in sessions]

@router.get("/sessions/user/{user_id}", response_model=list[schemas.Session])
def read_user_sessions(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    sessions = db.query(models.Session).filter(
        (models.Session.teacher_id == user_id) | (models.Session.student_id == user_id)
    ).offset(skip).limit(limit).all()
    return [map_session(s) for s in sessions]

@router.put("/sessions/{session_id}", response_model=schemas.Session)
def update_session(session_id: int, session: schemas.SessionEdit, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Admin edits a session."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    update_data = session.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_session, key, value)

    db.commit()
    db.refresh(db_session)
    return map_session(db_session)

@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(db_session)
    db.commit()
    return {"message": "Session deleted successfully"}

@router.post("/sessions/propose/student", response_model=schemas.Session)
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
        f"📋 Student {current_user.name} proposed a session with {teacher.name} on {dt_str} (Student ID: {current_user.id}). Awaiting teacher review.")

    return map_session(db_session)

@router.post("/sessions/propose/teacher", response_model=schemas.Session)
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

@router.post("/sessions/{session_id}/approve/teacher", response_model=schemas.Session)
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

@router.post("/sessions/{session_id}/reject/teacher", response_model=schemas.Session)
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

@router.post("/sessions/{session_id}/counter/teacher", response_model=schemas.Session)
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
    if db_session.teacher_id != current_user.id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="You can only counter sessions assigned to you")

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

@router.post("/sessions/{session_id}/counter/student", response_model=schemas.Session)
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
    if db_session.student_id != current_user.id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="You can only counter sessions assigned to you")

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

@router.post("/sessions/{session_id}/approve/student", response_model=schemas.Session)
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
    if db_session.student_id != current_user.id and current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="You can only approve sessions assigned to you")

    db_session.status = "pending_admin"
    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)
    notify_users(db, get_admin_ids(db), f"✅ Student {current_user.name} accepted the counter-proposal for {dt_str}. Awaiting your final approval.")

    return map_session(db_session)

@router.post("/sessions/{session_id}/approve/admin", response_model=schemas.Session)
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

@router.post("/sessions/{session_id}/reject/admin", response_model=schemas.Session)
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

    notify_ids = set()
    if db_session.proposed_by:
        notify_ids.add(db_session.proposed_by)
    notify_ids.add(db_session.teacher_id)
    notify_ids.add(db_session.student_id)

    for uid in notify_ids:
        notify_users(db, [uid],
            f"❌ The session proposal for {dt_str} was not approved by admin.{reason}")

    return map_session(db_session)

@router.post("/sessions/{session_id}/request-approval", response_model=schemas.Session)
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

    has_proof = any(p.uploader_role == 'student' for p in db_session.proofs)
    if not has_proof:
        raise HTTPException(status_code=400, detail="Must upload proof before requesting approval")

    db_session.status = "pending_verification"
    if approval_req.justification:
        db_session.proof_justification = approval_req.justification

    db.commit()
    db.refresh(db_session)

    dt_str = format_dt(db_session.start_time)

    notify_users(db, [db_session.teacher_id], f"🔔 {current_user.name} has submitted proof for the overdue session on {dt_str} and requested approval.", link=f"/teacher/dashboard")

    admin_ids = get_admin_ids(db)
    if admin_ids:
        notify_users(db, admin_ids, f"🔔 Proof submitted by {current_user.name} for overdue session on {dt_str} requires verification.", link=f"/admin/schedule?session_id={db_session.id}")

    return map_session(db_session)

@router.post("/sessions/{session_id}/nudge", response_model=schemas.Session)
def nudge_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Notify relevant party to upload proof or finalize a session."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    dt_str = format_dt(db_session.start_time)
    teacher_proof = any(p.uploader_role == 'teacher' for p in db_session.proofs)
    student_proof = any(p.uploader_role == 'student' for p in db_session.proofs)

    if not student_proof:
        notify_users(db, [db_session.student_id], f"🔔 Reminder from {current_user.name}: Please upload your proof for the session on {dt_str}.")
    elif not teacher_proof:
        notify_users(db, [db_session.teacher_id], f"🔔 Reminder from {current_user.name}: Please upload your proof for the session on {dt_str}.")
    else:
        notify_users(db, get_admin_ids(db), f"🔔 Reminder from {current_user.name}: Session on {dt_str} is ready for final approval. All proofs are in.")

    return map_session(db_session)

@router.post("/sessions/{session_id}/reject-proof", response_model=schemas.Session)
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

@router.post("/sessions/{session_id}/complete", response_model=schemas.Session)
def complete_session_as_admin(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Admin completes a session overriding proof requirements."""
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    if db_session.status not in ["scheduled", "overdue", "overdue_rejected", "pending_verification"]:
        raise HTTPException(status_code=409, detail="Only scheduled, overdue, overdue_rejected, or pending_verification sessions can be completed")

    is_force = False
    if db_session.status != "pending_verification":
        target_time = db_session.end_time + timedelta(hours=24)
        if datetime.utcnow() < target_time:
            raise HTTPException(status_code=400, detail="Cannot force complete a session until 24 hours after its end time.")
        is_force = True
        db_session.is_force_completed = True

    db_session.status = "completed"

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
    msg = f"✅ Session from {dt_str} has been marked complete by admin."
    if is_force:
        msg = f"⚠️ Session from {dt_str} has been force completed by admin."
    notify_users(db, [db_session.teacher_id, db_session.student_id], msg)

    return map_session(db_session)

# --- Enrollments ---

@router.post("/enrollments/", response_model=schemas.Enrollment)
def create_enrollment(enrollment: schemas.EnrollmentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    db_enrollment = models.Enrollment(**enrollment.model_dump())
    db.add(db_enrollment)
    db.commit()
    db.refresh(db_enrollment)
    return db_enrollment

@router.get("/enrollments/student/{student_id}", response_model=list[schemas.Enrollment])
def read_student_enrollments(student_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.student_id == student_id).all()
    return enrollments

# --- Homework ---

@router.post("/homework/", response_model=schemas.Homework)
def create_homework(session_id: int, homework: schemas.HomeworkCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_teacher)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    db_homework = models.Homework(**homework.model_dump(), session_id=session_id)
    db.add(db_homework)
    db.commit()
    db.refresh(db_homework)
    return db_homework

@router.put("/homework/{homework_id}", response_model=schemas.Homework)
def update_homework(homework_id: int, is_completed: bool, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    db_homework = db.query(models.Homework).filter(models.Homework.id == homework_id).first()
    if not db_homework:
        raise HTTPException(status_code=404, detail="Homework not found")

    db_homework.is_completed = is_completed
    db.commit()
    db.refresh(db_homework)
    return db_homework

# --- Session Proofs ---

@router.post("/session-proofs/", response_model=schemas.SessionProof)
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

    os.makedirs("uploads", exist_ok=True)
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

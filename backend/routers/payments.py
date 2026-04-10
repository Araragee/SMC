from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_active_user, require_admin

router = APIRouter()

@router.post("/", response_model=schemas.Payment)
def create_payment(payment: schemas.PaymentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    db_payment = models.Payment(**payment.model_dump())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

@router.get("/", response_model=List[schemas.Payment])
def read_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    # Admin sees all, Teacher sees their students' payments
    if current_user.role.name.lower() == "admin":
        return db.query(models.Payment).offset(skip).limit(limit).all()
    
    if current_user.role.name.lower() == "teacher":
        # Get student IDs assigned to this teacher
        student_ids = db.query(models.TeacherStudent.student_id).filter(models.TeacherStudent.teacher_id == current_user.id).all()
        ids = [sid[0] for sid in student_ids]
        return db.query(models.Payment).filter(models.Payment.student_id.in_(ids)).offset(skip).limit(limit).all()
    
    # Student sees only their own
    return db.query(models.Payment).filter(models.Payment.student_id == current_user.id).offset(skip).limit(limit).all()

@router.get("/student/{student_id}", response_model=List[schemas.Payment])
def read_student_payments(student_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    if current_user.role.name.lower() != "admin" and current_user.id != student_id:
        # Check if teacher of this student
        is_teacher = db.query(models.TeacherStudent).filter(
            models.TeacherStudent.teacher_id == current_user.id,
            models.TeacherStudent.student_id == student_id
        ).first()
        if not is_teacher:
            raise HTTPException(status_code=403, detail="Not authorized")
            
    return db.query(models.Payment).filter(models.Payment.student_id == student_id).all()

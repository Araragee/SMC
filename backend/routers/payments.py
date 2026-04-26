from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel
from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_active_user, require_admin
from .activity import log_activity

router = APIRouter()


def _enrich_payment(payment: models.Payment) -> dict:
    """Attach student_name to a payment ORM object before returning."""
    data = {
        "id": payment.id,
        "student_id": payment.student_id,
        "amount": payment.amount,
        "date": payment.date,
        "method": payment.method,
        "status": payment.status,
        "notes": payment.notes,
        "student_name": payment.student.name if payment.student else None,
    }
    return data


@router.post("/", response_model=schemas.Payment)
def create_payment(
    payment: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    db_payment = models.Payment(**payment.model_dump())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    # Eagerly reload with student relationship for name enrichment
    db_payment_with_student = (
        db.query(models.Payment)
        .options(joinedload(models.Payment.student))
        .filter(models.Payment.id == db_payment.id)
        .first()
    )
    enriched = _enrich_payment(db_payment_with_student)
    log_activity(
        db,
        action_type="payment_created",
        description=f"Payment of ${db_payment.amount / 100:.2f} recorded for {enriched.get('student_name') or f'student #{db_payment.student_id}'} via {db_payment.method}",
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="payment",
        target_id=db_payment.id,
    )
    return enriched


@router.get("/", response_model=List[schemas.Payment])
def read_payments(
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    base_query = db.query(models.Payment).options(joinedload(models.Payment.student))

    if current_user.role.name.lower() == "admin":
        payments = base_query.order_by(models.Payment.date.desc()).offset(skip).limit(limit).all()
    elif current_user.role.name.lower() == "teacher":
        student_ids = (
            db.query(models.TeacherStudent.student_id)
            .filter(models.TeacherStudent.teacher_id == current_user.id)
            .all()
        )
        ids = [sid[0] for sid in student_ids]
        payments = (
            base_query.filter(models.Payment.student_id.in_(ids))
            .order_by(models.Payment.date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    else:
        payments = (
            base_query.filter(models.Payment.student_id == current_user.id)
            .order_by(models.Payment.date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    return [_enrich_payment(p) for p in payments]


@router.get("/student/{student_id}", response_model=List[schemas.Payment])
def read_student_payments(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if current_user.role.name.lower() != "admin" and current_user.id != student_id:
        is_teacher = (
            db.query(models.TeacherStudent)
            .filter(
                models.TeacherStudent.teacher_id == current_user.id,
                models.TeacherStudent.student_id == student_id,
            )
            .first()
        )
        if not is_teacher:
            raise HTTPException(status_code=403, detail="Not authorized")

    payments = (
        db.query(models.Payment)
        .options(joinedload(models.Payment.student))
        .filter(models.Payment.student_id == student_id)
        .order_by(models.Payment.date.desc())
        .all()
    )
    return [_enrich_payment(p) for p in payments]


class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    method: Optional[str] = None
    amount: Optional[int] = None


@router.patch("/{payment_id}", response_model=schemas.Payment)
def update_payment(
    payment_id: int,
    payload: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Admin updates a payment's status, notes, method, or amount."""
    payment = (
        db.query(models.Payment)
        .options(joinedload(models.Payment.student))
        .filter(models.Payment.id == payment_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(payment, field, value)
    db.commit()
    db.refresh(payment)

    enriched = _enrich_payment(payment)
    log_activity(
        db,
        action_type="payment_updated",
        description=f"Payment #{payment_id} updated by {current_user.name}: {update_data}",
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="payment",
        target_id=payment_id,
    )
    return enriched

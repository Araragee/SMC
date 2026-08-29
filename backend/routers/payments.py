from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..dependencies import get_current_active_user, require_admin
from ..services.notifier import safe_notify
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
        description=f"Payment of ₱{db_payment.amount / 100:.2f} recorded for {enriched.get('student_name') or f'student #{db_payment.student_id}'} via {db_payment.method}",
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="payment",
        target_id=db_payment.id,
    )
    if db_payment_with_student and db_payment_with_student.student:
        safe_notify("send_payment_receipt", db_payment_with_student.student, db_payment_with_student)
    return enriched


@router.get("/", response_model=list[schemas.Payment])
def read_payments(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, le=1000),
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


@router.get("/student/{student_id}", response_model=list[schemas.Payment])
def read_student_payments(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    role = current_user.role.name.lower() if current_user.role else ""
    if role == "admin":
        pass
    elif role == "teacher":
        has_link = (
            db.query(models.TeacherStudent)
            .filter(
                models.TeacherStudent.teacher_id == current_user.id,
                models.TeacherStudent.student_id == student_id,
            )
            .first()
        )
        if not has_link:
            has_link = (
                db.query(models.Session)
                .filter(
                    models.Session.teacher_id == current_user.id,
                    models.Session.student_id == student_id,
                )
                .first()
            )
        if not has_link:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif role == "student":
        if current_user.id != student_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
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
    status: Literal["pending", "completed", "failed"] | None = None
    notes: Annotated[str | None, Field(default=None, max_length=500)] = None
    method: Literal["cash", "bank_transfer", "card", "gcash", "maya"] | None = None
    amount: Annotated[int | None, Field(default=None, gt=0, lt=10_000_000)] = None


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


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Admin deletes a payment record."""
    payment = (
        db.query(models.Payment)
        .options(joinedload(models.Payment.student))
        .filter(models.Payment.id == payment_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    student_name = payment.student.name if payment.student else f"student #{payment.student_id}"
    amount_cents = payment.amount
    method = payment.method

    db.delete(payment)
    db.commit()

    log_activity(
        db,
        action_type="payment_deleted",
        description=f"Payment #{payment_id} of ₱{amount_cents / 100:.2f} for {student_name} via {method} deleted by {current_user.name}",
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="payment",
        target_id=payment_id,
    )
    return None


@router.get("/{payment_id}/receipt.html")
def receipt(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Render a printable HTML receipt. Browser print-to-PDF gives a PDF."""
    payment = (
        db.query(models.Payment)
        .options(joinedload(models.Payment.student))
        .filter(models.Payment.id == payment_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    role = current_user.role.name.lower() if current_user.role else ""
    if role != "admin" and payment.student_id != current_user.id:
        if role == "teacher":
            has_link = (
                db.query(models.TeacherStudent).filter(
                    models.TeacherStudent.teacher_id == current_user.id,
                    models.TeacherStudent.student_id == payment.student_id,
                ).first()
            )
            if not has_link:
                raise HTTPException(status_code=403, detail="Not authorized")
        else:
            raise HTTPException(status_code=403, detail="Not authorized")

    student = payment.student.name if payment.student else f"#{payment.student_id}"
    amount = f"₱{payment.amount / 100:.2f}"
    date_str = payment.date.strftime("%B %d, %Y") if payment.date else ""
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><title>Receipt #{payment.id} — SMC</title>
<style>
  body{{font-family:system-ui,-apple-system,sans-serif;padding:48px;max-width:640px;margin:0 auto;color:#111;}}
  h1{{margin:0 0 8px;font-size:28px;}}
  .muted{{color:#666;}}
  table{{width:100%;border-collapse:collapse;margin-top:24px;}}
  th,td{{text-align:left;padding:12px 0;border-bottom:1px solid #eee;}}
  .total{{font-size:22px;font-weight:700;}}
  .footer{{margin-top:48px;font-size:12px;color:#888;}}
  @media print {{ body{{padding:24px;}} button{{display:none;}} }}
</style></head><body>
<h1>SMC Music School</h1>
<p class="muted">Payment Receipt</p>
<table>
  <tr><th>Receipt #</th><td>{payment.id}</td></tr>
  <tr><th>Date</th><td>{date_str}</td></tr>
  <tr><th>Student</th><td>{student}</td></tr>
  <tr><th>Method</th><td>{payment.method}</td></tr>
  <tr><th>Status</th><td>{payment.status}</td></tr>
  <tr><th class="total">Amount</th><td class="total">{amount}</td></tr>
  {"<tr><th>Notes</th><td>" + payment.notes + "</td></tr>" if payment.notes else ""}
</table>
<p class="footer">Thank you. For questions contact admin@smc.edu.</p>
<button onclick="window.print()" style="margin-top:24px;padding:8px 16px;cursor:pointer;">Print / Save as PDF</button>
</body></html>"""
    return Response(content=html, media_type="text/html")

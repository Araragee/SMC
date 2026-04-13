from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import datetime
import os
import shutil

from ..database import get_db
from .. import models, schemas
from ..dependencies import get_current_user, require_admin
from .notifications import notify_users

router = APIRouter()

# --- Products ---

@router.get("/products", response_model=List[schemas.InstrumentProduct])
def get_products(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    query = db.query(models.InstrumentProduct)
    if current_user.role.name != "admin":
        query = query.filter(models.InstrumentProduct.is_active == True)
    return query.all()

@router.get("/products/{id}", response_model=schemas.InstrumentProduct)
def get_product(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    product = db.query(models.InstrumentProduct).filter(models.InstrumentProduct.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/products", response_model=schemas.InstrumentProduct)
def create_product(product_in: schemas.InstrumentProductCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    product = models.InstrumentProduct(**product_in.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@router.put("/products/{id}", response_model=schemas.InstrumentProduct)
def update_product(id: int, product_in: schemas.InstrumentProductUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    product = db.query(models.InstrumentProduct).filter(models.InstrumentProduct.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product

@router.delete("/products/{id}")
def delete_product(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    product = db.query(models.InstrumentProduct).filter(models.InstrumentProduct.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    db.commit()
    return {"message": "Product deactivated"}

@router.post("/products/{id}/image")
def upload_product_image(id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    product = db.query(models.InstrumentProduct).filter(models.InstrumentProduct.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Simple validation
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Invalid image type")

    os.makedirs("uploads/shop", exist_ok=True)
    timestamp = int(datetime.datetime.utcnow().timestamp())
    ext = file.filename.split(".")[-1]
    filename = f"{id}_{timestamp}.{ext}"
    filepath = os.path.join("uploads/shop", filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    product.image_url = f"/uploads/shop/{filename}"
    db.commit()
    return {"url": product.image_url}

# --- Orders ---

@router.post("/orders", response_model=schemas.Order)
def create_order(order_in: schemas.OrderCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    total_cents = 0
    order_items = []

    for item_in in order_in.items:
        product = db.query(models.InstrumentProduct).filter(
            models.InstrumentProduct.id == item_in.product_id,
            models.InstrumentProduct.is_active == True
        ).first()

        if not product:
            raise HTTPException(status_code=400, detail=f"Product {item_in.product_id} not available")

        if product.stock < item_in.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}")

        item_total = product.price_cents * item_in.quantity
        total_cents += item_total

        order_items.append(models.OrderItem(
            product_id=product.id,
            quantity=item_in.quantity,
            price_cents_at_purchase=product.price_cents
        ))

    order = models.Order(
        user_id=current_user.id,
        status="pending",
        notes=order_in.notes,
        total_cents=total_cents,
        items=order_items
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    # Notify admins
    admins = db.query(models.User).join(models.Role).filter(models.Role.name == "admin").all()
    admin_ids = [a.id for a in admins]
    notify_users(
        db,
        admin_ids,
        "New Shop Order",
        f"{current_user.name} placed a new order for {total_cents/100:.2f} PHP",
        f"/admin/instruments"
    )

    return order

@router.get("/orders/me", response_model=List[schemas.Order])
def get_my_orders(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Order).filter(models.Order.user_id == current_user.id).order_by(models.Order.created_at.desc()).all()

@router.get("/orders", response_model=List[schemas.Order])
def get_all_orders(status: Optional[str] = None, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    query = db.query(models.Order)
    if status:
        query = query.filter(models.Order.status == status)
    return query.order_by(models.Order.created_at.desc()).all()

@router.get("/orders/{id}", response_model=schemas.Order)
def get_order(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    order = db.query(models.Order).filter(models.Order.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role.name != "admin" and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return order

@router.patch("/orders/{id}/status", response_model=schemas.Order)
def update_order_status(id: int, status_in: schemas.OrderStatusUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    order = db.query(models.Order).filter(models.Order.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    old_status = order.status
    new_status = status_in.status

    # State machine validation
    valid_transitions = {
        "pending": ["approved", "rejected", "cancelled"],
        "approved": ["fulfilled", "cancelled"],
    }

    if old_status not in valid_transitions or new_status not in valid_transitions[old_status]:
        if old_status != new_status:
            raise HTTPException(status_code=400, detail=f"Invalid status transition from {old_status} to {new_status}")

    # Business Logic: Stock handling
    if old_status == "pending" and new_status == "approved":
        # Check stock again before transition
        for item in order.items:
            if item.product.stock < item.quantity:
                raise HTTPException(status_code=409, detail=f"Insufficient stock for {item.product.name}")
            item.product.stock -= item.quantity
        order.approved_by = current_user.id
        order.approved_at = datetime.datetime.utcnow()

    elif old_status == "approved" and new_status == "cancelled":
        # Restore stock
        for item in order.items:
            item.product.stock += item.quantity

    order.status = new_status
    if status_in.rejection_reason:
        order.rejection_reason = status_in.rejection_reason

    db.commit()
    db.refresh(order)

    # Notify user
    notify_users(
        db,
        [order.user_id],
        f"Order Update: {new_status.capitalize()}",
        f"Your order #{order.id} is now {new_status}.",
        f"/student/shop" if order.user.role.name == "student" else "/teacher/shop"
    )

    return order

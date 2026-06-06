import datetime
from datetime import timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload, selectinload

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..dependencies import get_current_user, require_admin
from ..utils.uploads import save_upload
from .notifications import notify_users
from .activity import log_activity

router = APIRouter()

# Front-end route that admins see for shop/order management.
# Update this if the admin instruments/orders route ever moves.
_ADMIN_SHOP_ROUTE = "/admin/instruments"

# --- Products ---

@router.get("/products", response_model=list[schemas.InstrumentProduct])
def get_products(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    query = db.query(models.InstrumentProduct).options(
        joinedload(models.InstrumentProduct.category)
    )
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
    log_activity(db, action_type="product_created",
                 description=f"{current_user.name} created product '{product.name}' (stock: {product.stock})",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="product", target_id=product.id)
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
    log_activity(db, action_type="product_updated",
                 description=f"{current_user.name} updated product '{product.name}'",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="product", target_id=product.id)
    return product

@router.delete("/products/{id}")
def delete_product(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    product = db.query(models.InstrumentProduct).filter(models.InstrumentProduct.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    db.commit()
    log_activity(db, action_type="product_deactivated",
                 description=f"{current_user.name} deactivated product '{product.name}'",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="product", target_id=product.id)
    return {"message": "Product deactivated"}

@router.post("/products/{id}/image")
def upload_product_image(id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    product = db.query(models.InstrumentProduct).filter(models.InstrumentProduct.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    public_url, _ = save_upload(file, "shop", {"jpg", "jpeg", "png", "webp"})

    product.image_url = public_url
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

    log_activity(db, action_type="order_placed",
                 description=f"{current_user.name} placed order #{order.id} for {total_cents/100:.2f} PHP",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="order", target_id=order.id)

    # Notify admins
    admins = db.query(models.User).join(models.Role).filter(models.Role.name == "admin").all()
    admin_ids = [a.id for a in admins]
    notify_users(
        db,
        admin_ids,
        f"{current_user.name} placed a new order for {total_cents/100:.2f} PHP",
        title="New Shop Order",
        link=_ADMIN_SHOP_ROUTE,
    )

    return order

@router.get("/orders/me", response_model=list[schemas.Order])
def get_my_orders(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return (
        db.query(models.Order)
        .options(
            joinedload(models.Order.user),
            selectinload(models.Order.items).joinedload(models.OrderItem.product),
        )
        .filter(models.Order.user_id == current_user.id)
        .order_by(models.Order.created_at.desc())
        .all()
    )

@router.patch("/orders/{id}/cancel", response_model=schemas.Order)
def cancel_my_order(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Allow a user to cancel their own pending order (no admin required)."""
    order = db.query(models.Order).filter(models.Order.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this order")
    if order.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending orders can be cancelled by the user")

    order.status = "cancelled"
    db.commit()
    db.refresh(order)

    log_activity(
        db,
        action_type="order_cancelled",
        description=f"{current_user.name} cancelled their own order #{order.id}.",
        actor_id=current_user.id,
        actor_name=current_user.name,
        target_type="order",
        target_id=order.id,
    )

    # Notify the user who cancelled
    user_shop_link = "/student/shop" if current_user.role.name.lower() == "student" else "/teacher/shop"
    notify_users(
        db,
        [current_user.id],
        f"Your order #{order.id} has been successfully cancelled.",
        title="Order Cancelled",
        link=user_shop_link,
    )

    # Notify admins
    admins = db.query(models.User).join(models.Role).filter(models.Role.name == "admin").all()
    notify_users(
        db,
        [a.id for a in admins],
        f"{current_user.name} cancelled order #{order.id}.",
        title="Order Cancelled",
        link=_ADMIN_SHOP_ROUTE,
    )

    return order

@router.get("/orders", response_model=list[schemas.Order])
def get_all_orders(status: str | None = None, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    query = (
        db.query(models.Order)
        .options(
            joinedload(models.Order.user),
            selectinload(models.Order.items).joinedload(models.OrderItem.product),
        )
    )
    if status:
        query = query.filter(models.Order.status == status)
    return query.order_by(models.Order.created_at.desc()).all()

@router.get("/orders/{id}", response_model=schemas.Order)
def get_order(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    order = (
        db.query(models.Order)
        .options(
            joinedload(models.Order.user),
            selectinload(models.Order.items).joinedload(models.OrderItem.product),
        )
        .filter(models.Order.id == id)
        .first()
    )
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
    LOW_STOCK_THRESHOLD = settings.LOW_STOCK_THRESHOLD
    low_stock_products: list[models.InstrumentProduct] = []

    if old_status == "pending" and new_status == "approved":
        # Atomically deduct stock using UPDATE ... WHERE stock >= ? to prevent
        # overselling under concurrent approval requests (race condition guard).
        for item in order.items:
            result = db.execute(
                text(
                    "UPDATE instrument_products SET stock = stock - :qty "
                    "WHERE id = :pid AND stock >= :qty"
                ),
                {"qty": item.quantity, "pid": item.product_id},
            )
            if result.rowcount == 0:
                # Another concurrent request already exhausted the stock; roll back
                db.rollback()
                raise HTTPException(
                    status_code=409,
                    detail=f"Insufficient stock for '{item.product.name}' — it may have just sold out.",
                )
            # Refresh the ORM object so the in-memory stock reflects the DB change
            db.refresh(item.product)
            if item.product.stock < LOW_STOCK_THRESHOLD:
                low_stock_products.append(item.product)
        order.approved_by = current_user.id
        order.approved_at = datetime.datetime.now(timezone.utc)

    elif old_status == "approved" and new_status == "fulfilled":
        notify_users(
            db,
            [order.user_id],
            f"✅ Your order #{order.id} has been fulfilled and is ready for pickup!",
            title="Order Fulfilled",
            link="/student/shop" if order.user.role.name == "student" else "/teacher/shop",
        )

    elif old_status == "approved" and new_status == "cancelled":
        # Restore stock
        for item in order.items:
            item.product.stock += item.quantity

    order.status = new_status
    if status_in.rejection_reason:
        order.rejection_reason = status_in.rejection_reason

    db.commit()
    db.refresh(order)

    log_activity(db, action_type=f"order_{new_status}",
                 description=f"{current_user.name} changed order #{order.id} from {old_status} → {new_status}",
                 actor_id=current_user.id, actor_name=current_user.name,
                 target_type="order", target_id=order.id)

    # Notify user
    notify_users(
        db,
        [order.user_id],
        f"Your order #{order.id} is now {new_status}.",
        title=f"Order Update: {new_status.capitalize()}",
        link="/student/shop" if order.user.role.name == "student" else "/teacher/shop",
    )

    # Notify admins of any products that are now low on stock
    if low_stock_products:
        admins = db.query(models.User).join(models.Role).filter(models.Role.name == "admin").all()
        admin_ids = [a.id for a in admins]
        for product in low_stock_products:
            stock_label = "out of stock" if product.stock == 0 else f"only {product.stock} left"
            notify_users(
                db,
                admin_ids,
                f"'{product.name}' is running low — {stock_label}. Consider restocking.",
                title="⚠️ Low Stock Alert",
                link=_ADMIN_SHOP_ROUTE,
            )
            log_activity(
                db,
                action_type="low_stock_alert",
                description=f"Low stock alert: '{product.name}' dropped to {product.stock} unit(s) after order #{order.id} approval.",
                actor_id=current_user.id,
                actor_name=current_user.name,
                target_type="product",
                target_id=product.id,
            )

    return order

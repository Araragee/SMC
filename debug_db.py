from backend.database import SessionLocal
import backend.models as models

db = SessionLocal()
users = db.query(models.User).all()
for u in users:
    print(f"ID: {u.id}, Email: {u.email}, Hash: {u.hashed_password[:20]}...")
db.close()

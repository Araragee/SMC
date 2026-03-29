from backend.database import SessionLocal
from backend.models import Session
db = SessionLocal()
try:
    print(db.query(Session).first().id)
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()

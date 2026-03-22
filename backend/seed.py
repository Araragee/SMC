from backend.database import SessionLocal, engine
import backend.models as models
import passlib.hash

models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Check roles
roles = ["admin", "teacher", "student"]
for role_name in roles:
    if not db.query(models.Role).filter(models.Role.name == role_name).first():
        db.add(models.Role(name=role_name))
db.commit()

pwd_context = passlib.hash.bcrypt

users_to_seed = [
    {"email": "admin@example.com", "name": "Admin User", "role_name": "admin"},
    {"email": "teacher@example.com", "name": "Sernan Teacher", "role_name": "teacher"},
    {"email": "student@example.com", "name": "John Doe Student", "role_name": "student"}
]

for u in users_to_seed:
    if not db.query(models.User).filter(models.User.email == u["email"]).first():
        role = db.query(models.Role).filter(models.Role.name == u["role_name"]).first()
        hashed_password = pwd_context.hash("password123")
        db_user = models.User(
            email=u["email"],
            name=u["name"],
            hashed_password=hashed_password,
            role_id=role.id,
            is_active=True
        )
        db.add(db_user)

db.commit()
db.close()
print("Database seeded with default accounts.")

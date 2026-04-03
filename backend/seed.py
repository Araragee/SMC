import passlib.hash
from .database import SessionLocal, engine
from . import models

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
    {"email": "admin@smc.edu", "username": "admin", "name": "Admin User", "role_name": "admin"},
    {"email": "teacher@smc.edu", "username": "teacher", "name": "Sernan Teacher", "role_name": "teacher"},
    {"email": "student@smc.edu", "username": "student", "name": "John Doe Student", "role_name": "student"}
]

for u in users_to_seed:
    user = db.query(models.User).filter((models.User.email == u["email"]) | (models.User.username == u["username"])).first()
    if not user:
        role = db.query(models.Role).filter(models.Role.name == u["role_name"]).first()
        hashed_password = pwd_context.hash("password123")
        db_user = models.User(
            email=u["email"],
            username=u["username"],
            name=u["name"],
            hashed_password=hashed_password,
            role_id=role.id,
            is_active=True
        )
        db.add(db_user)

db.commit()
db.close()
print("Database seeded with default accounts: admin, teacher, student (password: password123)")

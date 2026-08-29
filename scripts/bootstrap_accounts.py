"""One-off: create the school's staff accounts on a fresh database.

Idempotent — re-running skips users that already exist. Passwords are random
and printed once; every account is flagged must_change_password.
"""
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import models
from backend.database import SessionLocal
from backend.dependencies import pwd_context

STAFF = [
    ("admin", "superadmin", "superadmin@smc.edu", "Super Admin"),
    ("admin", "admin1", "admin1@smc.edu", "Admin One"),
    ("admin", "admin2", "admin2@smc.edu", "Admin Two"),
] + [
    ("teacher", f"teacher{i}", f"teacher{i}@smc.edu", f"Teacher {i}")
    for i in range(1, 8)
]


def main() -> None:
    db = SessionLocal()
    created = []
    try:
        roles = {r.name: r for r in db.query(models.Role).all()}
        for name in ("admin", "teacher", "student"):
            if name not in roles:
                roles[name] = models.Role(name=name)
                db.add(roles[name])
        db.flush()

        for role_name, username, email, display in STAFF:
            existing = db.query(models.User).filter(
                (models.User.username == username) | (models.User.email == email)
            ).first()
            if existing:
                print(f"skip  {username} (exists)")
                continue
            password = secrets.token_urlsafe(12)
            db.add(models.User(
                email=email,
                username=username,
                name=display,
                hashed_password=pwd_context.hash(password),
                role_id=roles[role_name].id,
                is_active=True,
                email_verified=True,
                must_change_password=True,
            ))
            created.append((role_name, username, email, password))
        db.commit()
    finally:
        db.close()

    if not created:
        print("nothing to create")
        return
    print("\n  role     username      email                   password")
    print("  " + "-" * 62)
    for role_name, username, email, password in created:
        print(f"  {role_name:<8} {username:<13} {email:<23} {password}")
    print("\nAll accounts must change password on first login.")


if __name__ == "__main__":
    main()

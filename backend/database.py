import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL")
import platform
if not SQLALCHEMY_DATABASE_URL:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "sql_app.db")
    if platform.system() == "Windows":
        SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    else:
        # Default fallback to backend/sql_app.db
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DB_PATH = os.path.join(BASE_DIR, "sql_app.db")
        SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
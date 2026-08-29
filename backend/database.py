import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
if SQLALCHEMY_DATABASE_URL:
    # Dashboard env-var fields (Render, Fly, …) happily store a value pasted
    # with surrounding quotes or a stray leading space; SQLAlchemy then fails
    # with an opaque "Could not parse SQLAlchemy URL from given URL string".
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.strip().strip('"\'')
if not SQLALCHEMY_DATABASE_URL:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "sql_app.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

# Postgres needs a real pool; SQLite must skip thread-safety check.
engine_kwargs: dict = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Tuned for FastAPI uvicorn workers: keep small, recycle stale conns.
    engine_kwargs.update(
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
    )

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

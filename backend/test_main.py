from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base.metadata.create_all(bind=engine)

import pytest

@pytest.fixture(autouse=True)
def run_around_tests():
    # Setup
    Base.metadata.create_all(bind=engine)
    yield
    # Teardown
    Base.metadata.drop_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Music School API"}

def test_create_role():
    response = client.post(
        "/roles/",
        json={"name": "Admin"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Admin"
    assert "id" in data

def test_create_user():
    # Make sure we have a role first
    client.post("/roles/", json={"name": "Teacher"})
    response = client.post(
        "/users/",
        json={"email": "teacher@example.com", "name": "Test Teacher", "password": "password", "role_id": 1},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == "teacher@example.com"
    assert "id" in data

"""Health endpoints: liveness must not depend on the database, readiness must.

The platform restarts a container whose ``healthCheckPath`` stops answering
(``healthCheckPath: /health`` in render.yaml). If that probe opened a database
connection, a brief upstream blip would be read as "this instance is broken"
and turn into a restart loop — plus a cold start on a free instance — while
the process itself was perfectly healthy. These tests pin that separation so
the probe cannot quietly regain a dependency.
"""
import pytest
from fastapi.testclient import TestClient

from backend.database import Base
from backend.database import engine as app_engine
from backend.main import app


@pytest.fixture()
def client():
    # No lifespan: TestClient only runs startup when used as a context
    # manager, and these routes need no seeded data.
    Base.metadata.create_all(app_engine)
    return TestClient(app)


def _explode():
    raise RuntimeError("database is unreachable")


def test_liveness_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_liveness_survives_an_unreachable_database(client, monkeypatch):
    """The whole point of the split: no database, still alive."""
    monkeypatch.setattr("backend.main.SessionLocal", _explode)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_the_database(client):
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_readiness_fails_when_the_database_is_unreachable(client, monkeypatch):
    monkeypatch.setattr("backend.main.SessionLocal", _explode)
    response = client.get("/health/db")
    assert response.status_code == 503


def test_both_probes_stay_open_during_maintenance(client, monkeypatch):
    """An operator in maintenance mode still needs to see why things are down."""
    monkeypatch.setattr("backend.config.settings.MAINTENANCE_MODE", True)
    assert client.get("/health").status_code == 200
    assert client.get("/health/db").status_code == 200
    # Everything else is closed, which is what makes the exemption meaningful.
    assert client.get("/").status_code == 503

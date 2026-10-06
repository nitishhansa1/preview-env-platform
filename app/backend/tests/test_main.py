"""
Pytest Test Suite for Job Application Tracker API
=================================================
Purpose:
  Verifies all endpoints, database interactions, error handling, health probes,
  and metadata version endpoints using an isolated in-memory SQLite database.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Application

# Setup in-memory SQLite engine for fast, isolated unit & integration testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Creates fresh database schema before each test and tears it down afterwards.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    TestClient fixture with get_db dependency overridden to use in-memory SQLite.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ==============================================================================
# Health and Observability Probe Tests
# ==============================================================================

def test_liveness_healthz(client):
    """
    Verifies that the /healthz liveness probe always returns HTTP 200 OK.
    """
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_readyz_success(client, monkeypatch):
    """
    Verifies that the /readyz readiness probe returns HTTP 200 OK when DB is healthy.
    """
    monkeypatch.setattr("app.main.check_db_connection", lambda: True)
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}


def test_readiness_readyz_failure(client, monkeypatch):
    """
    Verifies that /readyz returns HTTP 503 Service Unavailable when DB is unreachable.
    """
    monkeypatch.setattr("app.main.check_db_connection", lambda: False)
    response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "disconnected"}


def test_version_endpoint(client):
    """
    Verifies that /api/version returns application version and PR metadata.
    """
    response = client.get("/api/version")
    assert response.status_code == 200
    data = response.json()
    assert "app_version" in data
    assert "git_sha" in data
    assert "pr_number" in data


# ==============================================================================
# Job Applications CRUD Tests
# ==============================================================================

def test_create_and_get_application(client):
    """
    Tests creating a new job application and retrieving it by ID.
    """
    payload = {
        "company": "Amazon AWS",
        "role": "Cloud Support Engineer",
        "status": "applied",
        "notes": "Applied on career portal.",
    }
    create_resp = client.post("/api/applications", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["id"] is not None
    assert created_data["company"] == "Amazon AWS"
    assert created_data["role"] == "Cloud Support Engineer"
    assert created_data["status"] == "applied"
    assert created_data["notes"] == "Applied on career portal."
    assert "created_at" in created_data

    app_id = created_data["id"]

    # Fetch by ID
    get_resp = client.get(f"/api/applications/{app_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["company"] == "Amazon AWS"


def test_list_applications_and_filter(client, db_session):
    """
    Tests listing applications and filtering by status query parameter.
    """
    app1 = Application(company="Apple", role="iOS Engineer", status="applied")
    app2 = Application(company="Microsoft", role="DevOps Engineer", status="interview")
    app3 = Application(company="Netflix", role="Platform Engineer", status="interview")
    db_session.add_all([app1, app2, app3])
    db_session.commit()

    # List all
    list_resp = client.get("/api/applications")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 3

    # Filter by status = interview
    filtered_resp = client.get("/api/applications?status=interview")
    assert filtered_resp.status_code == 200
    results = filtered_resp.json()
    assert len(results) == 2
    assert all(item["status"] == "interview" for item in results)


def test_update_application(client, db_session):
    """
    Tests updating an application's status and notes.
    """
    app_obj = Application(company="Meta", role="Production Engineer", status="applied")
    db_session.add(app_obj)
    db_session.commit()
    db_session.refresh(app_obj)

    update_payload = {
        "status": "offer",
        "notes": "Offer letter received.",
    }
    put_resp = client.put(f"/api/applications/{app_obj.id}", json=update_payload)
    assert put_resp.status_code == 200
    updated_data = put_resp.json()
    assert updated_data["status"] == "offer"
    assert updated_data["notes"] == "Offer letter received."
    assert updated_data["company"] == "Meta"


def test_delete_application(client, db_session):
    """
    Tests deleting an application and ensuring subsequent GET returns 404.
    """
    app_obj = Application(company="Uber", role="Infrastructure Engineer", status="rejected")
    db_session.add(app_obj)
    db_session.commit()
    db_session.refresh(app_obj)

    delete_resp = client.delete(f"/api/applications/{app_obj.id}")
    assert delete_resp.status_code == 204

    # Verify record is gone
    get_resp = client.get(f"/api/applications/{app_obj.id}")
    assert get_resp.status_code == 404


def test_get_nonexistent_application_returns_404(client):
    """
    Verifies that requesting a nonexistent ID returns 404 Not Found.
    """
    response = client.get("/api/applications/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_invalid_status_validation_error(client):
    """
    Verifies that submitting an invalid status string returns 422 Validation Error.
    """
    payload = {
        "company": "Test Co",
        "role": "Developer",
        "status": "invalid_status_value",
    }
    response = client.post("/api/applications", json=payload)
    assert response.status_code == 422

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_session
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


def test_ready_database(session):
    app.dependency_overrides[get_session] = lambda: session
    try:
        assert client.get("/api/v1/ready").json() == {"status": "ready"}
    finally:
        app.dependency_overrides.clear()


def test_ready_failure():
    class Unavailable:
        def execute(self, statement):
            raise OperationalError(
                "SELECT 1", {}, RuntimeError("private connection details")
            )

    app.dependency_overrides[get_session] = lambda: Unavailable()
    try:
        response = client.get("/api/v1/ready")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "database_unavailable"
        assert "private" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_business_data_requires_authentication():
    for path in ("customers", "accounts", "tickets", "approvals"):
        response = client.get(f"/api/v1/{path}")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "http_error"

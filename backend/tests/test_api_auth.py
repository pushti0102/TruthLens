import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, startup_event

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_app():
    startup_event()


def test_health_endpoints():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    res_ai = client.get("/api/health/ai")
    assert res_ai.status_code == 200
    assert "model_id" in res_ai.json()

    res_crypto = client.get("/api/health/crypto")
    assert res_crypto.status_code == 200
    assert res_crypto.json()["active_key_registered"] is True


def test_user_login_admin():
    res = client.post(
        "/api/auth/login",
        json={"email": "admin@truthlens.local", "password": "AdminPass123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "ADMIN"


def test_user_login_publisher():
    res = client.post(
        "/api/auth/login",
        json={"email": "publisher@truthlens.local", "password": "PublisherPass123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "PUBLISHER"


def test_user_login_invalid_password():
    res = client.post(
        "/api/auth/login",
        json={"email": "admin@truthlens.local", "password": "WrongPassword!"},
    )
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]


import uuid

def test_user_registration_and_me():
    email = f"newuser_{uuid.uuid4().hex[:8]}@truthlens.local"
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "NewUserPassword123!", "full_name": "Test User"},
    )
    assert res.status_code == 201
    token = res.json()["access_token"]

    # Verify /me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email
    assert me_res.json()["role"] == "USER"


def test_rbac_admin_endpoint_forbidden_for_normal_user():
    # Login as normal user
    res = client.post(
        "/api/auth/login",
        json={"email": "user@truthlens.local", "password": "UserPass123!"},
    )
    token = res.json()["access_token"]

    # Attempt to view audit logs (Admin only)
    audit_res = client.get(
        "/api/admin/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert audit_res.status_code == 403


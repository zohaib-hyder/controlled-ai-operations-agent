import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.passwords import hash_password, verify_password
from app.core.permissions import PERMISSIONS, Identity
from app.db.seed import seed, stable_id
from app.db.seed_auth import seed_auth
from app.db.session import get_session
from app.main import app
from app.models.entities import (
    AuthSession,
    Customer,
    LoginBucket,
    SecurityEvent,
    Tenant,
    User,
)
from app.services.authentication import COOKIE_NAME, digest, require_permission
from app.services.repository import TenantRepository

PASSWORD = secrets.token_urlsafe(24)
ENCODED = hash_password(PASSWORD)
ORIGIN = {"Origin": "http://localhost:3000"}


@pytest.fixture
def client(session):
    seed(session)
    for tenant in range(2):
        session.add(
            User(
                id=stable_id(f"{tenant}/user/admin"),
                tenant_id=stable_id(f"tenant/{tenant}"),
                email=f"admin.{tenant}@example.com",
                role="admin",
                password_hash=ENCODED,
            )
        )
    session.flush()
    for user in session.scalars(select(User)):
        user.password_hash = ENCODED
    session.flush()
    app.dependency_overrides[get_session] = lambda: session
    existing = list(app.routes)

    def admin_probe(
        identity: Annotated[Identity, Depends(require_permission("settings:manage"))],
    ):
        return {"ok": True}

    def review_probe(
        identity: Annotated[Identity, Depends(require_permission("approval:review"))],
    ):
        return {"ok": True}

    app.add_api_route("/__test/admin", admin_probe, methods=["GET"])
    app.add_api_route("/__test/review", review_probe, methods=["GET"])
    with TestClient(app) as client:
        client.headers.update(ORIGIN)
        yield client
    app.routes[:] = existing
    app.dependency_overrides.clear()


def login(client, role="operator", tenant=0):
    return client.post(
        "/api/v1/auth/login",
        json={"email": f"{role}.{tenant}@example.com", "password": PASSWORD},
    )


def test_login_and_me(client, session):
    response = login(client)
    assert response.status_code == 200
    identity = response.json()
    assert identity["tenant_id"] == str(stable_id("tenant/0"))
    assert identity["role"] == "operator"
    assert "password_hash" not in identity
    token = client.cookies.get(COOKIE_NAME)
    stored = session.scalar(select(AuthSession))
    assert (
        len(token) == 43
        and stored.token_hash == digest(token)
        and stored.token_hash != token
    )
    assert client.get("/api/v1/auth/me").json() == identity
    assert response.headers["cache-control"] == "no-store"
    assert session.get(User, UUID(identity["user_id"])).password_hash.startswith(
        "$argon2id$"
    )


def test_cookie_properties(client):
    cookie = login(client).headers["set-cookie"].lower()
    for part in ("httponly", "samesite=lax", "path=/", "max-age=3600", "expires="):
        assert part in cookie
    assert "domain=" not in cookie
    assert "secure" not in cookie


def test_https_cookie_flag(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "cookie_secure", True)
    assert "secure" in login(client).headers["set-cookie"].lower()


@pytest.mark.parametrize("email", ["operator.0@example.com", "missing@example.com"])
def test_generic_invalid_credentials(client, email):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": secrets.token_urlsafe(24)},
    )
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid email or password"


@pytest.mark.parametrize("state", ["expired", "revoked", "disabled"])
def test_invalidated_session(client, session, state):
    login(client)
    auth_session = session.scalar(select(AuthSession))
    if state == "expired":
        auth_session.created_at = datetime.now(UTC) - timedelta(hours=2)
        auth_session.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    elif state == "revoked":
        auth_session.revoked_at = datetime.now(UTC)
    else:
        session.get(User, auth_session.user_id).is_active = False
    session.flush()
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/customers").status_code == 401


def test_logout_revokes_cookie_and_replay(client, session):
    login(client)
    token = client.cookies.get(COOKIE_NAME)
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    client.cookies.set(COOKIE_NAME, token)
    assert client.get("/api/v1/auth/me").status_code == 401
    assert {e.event_type for e in session.scalars(select(SecurityEvent))} >= {
        "login_succeeded",
        "session_revoked",
        "logout",
    }


def test_login_rotates_browser_session(client, session):
    login(client)
    old = client.cookies.get(COOKIE_NAME)
    login(client)
    assert client.cookies.get(COOKIE_NAME) != old
    assert session.scalar(
        select(AuthSession).where(AuthSession.token_hash == digest(old))
    ).revoked_at
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, old)
    assert client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "null",
        "https://attacker.example.com",
        "http://localhost:3000.attacker.example.com",
    ],
)
def test_csrf_login_rejected(client, origin):
    client.headers.pop("origin", None)
    response = client.post(
        "/api/v1/auth/login",
        headers={} if origin is None else {"Origin": origin},
        json={"email": "operator.0@example.com", "password": PASSWORD},
    )
    assert response.status_code == 403


def test_csrf_logout_cannot_revoke_session(client):
    login(client)
    assert (
        client.post(
            "/api/v1/auth/logout", headers={"Origin": "https://attacker.example.com"}
        ).status_code
        == 403
    )
    assert client.get("/api/v1/auth/me").status_code == 200


def test_cross_site_fetch_rejected(client):
    response = client.post(
        "/api/v1/auth/login",
        headers={"Sec-Fetch-Site": "cross-site"},
        json={"email": "operator.0@example.com", "password": PASSWORD},
    )
    assert response.status_code == 403


def test_failed_login_limit_and_window(client, session):
    for _ in range(5):
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "operator.0@example.com", "password": "invalid"},
            ).status_code
            == 401
        )
    limited = login(client)
    assert limited.status_code == 429 and limited.headers["retry-after"] == "300"
    for bucket in session.scalars(select(LoginBucket)):
        bucket.window_started_at = datetime.now(UTC) - timedelta(minutes=6)
    session.flush()
    assert login(client).status_code == 200


def test_client_limit_blocks_unknown_identity_spray(client):
    for i in range(30):
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": f"unknown{i}@example.com", "password": "invalid"},
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "another@example.com", "password": "invalid"},
        ).status_code
        == 429
    )


@pytest.mark.parametrize(
    "role,admin_status,review_status",
    [
        ("operator", 403, 403),
        ("reviewer", 403, 200),
        ("admin", 200, 200),
        ("auditor", 403, 403),
    ],
)
def test_server_side_permissions(client, session, role, admin_status, review_status):
    assert login(client, role).status_code == 200
    assert client.get("/__test/admin").status_code == admin_status
    assert client.get("/__test/review").status_code == review_status
    assert client.get("/api/v1/customers").status_code == 200
    if admin_status == 403:
        event = session.scalar(
            select(SecurityEvent).where(SecurityEvent.event_type == "permission_denied")
        )
        assert event.tenant_id == stable_id("tenant/0") and event.request_id


@pytest.mark.parametrize(
    "role,expected",
    [
        (
            "operator",
            {"customer:read", "account:read", "ticket:read", "investigation:create"},
        ),
        (
            "reviewer",
            {
                "customer:read",
                "account:read",
                "ticket:read",
                "investigation:create",
                "approval:review",
            },
        ),
        (
            "admin",
            {
                "customer:read",
                "account:read",
                "ticket:read",
                "investigation:create",
                "approval:review",
                "audit:read",
                "user:manage",
                "settings:manage",
            },
        ),
        ("auditor", {"customer:read", "account:read", "ticket:read", "audit:read"}),
    ],
)
def test_exact_permission_matrix(role, expected):
    if role != "auditor":
        expected |= {
            "action:create_customer_note:propose",
            "action:add_ticket_note:propose",
            "action:request_account_reactivation:propose",
            "action:reactivate_account:propose",
            "action:close_duplicate_ticket:propose",
            "action:override_security_block:propose",
        }
    if role in {"operator", "admin"}:
        expected.add("action:execute")
    if role in {"reviewer", "admin"}:
        expected.add("action:approve")
    assert PERMISSIONS[role] == expected
    assert ("action:execute" in PERMISSIONS[role]) == (role in {"operator", "admin"})
    assert ("action:approve" in PERMISSIONS[role]) == (role in {"reviewer", "admin"})


def test_privilege_and_tenant_escalation_rejected(client):
    assert (
        client.post(
            "/api/v1/auth/login",
            json={
                "email": "operator.0@example.com",
                "password": PASSWORD,
                "role": "admin",
                "tenant_id": str(stable_id("tenant/1")),
            },
        ).status_code
        == 422
    )
    login(client)
    assert client.post("/api/v1/users", json={"role": "admin"}).status_code == 404
    assert client.post("/api/v1/accounts", json={"status": "active"}).status_code == 405
    assert (
        client.get(
            "/api/v1/customers?tenant_id=" + str(stable_id("tenant/1"))
        ).status_code
        == 422
    )
    response = client.get(
        "/api/v1/auth/me",
        headers={"X-Tenant-ID": str(stable_id("tenant/1")), "X-Role": "admin"},
    )
    assert (
        response.json()["tenant_id"] == str(stable_id("tenant/0"))
        and response.json()["role"] == "operator"
    )


def test_roles_are_revalidated_from_database(client, session):
    login(client, "admin")
    user = session.get(User, stable_id("0/user/admin"))
    user.role = "auditor"
    session.flush()
    assert client.get("/__test/admin").status_code == 403
    assert client.get("/api/v1/auth/me").json()["role"] == "auditor"


@pytest.mark.parametrize(
    "kind,singular,count",
    [
        ("customers", "customer", 10),
        ("accounts", "account", 10),
        ("tickets", "ticket", 15),
    ],
)
def test_tenant_isolation_and_non_disclosing_404(
    client, session, kind, singular, count
):
    login(client)
    response = client.get(
        f"/api/v1/{kind}?limit=2&offset=0",
        headers={"X-Tenant-ID": str(stable_id("tenant/1"))},
    )
    assert response.status_code == 200 and response.json()["total"] == count
    assert len(response.json()["items"]) == 2
    foreign_id = stable_id(f"1/{singular}/0")
    own_id = stable_id(f"0/{singular}/0")
    assert client.get(f"/api/v1/{kind}/{own_id}").status_code == 200
    denied = client.get(f"/api/v1/{kind}/{foreign_id}")
    missing = client.get(f"/api/v1/{kind}/{uuid4()}")
    assert denied.status_code == missing.status_code == 404
    assert (
        denied.json()["error"]["message"]
        == missing.json()["error"]["message"]
        == "Resource not found"
    )
    assert str(foreign_id) not in denied.text
    event = session.scalar(
        select(SecurityEvent).where(SecurityEvent.resource_id == foreign_id)
    )
    assert (
        event.event_type == "resource_access_denied"
        and event.tenant_id == stable_id("tenant/0")
    )
    # Both directions, with independently validated sessions.
    login(client, tenant=1)
    assert client.get(f"/api/v1/{kind}/{own_id}").status_code == 404
    assert client.get(f"/api/v1/{kind}/{foreign_id}").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "customers",
        "accounts",
        "tickets",
        "customers/00000000-0000-0000-0000-000000000000",
        "auth/me",
    ],
)
def test_unauthenticated_rejected(client, path):
    assert client.get(f"/api/v1/{path}").status_code == 401


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "offset=-1",
        "offset=10001",
        "limit=not-a-number",
        "role=admin",
    ],
)
def test_pagination_validation(client, query):
    login(client)
    assert client.get("/api/v1/customers?" + query).status_code == 422


def test_invalid_uuid_and_no_pii_response(client):
    login(client)
    assert client.get("/api/v1/customers/not-a-uuid").status_code == 422
    data = client.get("/api/v1/customers").json()
    assert set(data["items"][0]) == {"id", "name"}


def test_tampered_token_rejected(client):
    login(client)
    token = client.cookies.get(COOKIE_NAME)
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, token[:-1] + ("A" if token[-1] != "A" else "B"))
    assert client.get("/api/v1/customers").status_code == 401


def test_audit_secrets_and_append_only(client, session):
    login(client)
    token = client.cookies.get(COOKIE_NAME)
    event = session.scalar(select(SecurityEvent))
    assert PASSWORD not in str(event.__dict__) and token not in str(event.__dict__)
    assert event.actor_id == stable_id("0/user/operator") and event.request_id
    with pytest.raises(ValueError, match="append-only"), session.begin_nested():
        event.outcome = "modified"
        session.flush()


def test_authentication_seed_idempotent(session):
    assert seed_auth(session, PASSWORD, environment="test") == 8
    before = {
        u.id: (u.email, u.role, u.password_hash) for u in session.scalars(select(User))
    }
    assert seed_auth(session, secrets.token_urlsafe(24), environment="test") == 8
    assert {
        u.id: (u.email, u.role, u.password_hash) for u in session.scalars(select(User))
    } == before
    assert all(verify_password(row[2], PASSWORD) for row in before.values())


def test_production_demo_seed_refused(session):
    with pytest.raises(ValueError, match="forbidden"):
        seed_auth(session, PASSWORD, environment="production")
    assert session.scalar(select(func.count()).select_from(User)) == 0


def test_production_cookie_configuration():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", demo_password=None)
    valid = Settings(
        _env_file=None,
        app_env="production",
        cookie_secure=True,
        trusted_origins=["https://northstar.example.com"],
        demo_password=None,
    )
    assert valid.cookie_secure
    with pytest.raises(ValidationError) as rejected:
        Settings(
            _env_file=None,
            app_env="production",
            cookie_secure=True,
            trusted_origins=["https://northstar.example.com"],
            demo_password=PASSWORD,
        )
    assert PASSWORD not in str(rejected.value)


def test_tenant_repository_is_explicit(client, session):
    login(client)
    identity = Identity(
        stable_id("0/user/operator"),
        stable_id("tenant/0"),
        "operator",
        session.scalar(select(AuthSession)).id,
    )
    repository = TenantRepository(session, identity)
    assert repository.get(Customer, stable_id("1/customer/0")) is None
    with pytest.raises(ValueError):
        repository.list(Customer, limit=1000, offset=0)


def test_session_tenant_foreign_key(client, session):
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(
            AuthSession(
                tenant_id=stable_id("tenant/1"),
                user_id=stable_id("0/user/operator"),
                token_hash=digest(secrets.token_urlsafe(32)),
                created_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        session.flush()


def test_session_persists_across_connections(engine):
    tenant_id, user_id = uuid4(), uuid4()

    def database_session():
        with Session(engine) as session:
            yield session

    try:
        with Session(engine) as session, session.begin():
            session.add(Tenant(id=tenant_id, name=f"Synthetic persistence {tenant_id}"))
            session.flush()
            session.add(
                User(
                    id=user_id,
                    tenant_id=tenant_id,
                    email=f"{user_id}@example.com",
                    role="operator",
                    password_hash=ENCODED,
                )
            )
        app.dependency_overrides[get_session] = database_session
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/login",
                headers=ORIGIN,
                json={"email": f"{user_id}@example.com", "password": PASSWORD},
            )
            assert response.status_code == 200
            assert client.get("/api/v1/auth/me").json()["user_id"] == str(user_id)
            with Session(engine) as check:
                assert check.scalar(
                    select(AuthSession).where(AuthSession.user_id == user_id)
                )
    finally:
        app.dependency_overrides.clear()
        # Privileged test-only teardown; the application has no audit deletion path.
        with engine.begin() as connection:
            for model in (SecurityEvent, AuthSession, User):
                connection.execute(
                    model.__table__.delete().where(model.tenant_id == tenant_id)
                )
            connection.execute(Tenant.__table__.delete().where(Tenant.id == tenant_id))
            connection.execute(LoginBucket.__table__.delete())


def test_upgrade_from_phase0_preserves_data(engine):
    schema = "migration_" + uuid4().hex
    cfg = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "5cdee4cd2488")
            tenant, user, customer = uuid4(), uuid4(), uuid4()
            connection.execute(
                text(
                    "INSERT INTO tenants(id,name) VALUES (:id,'Synthetic migration tenant')"
                ),
                {"id": tenant},
            )
            connection.execute(
                text(
                    "INSERT INTO users(id,tenant_id,email,role) VALUES (:id,:tenant,'migration@example.com','approver')"
                ),
                {"id": user, "tenant": tenant},
            )
            connection.execute(
                text(
                    "INSERT INTO customers(id,tenant_id,name,email) VALUES (:id,:tenant,'Synthetic preserved client','preserved@example.com')"
                ),
                {"id": customer, "tenant": tenant},
            )
            before = connection.execute(text("SELECT * FROM customers")).all()
            command.upgrade(cfg, "head")
            assert connection.execute(text("SELECT * FROM customers")).all() == before
            row = connection.execute(
                text("SELECT id,role,password_hash FROM users")
            ).one()
            assert row == (user, "reviewer", None)
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


def test_production_setting_cannot_be_bypassed_by_seed_argument(session, monkeypatch):
    monkeypatch.setattr(get_settings(), "app_env", "production")
    with pytest.raises(ValueError, match="forbidden"):
        seed_auth(session, PASSWORD, environment="development")


def test_auth_seed_does_not_activate_non_fixture_users(session):
    seed(session)
    extra = User(
        tenant_id=stable_id("tenant/0"),
        email="extra.synthetic@example.com",
        role="operator",
    )
    session.add(extra)
    session.flush()
    seed_auth(session, PASSWORD, environment="test")
    assert extra.password_hash is None

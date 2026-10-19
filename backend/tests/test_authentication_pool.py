"""Authentication must not reserve the only connection needed by the handler."""

from datetime import UTC, datetime

import pytest
import test_tools as tools
from fastapi import HTTPException
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.permissions import PERMISSIONS
from app.models.entities import AuthSession
from app.services.authentication import COOKIE_NAME, current_identity, digest

client = tools.client
executor = tools.executor
tool_db = tools.tool_db


def test_identity_releases_connection_before_handler_and_on_revocation(client, tool_db):
    expected = tools.login(client)
    token = client.cookies.get(COOKIE_NAME)
    request = Request(
        {"type": "http", "headers": [(b"cookie", f"{COOKIE_NAME}={token}".encode())]}
    )
    engine = create_engine(
        tool_db.kw["bind"].url, pool_size=1, max_overflow=0, pool_timeout=0.1
    )
    try:
        with Session(engine) as handler:
            identity = current_identity(request, handler)
            assert str(identity.user_id) == expected["user_id"]
            assert identity.permissions == PERMISSIONS["operator"]
            assert engine.pool.checkedout() == 0
            # This is the service's separate connection, which previously starved.
            with engine.connect() as service:
                assert service.scalar(text("SELECT 1")) == 1
        with tool_db() as session, session.begin():
            row = session.scalar(
                select(AuthSession).where(AuthSession.token_hash == digest(token))
            )

            row.revoked_at = datetime.now(UTC)
        with Session(engine) as handler:
            with pytest.raises(HTTPException) as denied:
                current_identity(request, handler)
            assert denied.value.status_code == 401
            assert engine.pool.checkedout() == 0
    finally:
        engine.dispose()

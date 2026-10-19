import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture(scope="session")
def engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail(
            "Set TEST_DATABASE_URL to a dedicated disposable PostgreSQL database ending in _test"
        )
    engine = create_engine(url)
    if not engine.url.database or not engine.url.database.endswith("_test"):
        pytest.fail(
            "Refusing to test against a database whose name does not end in _test"
        )
    os.environ["DATABASE_URL"] = url
    from app.core.config import get_settings

    get_settings.cache_clear()
    cfg = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    from app.evaluations.isolation import exclusive_test_database

    try:
        with exclusive_test_database(engine):
            command.upgrade(cfg, "head")
            yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session(engine):
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        transaction.rollback()


@pytest.fixture(autouse=True)
def no_external_http_in_standard_evaluations(monkeypatch):
    if os.getenv("PHASE11_NO_EXTERNAL_HTTP") != "1":
        return
    import httpx

    def blocked(*args, **kwargs):
        raise AssertionError("Real HTTP transport is disabled in standard evaluations")

    async def async_blocked(*args, **kwargs):
        raise AssertionError("Real HTTP transport is disabled in standard evaluations")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", async_blocked)

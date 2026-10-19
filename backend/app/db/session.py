from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_timeout=3,
        connect_args={
            "connect_timeout": settings.database_timeout_seconds,
            "options": "-c statement_timeout=3000",
        },
    )


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session

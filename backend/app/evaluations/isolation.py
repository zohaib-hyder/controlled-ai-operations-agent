"""Session-wide exclusion for destructive disposable-database test fixtures."""

from contextlib import contextmanager

from sqlalchemy import text

# A fixed application namespace; held by a dedicated connection, not a transaction.
LOCK_KEY = 411_071_101


@contextmanager
def exclusive_test_database(engine):
    with engine.connect() as connection:
        acquired = connection.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}
        )
        if not acquired:
            raise RuntimeError(
                "Another integration suite owns this disposable database; use a different _test database or wait"
            )
        try:
            yield
        finally:
            connection.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY}
            )

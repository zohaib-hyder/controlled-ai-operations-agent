"""Explicit development-only authentication fixture. Never prints credentials."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.passwords import hash_password
from app.db.seed import FIXED_TIME, seed, stable_id
from app.db.session import get_engine
from app.models.entities import User


def seed_auth(session: Session, password: str, *, environment: str) -> int:
    if get_settings().app_env == "production" or environment not in {
        "development",
        "test",
    }:
        raise ValueError(
            "Demo authentication seeding is forbidden outside development/test"
        )
    if not 14 <= len(password) <= 256:
        raise ValueError("Provide a demo password of 14–256 characters")
    seed(session)
    for tenant in range(2):
        ident = stable_id(f"{tenant}/user/admin")
        if session.get(User, ident) is None:
            session.add(
                User(
                    id=ident,
                    tenant_id=stable_id(f"tenant/{tenant}"),
                    email=f"admin.{tenant}@example.com",
                    role="admin",
                    created_at=FIXED_TIME,
                    updated_at=FIXED_TIME,
                )
            )
    session.flush()
    fixture_ids = [
        stable_id(f"{tenant}/user/{key}")
        for tenant in range(2)
        for key in ("operator", "approver", "auditor", "admin")
    ]
    users = session.scalars(
        select(User).where(
            User.tenant_id.in_([stable_id("tenant/0"), stable_id("tenant/1")]),
            User.id.in_(fixture_ids),
        )
    ).all()
    for user in users:
        if user.password_hash is None:
            user.password_hash = hash_password(password)
    session.flush()
    return len(users)


def main():
    settings = get_settings()
    if not settings.demo_password:
        raise ValueError(
            "Set DEMO_PASSWORD explicitly for development authentication seeding"
        )
    with Session(get_engine()) as session, session.begin():
        count = seed_auth(session, settings.demo_password, environment=settings.app_env)
    print(
        f"Development authentication fixture available for {count} fictional users; existing passwords preserved"
    )


if __name__ == "__main__":
    main()

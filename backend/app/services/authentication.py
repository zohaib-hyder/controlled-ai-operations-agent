import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.passwords import hash_password, hasher, verify_password
from app.core.permissions import PERMISSIONS, Identity, Permission, Role
from app.db.session import get_session
from app.models.entities import AuthSession, LoginBucket, User
from app.services.security_audit import record

COOKIE_NAME = "northstar_session"
SessionDependency = Annotated[Session, Depends(get_session)]


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_origin(request: Request) -> None:
    if (
        request.headers.get("origin") not in get_settings().trusted_origins
        or request.headers.get("sec-fetch-site") == "cross-site"
    ):
        raise HTTPException(403, "Request origin is not permitted")


def current_identity(request: Request, session: SessionDependency) -> Identity:
    token = request.cookies.get(COOKIE_NAME, "")
    if not 32 <= len(token) <= 128:
        raise HTTPException(401, "Authentication required")
    # Release the read-only authentication connection before endpoint services acquire
    # their own transaction. Respect injected binds (including test savepoints).
    with Session(
        bind=session.get_bind(), join_transaction_mode="create_savepoint"
    ) as authentication:
        row = authentication.execute(
            select(AuthSession, User)
            .join(
                User,
                (User.id == AuthSession.user_id)
                & (User.tenant_id == AuthSession.tenant_id),
            )
            .where(
                AuthSession.token_hash == digest(token),
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > datetime.now(UTC),
                User.is_active.is_(True),
            )
        ).first()
        if not row or row.User.role not in PERMISSIONS:
            raise HTTPException(401, "Authentication required")
        return Identity(
            row.User.id,
            row.User.tenant_id,
            cast(Role, row.User.role),
            row.AuthSession.id,
        )


IdentityDependency = Annotated[Identity, Depends(current_identity)]


def require_permission(permission: Permission):
    def authorize(
        request: Request, identity: IdentityDependency, session: SessionDependency
    ) -> Identity:
        if permission not in identity.permissions:
            record(
                session,
                request,
                "permission_denied",
                "denied",
                tenant_id=identity.tenant_id,
                actor_id=identity.user_id,
                resource_type=permission,
            )
            session.commit()
            raise HTTPException(403, "Permission denied")
        return identity

    return authorize


def authenticate(
    session: Session, request: Request, email: str, password: str
) -> tuple[User, AuthSession, str]:
    settings = get_settings()
    now = datetime.now(UTC)
    normalized = email.strip().lower()
    # DB locks serialize counters across workers; never trust forwarded client-IP headers.
    keys = sorted(
        [
            digest("email:" + normalized),
            digest("client:" + (request.client.host if request.client else "unknown")),
        ]
    )
    buckets = []
    for key in keys:
        session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(key[:15], 16)}
        )
        bucket = session.get(LoginBucket, key)
        if bucket is None:
            bucket = LoginBucket(key=key, failures=0, window_started_at=now)
            session.add(bucket)
        elif bucket.window_started_at <= now - timedelta(
            seconds=settings.login_window_seconds
        ):
            bucket.failures = 0
            bucket.window_started_at = now
        buckets.append(bucket)
    # Opportunistic retention: old, inactive throttle keys are not permanent identity records.
    session.execute(
        delete(LoginBucket).where(
            LoginBucket.window_started_at < now - timedelta(days=1)
        )
    )
    identity_key = digest("email:" + normalized)
    limited = any(
        b.failures >= (settings.login_max_failures if b.key == identity_key else 30)
        for b in buckets
    )
    if limited:
        record(session, request, "login_failed", "rate_limited")
        session.commit()
        raise HTTPException(
            429,
            "Unable to sign in. Try again later",
            headers={"Retry-After": str(settings.login_window_seconds)},
        )
    user = session.scalar(select(User).where(func.lower(User.email) == normalized))
    valid = verify_password(user.password_hash if user else None, password)
    if not valid or not user or not user.is_active or user.role not in PERMISSIONS:
        for bucket in buckets:
            bucket.failures += 1
        record(
            session,
            request,
            "login_failed",
            "denied",
            tenant_id=user.tenant_id if user else None,
            actor_id=user.id if user else None,
        )
        session.commit()
        raise HTTPException(401, "Invalid email or password")
    # Do not reset the client-wide counter on success (prevents bypass with a valid account).
    for bucket in buckets:
        if bucket.key == identity_key:
            bucket.failures = 0
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    previous = request.cookies.get(COOKIE_NAME, "")
    if 32 <= len(previous) <= 128:
        old = session.scalar(
            select(AuthSession)
            .where(
                AuthSession.token_hash == digest(previous),
                AuthSession.revoked_at.is_(None),
            )
            .with_for_update()
        )
        if old:
            old.revoked_at = now
            record(
                session,
                request,
                "session_revoked",
                "success",
                tenant_id=old.tenant_id,
                actor_id=old.user_id,
                resource_type="session",
                resource_id=old.id,
            )
    token = secrets.token_urlsafe(32)
    auth_session = AuthSession(
        tenant_id=user.tenant_id,
        user_id=user.id,
        token_hash=digest(token),
        created_at=now,
        expires_at=now + timedelta(seconds=settings.session_ttl_seconds),
    )
    session.add(auth_session)
    session.flush()
    record(
        session,
        request,
        "login_succeeded",
        "success",
        tenant_id=user.tenant_id,
        actor_id=user.id,
        resource_type="session",
        resource_id=auth_session.id,
    )
    session.commit()
    return user, auth_session, token


def revalidate_identity(session: Session, identity: Identity) -> Identity:
    """Revalidate a server session reference without accepting caller role assertions."""
    if identity.job_id is not None:
        # Internal worker capability; never populated by HTTP authentication or request schemas.
        from app.jobs.authority import revalidate_job_identity

        return revalidate_job_identity(session, identity)
    user = session.scalar(
        select(User)
        .join(
            AuthSession,
            (User.id == AuthSession.user_id)
            & (User.tenant_id == AuthSession.tenant_id),
        )
        .where(
            AuthSession.id == identity.session_id,
            AuthSession.user_id == identity.user_id,
            AuthSession.tenant_id == identity.tenant_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(UTC),
            User.is_active.is_(True),
        )
    )
    if user is None or user.role not in PERMISSIONS:
        raise HTTPException(401, "Authentication required")
    return Identity(user.id, user.tenant_id, cast(Role, user.role), identity.session_id)

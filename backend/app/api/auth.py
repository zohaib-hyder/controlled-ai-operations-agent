from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select

from app.core.config import get_settings
from app.core.permissions import Identity
from app.models.entities import AuthSession, User
from app.schemas.auth import CurrentUser, Login
from app.services.authentication import (
    COOKIE_NAME,
    IdentityDependency,
    SessionDependency,
    authenticate,
    require_origin,
)
from app.services.security_audit import record

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def describe(identity: Identity, user: User) -> CurrentUser:
    return CurrentUser(
        user_id=identity.user_id,
        tenant_id=identity.tenant_id,
        session_id=identity.session_id,
        email=user.email,
        role=identity.role,
        permissions=sorted(identity.permissions),
    )


@router.post(
    "/login", response_model=CurrentUser, dependencies=[Depends(require_origin)]
)
def login(
    body: Login, request: Request, response: Response, session: SessionDependency
) -> CurrentUser:
    user, auth_session, token = authenticate(
        session, request, body.email, body.password
    )
    settings = get_settings()
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.session_ttl_seconds,
        expires=auth_session.expires_at,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return describe(Identity(user.id, user.tenant_id, user.role, auth_session.id), user)


@router.get("/me", response_model=CurrentUser)
def me(identity: IdentityDependency, session: SessionDependency) -> CurrentUser:
    user = session.scalar(
        select(User).where(
            User.id == identity.user_id, User.tenant_id == identity.tenant_id
        )
    )
    return describe(identity, user)


@router.post("/logout", status_code=204, dependencies=[Depends(require_origin)])
def logout(
    request: Request,
    response: Response,
    identity: IdentityDependency,
    session: SessionDependency,
) -> None:
    auth_session = session.scalar(
        select(AuthSession)
        .where(
            AuthSession.id == identity.session_id,
            AuthSession.tenant_id == identity.tenant_id,
            AuthSession.user_id == identity.user_id,
        )
        .with_for_update()
    )
    auth_session.revoked_at = datetime.now(UTC)
    for event_type in ("session_revoked", "logout"):
        record(
            session,
            request,
            event_type,
            "success",
            tenant_id=identity.tenant_id,
            actor_id=identity.user_id,
            resource_type="session",
            resource_id=identity.session_id,
        )
    session.commit()
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        secure=get_settings().cookie_secure,
        httponly=True,
        samesite="lax",
    )

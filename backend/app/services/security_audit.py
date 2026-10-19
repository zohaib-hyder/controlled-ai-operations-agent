from uuid import UUID

from fastapi import Request
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.entities import SecurityEvent


@event.listens_for(SecurityEvent, "before_update")
@event.listens_for(SecurityEvent, "before_delete")
def prevent_event_mutation(mapper, connection, target):
    raise ValueError("Security audit events are append-only")


def record(
    session: Session,
    request: Request,
    event_type: str,
    outcome: str,
    *,
    tenant_id: UUID | None = None,
    actor_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
) -> None:
    session.add(
        SecurityEvent(
            tenant_id=tenant_id,
            actor_id=actor_id,
            event_type=event_type,
            outcome=outcome,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=UUID(request.state.request_id),
        )
    )

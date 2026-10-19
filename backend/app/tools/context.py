from dataclasses import dataclass
from datetime import datetime
from threading import Event
from uuid import UUID

from app.core.permissions import Identity, Permission, Role
from app.services.repository import TenantRepository


@dataclass(frozen=True, slots=True)
class ToolExecutionContext:
    user_id: UUID
    tenant_id: UUID
    role: Role
    permissions: frozenset[Permission]
    session_id: UUID
    correlation_id: UUID
    execution_id: UUID
    invoked_at: datetime


@dataclass(frozen=True, slots=True)
class ReadScope:
    context: ToolExecutionContext
    repository: TenantRepository
    stop: Event

    def check_cancelled(self) -> None:
        if self.stop.is_set():
            from app.tools.errors import ToolError

            raise ToolError("cancelled")

    @classmethod
    def for_context(cls, context: ToolExecutionContext, session, stop: Event):
        identity = Identity(
            context.user_id, context.tenant_id, context.role, context.session_id
        )
        return cls(context, TenantRepository(session, identity), stop)

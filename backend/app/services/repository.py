from dataclasses import dataclass
from typing import TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import Identity
from app.models.entities import Account, Customer, Policy, Ticket, Transaction

Entity = TypeVar("Entity", Customer, Account, Ticket, Transaction, Policy)


@dataclass(frozen=True)
class TenantRepository:
    session: Session
    identity: Identity

    def list(
        self, model: type[Entity], *, limit: int, offset: int
    ) -> tuple[list[Entity], int]:
        if not 1 <= limit <= 100 or not 0 <= offset <= 10000:
            raise ValueError("Pagination is out of bounds")
        scope = model.tenant_id == self.identity.tenant_id
        rows = list(
            self.session.scalars(
                select(model)
                .where(scope)
                .order_by(model.id)
                .limit(limit)
                .offset(offset)
            )
        )
        total = self.session.scalar(
            select(func.count()).select_from(model).where(scope)
        )
        return rows, total

    def get(self, model: type[Entity], resource_id: UUID) -> Entity | None:
        return self.session.scalar(
            select(model).where(
                model.tenant_id == self.identity.tenant_id, model.id == resource_id
            )
        )

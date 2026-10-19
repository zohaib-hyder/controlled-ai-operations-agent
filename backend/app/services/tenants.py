from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Account


def find_account(
    session: Session, *, tenant_id: UUID, account_id: UUID
) -> Account | None:
    """Internal data access only. Tenant ID is not authentication or authorization."""
    return session.scalar(
        select(Account).where(Account.tenant_id == tenant_id, Account.id == account_id)
    )

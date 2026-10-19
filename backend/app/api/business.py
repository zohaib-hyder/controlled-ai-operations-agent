from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.permissions import Identity
from app.models.entities import Account, Customer, Ticket
from app.schemas.business import (
    AccountView,
    CustomerView,
    Page,
    Pagination,
    TicketDetail,
    TicketView,
)
from app.services.authentication import SessionDependency, require_permission
from app.services.repository import TenantRepository
from app.services.security_audit import record

router = APIRouter(prefix="/api/v1", tags=["tenant data"])
CustomerReader = Annotated[Identity, Depends(require_permission("customer:read"))]
AccountReader = Annotated[Identity, Depends(require_permission("account:read"))]
TicketReader = Annotated[Identity, Depends(require_permission("ticket:read"))]
Paging = Annotated[Pagination, Query()]


def list_records(model, schema, identity, session, paging):
    rows, total = TenantRepository(session, identity).list(
        model, limit=paging.limit, offset=paging.offset
    )
    return Page(
        items=[schema.model_validate(row) for row in rows],
        total=total,
        limit=paging.limit,
        offset=paging.offset,
    )


def get_record(model, schema, resource_id, identity, session, request):
    row = TenantRepository(session, identity).get(model, resource_id)
    if row is None:
        # Do not probe other tenants to distinguish nonexistent IDs from cross-tenant IDs.
        record(
            session,
            request,
            "resource_access_denied",
            "denied",
            tenant_id=identity.tenant_id,
            actor_id=identity.user_id,
            resource_type=model.__tablename__,
            resource_id=resource_id,
        )
        session.commit()
        raise HTTPException(404, "Resource not found")
    return schema.model_validate(row)


@router.get("/customers", response_model=Page[CustomerView])
def customers(identity: CustomerReader, session: SessionDependency, paging: Paging):
    return list_records(Customer, CustomerView, identity, session, paging)


@router.get("/customers/{customer_id}", response_model=CustomerView)
def customer(
    customer_id: UUID,
    request: Request,
    identity: CustomerReader,
    session: SessionDependency,
):
    return get_record(Customer, CustomerView, customer_id, identity, session, request)


@router.get("/accounts", response_model=Page[AccountView])
def accounts(identity: AccountReader, session: SessionDependency, paging: Paging):
    return list_records(Account, AccountView, identity, session, paging)


@router.get("/accounts/{account_id}", response_model=AccountView)
def account(
    account_id: UUID,
    request: Request,
    identity: AccountReader,
    session: SessionDependency,
):
    return get_record(Account, AccountView, account_id, identity, session, request)


@router.get("/tickets", response_model=Page[TicketView])
def tickets(identity: TicketReader, session: SessionDependency, paging: Paging):
    return list_records(Ticket, TicketView, identity, session, paging)


@router.get("/tickets/{ticket_id}", response_model=TicketDetail)
def ticket(
    ticket_id: UUID,
    request: Request,
    identity: TicketReader,
    session: SessionDependency,
):
    return get_record(Ticket, TicketDetail, ticket_id, identity, session, request)

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Pagination(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)


class Entity(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", strict=True)
    id: UUID


class CustomerView(Entity):
    name: str


class AccountView(Entity):
    customer_id: UUID
    status: str
    block_reason: str | None
    evidence_version: int


class TicketView(Entity):
    account_id: UUID
    subject: str
    status: str
    duplicate_of_id: UUID | None


class TicketDetail(TicketView):
    body: str


class Page[T](BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    items: list[T]
    total: int
    limit: int
    offset: int

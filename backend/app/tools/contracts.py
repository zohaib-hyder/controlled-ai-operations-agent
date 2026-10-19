from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)


class Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, hide_input_in_errors=True
    )


class CustomerInput(Contract):
    customer_id: UUID


class AccountInput(Contract):
    account_id: UUID


class TicketInput(Contract):
    ticket_id: UUID


class CustomerTicketsInput(CustomerInput):
    limit: int = Field(default=10, ge=1, le=20)


class TransactionsInput(AccountInput):
    limit: int = Field(default=10, ge=1, le=20)


class PolicyInput(Contract):
    query: str = Field(min_length=2, max_length=240)
    limit: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def meaningful_query(cls, value: str) -> str:
        import re

        if not re.search(r"[a-zA-Z0-9]{2,}", value):
            raise ValueError("Supply a keyword with at least two letters/digits")
        return value.strip()


class CustomerOutput(Contract):
    customer_id: UUID
    name: str = Field(max_length=120)
    updated_at: datetime


class AccountOutput(Contract):
    account_id: UUID
    customer_id: UUID
    status: Literal["active", "blocked", "inactive"]
    block_reason: str | None = Field(max_length=120)
    evidence_version: int = Field(ge=1)
    updated_at: datetime


class TicketOutput(Contract):
    ticket_id: UUID
    account_id: UUID
    status: Literal["open", "closed"]
    category: Literal[
        "billing",
        "security",
        "duplicate",
        "reactivation",
        "evidence_conflict",
        "service",
    ]
    summary: str = Field(max_length=400)
    duplicate_of_id: UUID | None
    updated_at: datetime
    evidence_untrusted: Literal[True] = True


class TicketsOutput(Contract):
    customer_id: UUID
    items: list[TicketOutput] = Field(max_length=20)
    limit: int = Field(ge=1, le=20)


class TransactionSummary(Contract):
    updated_at: datetime | None = None
    transaction_id: UUID
    amount_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    status: Literal["paid", "unpaid", "disputed"]
    created_at: datetime


class TransactionsOutput(Contract):
    account_id: UUID
    items: list[TransactionSummary] = Field(max_length=20)
    limit: int = Field(ge=1, le=20)


class PolicyMatch(Contract):
    policy_id: UUID
    version: int = Field(ge=1)
    title: str = Field(max_length=120)
    summary: str = Field(max_length=400)
    relevance: int = Field(ge=1, le=8)
    key: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=40)
    resource_type: str | None = Field(default=None, max_length=40)
    effective_at: datetime | None = None
    expires_at: datetime | None = None
    updated_at: datetime | None = None
    account_states: list[str] = Field(default_factory=list, max_length=10)
    scenarios: list[str] = Field(default_factory=list, max_length=10)
    policy_status: Literal["current", "unknown"] = "unknown"


class PoliciesOutput(Contract):
    items: list[PolicyMatch] = Field(max_length=20)
    limit: int = Field(ge=1, le=20)
    evidence_untrusted: Literal[True] = True


class Invocation(Contract):
    tool_name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    tool_version: str = Field(min_length=1, max_length=20)
    mode: Literal["read"] = "read"
    arguments: dict[str, JsonValue]


class SafeError(Contract):
    code: str
    message: str


class Result(Contract):
    execution_id: UUID
    tool_name: str
    tool_version: str
    status: Literal["success", "error", "cancelled"]
    data: dict[str, JsonValue] | None
    error: SafeError | None
    started_at: datetime
    completed_at: datetime
    duration_ms: float = Field(ge=0)
    correlation_id: UUID

    @model_validator(mode="after")
    def consistent(self):
        if (self.status == "success") != (self.data is not None and self.error is None):
            raise ValueError("Result payload does not match status")
        if self.status != "success" and (self.data is not None or self.error is None):
            raise ValueError("Failures require only a safe error")
        return self


class ToolDescription(Contract):
    name: str
    version: str
    description: str
    input_schema: dict[str, JsonValue]
    output_schema: dict[str, JsonValue]
    required_permission: str
    classification: Literal["read"]
    timeout_seconds: float
    max_result_bytes: int

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.actions import DecisionReceipt
from app.schemas.evidence import SourceEvidence
from app.tools.contracts import Contract, JsonValue

ApprovalState = Literal[
    "PENDING", "APPROVED", "REJECTED", "EXPIRED", "CANCELLED", "INVALIDATED"
]
TRANSITIONS = {
    "PENDING": frozenset(
        {"APPROVED", "REJECTED", "EXPIRED", "CANCELLED", "INVALIDATED"}
    ),
    "APPROVED": frozenset({"EXPIRED", "CANCELLED", "INVALIDATED"}),
}


def transition(source: str, target: str):
    if target not in TRANSITIONS.get(source, frozenset()):
        raise ValueError("Invalid approval transition")
    return target


class EmptyCommand(Contract):
    pass


class ApprovalCommand(Contract):
    reason: str = Field(min_length=5, max_length=300)


class ExecuteCommand(Contract):
    decision_id: UUID
    approval_id: UUID | None = None

    @field_validator("decision_id", "approval_id", mode="before")
    @classmethod
    def parse_id(cls, value):
        return UUID(value) if isinstance(value, str) else value


class ApprovalItem(Contract):
    approval_id: UUID
    proposal_id: UUID
    status: ApprovalState
    requested_by: UUID
    expires_at: datetime


class ApprovalQueue(Contract):
    items: tuple[ApprovalItem, ...] = Field(max_length=50)


class ReviewRecord(Contract):
    status: ApprovalState
    reason: str = Field(max_length=300)
    actor_id: UUID
    created_at: datetime


class ApprovalDetail(ApprovalItem):
    tenant_id: UUID
    decision_id: UUID
    reviewer_id: UUID | None
    consumed: bool
    action_name: str = Field(max_length=80)
    target_resource_id: UUID
    receipt: DecisionReceipt
    decisions: tuple[ReviewRecord, ...] = Field(max_length=20)
    sources: tuple[SourceEvidence, ...] = Field(default=(), max_length=80)
    error_code: str | None = Field(default=None, max_length=80)


class ExecutionEvent(Contract):
    type: str = Field(max_length=60)
    correlation_id: UUID
    created_at: datetime


class ExecutionReceipt(Contract):
    status: Literal["COMMITTED", "FAILED", "DENIED"]
    verified: bool
    replayed: bool = False
    error_code: str | None = Field(default=None, max_length=80)
    execution_id: UUID | None = None
    proposal_id: UUID | None = None
    approval_id: UUID | None = None
    actor_id: UUID | None = None
    tenant_id: UUID | None = None
    action_name: str | None = Field(default=None, max_length=80)
    action_version: str | None = Field(default=None, max_length=20)
    target_resource_id: UUID | None = None
    canonical_arguments_hash: str | None = None
    decision_id: UUID | None = None
    before: dict[str, JsonValue] = Field(default_factory=dict, max_length=10)
    after: dict[str, JsonValue] = Field(default_factory=dict, max_length=10)
    created_at: datetime | None = None
    idempotency_key: str | None = Field(default=None, max_length=80)
    events: tuple[ExecutionEvent, ...] = Field(default=(), max_length=20)

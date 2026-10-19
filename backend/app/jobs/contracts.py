from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.execution import ExecuteCommand
from app.tools.contracts import Contract

State = Literal[
    "QUEUED",
    "CLAIMED",
    "RUNNING",
    "RETRY_SCHEDULED",
    "RECONCILIATION_REQUIRED",
    "COMPLETED",
    "FAILED",
    "DEAD_LETTERED",
    "CANCELLED",
]
TRANSITIONS = {
    "QUEUED": {"CLAIMED", "CANCELLED"},
    "CLAIMED": {
        "RUNNING",
        "RETRY_SCHEDULED",
        "CANCELLED",
        "RECONCILIATION_REQUIRED",
        "DEAD_LETTERED",
    },
    "RUNNING": {
        "CANCELLED",
        "COMPLETED",
        "FAILED",
        "RETRY_SCHEDULED",
        "RECONCILIATION_REQUIRED",
        "DEAD_LETTERED",
    },
    "RETRY_SCHEDULED": {"CLAIMED", "CANCELLED"},
    "RECONCILIATION_REQUIRED": {
        "COMPLETED",
        "FAILED",
        "RETRY_SCHEDULED",
        "DEAD_LETTERED",
    },
    # Only the authorized explicit retry operation can use this transition.
    "DEAD_LETTERED": {"RETRY_SCHEDULED"},
}


class Submit(ExecuteCommand):
    proposal_id: UUID

    @field_validator("proposal_id", mode="before")
    @classmethod
    def parse_proposal(cls, v):
        return UUID(v) if isinstance(v, str) else v


class JobView(Contract):
    id: UUID
    proposal_id: UUID
    actor_id: UUID
    action_name: str = Field(max_length=80)
    action_version: str = Field(max_length=20)
    status: State
    attempt_count: int
    max_attempts: int
    next_run_at: datetime
    created_at: datetime
    updated_at: datetime
    lease_expires_at: datetime | None
    receipt_id: UUID | None
    last_error: str | None
    age_seconds: float
    can_cancel: bool
    can_retry: bool


class JobList(Contract):
    items: tuple[JobView, ...] = Field(max_length=50)
    queue_depth: int
    oldest_age_seconds: float


class AttemptView(Contract):
    number: int
    fence: int
    correlation_id: UUID
    outcome: str
    error_category: str | None
    created_at: datetime
    finished_at: datetime | None


class Attempts(Contract):
    items: tuple[AttemptView, ...] = Field(max_length=100)


class EventView(Contract):
    state: State
    category: str
    correlation_id: UUID
    created_at: datetime


class Events(Contract):
    items: tuple[EventView, ...] = Field(max_length=200)

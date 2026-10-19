from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from app.agents.checkpoints import Counters
from app.agents.contracts import InvestigationResult, State
from app.tools.contracts import Contract


class InvestigationView(InvestigationResult):
    version: int
    customer_id: UUID
    ticket_id: UUID | None
    created_at: datetime
    updated_at: datetime
    checkpoint_sequence: int
    checkpoint_valid: bool
    recovery_attempts: int
    cancel_requested: bool
    lease_expires_at: datetime | None
    recovery_available: bool
    planner_type: str
    planner_version: str
    budget_counters: Counters


class HistoryQuery(Contract):
    model_config = ConfigDict(extra="forbid", strict=False)
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=10000)
    status: State | None = None
    customer_id: UUID | None = None


class SequenceQuery(Contract):
    model_config = ConfigDict(extra="forbid", strict=False)
    limit: int = Field(default=50, ge=1, le=100)
    after: int = Field(default=0, ge=0, le=1000000)


class ControlRequest(Contract):
    pass

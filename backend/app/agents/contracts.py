from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.evidence import Reconciliation, SourceEvidence
from app.schemas.planning import SelectionTrace
from app.tools.contracts import Contract, Invocation


class State(StrEnum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"


TERMINAL = frozenset(State) - {State.CREATED, State.PLANNING, State.RUNNING}
TRANSITIONS = {
    State.CREATED: {State.PLANNING, State.FAILED, State.CANCELLED},
    State.PLANNING: {
        State.RUNNING,
        State.FAILED,
        State.CANCELLED,
        State.BUDGET_EXCEEDED,
    },
    State.RUNNING: set(TERMINAL),
}


def transition(current: State, target: State) -> State:
    if target not in TRANSITIONS.get(current, set()):
        raise ValueError("Invalid investigation state transition")
    return target


class InvestigationContext(Contract):
    operator_note: str = Field(default="", max_length=500)


class InvestigationRequest(Contract):
    goal: str = Field(min_length=5, max_length=1000, pattern=r"\S")
    customer_id: UUID
    ticket_id: UUID | None = None
    context: InvestigationContext | None = None

    @field_validator("customer_id", "ticket_id", mode="before")
    @classmethod
    def json_uuid(cls, value):
        # FastAPI parses JSON to Python first; bridge only JSON UUID strings.
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                raise ValueError("Invalid resource identifier") from None
        return value


class Limits(Contract):
    max_no_progress: int = Field(default=1, ge=1, le=3)
    provider_requests: int = Field(default=8, ge=1, le=20)
    provider_output_tokens: int = Field(default=8192, ge=1, le=65536)
    provider_cost_microusd: int = Field(default=100000, ge=1, le=100000000)
    max_steps: int = Field(default=8, ge=1, le=20)
    max_tool_calls: int = Field(default=8, ge=1, le=20)
    wall_seconds: float = Field(default=8.0, gt=0, le=30)
    max_repeats: int = Field(default=1, ge=1, le=2)
    observation_bytes: int = Field(default=48000, ge=128, le=100000)
    planning_iterations: int = Field(default=8, ge=1, le=20)


class Step(Contract):
    step_id: str = Field(min_length=1, max_length=40)
    invocation: Invocation
    purpose: str = Field(min_length=1, max_length=200)
    expected_evidence: str = Field(min_length=1, max_length=200)
    status: Literal["proposed", "succeeded", "failed"] = "proposed"


class Plan(Contract):
    steps: tuple[Step, ...] = Field(max_length=20)


class Evidence(Contract):
    sources: tuple[SourceEvidence, ...] = Field(default=(), max_length=20)
    evidence_id: UUID
    tool_execution_id: UUID
    tool_name: str
    tool_version: str
    source_reference: str = Field(max_length=160)
    source_references: tuple[str, ...] = Field(max_length=20)
    summary: str = Field(max_length=400)
    collected_at: datetime
    validation_status: Literal["schema_validated"] = "schema_validated"


class Finding(Contract):
    text: str = Field(max_length=400)
    evidence_ids: tuple[UUID, ...] = Field(min_length=1, max_length=20)


class Interpretation(Contract):
    scenario: Literal[
        "billing", "security", "duplicate", "reactivation", "conflict", "unknown"
    ]


class Recommendation(Contract):
    next_steps: tuple[str, ...] = Field(max_length=4)
    uncertainty: tuple[str, ...] = Field(max_length=4)
    human_review: bool = True


class InvestigationResult(Contract):
    tool_selection_trace: tuple[SelectionTrace, ...] = Field(default=(), max_length=64)
    iteration_count: int = Field(default=0, ge=0, le=20)
    execution_limits: Limits | None = None
    reconciliation: Reconciliation | None = None
    investigation_id: UUID
    goal: str
    status: State
    history: tuple[State, ...]
    steps: tuple[Step, ...]
    evidence: tuple[Evidence, ...]
    findings: tuple[Finding, ...]
    recommended_next_steps: tuple[str, ...]
    uncertainty: tuple[str, ...]
    stop_reason: str
    tool_calls_performed: int
    duration_ms: float
    human_review_recommended: bool
    correlation_id: UUID

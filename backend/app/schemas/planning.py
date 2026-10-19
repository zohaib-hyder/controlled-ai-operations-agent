"""Planner proposals are untrusted data, never authority to execute."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, TypeAdapter

from app.schemas.evidence import GroundedFinding, SourceEvidence
from app.tools.contracts import Contract, Invocation, JsonValue, ToolDescription


class CallTool(Contract):
    kind: Literal["CALL_TOOL"] = "CALL_TOOL"
    invocation: Invocation
    step_id: str = Field(min_length=1, max_length=40)
    purpose: str = Field(min_length=1, max_length=200)
    expected_evidence: str = Field(min_length=1, max_length=200)


class Finish(Contract):
    kind: Literal["FINISH"] = "FINISH"
    findings: tuple[GroundedFinding, ...] = Field(max_length=40)
    evidence_ids: tuple[UUID, ...] = Field(max_length=80)
    advisory_recommendation: tuple[str, ...] = Field(min_length=1, max_length=4)
    uncertainty: tuple[str, ...] = Field(min_length=1, max_length=4)


class Escalate(Contract):
    kind: Literal["ESCALATE"] = "ESCALATE"
    reason: Literal[
        "security_review_required", "conflicting_evidence", "human_review_required"
    ]
    evidence_ids: tuple[UUID, ...] = Field(min_length=1, max_length=80)
    required_follow_up: str = Field(min_length=1, max_length=200)


class Insufficient(Contract):
    kind: Literal["STOP_INSUFFICIENT_EVIDENCE"] = "STOP_INSUFFICIENT_EVIDENCE"
    reason: Literal["missing_evidence", "unsupported_scenario"]
    evidence_ids: tuple[UUID, ...] = Field(max_length=80)


Decision = Annotated[
    CallTool | Finish | Escalate | Insufficient, Field(discriminator="kind")
]
DECISION = TypeAdapter(Decision)


class PlannerContext(Contract):
    allowed_advisories: tuple[str, ...] = Field(default=(), max_length=6)
    required_uncertainty: str = Field(
        default="Read-only observations do not constitute policy evaluation or authorization to change an account.",
        max_length=200,
    )
    goal: str = Field(max_length=1000)
    resource_identifiers: dict[str, UUID] = Field(max_length=3)
    available_tools: tuple[ToolDescription, ...] = Field(max_length=6)
    completed_calls: tuple[Invocation, ...] = Field(max_length=20)
    observations: dict[str, dict[str, JsonValue]] = Field(max_length=6)
    evidence: tuple[SourceEvidence, ...] = Field(max_length=400)
    remaining_budgets: dict[str, JsonValue] = Field(max_length=15)
    state: Literal["RUNNING"] = "RUNNING"


class SelectionTrace(Contract):
    iteration: int = Field(ge=0, le=20)
    decision_type: Literal[
        "CALL_TOOL", "FINISH", "ESCALATE", "STOP_INSUFFICIENT_EVIDENCE", "STOP"
    ]
    summary: str = Field(max_length=240)
    selected_tool: str | None = Field(default=None, max_length=64)
    arguments_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    step_id: str | None = Field(default=None, max_length=40)
    tool_execution_id: UUID | None = None
    observation_id: UUID | None = None
    evidence_ids: tuple[UUID, ...] = Field(default=(), max_length=80)
    validation_outcome: Literal[
        "validated", "rejected", "executed", "failed", "stopped"
    ]
    budget_consumption: dict[str, JsonValue] = Field(max_length=15)
    stop_reason: str | None = Field(default=None, max_length=80)
    timestamp: datetime

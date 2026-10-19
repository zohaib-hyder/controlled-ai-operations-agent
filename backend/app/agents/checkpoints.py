"""Versioned recovery data; never executable instructions."""

import json
from collections import Counter
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.agents.contracts import (
    Evidence,
    Finding,
    Limits,
    Plan,
    State,
    Step,
    transition,
)
from app.schemas.planning import SelectionTrace
from app.tools.contracts import Contract, JsonValue
from app.tools.handlers import build_registry

MAX_CHECKPOINT_BYTES = 131072


class Counters(Contract):
    provider_requests: int = Field(default=0, ge=0, le=20)
    provider_output_tokens_reserved: int = Field(default=0, ge=0, le=65536)
    provider_cost_microusd_reserved: int = Field(default=0, ge=0, le=100000000)
    no_progress: int = Field(default=0, ge=0, le=20)
    tool_calls: int = Field(default=0, ge=0, le=20)
    planning_iterations: int = Field(default=0, ge=0, le=20)
    observation_bytes: int = Field(default=0, ge=0, le=100000)
    elapsed_ms: float = Field(default=0.0, ge=0)
    repetitions: dict[str, int] = Field(default_factory=dict, max_length=20)


class Snapshot(Contract):
    tool_selection_trace: tuple[SelectionTrace, ...] = Field(default=(), max_length=64)
    observation_fingerprints: tuple[str, ...] = Field(default=(), max_length=20)
    planner_config_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    schema_version: Literal[1] = 1
    planner_type: Literal["deterministic_mock", "openai_compatible"] = (
        "deterministic_mock"
    )
    planner_version: Literal["1.0", "2.0"] = "1.0"
    state: State
    history: tuple[State, ...] = Field(min_length=1, max_length=8)
    phase: Literal[
        "created",
        "state_changed",
        "planning",
        "plan_validated",
        "before_tool",
        "after_observation",
        "final",
    ]
    step_index: int = Field(ge=0, le=20)
    plan_reference: UUID
    plan: Plan | None = None
    steps: tuple[Step, ...] = Field(default=(), max_length=20)
    completed_step_ids: tuple[str, ...] = Field(default=(), max_length=20)
    counters: Counters
    limits: Limits
    observations: dict[str, dict[str, JsonValue]] = Field(
        default_factory=dict, max_length=6
    )
    evidence_ids: tuple[UUID, ...] = Field(default=(), max_length=20)
    last_event_sequence: int = Field(ge=1)
    recovery_error: Literal["corrupt_checkpoint"] | None = None
    recovery_attempts: int = Field(default=0, ge=0, le=20)
    inflight_step: str | None = Field(default=None, max_length=40)
    correlation_id: UUID

    @model_validator(mode="after")
    def consistent(self):
        if self.history[0] != State.CREATED or self.history[-1] != self.state:
            raise ValueError("Invalid checkpoint history")
        for current, target in zip(self.history, self.history[1:], strict=False):
            transition(current, target)
        if self.step_index != len(self.steps) or len(
            {s.step_id for s in self.steps}
        ) != len(self.steps):
            raise ValueError("Invalid step index")
        if self.completed_step_ids != tuple(
            s.step_id for s in self.steps if s.status == "succeeded"
        ):
            raise ValueError("Invalid completed references")
        if self.counters.tool_calls != len(self.steps) or len(self.evidence_ids) != len(
            self.completed_step_ids
        ):
            raise ValueError("Invalid checkpoint counters/evidence")
        if self.inflight_step is not None and (
            not self.steps
            or self.steps[-1].step_id != self.inflight_step
            or self.steps[-1].status != "proposed"
        ):
            raise ValueError("Invalid in-flight marker")
        expected = Counter(
            step.invocation.tool_name
            + json.dumps(
                step.invocation.arguments, sort_keys=True, separators=(",", ":")
            )
            for step in self.steps
        )
        if dict(expected) != self.counters.repetitions or len(
            set(self.evidence_ids)
        ) != len(self.evidence_ids):
            raise ValueError("Invalid replay counters or evidence identifiers")
        registry = build_registry()
        for step in (*self.steps, *(self.plan.steps if self.plan else ())):
            definition = registry.resolve(
                step.invocation.tool_name, step.invocation.tool_version
            )
            definition.input_model.model_validate_json(
                json.dumps(step.invocation.arguments), strict=True
            )
            if definition.classification != "read":
                raise ValueError("Checkpoint references non-read tool")
        if any(count > self.limits.max_repeats for count in expected.values()):
            raise ValueError("Replay counters exceed limits")
        for name, data in self.observations.items():
            registry.resolve(name, "1.0").output_model.model_validate_json(
                json.dumps(data), strict=True
            )
        if len(self.model_dump_json().encode()) > MAX_CHECKPOINT_BYTES:
            raise ValueError("Checkpoint too large")
        return self


def minimize(observations: dict) -> dict:
    result = json.loads(json.dumps(observations))
    if "get_customer" in result:
        result["get_customer"]["name"] = "Customer identity verified"
    if "get_ticket" in result:
        result["get_ticket"]["summary"] = "Source prose omitted from checkpoint"
    for ticket in result.get("list_customer_tickets", {}).get("items", []):
        ticket["summary"] = "Source prose omitted from checkpoint"
    for policy in result.get("search_policy", {}).get("items", []):
        policy["title"] = "Policy evidence"
        policy["summary"] = "Source prose omitted from checkpoint"
    return result


def checkpoint_evidence_findings(evidence: list[Evidence]) -> list[Finding]:
    return [
        Finding(text=item.summary, evidence_ids=(item.evidence_id,))
        for item in evidence
    ]

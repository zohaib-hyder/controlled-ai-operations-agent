"""Additive, strict evidence contracts; legacy envelopes remain readable."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.tools.contracts import Contract, JsonValue


class SourceEvidence(Contract):
    evidence_id: UUID
    investigation_id: UUID
    tenant_id: UUID
    source_type: Literal["customer", "account", "ticket", "transaction", "policy"]
    source_resource_id: UUID
    source_reference: str = Field(max_length=160)
    source_version: int | None = Field(default=None, ge=1)
    source_updated_at: datetime | None = None
    tool_execution_id: UUID
    collected_at: datetime
    facts: dict[str, JsonValue] = Field(max_length=20)
    summary: str = Field(max_length=400)
    freshness: Literal["CURRENT", "STALE", "UNKNOWN"]
    historical: bool = False
    evidence_status: Literal["schema_validated"] = "schema_validated"
    retrieval_metadata: dict[str, JsonValue] = Field(max_length=20)

    @model_validator(mode="after")
    def verify_reference(self):
        expected = f"{self.source_type}:{self.source_resource_id}" + (
            f":v{self.source_version}" if self.source_version else ""
        )
        if self.source_reference != expected:
            raise ValueError("Source reference does not match resource/version")
        return self


class Conflict(Contract):
    conflict_id: UUID
    conflict_type: str = Field(max_length=80)
    evidence_ids: tuple[UUID, ...] = Field(min_length=1, max_length=80)
    severity: Literal["warning", "high"]
    explanation: str = Field(max_length=400)
    required_follow_up: str = Field(max_length=400)


class Gap(Contract):
    gap_id: UUID
    kind: str = Field(max_length=80)
    explanation: str = Field(max_length=400)


class GroundedFinding(Contract):
    kind: Literal["observed_fact", "inference", "uncertainty", "advisory"]
    text: str = Field(max_length=400)
    evidence_ids: tuple[UUID, ...] = Field(max_length=80)


class Reconciliation(Contract):
    conflicts: tuple[Conflict, ...] = Field(default=(), max_length=20)
    gaps: tuple[Gap, ...] = Field(default=(), max_length=20)
    grounded_findings: tuple[GroundedFinding, ...] = Field(default=(), max_length=420)

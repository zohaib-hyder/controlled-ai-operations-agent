from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.tools.contracts import Contract, JsonValue


class ProposalInput(Contract):
    investigation_id: UUID
    action_name: str = Field(min_length=1, max_length=80)
    action_version: str = Field(default="1.0", min_length=1, max_length=20)
    target_resource_id: UUID
    arguments: dict[str, JsonValue] = Field(default_factory=dict, max_length=5)
    evidence_references: tuple[UUID, ...] = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=5, max_length=500)

    @field_validator("investigation_id", "target_resource_id", mode="before")
    @classmethod
    def parse_id(cls, value):
        return UUID(value) if isinstance(value, str) else value

    @field_validator("evidence_references", mode="before")
    @classmethod
    def parse_references(cls, value):
        if isinstance(value, (list, tuple)):
            return tuple(UUID(v) if isinstance(v, str) else v for v in value)
        return value

    @field_validator("evidence_references")
    @classmethod
    def unique_references(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Duplicate evidence references")
        return value


class TrustedProposal(ProposalInput):
    proposal_id: UUID
    actor_id: UUID
    tenant_id: UUID
    created_at: datetime


Decision = Literal["ALLOW", "REQUIRE_APPROVAL", "DENY"]


class PolicyBinding(Contract):
    id: UUID
    version: int = Field(ge=1)
    key: str = Field(max_length=100)
    binding: str = Field(pattern=r"^[a-f0-9]{64}$")


class DecisionReceipt(Contract):
    decision_id: UUID
    proposal_id: UUID
    tenant_id: UUID
    actor_id: UUID
    investigation_id: UUID
    action_name: str = Field(max_length=80)
    action_version: str = Field(max_length=20)
    target_resource_id: UUID
    resource_type: Literal["customer", "account", "ticket", "unknown"]
    canonical_arguments_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    decision: Decision
    rule_identifiers: tuple[str, ...] = Field(max_length=20)
    policy_versions: tuple[PolicyBinding, ...] = Field(max_length=20)
    evidence_references: tuple[UUID, ...] = Field(max_length=80)
    resource_versions: dict[str, str] = Field(max_length=100)
    actor_permissions: tuple[str, ...] = Field(max_length=40)
    reason_codes: tuple[str, ...] = Field(max_length=40)
    created_at: datetime
    expires_at: datetime
    execution_authorized: Literal[False] = False


class ProposalEvaluation(Contract):
    proposal: TrustedProposal
    receipt: DecisionReceipt
    status: Literal["ALLOWED", "APPROVAL REQUIRED", "DENIED", "STALE"]
    stale_reasons: tuple[str, ...] = Field(max_length=10)
    execution_authorized: Literal[False] = False

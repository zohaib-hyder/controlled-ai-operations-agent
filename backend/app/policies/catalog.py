"""Static evaluation catalog. Nothing here grants execution permissions."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.tools.contracts import Contract


class NoteArguments(Contract):
    content: str = Field(min_length=5, max_length=500)


class EmptyArguments(Contract):
    pass


class DuplicateArguments(Contract):
    duplicate_of_id: UUID


@dataclass(frozen=True)
class Action:
    name: str
    resource_type: Literal["customer", "account", "ticket"]
    schema: type[Contract]
    required_evidence: tuple[str, ...]
    approval: bool
    risk: str
    rules: tuple[str, ...]
    prohibited: tuple[str, ...]
    description: str
    version: str = "1.0"

    @property
    def permission(self):
        return f"action:{self.name}:propose"

    def public(self):
        return dict(
            name=self.name,
            version=self.version,
            description=self.description,
            resource_type=self.resource_type,
            input_schema=self.schema.model_json_schema(),
            required_permission=self.permission,
            required_evidence=self.required_evidence,
            approval_required=self.approval,
            risk=self.risk,
            eligibility_rules=self.rules,
            prohibited_conditions=self.prohibited,
            execution_available=False,
        )


CATALOG = MappingProxyType(
    {
        a.name: a
        for a in (
            Action(
                "create_customer_note",
                "customer",
                NoteArguments,
                ("customer",),
                False,
                "low",
                ("tenant_owned", "verified_evidence", "safe_content"),
                ("prohibited_content",),
                "Evaluate a customer note; does not save a note.",
            ),
            Action(
                "add_ticket_note",
                "ticket",
                NoteArguments,
                ("ticket",),
                False,
                "low",
                ("tenant_owned", "verified_evidence", "ticket_open", "safe_content"),
                ("prohibited_content", "closed_ticket"),
                "Evaluate an open-ticket note.",
            ),
            Action(
                "request_account_reactivation",
                "account",
                EmptyArguments,
                ("account", "transaction", "policy"),
                True,
                "medium",
                (
                    "account_blocked",
                    "clear_billing",
                    "clear_security",
                    "consistent_evidence",
                    "current_policy",
                ),
                ("security_hold", "unresolved_payment", "evidence_conflict"),
                "Evaluate a reactivation review request.",
            ),
            Action(
                "reactivate_account",
                "account",
                EmptyArguments,
                ("account", "transaction", "policy"),
                True,
                "high",
                (
                    "account_blocked",
                    "eligible_block",
                    "clear_billing",
                    "clear_security",
                    "consistent_evidence",
                    "current_policy",
                ),
                ("security_hold", "unresolved_payment", "evidence_conflict"),
                "Evaluate eligibility only; never reactivate an account.",
            ),
            Action(
                "close_duplicate_ticket",
                "ticket",
                DuplicateArguments,
                ("ticket", "policy"),
                True,
                "medium",
                ("ticket_open", "verified_duplicate", "current_policy"),
                ("unsupported_duplicate", "closed_ticket"),
                "Evaluate closure of a verified duplicate.",
            ),
            Action(
                "override_security_block",
                "account",
                EmptyArguments,
                ("account",),
                False,
                "critical",
                ("override_forbidden",),
                ("always_prohibited",),
                "Security overrides are always denied.",
            ),
        )
    }
)

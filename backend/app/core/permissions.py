from dataclasses import dataclass
from typing import Literal
from uuid import UUID

Role = Literal["operator", "reviewer", "admin", "auditor"]
Permission = Literal[
    "action:approve",
    "action:execute",
    "action:create_customer_note:propose",
    "action:add_ticket_note:propose",
    "action:request_account_reactivation:propose",
    "action:reactivate_account:propose",
    "action:close_duplicate_ticket:propose",
    "action:override_security_block:propose",
    "customer:read",
    "account:read",
    "ticket:read",
    "investigation:create",
    "approval:review",
    "user:manage",
    "audit:read",
    "settings:manage",
]
READ: frozenset[Permission] = frozenset(
    {"customer:read", "account:read", "ticket:read"}
)
ACTION_PROPOSALS: frozenset[Permission] = frozenset(
    {
        "action:create_customer_note:propose",
        "action:add_ticket_note:propose",
        "action:request_account_reactivation:propose",
        "action:reactivate_account:propose",
        "action:close_duplicate_ticket:propose",
        "action:override_security_block:propose",
    }
)
OPERATOR = READ | {"investigation:create"} | ACTION_PROPOSALS
REVIEWER = OPERATOR | {"approval:review"}
PERMISSIONS: dict[str, frozenset[Permission]] = {
    "operator": OPERATOR | {"action:execute"},
    "reviewer": REVIEWER | {"action:approve"},
    "admin": REVIEWER
    | {
        "action:approve",
        "action:execute",
        "user:manage",
        "audit:read",
        "settings:manage",
    },
    "auditor": READ | {"audit:read"},
}


@dataclass(frozen=True)
class Identity:
    user_id: UUID
    tenant_id: UUID
    role: Role
    session_id: UUID

    job_id: UUID | None = None
    job_fence: int | None = None
    job_owner: str | None = None

    @property
    def permissions(self) -> frozenset[Permission]:
        return PERMISSIONS.get(self.role, frozenset())

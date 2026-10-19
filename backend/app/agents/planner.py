from abc import ABC, abstractmethod

from app.agents.contracts import (
    Interpretation,
    InvestigationRequest,
    Plan,
    Recommendation,
    Step,
)
from app.tools.contracts import Invocation


def step(name: str, arguments: dict, purpose: str) -> Step:
    return Step(
        step_id=name,
        invocation=Invocation(tool_name=name, tool_version="1.0", arguments=arguments),
        purpose=purpose,
        expected_evidence="Validated tenant-scoped structured records",
    )


class AgentPlanner(ABC):
    mode = "deterministic_mock"
    planner_version = "2.0"
    config_hash = None

    async def decide(self, request, context):
        from app.schemas.evidence import GroundedFinding
        from app.schemas.planning import CallTool, Escalate, Finish, Insufficient

        proposed = await self.next_step(request, context.observations)
        if proposed is not None:
            if not isinstance(proposed, Step):
                raise ValueError("Invalid planner step")
            return CallTool(
                invocation=proposed.invocation,
                step_id=proposed.step_id,
                purpose=proposed.purpose,
                expected_evidence=proposed.expected_evidence,
            )
        safe = DeterministicMockPlanner()
        advice = await safe.recommend(await safe.interpret(context.observations))
        refs = tuple(e.evidence_id for e in context.evidence[:80])
        if any(
            not context.observations.get(name, {}).get("items")
            for name in ("list_recent_transactions", "search_policy")
        ):
            return Insufficient(reason="missing_evidence", evidence_ids=refs)
        scenario = (await safe.interpret(context.observations)).scenario
        if scenario in {"security", "conflict"}:
            return Escalate(
                reason="security_review_required"
                if scenario == "security"
                else "conflicting_evidence",
                evidence_ids=refs,
                required_follow_up=advice.next_steps[0],
            )
        facts = tuple(
            GroundedFinding(
                kind="observed_fact", text=e.summary, evidence_ids=(e.evidence_id,)
            )
            for e in context.evidence[:40]
        )
        return Finish(
            findings=facts,
            evidence_ids=tuple(e.evidence_id for e in context.evidence[:80]),
            advisory_recommendation=advice.next_steps,
            uncertainty=advice.uncertainty,
        )

    @abstractmethod
    async def initial_plan(self, request: InvestigationRequest) -> Plan: ...

    @abstractmethod
    async def next_step(
        self, request: InvestigationRequest, observations: dict
    ) -> Step | None: ...

    @abstractmethod
    async def interpret(self, observations: dict) -> Interpretation: ...

    @abstractmethod
    async def recommend(self, interpretation: Interpretation) -> Recommendation: ...


class DeterministicMockPlanner(AgentPlanner):
    """Only structured status fields influence planning. Text is never instruction input."""

    async def initial_plan(self, request):
        return Plan(
            steps=(
                step(
                    "get_customer",
                    {"customer_id": str(request.customer_id)},
                    "Verify customer ownership",
                ),
                step(
                    "list_customer_tickets",
                    {"customer_id": str(request.customer_id), "limit": 20},
                    "Discover customer-linked account evidence",
                ),
            )
        )

    async def next_step(self, request, observations):
        tickets = observations.get("list_customer_tickets", {}).get("items", [])
        selected = (
            next(
                (t for t in tickets if str(t["ticket_id"]) == str(request.ticket_id)),
                None,
            )
            if request.ticket_id
            else (tickets[0] if tickets else None)
        )
        if not selected:
            return None
        # Ticket discovery supplies scope, not action authority. Branch only on structured facts.
        if "get_ticket" not in observations:
            return step(
                "get_ticket",
                {"ticket_id": selected["ticket_id"]},
                "Inspect the selected customer ticket",
            )
        if "get_account_status" not in observations:
            return step(
                "get_account_status",
                {"account_id": selected["account_id"]},
                "Read account state before choosing follow-up evidence",
            )
        account = observations["get_account_status"]
        ticket = observations["get_ticket"]
        security = account.get("block_reason") == "security_review"
        duplicate = (
            ticket.get("duplicate_of_id") or ticket.get("category") == "duplicate"
        )
        policy_first = security or duplicate
        if policy_first and "search_policy" not in observations:
            return step(
                "search_policy",
                {
                    "query": "security review" if security else "duplicate ticket",
                    "limit": 10,
                },
                "Observed security hold or duplicate relationship requires focused policy context",
            )
        if "list_recent_transactions" not in observations:
            return step(
                "list_recent_transactions",
                {"account_id": account["account_id"], "limit": 20},
                "Compare bounded ledger evidence; payment alone cannot establish eligibility",
            )
        if "search_policy" not in observations:
            statuses = {
                r["status"] for r in observations["list_recent_transactions"]["items"]
            }
            query = (
                "billing consistent reactivation"
                if statuses >= {"paid", "unpaid"}
                else (
                    "billing unpaid"
                    if account.get("block_reason") == "unpaid_invoice"
                    else "reactivation consistent"
                )
            )
            return step(
                "search_policy",
                {"query": query, "limit": 10},
                "Select policy keywords from observed account state and ledger evidence",
            )
        return None

    async def interpret(self, observations):
        reason = observations.get("get_account_status", {}).get("block_reason")
        ticket = observations.get("get_ticket", {})
        scenario = {
            "unpaid_invoice": "billing",
            "security_review": "security",
            "resolved_billing": "reactivation",
            "conflicting_evidence": "conflict",
        }.get(reason, "unknown")
        if reason == "resolved_billing" and any(
            t["status"] == "unpaid"
            for t in observations.get("list_recent_transactions", {}).get("items", [])
        ):
            scenario = "conflict"
        if ticket.get("duplicate_of_id") or ticket.get("category") == "duplicate":
            scenario = "duplicate"
        return Interpretation(scenario=scenario)

    async def recommend(self, interpretation):
        advice = ADVISORIES
        return Recommendation(
            next_steps=(advice[interpretation.scenario],),
            uncertainty=(
                "Read-only observations do not constitute policy evaluation or authorization to change an account.",
            ),
        )


class LegacyDeterministicPlanner(DeterministicMockPlanner):
    """Frozen v1 selection order for pre-Phase 6 checkpoint recovery."""

    planner_version = "1.0"

    async def next_step(self, request, observations):
        tickets = observations.get("list_customer_tickets", {}).get("items", [])
        selected = (
            next(
                (t for t in tickets if str(t["ticket_id"]) == str(request.ticket_id)),
                None,
            )
            if request.ticket_id
            else (tickets[0] if tickets else None)
        )
        if not selected:
            return None
        if "get_ticket" not in observations:
            return step(
                "get_ticket",
                {"ticket_id": selected["ticket_id"]},
                "Inspect the selected customer ticket",
            )
        account = selected["account_id"]
        if "get_account_status" not in observations:
            return step(
                "get_account_status",
                {"account_id": account},
                "Read authoritative account status",
            )
        if "list_recent_transactions" not in observations:
            return step(
                "list_recent_transactions",
                {"account_id": account, "limit": 20},
                "Check bounded payment evidence",
            )
        if "search_policy" not in observations:
            return step(
                "search_policy",
                {"query": "billing security duplicate reactivation", "limit": 10},
                "Retrieve policy context as untrusted evidence",
            )
        return None


ADVISORIES = {
    "billing": "Ask an authorized billing operator to review unpaid invoice evidence.",
    "security": "Escalate to an authorized security reviewer; retain the block.",
    "duplicate": "Ask an operator to verify the duplicate relationship before proposing closure.",
    "reactivation": "Request human assessment of the reactivation candidate; eligibility has not been determined.",
    "conflict": "Reconcile conflicting evidence with an authorized reviewer before any action.",
    "unknown": "Request human investigation; the available evidence does not establish a supported scenario.",
}

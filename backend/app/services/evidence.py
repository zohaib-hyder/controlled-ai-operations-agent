"""Normalize already-authorized results. Never executes SQL or interprets source prose."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, UUID, uuid5

if TYPE_CHECKING:
    from app.agents.contracts import Evidence
    from app.core.permissions import Identity
    from app.tools.contracts import Invocation, Result
    from app.tools.executor import ToolExecutor

from app.core.config import get_settings
from app.schemas.evidence import (
    Conflict,
    Gap,
    GroundedFinding,
    Reconciliation,
    SourceEvidence,
)


def stable(*parts):
    return uuid5(NAMESPACE_URL, "northstar.evidence/" + "/".join(map(str, parts)))


def freshness(updated: datetime | None, collected: datetime, threshold: int) -> str:
    if (
        updated is None
        or updated.tzinfo is None
        or collected.tzinfo is None
        or updated > collected
    ):
        return "UNKNOWN"
    return "CURRENT" if (collected - updated).total_seconds() <= threshold else "STALE"


class EvidenceRetrievalService:
    """Consumes ToolExecutor output only; existing orchestrator owns dispatch and budgets."""

    def __init__(self, executor: ToolExecutor | None = None):
        self.executor = executor

    async def retrieve(
        self, invocation: Invocation, *, identity: Identity, correlation_id: UUID
    ) -> Result:
        if self.executor is None:
            raise ValueError("An authorized executor is required for retrieval")
        return await self.executor.execute(
            invocation,
            identity=identity,
            correlation_id=correlation_id,
            required_permission="investigation:create",
        )

    def normalize(
        self,
        result: Result,
        investigation_id: UUID,
        tenant_id: UUID,
        *,
        account: dict | None = None,
        ticket: dict | None = None,
    ) -> tuple[SourceEvidence, ...]:
        if result.status != "success":
            return ()
        name, data = result.tool_name, result.data
        kind = {
            "get_customer": "customer",
            "get_account_status": "account",
            "get_ticket": "ticket",
            "list_customer_tickets": "ticket",
            "list_recent_transactions": "transaction",
            "search_policy": "policy",
        }[name]
        rows = data.get("items", [data])
        sources = []
        for row in rows[:20]:
            resource = UUID(row[f"{kind}_id"])
            version = row.get("evidence_version", row.get("version"))
            timestamp = row.get("updated_at")
            updated = (
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if timestamp
                else None
            )
            keys = {
                "customer": (),
                "account": (
                    "status",
                    "block_reason",
                    "customer_id",
                    "evidence_version",
                ),
                "ticket": ("account_id", "status", "category", "duplicate_of_id"),
                "transaction": ("status", "currency", "amount_minor"),
                "policy": (
                    "key",
                    "version",
                    "category",
                    "resource_type",
                    "effective_at",
                    "expires_at",
                    "account_states",
                    "scenarios",
                    "policy_status",
                    "relevance",
                ),
            }[kind]
            facts = {key: row[key] for key in keys if key in row}
            # Include ledger parent, never financial reference or customer name/email.
            if kind == "transaction":
                facts["account_id"] = data["account_id"]
            summary = {
                "customer": "Customer ownership verified by tenant-scoped retrieval.",
                "account": f"Account status: {row.get('status')}; block reason: {row.get('block_reason') or 'not recorded'}.",
                "ticket": f"Ticket status: {row.get('status')}; category: {row.get('category')}; duplicate reference: {row.get('duplicate_of_id') or 'none'}.",
                "transaction": f"Historical transaction status: {row.get('status')}; this record alone does not establish an outstanding balance.",
                "policy": f"Policy {row.get('key') or resource} v{version}; date status: {row.get('policy_status', 'unknown')}; advisory applicability only.",
            }[kind]
            reference = f"{kind}:{resource}" + (f":v{version}" if version else "")
            metadata = {
                "tool": name,
                "tool_version": result.tool_version,
                "limit": data.get("limit", 1),
                "bounded": True,
            }
            if kind == "transaction":
                metadata["source_created_at"] = row.get("created_at")
            if kind == "policy":
                scenario = {
                    "unpaid_invoice": "billing_block",
                    "security_review": "security_review",
                    "resolved_billing": "reactivation",
                    "conflicting_evidence": "reactivation",
                }.get((account or {}).get("block_reason"))
                if (ticket or {}).get("category") == "duplicate":
                    scenario = "duplicate_ticket"
                states, scenarios = (
                    row.get("account_states", []),
                    row.get("scenarios", []),
                )
                applicable = (
                    None
                    if account is None or scenario is None
                    else (
                        row.get("policy_status") == "current"
                        and row.get("resource_type") == "account"
                        and (not states or account.get("status") in states)
                        and (not scenarios or scenario in scenarios)
                    )
                )
                metadata.update(
                    {
                        "applicability_suggestion": applicable,
                        "account_state": (account or {}).get("status"),
                        "scenario": scenario,
                        "authorization": "not_evaluated",
                    }
                )
            sources.append(
                SourceEvidence(
                    evidence_id=stable(
                        investigation_id, tenant_id, result.execution_id, reference
                    ),
                    investigation_id=investigation_id,
                    tenant_id=tenant_id,
                    source_type=kind,
                    source_resource_id=resource,
                    source_reference=reference,
                    source_version=version,
                    source_updated_at=updated,
                    tool_execution_id=result.execution_id,
                    collected_at=result.completed_at,
                    facts=facts,
                    summary=summary,
                    freshness=freshness(
                        updated,
                        result.completed_at,
                        get_settings().evidence_freshness_seconds,
                    ),
                    historical=kind == "transaction",
                    retrieval_metadata=metadata,
                )
            )
        return tuple(sources)

    def reconcile(
        self, investigation_id: UUID, envelopes: Sequence[Evidence]
    ) -> Reconciliation:
        # Repeated source observations are retained for provenance but deduplicated for findings.
        all_sources = [s for e in envelopes for s in e.sources]
        unique = {}
        for source in all_sources:
            unique[(source.source_reference, source.tool_execution_id)] = source
        sources = list(unique.values())
        if len(sources) > 400:
            raise ValueError("Evidence bound exceeded")
        by_kind = {
            k: [s for s in sources if s.source_type == k]
            for k in ("customer", "account", "ticket", "transaction", "policy")
        }
        gaps, conflicts = [], []
        for kind in by_kind:
            if not by_kind[kind]:
                gaps.append(
                    Gap(
                        gap_id=stable(investigation_id, "gap", kind),
                        kind=f"missing_{kind}",
                        explanation=f"No authorized {kind} evidence was collected; no fact can be inferred from its absence.",
                    )
                )
        for account in by_kind["account"]:
            if account.facts.get("status") == "blocked" and not account.facts.get(
                "block_reason"
            ):
                gaps.append(
                    Gap(
                        gap_id=stable(
                            investigation_id, "block_reason", account.source_resource_id
                        ),
                        kind="missing_block_reason",
                        explanation="The account is blocked but its reason is not recorded.",
                    )
                )

        def conflict(kind, refs, explanation):
            ids = tuple(sorted({s.evidence_id for s in refs}, key=str))
            conflicts.append(
                Conflict(
                    conflict_id=stable(investigation_id, kind, *ids),
                    conflict_type=kind,
                    evidence_ids=ids,
                    severity="high",
                    explanation=explanation,
                    required_follow_up="Ask an authorized operator to reconcile source records; no source has been selected as authoritative.",
                )
            )

        for account in by_kind["account"]:
            transactions = [
                s
                for s in by_kind["transaction"]
                if s.facts.get("account_id") == str(account.source_resource_id)
            ]
            if {s.facts.get("status") for s in transactions} >= {"paid", "unpaid"}:
                conflict(
                    "payment_unresolved",
                    [account, *transactions],
                    "Paid and unpaid transactions coexist in a bounded sample. Payment allocation and outstanding balance remain unresolved.",
                )
            resolved = [
                s
                for s in by_kind["ticket"]
                if s.facts.get("account_id") == str(account.source_resource_id)
                and s.facts.get("status") == "closed"
            ]
            if account.facts.get("status") == "blocked" and resolved:
                conflict(
                    "ticket_closed_account_blocked",
                    [account, *resolved],
                    "A closed ticket coexists with a blocked account; closure does not prove account resolution.",
                )
            alternatives = [
                s
                for s in by_kind["account"]
                if s.source_resource_id == account.source_resource_id
                and s.freshness == "CURRENT"
                and account.freshness == "CURRENT"
                and s.facts.get("status") != account.facts.get("status")
            ]
            if alternatives:
                conflict(
                    "account_state_mismatch",
                    [account, *alternatives],
                    "Current observations disagree on account state.",
                )
        policies = by_kind["policy"]
        for key in sorted({s.facts.get("key") for s in policies if s.facts.get("key")}):
            matched = [
                s
                for s in policies
                if s.facts.get("key") == key
                and s.facts.get("policy_status") == "current"
            ]
            if len({s.source_version for s in matched}) > 1:
                conflict(
                    "policy_version_overlap",
                    matched,
                    "Multiple versions of one policy key appear current; applicability requires review.",
                )
        if by_kind["policy"] and all(
            s.retrieval_metadata.get("applicability_suggestion") is False
            for s in by_kind["policy"]
        ):
            gaps.append(
                Gap(
                    gap_id=stable(investigation_id, "gap", "relevant_policy"),
                    kind="missing_relevant_policy",
                    explanation="Retrieved policies do not match the observed account state and scenario; no applicable policy was established.",
                )
            )
        if len(conflicts) > 20:
            gaps.append(
                Gap(
                    gap_id=stable(investigation_id, "gap", "conflict_limit"),
                    kind="conflict_result_limit",
                    explanation="Conflict output reached its bound; further reconciliation requires human review.",
                )
            )
        conflicts = list({c.conflict_id: c for c in conflicts}.values())[:20]
        findings = [
            GroundedFinding(
                kind="observed_fact", text=s.summary, evidence_ids=(s.evidence_id,)
            )
            for s in sources
        ]
        findings += [
            GroundedFinding(
                kind="uncertainty", text=c.explanation, evidence_ids=c.evidence_ids
            )
            for c in conflicts
        ]
        # Stable conflict IDs deduplicate pairwise comparisons.
        return Reconciliation(
            conflicts=tuple({c.conflict_id: c for c in conflicts}.values()),
            gaps=tuple(gaps),
            grounded_findings=tuple(findings),
        )

    def validate_finding(
        self, finding: GroundedFinding, sources: Sequence[SourceEvidence]
    ) -> GroundedFinding:
        known = {s.evidence_id: s for s in sources}
        if not finding.evidence_ids or not set(finding.evidence_ids) <= known.keys():
            raise ValueError("Unsupported citation")
        if finding.kind == "observed_fact" and not any(
            finding.text == known[i].summary for i in finding.evidence_ids
        ):
            raise ValueError("Unsupported factual claim")
        return finding

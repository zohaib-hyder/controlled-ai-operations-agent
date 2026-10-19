"""Deterministic, evaluation-only PDP. No business writes or execution capability."""

import hashlib
import json
import re
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import event, func, select, text

from app.core.config import get_settings
from app.models.entities import (
    Account,
    ActionProposal,
    Customer,
    Policy,
    PolicyDecisionReceipt,
    SecurityEvent,
    Ticket,
    Transaction,
)
from app.policies.catalog import CATALOG
from app.schemas.actions import DecisionReceipt, ProposalInput, TrustedProposal
from app.services.authentication import revalidate_identity
from app.services.investigations import InvestigationRepository

RESOURCE_MODELS = {
    "customer": Customer,
    "account": Account,
    "ticket": Ticket,
    "transaction": Transaction,
    "policy": Policy,
}
PROHIBITED_CONTENT = re.compile(
    r"ignore\s+(all\s+)?(previous|prior)|system\s*prompt|api[_ -]?key|password\s*[:=]|bypass|override\s+security|<\s*script",
    re.I,
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def resource_binding(row):
    """Bind full eligibility facts, including rows changed without version increments."""
    fields = {"id": str(row.id), "updated_at": row.updated_at.isoformat()}
    for name in (
        "status",
        "block_reason",
        "evidence_version",
        "customer_id",
        "account_id",
        "duplicate_of_id",
        "amount_minor",
        "currency",
    ):
        if hasattr(row, name):
            value = getattr(row, name)
            fields[name] = str(value) if isinstance(value, UUID) else value
    return fingerprint(fields)


for _model in (ActionProposal, PolicyDecisionReceipt):

    @event.listens_for(_model, "before_update")
    @event.listens_for(_model, "before_delete")
    def immutable(mapper, connection, target):
        raise ValueError("Policy records are append-only")


class PolicyDecisionEngine:
    ttl_seconds = 300

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.investigations = InvestigationRepository(session_factory)

    def _actor(self, session, identity):
        session.execute(text("SELECT set_config('statement_timeout', '3000', true)"))
        session.execute(text("SELECT set_config('lock_timeout', '1000', true)"))
        return revalidate_identity(session, identity)

    def _proposal(self, session, actor, proposal_id):
        row = session.scalar(
            select(ActionProposal)
            .where(
                ActionProposal.id == proposal_id,
                ActionProposal.tenant_id == actor.tenant_id,
                ActionProposal.actor_id == actor.user_id,
            )
            .with_for_update()
        )
        if row is None:
            raise HTTPException(404, "Proposal not found")
        return row

    def _event(
        self,
        session,
        actor,
        proposal_id,
        correlation,
        kind,
        outcome,
        *,
        resource_type="action_proposal",
    ):
        session.add(
            SecurityEvent(
                tenant_id=actor.tenant_id,
                actor_id=actor.user_id,
                resource_type=resource_type,
                resource_id=proposal_id,
                request_id=correlation,
                event_type=kind,
                outcome=outcome,
            )
        )

    def create(self, identity, body: ProposalInput, correlation: UUID):
        body = ProposalInput.model_validate_json(body.model_dump_json())
        # Repository read verifies checkpoint, provenance, actor and tenant first.
        view = self.investigations.get(identity, body.investigation_id)
        with self.session_factory() as session, session.begin():
            actor = self._actor(session, identity)
            if "investigation:create" not in actor.permissions:
                raise HTTPException(403, "Permission denied")
            now = session.scalar(select(func.clock_timestamp()))
            action = CATALOG.get(body.action_name)
            args = body.arguments
            if action and action.version == body.action_version:
                try:
                    args = action.schema.model_validate_json(
                        canonical(args)
                    ).model_dump(mode="json")
                except ValidationError:
                    # Invalid arguments remain a denied, auditable proposal.
                    args = {}  # Do not persist rejected arbitrary input.
                    invalid = True
                else:
                    invalid = False
            else:
                args, invalid = {}, False
            if (
                action
                and action.schema.__name__ == "NoteArguments"
                and PROHIBITED_CONTENT.search(str(args.get("content", "")))
            ):
                args, invalid = {"content": "[prohibited content removed]"}, True
            if PROHIBITED_CONTENT.search(body.reason):
                body = body.model_copy(update={"reason": "[prohibited reason removed]"})
                invalid = True
            proposal = TrustedProposal(
                **{**body.model_dump(), "arguments": args},
                proposal_id=uuid4(),
                actor_id=actor.user_id,
                tenant_id=actor.tenant_id,
                created_at=now,
            )
            row = ActionProposal(
                id=proposal.proposal_id,
                tenant_id=actor.tenant_id,
                actor_id=actor.user_id,
                investigation_id=body.investigation_id,
                payload={
                    **proposal.model_dump(mode="json"),
                    "invalid_arguments": invalid,
                },
            )
            session.add(row)
            session.flush()
            self._event(
                session, actor, row.id, correlation, "proposal_created", "recorded"
            )
            receipt = self._evaluate(session, actor, row, view, now)
            self._persist(session, actor, row, receipt, correlation, 1)
            return self._response(row, receipt, receipt, ())

    def _evaluate(self, session, actor, row, view, now):
        proposal = {k: v for k, v in row.payload.items() if k != "invalid_arguments"}
        proposal = TrustedProposal.model_validate_json(canonical(proposal))
        reasons, rules, bindings, policies = [], [], {}, []
        action = CATALOG.get(proposal.action_name)
        sources = {s.evidence_id: s for e in view.evidence for s in e.sources}
        evidence = [sources[r] for r in proposal.evidence_references if r in sources]
        age = get_settings().evidence_freshness_seconds

        def deny(code):
            if code not in reasons:
                reasons.append(code)

        def owned(model, resource_id):
            return session.scalar(
                select(model)
                .where(model.id == resource_id, model.tenant_id == actor.tenant_id)
                .with_for_update()
            )

        if not action:
            deny("unknown_action")
        elif proposal.action_version != action.version:
            deny("invalid_action_version")
        elif row.payload.get("invalid_arguments"):
            deny("invalid_arguments")
        elif action.permission not in actor.permissions:
            deny("proposal_permission_denied")
        target = (
            owned(RESOURCE_MODELS[action.resource_type], proposal.target_resource_id)
            if action
            else None
        )
        if target is None:
            deny("target_not_found")
        else:
            bindings[f"{action.resource_type}:{target.id}"] = resource_binding(target)
        if len(evidence) != len(proposal.evidence_references):
            deny("unverified_evidence_reference")
        if not view.checkpoint_valid:
            deny("invalid_investigation_checkpoint")
        if view.status.value not in {"COMPLETED", "NEEDS_REVIEW"}:
            deny("investigation_not_final")
        if not view.reconciliation:
            deny("missing_verified_reconciliation")
        elif any(c.severity == "high" for c in view.reconciliation.conflicts):
            deny("unresolved_high_severity_conflict")
        # Every cited fact must still match its current authorized source.
        for source in evidence:
            if (
                source.tenant_id != actor.tenant_id
                or source.investigation_id != row.investigation_id
            ):
                deny("evidence_scope_mismatch")
                continue
            current = owned(
                RESOURCE_MODELS[source.source_type], source.source_resource_id
            )
            if not current:
                deny("evidence_source_missing")
                continue
            bindings[f"{source.source_type}:{current.id}"] = resource_binding(current)
            if (
                source.source_updated_at is None
                or source.source_updated_at != current.updated_at
                or source.source_updated_at > now
                or (now - source.source_updated_at).total_seconds() > age
                or source.collected_at > now
                or (now - source.collected_at).total_seconds() > age
            ):
                deny("stale_evidence")
            # Validate facts rather than trusting citations or presentation summaries.
            for key, value in source.facts.items():
                attr = "id" if key == f"{source.source_type}_id" else key
                if hasattr(current, attr):
                    live = getattr(current, attr)
                    if isinstance(live, UUID):
                        live = str(live)
                    if isinstance(live, datetime):
                        if isinstance(value, str):
                            try:
                                value = datetime.fromisoformat(
                                    value.replace("Z", "+00:00")
                                )
                            except ValueError:
                                deny("evidence_fact_changed")
                    if live != value:
                        deny("evidence_fact_changed")
            if target and action:
                if action.resource_type == "customer":
                    related = (
                        source.source_type == "customer" and current.id == target.id
                    )
                elif action.resource_type == "account":
                    related = (
                        (source.source_type == "account" and current.id == target.id)
                        or (
                            source.source_type == "transaction"
                            and current.account_id == target.id
                        )
                        or source.source_type == "policy"
                    )
                else:
                    related = (
                        source.source_type == "ticket"
                        and (
                            current.id == target.id
                            or current.id == target.duplicate_of_id
                        )
                    ) or source.source_type == "policy"
                if not related:
                    deny("evidence_target_mismatch")
        if action:
            rules = list(action.rules)
            if not set(action.required_evidence) <= {s.source_type for s in evidence}:
                deny("missing_mandatory_evidence")
            if not any(
                s.source_type == action.resource_type
                and s.source_resource_id == proposal.target_resource_id
                for s in evidence
            ):
                deny("missing_target_evidence")
            if action.name == "override_security_block":
                deny("security_override_prohibited")
            if action.schema.__name__ == "NoteArguments":
                content = proposal.arguments.get("content", "")
                if (
                    not isinstance(content, str)
                    or not content.strip()
                    or PROHIBITED_CONTENT.search(content)
                ):
                    deny("prohibited_content")
            if action.resource_type == "ticket" and target and target.status != "open":
                deny("ticket_not_open")
            if (
                action.name in {"reactivate_account", "request_account_reactivation"}
                and target
            ):
                if target.status != "blocked":
                    deny("account_not_blocked")
                if target.block_reason == "security_review":
                    deny("security_hold")
                elif target.block_reason != "resolved_billing":
                    deny("ineligible_block_reason")
                txns = session.scalars(
                    select(Transaction)
                    .where(
                        Transaction.tenant_id == actor.tenant_id,
                        Transaction.account_id == target.id,
                    )
                    .with_for_update()
                ).all()
                if not txns or any(t.status != "paid" for t in txns):
                    deny("unresolved_payment")
                if {t.id for t in txns} != {
                    s.source_resource_id
                    for s in evidence
                    if s.source_type == "transaction"
                }:
                    deny("incomplete_transaction_evidence")
                policies = self._policies(
                    session, actor, now, "reactivation", target, deny
                )
            if action.name == "close_duplicate_ticket" and target:
                try:
                    original_id = UUID(proposal.arguments.get("duplicate_of_id", ""))
                except (ValueError, TypeError):
                    original_id = None
                original = owned(Ticket, original_id) if original_id else None
                if (
                    not original
                    or original.id == target.id
                    or target.duplicate_of_id != original.id
                    or original.account_id != target.account_id
                ):
                    deny("unsupported_duplicate")
                elif not any(
                    s.source_type == "ticket" and s.source_resource_id == original.id
                    for s in evidence
                ):
                    deny("missing_original_ticket_evidence")
                if original:
                    bindings[f"ticket:{original.id}"] = resource_binding(original)
                parent = owned(Account, target.account_id)
                if parent is None:
                    deny("missing_ticket_account")
                else:
                    bindings[f"account:{parent.id}"] = resource_binding(parent)
                policies = self._policies(
                    session, actor, now, "duplicate_ticket", parent, deny
                )
            for p in policies:
                if not any(
                    s.source_type == "policy"
                    and s.source_resource_id == p["id"]
                    and s.source_version == p["version"]
                    for s in evidence
                ):
                    deny("missing_current_policy_evidence")
        decision = (
            "DENY" if reasons else "REQUIRE_APPROVAL" if action.approval else "ALLOW"
        )
        return dict(
            decision_id=str(uuid4()),
            proposal_id=str(row.id),
            tenant_id=str(actor.tenant_id),
            actor_id=str(actor.user_id),
            investigation_id=str(row.investigation_id),
            action_name=proposal.action_name,
            action_version=proposal.action_version,
            target_resource_id=str(proposal.target_resource_id),
            resource_type=action.resource_type if action else "unknown",
            canonical_arguments_hash=fingerprint(proposal.arguments),
            decision=decision,
            rule_identifiers=rules,
            policy_versions=[{**p, "id": str(p["id"])} for p in policies],
            evidence_references=[str(x) for x in proposal.evidence_references],
            resource_versions=bindings,
            actor_permissions=sorted(actor.permissions),
            reason_codes=reasons
            or ["eligible_for_review" if action.approval else "eligible_note"],
            created_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=self.ttl_seconds)).isoformat(),
            execution_authorized=False,
        )

    def _policies(self, session, actor, now, key, target, deny):
        # Explicit supersession requires the old version's effective window to end.
        records = session.scalars(
            select(Policy)
            .where(
                Policy.tenant_id == actor.tenant_id,
                Policy.key == key,
                Policy.effective_at <= now,
                (Policy.expires_at.is_(None) | (Policy.expires_at > now)),
            )
            .with_for_update()
        ).all()
        if len(records) != 1:
            deny("missing_policy" if not records else "ambiguous_policy_versions")
            return []
        policy = records[0]
        expected = (
            {"approval_required": True}
            if key == "duplicate_ticket"
            else {
                "clear_billing": True,
                "clear_security": True,
                "consistent_evidence": True,
                "approval_required": True,
            }
        )
        if (
            not isinstance(policy.rules, dict)
            or policy.rules != expected
            or any(type(value) is not bool for value in policy.rules.values())
        ):
            deny("unsupported_policy_rules")
        if (
            not isinstance(policy.scenarios, list)
            or not isinstance(policy.account_states, list)
            or policy.resource_type != "account"
            or key not in policy.scenarios
            or (
                target
                and policy.account_states
                and target.status not in policy.account_states
            )
        ):
            deny("policy_not_applicable")
        return [
            {
                "id": policy.id,
                "version": policy.version,
                "key": policy.key,
                "binding": fingerprint(
                    {
                        "rules": policy.rules,
                        "effective_at": policy.effective_at.isoformat(),
                        "expires_at": policy.expires_at.isoformat()
                        if policy.expires_at
                        else None,
                        "states": policy.account_states,
                        "scenarios": policy.scenarios,
                        "resource_type": policy.resource_type,
                    }
                ),
            }
        ]

    def _persist(self, session, actor, row, receipt, correlation, sequence):
        receipt = DecisionReceipt.model_validate_json(canonical(receipt)).model_dump(
            mode="json"
        )
        session.add(
            PolicyDecisionReceipt(
                id=UUID(receipt["decision_id"]),
                tenant_id=actor.tenant_id,
                proposal_id=row.id,
                sequence=sequence,
                payload=receipt,
            )
        )
        self._event(session, actor, row.id, correlation, "policy_evaluated", "recorded")
        self._event(
            session,
            actor,
            row.id,
            correlation,
            "decision_denied" if receipt["decision"] == "DENY" else "decision_issued",
            receipt["decision"],
        )

    def _stale(self, prior, current, now):
        from datetime import datetime

        codes = []
        if now >= datetime.fromisoformat(prior["expires_at"]):
            codes.append("decision_expired")
        for key, reason in (
            ("resource_versions", "resource_changed"),
            ("policy_versions", "policy_changed"),
            ("actor_permissions", "authorization_changed"),
        ):
            if prior[key] != current[key]:
                codes.append(reason)
        if (
            current["decision"] != prior["decision"]
            or current["reason_codes"] != prior["reason_codes"]
        ):
            codes.append("eligibility_changed")
        return tuple(codes)

    def _response(self, row, receipt, current, stale):
        return {
            "proposal": {
                k: v for k, v in row.payload.items() if k != "invalid_arguments"
            },
            "receipt": receipt,
            "status": "STALE"
            if stale
            else {
                "ALLOW": "ALLOWED",
                "REQUIRE_APPROVAL": "APPROVAL REQUIRED",
                "DENY": "DENIED",
            }[receipt["decision"]],
            "stale_reasons": stale,
            "execution_authorized": False,
        }

    def get(self, identity, proposal_id, correlation, *, revalidate=False):
        # Serialize concurrent revalidation, and keep historical receipts immutable.
        with self.session_factory() as session, session.begin():
            actor = self._actor(session, identity)
            row = self._proposal(session, actor, proposal_id)
            view = (
                self.investigations.get(identity, row.investigation_id)
                if "investigation:create" in actor.permissions
                else None
            )
            now = session.scalar(select(func.clock_timestamp()))
            prior_row = session.scalar(
                select(PolicyDecisionReceipt)
                .where(
                    PolicyDecisionReceipt.tenant_id == actor.tenant_id,
                    PolicyDecisionReceipt.proposal_id == row.id,
                )
                .order_by(PolicyDecisionReceipt.sequence.desc())
                .limit(1)
            )
            if view is None:
                current = {
                    **prior_row.payload,
                    "decision_id": str(uuid4()),
                    "decision": "DENY",
                    "actor_permissions": sorted(actor.permissions),
                    "reason_codes": ["proposal_permission_denied"],
                    "created_at": now.isoformat(),
                    "expires_at": (
                        now + timedelta(seconds=self.ttl_seconds)
                    ).isoformat(),
                }
            else:
                current = self._evaluate(session, actor, row, view, now)
            stale = self._stale(prior_row.payload, current, now)
            if "decision_expired" in stale:
                receipt_id = UUID(prior_row.payload["decision_id"])
                expired_event = session.scalar(
                    select(SecurityEvent.id)
                    .where(
                        SecurityEvent.tenant_id == actor.tenant_id,
                        SecurityEvent.actor_id == actor.user_id,
                        SecurityEvent.resource_id == receipt_id,
                        SecurityEvent.event_type == "decision_expired",
                    )
                    .limit(1)
                )
                if expired_event is None:
                    self._event(
                        session,
                        actor,
                        receipt_id,
                        correlation,
                        "decision_expired",
                        "stale",
                        resource_type="policy_decision",
                    )
            if revalidate:
                self._persist(
                    session, actor, row, current, correlation, prior_row.sequence + 1
                )
                self._event(
                    session,
                    actor,
                    row.id,
                    correlation,
                    "decision_revalidated",
                    current["decision"],
                )
                return self._response(row, current, current, ())
            return self._response(row, prior_row.payload, current, stale)

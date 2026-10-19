"""Human-only controlled execution, with atomic local effects and verified receipts."""

import re
from contextlib import contextmanager
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import event, func, select, text, update
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.core.permissions import PERMISSIONS, Identity
from app.models.entities import (
    Account,
    ActionExecution,
    ActionExecutionEvent,
    ActionProposal,
    ApprovalDecision,
    ApprovalRequest,
    AuthSession,
    BusinessRecord,
    Customer,
    Policy,
    PolicyDecisionReceipt,
    SecurityEvent,
    Ticket,
    User,
)
from app.policies.catalog import CATALOG
from app.policies.engine import (
    PolicyDecisionEngine,
    canonical,
    fingerprint,
    resource_binding,
)
from app.schemas.actions import DecisionReceipt, TrustedProposal
from app.schemas.execution import (
    TRANSITIONS,
    ApprovalCommand,
    ApprovalDetail,
    ExecuteCommand,
    ExecutionReceipt,
    transition,
)
from app.services.authentication import revalidate_identity

WRITES = frozenset(
    {
        "create_customer_note",
        "add_ticket_note",
        "request_account_reactivation",
        "reactivate_account",
        "close_duplicate_ticket",
    }
)


for _model in (ApprovalDecision, ActionExecution, ActionExecutionEvent, BusinessRecord):

    @event.listens_for(_model, "before_update")
    @event.listens_for(_model, "before_delete")
    def immutable(mapper, connection, target):
        raise ValueError("Controlled operation records are append-only")


class ControlledActionExecutor:
    def __init__(self, session_factory):
        self.factory = session_factory
        self.pdp = PolicyDecisionEngine(session_factory)

    @contextmanager
    def transaction(self, identity):
        with self.factory() as session:
            # Must be the first SQL statement: prevent ledger/policy insertion phantoms.
            session.connection(execution_options={"isolation_level": "SERIALIZABLE"})
            try:
                session.execute(text("SET LOCAL statement_timeout = '3000ms'"))
                session.execute(text("SET LOCAL lock_timeout = '1000ms'"))
                session.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"),
                    {"key": int(identity.tenant_id.hex[:15], 16)},
                )
                if identity.job_id is not None:
                    from app.models.entities import ExecutionJob

                    session.scalar(
                        select(ExecutionJob)
                        .where(
                            ExecutionJob.id == identity.job_id,
                            ExecutionJob.tenant_id == identity.tenant_id,
                        )
                        .with_for_update()
                    )
                # Lock current session and role against concurrent revocation/demotion.
                session.scalar(
                    select(AuthSession)
                    .where(
                        AuthSession.id == identity.session_id,
                        AuthSession.tenant_id == identity.tenant_id,
                    )
                    .with_for_update()
                )
                session.scalar(
                    select(User)
                    .where(
                        User.id == identity.user_id,
                        User.tenant_id == identity.tenant_id,
                    )
                    .with_for_update()
                )
                actor = revalidate_identity(session, identity)
                yield session, actor
                session.commit()
            except BaseException:
                session.rollback()
                raise

    def audit(self, session, actor, resource_id, correlation, kind, outcome):
        session.add(
            SecurityEvent(
                tenant_id=actor.tenant_id,
                actor_id=actor.user_id,
                resource_type="controlled_action",
                resource_id=resource_id,
                request_id=correlation,
                event_type=kind,
                outcome=outcome,
            )
        )

    def _proposal(self, session, actor, proposal_id, *, owner=False):
        conditions = [
            ActionProposal.tenant_id == actor.tenant_id,
            ActionProposal.id == proposal_id,
        ]
        if owner:
            conditions.append(ActionProposal.actor_id == actor.user_id)
        row = session.scalar(
            select(ActionProposal).where(*conditions).with_for_update()
        )
        if row is None:
            raise HTTPException(404, "Proposal not found")
        return row

    def _receipt(self, session, actor, proposal, decision_id=None):
        query = select(PolicyDecisionReceipt).where(
            PolicyDecisionReceipt.tenant_id == actor.tenant_id,
            PolicyDecisionReceipt.proposal_id == proposal.id,
        )
        if decision_id is not None:
            query = query.where(PolicyDecisionReceipt.id == decision_id)
        row = session.scalar(
            query.order_by(PolicyDecisionReceipt.sequence.desc()).limit(1)
        )
        if row is None:
            raise HTTPException(409, "decision_not_found")
        receipt = DecisionReceipt.model_validate_json(
            canonical(row.payload)
        ).model_dump(mode="json")
        if receipt["tenant_id"] != str(actor.tenant_id) or receipt["actor_id"] != str(
            proposal.actor_id
        ):
            raise HTTPException(409, "decision_binding_invalid")
        return receipt

    def _view(self, identity, proposal):
        return self.pdp.investigations.get(
            identity, proposal.investigation_id, review=True
        )

    def _current(self, session, actor, proposal, receipt, view):
        # Execution is creator-only; review evaluates the actual creator's live proposal permissions.
        user = session.scalar(
            select(User)
            .where(User.id == proposal.actor_id, User.tenant_id == actor.tenant_id)
            .with_for_update()
        )
        if (
            not user
            or not user.is_active
            or "investigation:create" not in PERMISSIONS.get(user.role, ())
        ):
            return ("proposal_actor_revoked",)
        principal = Identity(user.id, user.tenant_id, user.role, actor.session_id)
        # The principal here is ONLY policy input from locked DB User, never session authentication.
        now = session.scalar(select(func.clock_timestamp()))
        current = self.pdp._evaluate(session, principal, proposal, view, now)
        current_args = fingerprint(proposal.payload["arguments"])
        if (
            receipt["proposal_id"] != str(proposal.id)
            or receipt["investigation_id"] != str(proposal.investigation_id)
            or receipt["action_name"] != proposal.payload["action_name"]
            or receipt["action_version"] != proposal.payload["action_version"]
            or receipt["target_resource_id"] != proposal.payload["target_resource_id"]
            or receipt["canonical_arguments_hash"] != current_args
            or receipt["evidence_references"] != proposal.payload["evidence_references"]
        ):
            return ("proposal_binding_changed",)
        now = session.scalar(select(func.clock_timestamp()))
        stale = self.pdp._stale(receipt, current, now)
        if current["decision"] == "DENY":
            return tuple(current["reason_codes"]) or ("policy_denied",)
        return stale

    def _approval(self, session, actor, approval_id):
        row = session.scalar(
            select(ApprovalRequest)
            .where(
                ApprovalRequest.id == approval_id,
                ApprovalRequest.tenant_id == actor.tenant_id,
            )
            .with_for_update()
        )
        if not row or (
            row.requested_by != actor.user_id
            and "action:approve" not in actor.permissions
        ):
            raise HTTPException(404, "Approval not found")
        return row

    def _change(self, session, actor, row, status, reason, correlation):
        row.status = transition(row.status, status)
        sequence = (
            session.scalar(
                select(func.count())
                .select_from(ApprovalDecision)
                .where(
                    ApprovalDecision.tenant_id == actor.tenant_id,
                    ApprovalDecision.approval_id == row.id,
                )
            )
            + 1
        )
        session.add(
            ApprovalDecision(
                tenant_id=actor.tenant_id,
                approval_id=row.id,
                actor_id=actor.user_id,
                sequence=sequence,
                status=status,
                reason=reason,
            )
        )
        self.audit(
            session,
            actor,
            row.id,
            correlation,
            {
                "APPROVED": "approval_granted",
                "REJECTED": "approval_rejected",
                "CANCELLED": "approval_cancelled",
                "EXPIRED": "approval_expired",
                "INVALIDATED": "approval_invalidated",
            }[status],
            status,
        )

    def _reviewer_valid(self, session, row, now):
        if row.reviewer_id is None or row.reviewer_id == row.requested_by:
            return False
        user = session.scalar(
            select(User)
            .where(User.id == row.reviewer_id, User.tenant_id == row.tenant_id)
            .with_for_update()
        )
        auth = session.scalar(
            select(AuthSession)
            .where(
                AuthSession.id == row.reviewer_session_id,
                AuthSession.tenant_id == row.tenant_id,
                AuthSession.user_id == row.reviewer_id,
            )
            .with_for_update()
        )
        return bool(
            user
            and user.is_active
            and "action:approve" in PERMISSIONS.get(user.role, ())
            and auth
            and auth.revoked_at is None
            and auth.expires_at > now
        )

    def request_approval(self, identity, proposal_id, correlation):
        with self.transaction(identity) as (session, actor):
            proposal = self._proposal(session, actor, proposal_id, owner=True)
            view = self._view(identity, proposal)
            receipt = self._receipt(session, actor, proposal)
            if receipt["decision"] != "REQUIRE_APPROVAL" or self._current(
                session, actor, proposal, receipt, view
            ):
                raise HTTPException(409, "current_approval_eligible_decision_required")
            if proposal.payload["action_name"] not in WRITES:
                raise HTTPException(403, "action_prohibited")
            existing = session.scalar(
                select(ApprovalRequest).where(
                    ApprovalRequest.tenant_id == actor.tenant_id,
                    ApprovalRequest.proposal_id == proposal.id,
                )
            )
            if existing:
                if existing.decision_id == UUID(
                    receipt["decision_id"]
                ) and existing.status in {"PENDING", "APPROVED"}:
                    return self._describe(session, existing, proposal)
                raise HTTPException(409, "approval_already_requested")
            row = ApprovalRequest(
                id=uuid4(),
                tenant_id=actor.tenant_id,
                proposal_id=proposal.id,
                decision_id=UUID(receipt["decision_id"]),
                requested_by=actor.user_id,
                status="PENDING",
                expires_at=datetime.fromisoformat(receipt["expires_at"]),
                binding=receipt,
            )
            session.add(row)
            self.audit(
                session, actor, row.id, correlation, "approval_requested", "PENDING"
            )
            result = self._describe(session, row, proposal)
        return result

    def _refresh(self, session, actor, identity, row, proposal, correlation):
        if row.status not in {"PENDING", "APPROVED"} or row.consumed_at:
            return
        now = session.scalar(select(func.clock_timestamp()))
        if now >= row.expires_at:
            self._change(
                session, actor, row, "EXPIRED", "approval_expired", correlation
            )
            return
        invalid = self._current(
            session, actor, proposal, row.binding, self._view(identity, proposal)
        )
        if row.status == "APPROVED" and not self._reviewer_valid(session, row, now):
            invalid = (*invalid, "reviewer_authorization_revoked")
        if invalid:
            self._change(session, actor, row, "INVALIDATED", invalid[0], correlation)

    def decide(
        self, identity, approval_id, command: ApprovalCommand, operation, correlation
    ):
        command = ApprovalCommand.model_validate_json(command.model_dump_json())
        with self.transaction(identity) as (session, actor):
            row = self._approval(session, actor, approval_id)
            proposal = self._proposal(session, actor, row.proposal_id)
            if operation == "cancel":
                if row.requested_by != actor.user_id:
                    raise HTTPException(403, "Only the requester may cancel")
            elif "action:approve" not in actor.permissions or actor.user_id in {
                row.requested_by,
                proposal.actor_id,
            }:
                raise HTTPException(403, "separation_of_duties_required")
            self._refresh(session, actor, identity, row, proposal, correlation)
            desired = {
                "approve": "APPROVED",
                "reject": "REJECTED",
                "cancel": "CANCELLED",
            }[operation]
            if row.consumed_at or desired not in TRANSITIONS.get(row.status, ()):
                result = self._describe(session, row, proposal)
                result["error_code"] = "invalid_approval_transition"
            else:
                if desired == "APPROVED":
                    row.reviewer_id, row.reviewer_session_id = (
                        actor.user_id,
                        actor.session_id,
                    )
                self._change(session, actor, row, desired, command.reason, correlation)
                result = self._describe(session, row, proposal)
        return result

    def _describe(self, session, row, proposal):
        session.flush()
        decisions = session.scalars(
            select(ApprovalDecision)
            .where(
                ApprovalDecision.tenant_id == row.tenant_id,
                ApprovalDecision.approval_id == row.id,
            )
            .order_by(ApprovalDecision.sequence)
            .limit(20)
        ).all()
        result = dict(
            approval_id=str(row.id),
            tenant_id=str(row.tenant_id),
            proposal_id=str(row.proposal_id),
            decision_id=str(row.decision_id),
            requested_by=str(row.requested_by),
            reviewer_id=str(row.reviewer_id) if row.reviewer_id else None,
            status=row.status,
            expires_at=row.expires_at.isoformat(),
            consumed=row.consumed_at is not None,
            action_name=proposal.payload["action_name"],
            target_resource_id=proposal.payload["target_resource_id"],
            receipt=row.binding,
            decisions=[
                dict(
                    status=d.status,
                    reason=d.reason,
                    actor_id=str(d.actor_id),
                    created_at=d.created_at.isoformat(),
                )
                for d in decisions
            ],
        )

        return ApprovalDetail.model_validate_json(canonical(result)).model_dump(
            mode="json"
        )

    def detail(self, identity, approval_id, correlation):
        with self.transaction(identity) as (session, actor):
            row = self._approval(session, actor, approval_id)
            proposal = self._proposal(session, actor, row.proposal_id)
            self._refresh(session, actor, identity, row, proposal, correlation)
            result = self._describe(session, row, proposal)
            refs = set(row.binding["evidence_references"])
            view = self._view(identity, proposal)
            result["sources"] = [
                s.model_dump(mode="json")
                for e in view.evidence
                for s in e.sources
                if str(s.evidence_id) in refs
            ][:80]
        return result

    def queue(self, identity, limit=20, offset=0):
        with self.transaction(identity) as (session, actor):
            if "action:approve" not in actor.permissions:
                raise HTTPException(403, "Approval permission required")
            rows = session.scalars(
                select(ApprovalRequest)
                .where(ApprovalRequest.tenant_id == actor.tenant_id)
                .order_by(ApprovalRequest.created_at.desc(), ApprovalRequest.id)
                .limit(limit)
                .offset(offset)
            ).all()
            return {
                "items": [
                    dict(
                        approval_id=str(r.id),
                        proposal_id=str(r.proposal_id),
                        status=r.status,
                        requested_by=str(r.requested_by),
                        expires_at=r.expires_at.isoformat(),
                    )
                    for r in rows
                ]
            }

    def _protected_binding(self, target, action):
        allowed = {"updated_at"}
        if action in {"request_account_reactivation", "reactivate_account"}:
            allowed.add("evidence_version")
        if action == "reactivate_account":
            allowed.update({"status", "block_reason"})
        if action == "close_duplicate_ticket":
            allowed.add("status")
        return fingerprint(
            {
                c.name: str(getattr(target, c.name))
                for c in target.__table__.columns
                if c.name not in allowed
            }
        )

    def _mutate(self, session, actor, proposal, execution_id, deadline):
        trusted = TrustedProposal.model_validate_json(
            canonical(
                {k: v for k, v in proposal.payload.items() if k != "invalid_arguments"}
            )
        )
        action = CATALOG[trusted.action_name]
        args = action.schema.model_validate_json(canonical(trusted.arguments))
        model = {"customer": Customer, "ticket": Ticket, "account": Account}[
            action.resource_type
        ]
        target = session.scalar(
            select(model)
            .where(
                model.id == trusted.target_resource_id,
                model.tenant_id == actor.tenant_id,
            )
            .with_for_update()
        )
        if target is None:
            raise ValueError("target_missing")
        before = {
            "resource_hash": resource_binding(target),
            "protected_hash": self._protected_binding(target, trusted.action_name),
            "status": getattr(target, "status", None),
            "version": getattr(target, "evidence_version", None),
        }
        values = {"updated_at": func.clock_timestamp()}
        record = None
        name = trusted.action_name
        if name in {
            "create_customer_note",
            "add_ticket_note",
            "request_account_reactivation",
        }:
            kind = {
                "create_customer_note": "customer_note",
                "add_ticket_note": "ticket_note",
                "request_account_reactivation": "reactivation_request",
            }[name]
            record = BusinessRecord(
                id=uuid4(),
                tenant_id=actor.tenant_id,
                execution_id=execution_id,
                kind=kind,
                **{f"{action.resource_type}_id": target.id},
                content=args.content if hasattr(args, "content") else None,
            )
            session.add(record)
            if name == "add_ticket_note" and target.status != "open":
                raise ValueError("ticket_not_open")
            if name == "request_account_reactivation":
                values["evidence_version"] = target.evidence_version + 1
        elif name == "reactivate_account":
            if target.status != "blocked" or target.block_reason != "resolved_billing":
                raise ValueError("ineligible_reactivation")
            values.update(
                status="active",
                block_reason=None,
                evidence_version=target.evidence_version + 1,
            )
        elif name == "close_duplicate_ticket":
            if (
                target.status != "open"
                or target.duplicate_of_id != args.duplicate_of_id
            ):
                raise ValueError("unsupported_duplicate")
            values["status"] = "closed"
        else:
            raise ValueError("action_prohibited")
        changed = session.execute(
            update(model)
            .where(
                model.id == target.id,
                model.tenant_id == actor.tenant_id,
                model.updated_at == target.updated_at,
                func.clock_timestamp() < deadline,
            )
            .values(**values)
            .returning(model.id)
        ).scalar_one_or_none()
        if changed is None:
            raise ValueError("optimistic_conflict")
        session.flush()
        session.refresh(target)
        after = {
            "resource_hash": resource_binding(target),
            "status": getattr(target, "status", None),
            "version": getattr(target, "evidence_version", None),
            "business_record_id": str(record.id) if record else None,
        }
        return before, after

    def _verify(self, session, actor, proposal, execution_id, before, after):
        name, target_id = (
            proposal.payload["action_name"],
            UUID(proposal.payload["target_resource_id"]),
        )
        model = {
            "create_customer_note": Customer,
            "add_ticket_note": Ticket,
            "close_duplicate_ticket": Ticket,
            "request_account_reactivation": Account,
            "reactivate_account": Account,
        }[name]
        target = session.scalar(
            select(model)
            .where(model.tenant_id == actor.tenant_id, model.id == target_id)
            .execution_options(populate_existing=True)
        )
        if (
            not target
            or resource_binding(target) != after["resource_hash"]
            or before["resource_hash"] == after["resource_hash"]
            or self._protected_binding(target, name) != before["protected_hash"]
        ):
            return False
        if name == "reactivate_account":
            return (
                target.status == "active"
                and target.block_reason is None
                and target.evidence_version == before["version"] + 1
            )
        if name == "close_duplicate_ticket":
            return (
                target.status == "closed"
                and str(target.duplicate_of_id)
                == proposal.payload["arguments"]["duplicate_of_id"]
            )
        record = session.scalar(
            select(BusinessRecord).where(
                BusinessRecord.tenant_id == actor.tenant_id,
                BusinessRecord.execution_id == execution_id,
            )
        )
        field = {
            "create_customer_note": "customer_id",
            "add_ticket_note": "ticket_id",
            "request_account_reactivation": "account_id",
        }[name]
        return bool(
            record
            and record.kind
            == {
                "create_customer_note": "customer_note",
                "add_ticket_note": "ticket_note",
                "request_account_reactivation": "reactivation_request",
            }[name]
            and getattr(record, field) == target_id
            and record.content == proposal.payload["arguments"].get("content")
            and (name != "request_account_reactivation" or target.status == "blocked")
        )

    def execute(self, identity, proposal_id, command: ExecuteCommand, key, correlation):
        command = ExecuteCommand.model_validate_json(command.model_dump_json())
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", key):
            raise HTTPException(422, "invalid_idempotency_key")
        with self.transaction(identity) as (session, actor):
            if "action:execute" not in actor.permissions:
                raise HTTPException(403, "Execution permission required")
            proposal = self._proposal(session, actor, proposal_id, owner=True)
            request_hash = fingerprint(
                {
                    "tenant": str(actor.tenant_id),
                    "actor": str(actor.user_id),
                    "proposal": str(proposal.id),
                    "payload": proposal.payload,
                    "command": command.model_dump(mode="json"),
                }
            )
            if identity.job_id is not None:
                from app.models.entities import ExecutionJob

                job = session.scalar(
                    select(ExecutionJob).where(
                        ExecutionJob.id == identity.job_id,
                        ExecutionJob.tenant_id == actor.tenant_id,
                    )
                )
                if (
                    job.binding_hash != request_hash
                    or job.proposal_id != proposal.id
                    or job.idempotency_key != key
                    or job.action_name != proposal.payload["action_name"]
                    or job.action_version != proposal.payload["action_version"]
                ):
                    raise HTTPException(409, "job_binding_changed")
            previous = session.scalar(
                select(ActionExecution).where(
                    ActionExecution.tenant_id == actor.tenant_id,
                    (ActionExecution.idempotency_key == key)
                    | (ActionExecution.proposal_id == proposal.id),
                )
            )
            if previous:
                if (
                    previous.idempotency_key != key
                    or previous.request_hash != request_hash
                    or previous.actor_id != actor.user_id
                ):
                    raise HTTPException(409, "idempotency_conflict")
                return {**previous.payload, "replayed": True}
            self.audit(
                session,
                actor,
                proposal.id,
                correlation,
                "execution_requested",
                "requested",
            )
            receipt = self._receipt(session, actor, proposal, command.decision_id)
            if (
                proposal.payload["action_name"] not in WRITES
                or receipt["decision"] == "DENY"
            ):
                raise HTTPException(403, "action_prohibited")
            approval = None
            if receipt["decision"] == "REQUIRE_APPROVAL":
                if command.approval_id is None:
                    raise HTTPException(409, "approval_required")
                approval = self._approval(session, actor, command.approval_id)
                if approval.proposal_id != proposal.id:
                    raise HTTPException(409, "approval_proposal_mismatch")
                self._refresh(session, actor, identity, approval, proposal, correlation)
                if (
                    approval.proposal_id != proposal.id
                    or approval.decision_id != command.decision_id
                    or approval.binding != receipt
                    or approval.status != "APPROVED"
                    or approval.consumed_at is not None
                ):
                    # Preserve expiry/invalidation; return a denied result after committing metadata only.
                    self.audit(
                        session,
                        actor,
                        proposal.id,
                        correlation,
                        "execution_denied",
                        "denied",
                    )
                    return {
                        "status": "DENIED",
                        "error_code": "approval_not_current",
                        "verified": False,
                        "replayed": False,
                    }
            elif command.approval_id is not None:
                raise HTTPException(409, "unexpected_approval")
            stale = self._current(
                session, actor, proposal, receipt, self._view(identity, proposal)
            )
            if stale:
                self.audit(
                    session,
                    actor,
                    proposal.id,
                    correlation,
                    "execution_denied",
                    "denied",
                )
                return {
                    "status": "DENIED",
                    "error_code": stale[0],
                    "verified": False,
                    "replayed": False,
                }
            # Recheck authentication after all reads, immediately before the bounded mutation.
            revalidate_identity(session, identity)
            deadline = datetime.fromisoformat(receipt["expires_at"])
            session_expiry = session.scalar(
                select(AuthSession.expires_at).where(
                    AuthSession.id == actor.session_id,
                    AuthSession.tenant_id == actor.tenant_id,
                )
            )
            if identity.job_id is not None:
                from app.models.entities import ExecutionJob

                session_expiry = session.scalar(
                    select(ExecutionJob.lease_expires_at).where(
                        ExecutionJob.id == identity.job_id,
                        ExecutionJob.tenant_id == identity.tenant_id,
                    )
                )
            deadline = min(deadline, session_expiry)
            if approval:
                reviewer_expiry = session.scalar(
                    select(AuthSession.expires_at).where(
                        AuthSession.id == approval.reviewer_session_id,
                        AuthSession.tenant_id == actor.tenant_id,
                    )
                )
                deadline = min(deadline, approval.expires_at, reviewer_expiry)
            keys = [p["key"] for p in receipt["policy_versions"]]
            if keys:
                cutoffs = session.scalars(
                    select(Policy.expires_at).where(
                        Policy.tenant_id == actor.tenant_id,
                        Policy.id.in_(
                            [UUID(p["id"]) for p in receipt["policy_versions"]]
                        ),
                        Policy.expires_at.is_not(None),
                    )
                ).all()
                future = session.scalar(
                    select(func.min(Policy.effective_at)).where(
                        Policy.tenant_id == actor.tenant_id,
                        Policy.key.in_(keys),
                        Policy.effective_at > func.clock_timestamp(),
                    )
                )
                if future:
                    cutoffs.append(future)
                if cutoffs:
                    deadline = min(deadline, *cutoffs)
            execution_id = uuid4()
            self.audit(
                session,
                actor,
                execution_id,
                correlation,
                "execution_started",
                "started",
            )
            before, after, error_code = {}, {}, None
            try:
                with session.begin_nested():
                    before, after = self._mutate(
                        session, actor, proposal, execution_id, deadline
                    )
                    if not self._verify(
                        session, actor, proposal, execution_id, before, after
                    ):
                        raise ValueError("outcome_verification_failed")
            except (ValueError, SQLAlchemyError) as exc:
                if isinstance(exc, DBAPIError) and getattr(
                    exc.orig, "sqlstate", None
                ) in {"40001", "40P01", "55P03"}:
                    # Known transient rollback: abort the whole transaction and let the
                    # durable worker retry the exact binding. Never persist a terminal
                    # FAILED receipt for a serialization/deadlock/lock-timeout abort.
                    raise
                # No raw exception/proposal content in receipts. Rollback restores all business effects.
                before, after, error_code = {}, {}, "mutation_or_verification_failed"
            status = "FAILED" if error_code else "COMMITTED"
            result = dict(
                execution_id=str(execution_id),
                proposal_id=str(proposal.id),
                approval_id=str(approval.id) if approval else None,
                actor_id=str(actor.user_id),
                tenant_id=str(actor.tenant_id),
                action_name=proposal.payload["action_name"],
                action_version=proposal.payload["action_version"],
                target_resource_id=proposal.payload["target_resource_id"],
                canonical_arguments_hash=receipt["canonical_arguments_hash"],
                decision_id=str(command.decision_id),
                before=before,
                after=after,
                verified=not bool(error_code),
                status=status,
                error_code=error_code,
                created_at=session.scalar(select(func.clock_timestamp())).isoformat(),
                idempotency_key=key,
                replayed=False,
            )
            result = ExecutionReceipt.model_validate_json(canonical(result)).model_dump(
                mode="json"
            )
            session.add(
                ActionExecution(
                    id=execution_id,
                    tenant_id=actor.tenant_id,
                    proposal_id=proposal.id,
                    actor_id=actor.user_id,
                    decision_id=command.decision_id,
                    approval_id=approval.id if approval else None,
                    idempotency_key=key,
                    request_hash=request_hash,
                    payload=result,
                )
            )
            if not error_code and approval:
                approval.consumed_at = session.scalar(select(func.clock_timestamp()))
            session.flush()
            kinds = (
                ["execution_requested", "execution_started", "execution_failed"]
                if error_code
                else [
                    "execution_requested",
                    "execution_started",
                    "execution_committed",
                    "execution_verified",
                ]
            )
            for sequence, kind in enumerate(kinds, 1):
                session.add(
                    ActionExecutionEvent(
                        tenant_id=actor.tenant_id,
                        execution_id=execution_id,
                        sequence=sequence,
                        event_type=kind,
                        correlation_id=correlation,
                    )
                )
                if kind not in {"execution_requested", "execution_started"}:
                    self.audit(session, actor, execution_id, correlation, kind, status)
        # Returning success only after the surrounding transaction committed.
        return result

    def execution(self, identity, execution_id):
        with self.transaction(identity) as (session, actor):
            row = session.scalar(
                select(ActionExecution).where(
                    ActionExecution.tenant_id == actor.tenant_id,
                    ActionExecution.id == execution_id,
                )
            )
            if not row or (
                row.actor_id != actor.user_id
                and "action:approve" not in actor.permissions
            ):
                raise HTTPException(404, "Execution not found")
            events = session.scalars(
                select(ActionExecutionEvent)
                .where(
                    ActionExecutionEvent.tenant_id == actor.tenant_id,
                    ActionExecutionEvent.execution_id == row.id,
                )
                .order_by(ActionExecutionEvent.sequence)
                .limit(20)
            ).all()
            return {
                **row.payload,
                "events": [
                    dict(
                        type=e.event_type,
                        correlation_id=str(e.correlation_id),
                        created_at=e.created_at.isoformat(),
                    )
                    for e in events
                ],
            }

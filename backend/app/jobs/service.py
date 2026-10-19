"""Durable scheduling metadata only. Business writes remain in ControlledActionExecutor."""

import json
import logging
import re
from datetime import timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.core.permissions import Identity
from app.execution.service import WRITES, ControlledActionExecutor
from app.jobs.contracts import TRANSITIONS, Submit
from app.models.entities import (
    Account,
    ActionExecution,
    ApprovalRequest,
    BusinessRecord,
    Customer,
    SecurityEvent,
    Ticket,
    User,
)
from app.models.entities import (
    ExecutionDeadLetter as DeadLetter,
)
from app.models.entities import (
    ExecutionJob as Job,
)
from app.models.entities import (
    ExecutionJobAttempt as Attempt,
)
from app.models.entities import (
    ExecutionJobEvent as Event,
)
from app.policies.engine import fingerprint, resource_binding
from app.schemas.execution import ExecuteCommand, ExecutionReceipt
from app.services.authentication import revalidate_identity

logger = logging.getLogger("northstar.jobs")
ACTIVE = ("QUEUED", "CLAIMED", "RUNNING", "RETRY_SCHEDULED", "RECONCILIATION_REQUIRED")
LEASE_SECONDS = 30
GLOBAL_LIMIT = 4
TENANT_LIMIT = 1
MAX_QUEUE_DEPTH = 100
SUBMISSIONS_PER_MINUTE = 20

for model in (Event, DeadLetter):

    @event.listens_for(model, "before_update")
    @event.listens_for(model, "before_delete")
    def immutable(mapper, connection, target):
        raise ValueError("Job history is append-only")


def classify(exc):
    """Only known rolled-back SQL states are immediately retryable; transport is uncertain."""
    if isinstance(exc, HTTPException):
        return "authorization_or_validation", False
    if isinstance(exc, DBAPIError):
        state = getattr(exc.orig, "sqlstate", None)
        if state in {"40001", "40P01", "55P03"}:
            return "transaction_conflict", True
        if state and state.startswith("08") or exc.connection_invalidated:
            return "database_connectivity", False
    return "uncertain_infrastructure", False


def backoff(job_id, attempt):
    # Stable bounded jitter makes recovery reproducible without synchronized retries.
    return min(60, 2 ** min(attempt, 6)) + (int(job_id.hex[-4:], 16) % 1000) / 1000


class JobService:
    def __init__(self, factory):
        self.factory = factory
        self.executor = ControlledActionExecutor(factory)

    def move(self, session, job, target, category, correlation):
        if target not in TRANSITIONS.get(job.status, set()):
            raise ValueError(f"Illegal job transition {job.status}->{target}")
        job.status = target
        job.last_error = (
            category
            if target not in {"COMPLETED", "CLAIMED", "RUNNING", "CANCELLED"}
            else None
        )
        job.updated_at = session.scalar(select(func.clock_timestamp()))
        session.add(
            Event(
                tenant_id=job.tenant_id,
                job_id=job.id,
                state=target,
                created_at=job.updated_at,
                category=category,
                correlation_id=correlation,
            )
        )
        # Audit attribution uses stored IDs; no synthetic worker principal or role.
        session.add(
            SecurityEvent(
                tenant_id=job.tenant_id,
                actor_id=job.actor_id,
                resource_type="execution_job",
                resource_id=job.id,
                request_id=correlation,
                event_type="job_" + target.lower(),
                outcome=target,
            )
        )
        logger.info(
            "job_transition",
            extra={
                "job_id": str(job.id),
                "tenant_id": str(job.tenant_id),
                "state": target,
                "category": category,
                "correlation_id": str(correlation),
            },
        )

    def _owned(self, session, actor, job_id):
        row = session.scalar(
            select(Job)
            .where(Job.id == job_id, Job.tenant_id == actor.tenant_id)
            .with_for_update()
        )
        if not row or (
            row.actor_id != actor.user_id and "settings:manage" not in actor.permissions
        ):
            raise HTTPException(404, "Job not found")
        return row

    def _validate_submission(self, session, actor, body, correlation):
        if "action:execute" not in actor.permissions:
            raise HTTPException(403, "Execution permission required")
        proposal = self.executor._proposal(session, actor, body.proposal_id, owner=True)
        receipt = self.executor._receipt(session, actor, proposal, body.decision_id)
        if (
            proposal.payload["action_name"] not in WRITES
            or receipt["decision"] == "DENY"
        ):
            raise HTTPException(403, "action_prohibited")
        if receipt["decision"] == "REQUIRE_APPROVAL":
            if body.approval_id is None:
                raise HTTPException(409, "approval_required")
            approval = self.executor._approval(session, actor, body.approval_id)
            if approval.proposal_id != proposal.id:
                raise HTTPException(409, "approval_proposal_mismatch")
            self.executor._refresh(
                session, actor, actor, approval, proposal, correlation
            )
            if (
                approval.status != "APPROVED"
                or approval.consumed_at
                or approval.decision_id != body.decision_id
                or approval.binding != receipt
            ):
                raise HTTPException(409, "approval_not_current")
        elif body.approval_id is not None:
            raise HTTPException(409, "unexpected_approval")
        stale = self.executor._current(
            session, actor, proposal, receipt, self.executor._view(actor, proposal)
        )
        if stale:
            raise HTTPException(409, stale[0])
        command = ExecuteCommand(
            decision_id=body.decision_id, approval_id=body.approval_id
        )
        binding = fingerprint(
            {
                "tenant": str(actor.tenant_id),
                "actor": str(actor.user_id),
                "proposal": str(proposal.id),
                "payload": proposal.payload,
                "command": command.model_dump(mode="json"),
            }
        )
        return proposal, command, binding

    def submit(self, identity, body, key, correlation):
        body = Submit.model_validate_json(body.model_dump_json())
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", key):
            raise HTTPException(422, "invalid_idempotency_key")
        with self.executor.transaction(identity) as (session, actor):
            # Replay remains available after the original decision expires, without new authority.
            old = session.scalar(
                select(Job).where(
                    Job.tenant_id == actor.tenant_id,
                    (Job.idempotency_key == key)
                    | (Job.proposal_id == body.proposal_id),
                )
            )
            if old:
                if (
                    old.actor_id != actor.user_id
                    or old.idempotency_key != key
                    or old.proposal_id != body.proposal_id
                    or old.command
                    != body.model_dump(mode="json", exclude={"proposal_id"})
                ):
                    raise HTTPException(409, "idempotency_conflict")
                if "action:execute" not in actor.permissions:
                    raise HTTPException(403, "Execution permission required")
                session.add(
                    Event(
                        tenant_id=old.tenant_id,
                        job_id=old.id,
                        state=old.status,
                        category="duplicate_submission",
                        correlation_id=correlation,
                    )
                )
                return self.describe(session, old, actor)
            proposal, command, binding = self._validate_submission(
                session, actor, body, correlation
            )
            count = session.scalar(
                select(func.count())
                .select_from(Job)
                .where(Job.tenant_id == actor.tenant_id, Job.status.in_(ACTIVE))
            )
            recent = session.scalar(
                select(func.count())
                .select_from(Job)
                .where(
                    Job.tenant_id == actor.tenant_id,
                    Job.created_at > func.clock_timestamp() - timedelta(minutes=1),
                )
            )
            if count >= MAX_QUEUE_DEPTH or recent >= SUBMISSIONS_PER_MINUTE:
                raise HTTPException(
                    429, "execution_queue_backpressure", headers={"Retry-After": "60"}
                )
            now = session.scalar(select(func.clock_timestamp()))
            row = Job(
                id=uuid4(),
                tenant_id=actor.tenant_id,
                actor_id=actor.user_id,
                session_id=actor.session_id,
                proposal_id=proposal.id,
                action_name=proposal.payload["action_name"],
                action_version=proposal.payload["action_version"],
                idempotency_key=key,
                binding_hash=binding,
                command=command.model_dump(mode="json"),
                status="QUEUED",
                priority=0,
                attempt_count=0,
                max_attempts=3,
                fence=0,
                retry_deadline=now + timedelta(minutes=10),
                next_run_at=now,
            )
            session.add(row)
            session.flush()
            session.add(
                Event(
                    tenant_id=row.tenant_id,
                    job_id=row.id,
                    state="QUEUED",
                    category="submitted",
                    correlation_id=correlation,
                )
            )
            self.executor.audit(
                session, actor, row.id, correlation, "job_queued", "QUEUED"
            )
            return self.describe(session, row, actor)

    def describe(self, session, row, actor):
        now = session.scalar(select(func.clock_timestamp()))
        names = (
            "id",
            "proposal_id",
            "actor_id",
            "action_name",
            "action_version",
            "status",
            "attempt_count",
            "max_attempts",
            "next_run_at",
            "created_at",
            "updated_at",
            "lease_expires_at",
            "receipt_id",
            "last_error",
        )
        result = {name: getattr(row, name) for name in names}
        allowed = (
            row.actor_id == actor.user_id and "action:execute" in actor.permissions
        )
        result.update(
            age_seconds=max(0.0, (now - row.created_at).total_seconds()),
            can_cancel=allowed
            and row.status in {"QUEUED", "RETRY_SCHEDULED", "CLAIMED"},
            can_retry=allowed
            and row.status == "DEAD_LETTERED"
            and row.attempt_count < 5
            and now < row.retry_deadline,
        )
        return result

    def read(self, identity, job_id=None, kind=None, limit=20, offset=0):
        with self.factory() as session:
            actor = revalidate_identity(session, identity)
            if job_id:
                row = self._owned(session, actor, job_id)
                if kind:
                    model = Attempt if kind == "attempts" else Event
                    rows = session.scalars(
                        select(model)
                        .where(
                            model.tenant_id == actor.tenant_id, model.job_id == row.id
                        )
                        .order_by(model.created_at.desc(), model.id.desc())
                        .limit(100 if kind == "attempts" else 200)
                    ).all()
                    names = (
                        (
                            "number",
                            "fence",
                            "correlation_id",
                            "outcome",
                            "error_category",
                            "created_at",
                            "finished_at",
                        )
                        if kind == "attempts"
                        else ("state", "category", "correlation_id", "created_at")
                    )
                    return {
                        "items": [
                            {n: getattr(r, n) for n in names} for r in reversed(rows)
                        ]
                    }
                return self.describe(session, row, actor)
            cond = [Job.tenant_id == actor.tenant_id]
            if "settings:manage" not in actor.permissions:
                cond.append(Job.actor_id == actor.user_id)
            rows = session.scalars(
                select(Job)
                .where(*cond)
                .order_by(Job.created_at.desc(), Job.id)
                .limit(limit)
                .offset(offset)
            ).all()
            depth = session.scalar(
                select(func.count())
                .select_from(Job)
                .where(*cond, Job.status.in_(ACTIVE))
            )
            oldest = session.scalar(
                select(func.min(Job.created_at)).where(*cond, Job.status.in_(ACTIVE))
            )
            now = session.scalar(select(func.clock_timestamp()))
            return {
                "items": [self.describe(session, r, actor) for r in rows],
                "queue_depth": depth,
                "oldest_age_seconds": max(0.0, (now - oldest).total_seconds())
                if oldest
                else 0.0,
            }

    def control(self, identity, job_id, operation, correlation):
        with self.executor.transaction(identity) as (session, actor):
            row = self._owned(session, actor, job_id)
            if (
                row.actor_id != actor.user_id
                or "action:execute" not in actor.permissions
            ):
                raise HTTPException(403, "Job owner execution permission required")
            if operation == "cancel":
                if row.status == "CANCELLED":
                    return self.describe(session, row, actor)
                committed = session.scalar(
                    select(ActionExecution.id).where(
                        ActionExecution.tenant_id == row.tenant_id,
                        ActionExecution.proposal_id == row.proposal_id,
                    )
                )
                if (
                    row.status
                    not in {"QUEUED", "RETRY_SCHEDULED", "CLAIMED", "RUNNING"}
                    or committed
                ):
                    raise HTTPException(
                        409,
                        "Running or committed work cannot be claimed rolled back; reconcile first",
                    )
                row.fence += 1
                self.move(session, row, "CANCELLED", "operator_cancelled", correlation)
                self.finish_attempt(session, row, "CANCELLED", None)
            else:
                now = session.scalar(select(func.clock_timestamp()))
                if (
                    row.status != "DEAD_LETTERED"
                    or row.attempt_count >= 5
                    or now >= row.retry_deadline
                ):
                    raise HTTPException(
                        409, "Retry budget exhausted or job not dead-lettered"
                    )
                body = Submit(
                    proposal_id=row.proposal_id,
                    **ExecuteCommand.model_validate_json(
                        json.dumps(row.command)
                    ).model_dump(),
                )
                _, _, binding = self._validate_submission(
                    session, actor, body, correlation
                )
                if binding != row.binding_hash:
                    raise HTTPException(409, "job_binding_changed")
                row.max_attempts = min(5, row.attempt_count + 1)
                row.next_run_at = now + timedelta(
                    seconds=backoff(row.id, row.attempt_count)
                )
                self.move(session, row, "RETRY_SCHEDULED", "manual_retry", correlation)
            row.lease_owner = None
            row.lease_expires_at = None
            return self.describe(session, row, actor)

    def claim(self, owner):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", owner):
            raise ValueError("Invalid worker owner")
        with self.factory() as session, session.begin():
            # Shared PostgreSQL lock makes global/per-tenant caps hold across worker processes.
            session.execute(text("SELECT pg_advisory_xact_lock(9090909)"))
            live = list(
                session.scalars(
                    select(Job).where(Job.status.in_(("CLAIMED", "RUNNING")))
                )
            )
            if len(live) >= GLOBAL_LIMIT:
                return None
            busy = [j.tenant_id for j in live]
            query = select(Job).where(
                Job.status.in_(("QUEUED", "RETRY_SCHEDULED")),
                Job.next_run_at <= func.clock_timestamp(),
            )
            if busy:
                query = query.where(Job.tenant_id.not_in(busy))
            # Oldest eligible first; at most one active per tenant prevents tenant monopolization.
            row = session.scalar(
                query.order_by(Job.next_run_at, Job.created_at, Job.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if not row:
                return None
            row.fence += 1
            row.attempt_count += 1
            now = session.scalar(select(func.clock_timestamp()))
            if now >= row.retry_deadline:
                # A delayed scheduler cannot extend the original retry window.
                correlation = uuid4()
                self.move(session, row, "CLAIMED", "worker_claimed", correlation)
                session.add(
                    Attempt(
                        tenant_id=row.tenant_id,
                        job_id=row.id,
                        number=row.attempt_count,
                        fence=row.fence,
                        correlation_id=correlation,
                        outcome="CLAIMED",
                    )
                )
                session.flush()
                self.retry_or_dead(session, row, "retry_window_exhausted", correlation)
                return None
            row.lease_owner = owner
            row.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
            row.heartbeat_at = now
            correlation = uuid4()
            self.move(session, row, "CLAIMED", "worker_claimed", correlation)
            session.add(
                Attempt(
                    tenant_id=row.tenant_id,
                    job_id=row.id,
                    number=row.attempt_count,
                    fence=row.fence,
                    correlation_id=correlation,
                    outcome="CLAIMED",
                )
            )
            return row.id, row.tenant_id, row.fence

    def _leased(self, session, job_id, tenant_id, owner, fence):
        row = session.scalar(
            select(Job)
            .where(Job.id == job_id, Job.tenant_id == tenant_id)
            .with_for_update()
        )
        now = session.scalar(select(func.clock_timestamp()))
        if (
            not row
            or row.status not in {"CLAIMED", "RUNNING"}
            or row.fence != fence
            or row.lease_owner != owner
            or row.lease_expires_at <= now
        ):
            raise HTTPException(409, "worker_lease_lost")
        return row

    def finish_attempt(self, session, row, outcome, error):
        attempt = session.scalar(
            select(Attempt).where(
                Attempt.tenant_id == row.tenant_id,
                Attempt.job_id == row.id,
                Attempt.number == row.attempt_count,
            )
        )
        if attempt and attempt.finished_at is None:
            attempt.outcome = outcome
            attempt.error_category = error
            attempt.finished_at = session.scalar(select(func.clock_timestamp()))

    def retry_or_dead(self, session, row, category, correlation):
        now = session.scalar(select(func.clock_timestamp()))
        due = now + timedelta(seconds=backoff(row.id, row.attempt_count))
        if row.attempt_count >= row.max_attempts or due >= row.retry_deadline:
            self.move(session, row, "DEAD_LETTERED", category, correlation)
            session.add(
                DeadLetter(
                    tenant_id=row.tenant_id,
                    job_id=row.id,
                    attempt_count=row.attempt_count,
                    error_category=category,
                    correlation_id=correlation,
                )
            )
        else:
            row.next_run_at = due
            self.move(session, row, "RETRY_SCHEDULED", category, correlation)
        self.finish_attempt(session, row, row.status, category)
        row.lease_owner = None
        row.lease_expires_at = None

    def process(self, claim, owner, fault=None):
        job_id, tenant_id, fence = claim
        correlation = uuid4()
        with self.factory() as session, session.begin():
            row = self._leased(session, job_id, tenant_id, owner, fence)
            row.heartbeat_at = session.scalar(select(func.clock_timestamp()))
            self.move(session, row, "RUNNING", "execution_started", correlation)
            user = session.scalar(
                select(User).where(User.id == row.actor_id, User.tenant_id == tenant_id)
            )
            identity = Identity(
                row.actor_id, tenant_id, user.role, row.session_id, row.id, fence, owner
            )
            proposal = row.proposal_id
            key = row.idempotency_key
            command = ExecuteCommand.model_validate_json(json.dumps(row.command))
        if fault:
            fault("before_execution")
        try:
            result = self.executor.execute(
                identity, proposal, command, key, correlation
            )
            if fault:
                fault("after_commit")
            with self.factory() as session, session.begin():
                row = self._leased(session, job_id, tenant_id, owner, fence)
                if result.get("execution_id"):
                    row.receipt_id = UUID(result["execution_id"])
                target = (
                    "COMPLETED"
                    if result["status"] == "COMMITTED" and result["verified"]
                    else "FAILED"
                )
                self.move(
                    session,
                    row,
                    target,
                    result.get("error_code") or "verified_receipt",
                    correlation,
                )
                self.finish_attempt(session, row, target, result.get("error_code"))
                row.lease_owner = None
                row.lease_expires_at = None
        except (SQLAlchemyError, HTTPException) as exc:
            category, retryable = classify(exc)
            with self.factory() as session, session.begin():
                row = self._leased(session, job_id, tenant_id, owner, fence)
                if retryable:
                    self.retry_or_dead(session, row, category, correlation)
                else:
                    target = (
                        "FAILED"
                        if isinstance(exc, HTTPException)
                        else "RECONCILIATION_REQUIRED"
                    )
                    self.move(session, row, target, category, correlation)
                    self.finish_attempt(session, row, target, category)
                    row.lease_owner = None
                    row.lease_expires_at = None

    def reconcile(self):
        """Privileged worker scan; every effect/receipt lookup is scoped to the selected job tenant."""
        changed = 0
        with self.factory() as session, session.begin():
            rows = session.scalars(
                select(Job)
                .where(
                    (
                        Job.status.in_(("CLAIMED", "RUNNING"))
                        & (Job.lease_expires_at <= func.clock_timestamp())
                    )
                    | (Job.status == "RECONCILIATION_REQUIRED")
                )
                .order_by(Job.updated_at)
                .with_for_update(skip_locked=True)
                .limit(50)
            ).all()
            for row in rows:
                correlation = uuid4()
                original = row.status
                if original != "RECONCILIATION_REQUIRED":
                    self.move(
                        session,
                        row,
                        "RECONCILIATION_REQUIRED",
                        "lease_expired",
                        correlation,
                    )
                    row.fence += 1
                receipt = session.scalar(
                    select(ActionExecution).where(
                        ActionExecution.tenant_id == row.tenant_id,
                        (
                            (ActionExecution.idempotency_key == row.idempotency_key)
                            | (ActionExecution.proposal_id == row.proposal_id)
                        ),
                    )
                )
                if receipt:
                    try:
                        payload = ExecutionReceipt.model_validate_json(
                            json.dumps(receipt.payload)
                        )
                    except ValueError:
                        row.last_error = "receipt_invalid"
                        row.lease_owner = None
                        row.lease_expires_at = None
                        continue
                    exact = (
                        receipt.actor_id == row.actor_id
                        and receipt.proposal_id == row.proposal_id
                        and receipt.idempotency_key == row.idempotency_key
                        and receipt.request_hash == row.binding_hash
                    )
                    record = session.scalar(
                        select(BusinessRecord).where(
                            BusinessRecord.tenant_id == row.tenant_id,
                            BusinessRecord.execution_id == receipt.id,
                        )
                    )
                    approval = None
                    if row.command.get("approval_id"):
                        approval = session.scalar(
                            select(ApprovalRequest).where(
                                ApprovalRequest.tenant_id == row.tenant_id,
                                ApprovalRequest.id == UUID(row.command["approval_id"]),
                            )
                        )
                    proof = exact and (
                        not row.command.get("approval_id")
                        or (
                            approval
                            and (approval.consumed_at or payload.status == "FAILED")
                        )
                    )
                    # The receipt is the immutable atomic transaction evidence. Mutable resources can legitimately change later.
                    proof = proof and (
                        row.action_name
                        not in {
                            "create_customer_note",
                            "add_ticket_note",
                            "request_account_reactivation",
                        }
                        or payload.status == "FAILED"
                        or record is not None
                    )
                    if proof and payload.status == "COMMITTED":
                        model = (
                            Customer
                            if row.action_name == "create_customer_note"
                            else Ticket
                            if row.action_name
                            in {"add_ticket_note", "close_duplicate_ticket"}
                            else Account
                        )
                        target = session.scalar(
                            select(model).where(
                                model.tenant_id == row.tenant_id,
                                model.id == payload.target_resource_id,
                            )
                        )
                        # A later legitimate update must not erase an immutable committed receipt.
                        proof = bool(
                            target
                            and (
                                resource_binding(target)
                                == payload.after.get("resource_hash")
                                or target.updated_at > payload.created_at
                            )
                        )
                    if proof and payload.status in {"COMMITTED", "FAILED"}:
                        row.receipt_id = receipt.id
                        self.move(
                            session,
                            row,
                            "COMPLETED"
                            if payload.status == "COMMITTED" and payload.verified
                            else "FAILED",
                            "receipt_reconciled",
                            correlation,
                        )
                        self.finish_attempt(session, row, row.status, None)
                        changed += 1
                else:
                    consumed = False
                    if row.command.get("approval_id"):
                        consumed = (
                            session.scalar(
                                select(ApprovalRequest.consumed_at).where(
                                    ApprovalRequest.tenant_id == row.tenant_id,
                                    ApprovalRequest.id
                                    == UUID(row.command["approval_id"]),
                                )
                            )
                            is not None
                        )
                    if not consumed:
                        # Row lock fences all older writers. Atomic executor guarantees no receipt => no committed local mutation.
                        self.retry_or_dead(
                            session, row, "proven_unexecuted", correlation
                        )
                        changed += 1
                row.lease_owner = None
                row.lease_expires_at = None
        return changed

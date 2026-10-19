"""All durable lifecycle writes live here, scoped to a freshly validated actor/tenant."""

import hashlib
import json
import re
from datetime import timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import event, func, select, text
from sqlalchemy.dialects.postgresql import insert

from app.agents.checkpoints import Counters, Snapshot, checkpoint_evidence_findings
from app.agents.contracts import (
    TERMINAL,
    Evidence,
    InvestigationRequest,
    InvestigationResult,
    Limits,
    State,
    Step,
    transition,
)
from app.agents.persistence_contracts import InvestigationView
from app.models.entities import (
    Account,
    Customer,
    Investigation,
    InvestigationCheckpoint,
    InvestigationEvent,
    InvestigationEvidence,
    InvestigationStep,
    Ticket,
    ToolExecution,
)
from app.services.authentication import revalidate_identity
from app.services.repository import TenantRepository
from app.tools.errors import ToolError

LEASE_SECONDS = 120


def digest(data):
    return hashlib.sha256(
        json.dumps(
            data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


for _model in (InvestigationEvent, InvestigationCheckpoint, InvestigationEvidence):

    @event.listens_for(_model, "before_update")
    @event.listens_for(_model, "before_delete")
    def immutable(mapper, connection, target):
        raise ValueError("Investigation history records are append-only")


class InvestigationRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def _authorize(self, session, identity):
        session.execute(text("SELECT set_config('statement_timeout', '3000', true)"))
        session.execute(text("SELECT set_config('lock_timeout', '1000', true)"))
        trusted = revalidate_identity(session, identity)
        if "investigation:create" not in trusted.permissions:
            raise HTTPException(403, "Permission denied")
        return trusted

    def _row(self, session, identity, investigation_id, *, lock=False, review=False):
        trusted = self._authorize(session, identity)
        query = select(Investigation).where(
            Investigation.id == investigation_id,
            Investigation.tenant_id == trusted.tenant_id,
            (Investigation.actor_id == trusted.user_id)
            | (review and "action:approve" in trusted.permissions),
        )
        row = session.scalar(query.with_for_update() if lock else query)
        if row is None:
            raise HTTPException(404, "Investigation not found")
        return row

    def _checkpoint(self, session, row):
        checkpoint = session.scalar(
            select(InvestigationCheckpoint)
            .where(
                InvestigationCheckpoint.tenant_id == row.tenant_id,
                InvestigationCheckpoint.investigation_id == row.id,
            )
            .order_by(InvestigationCheckpoint.sequence.desc())
            .limit(1)
        )
        if checkpoint is None or checkpoint.checksum != digest(checkpoint.payload):
            raise ValueError("Invalid checkpoint checksum")
        snapshot = Snapshot.model_validate_json(json.dumps(checkpoint.payload))
        if (
            snapshot.plan_reference != row.id
            or snapshot.step_index != row.current_step
            or snapshot.planner_type != row.planner_type
            or snapshot.planner_version != row.planner_version
            or snapshot.state.value != row.status
            or snapshot.counters
            != Counters.model_validate_json(json.dumps(row.budget_counters))
            or snapshot.limits
            != Limits.model_validate_json(json.dumps(row.budget_limits))
            or snapshot.last_event_sequence != row.event_sequence
            or checkpoint.sequence != row.checkpoint_sequence
            or checkpoint.applied_version != row.version
        ):
            raise ValueError("Checkpoint does not match investigation")
        ids = tuple(
            session.scalars(
                select(InvestigationEvidence.id)
                .where(
                    InvestigationEvidence.tenant_id == row.tenant_id,
                    InvestigationEvidence.investigation_id == row.id,
                )
                .order_by(InvestigationEvidence.sequence)
            )
        )
        if ids != snapshot.evidence_ids:
            raise ValueError("Checkpoint evidence references do not match")
        stored_steps = tuple(
            Step.model_validate_json(json.dumps(s.definition))
            for s in session.scalars(
                select(InvestigationStep)
                .where(
                    InvestigationStep.tenant_id == row.tenant_id,
                    InvestigationStep.investigation_id == row.id,
                )
                .order_by(InvestigationStep.step_index)
            )
        )
        if stored_steps != snapshot.steps:
            raise ValueError("Checkpoint steps do not match durable history")
        return snapshot, checkpoint.created_at

    def _evidence(self, session, row):
        evidence = [
            Evidence.model_validate_json(json.dumps(r.payload))
            for r in session.scalars(
                select(InvestigationEvidence)
                .where(
                    InvestigationEvidence.tenant_id == row.tenant_id,
                    InvestigationEvidence.investigation_id == row.id,
                )
                .order_by(InvestigationEvidence.sequence)
            )
        ]
        for envelope in evidence:
            self._validate_sources(row, envelope)
        return evidence

    @staticmethod
    def _validate_sources(row, envelope):
        from app.services.evidence import stable

        for source in envelope.sources:
            if (
                source.tenant_id != row.tenant_id
                or source.investigation_id != row.id
                or source.tool_execution_id != envelope.tool_execution_id
                or source.collected_at != envelope.collected_at
                or source.evidence_id
                != stable(
                    row.id,
                    row.tenant_id,
                    envelope.tool_execution_id,
                    source.source_reference,
                )
            ):
                raise HTTPException(503, "Evidence provenance integrity check failed")

    def _write(self, session, row, snapshot, events):
        for kind, data in events:
            row.event_sequence += 1
            session.add(
                InvestigationEvent(
                    tenant_id=row.tenant_id,
                    investigation_id=row.id,
                    sequence=row.event_sequence,
                    event_type=kind,
                    data=data,
                )
            )
        row.version += 1
        row.checkpoint_sequence += 1
        snapshot = Snapshot.model_validate_json(
            snapshot.model_copy(
                update={"last_event_sequence": row.event_sequence}
            ).model_dump_json()
        )
        row.status = snapshot.state.value
        row.current_step = snapshot.step_index
        row.budget_counters = snapshot.counters.model_dump(mode="json")
        session.add(
            InvestigationCheckpoint(
                tenant_id=row.tenant_id,
                investigation_id=row.id,
                sequence=row.checkpoint_sequence,
                applied_version=row.version,
                schema_version=1,
                payload=snapshot.model_dump(mode="json"),
                checksum=digest(snapshot.model_dump(mode="json")),
            )
        )
        session.flush()
        return row.version, snapshot

    def create(
        self,
        identity,
        request: InvestigationRequest,
        correlation_id: UUID,
        limits: Limits,
        key: str | None = None,
        *,
        planner_type="deterministic_mock",
        planner_version="1.0",
        planner_config_hash=None,
    ):
        key = key or str(uuid4())
        if not re.fullmatch(r"[a-zA-Z0-9_-]{16,80}", key):
            raise HTTPException(422, "Invalid idempotency key")
        payload = request.model_dump(mode="json")
        hashed = digest(payload)
        with self.session_factory() as session, session.begin():
            trusted = self._authorize(session, identity)
            lock_key = int(
                hashlib.sha256(
                    f"{trusted.tenant_id}:{trusted.user_id}:{key}".encode()
                ).hexdigest()[:15],
                16,
            )
            session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key}
            )
            existing = session.scalar(
                select(Investigation).where(
                    Investigation.tenant_id == trusted.tenant_id,
                    Investigation.actor_id == trusted.user_id,
                    Investigation.idempotency_key == key,
                )
            )
            if existing:
                if existing.request_hash != hashed:
                    raise HTTPException(
                        409, "Idempotency key already binds a different request"
                    )
                return existing.id, False
            if (
                TenantRepository(session, trusted).get(Customer, request.customer_id)
                is None
            ):
                raise HTTPException(404, "Resource not found")
            if (
                request.ticket_id is not None
                and session.scalar(
                    select(Ticket.id)
                    .join(
                        Account,
                        (Account.id == Ticket.account_id)
                        & (Account.tenant_id == Ticket.tenant_id),
                    )
                    .where(
                        Ticket.id == request.ticket_id,
                        Ticket.tenant_id == trusted.tenant_id,
                        Account.tenant_id == trusted.tenant_id,
                        Account.customer_id == request.customer_id,
                    )
                )
                is None
            ):
                raise HTTPException(404, "Resource not found")
            ident = uuid4()
            result = session.execute(
                insert(Investigation)
                .values(
                    id=ident,
                    tenant_id=trusted.tenant_id,
                    actor_id=trusted.user_id,
                    customer_id=request.customer_id,
                    ticket_id=request.ticket_id,
                    goal=request.goal,
                    context=request.context.model_dump(mode="json")
                    if request.context
                    else None,
                    status=State.CREATED.value,
                    planner_type=planner_type,
                    planner_version=planner_version,
                    idempotency_key=key,
                    request_hash=hashed,
                    version=1,
                    event_sequence=1,
                    checkpoint_sequence=1,
                    current_step=0,
                    budget_counters=Counters().model_dump(mode="json"),
                    budget_limits=limits.model_dump(mode="json"),
                    cancel_requested=False,
                )
                .on_conflict_do_nothing(
                    index_elements=["tenant_id", "actor_id", "idempotency_key"]
                )
                .returning(Investigation.id)
            ).scalar_one_or_none()
            if result is None:
                row = session.scalar(
                    select(Investigation).where(
                        Investigation.tenant_id == trusted.tenant_id,
                        Investigation.actor_id == trusted.user_id,
                        Investigation.idempotency_key == key,
                    )
                )
                if row.request_hash != hashed:
                    raise HTTPException(
                        409, "Idempotency key already binds a different request"
                    )
                return row.id, False
            snapshot = Snapshot(
                planner_type=planner_type,
                planner_version=planner_version,
                planner_config_hash=planner_config_hash,
                state=State.CREATED,
                history=(State.CREATED,),
                phase="created",
                step_index=0,
                plan_reference=ident,
                counters=Counters(),
                limits=limits,
                last_event_sequence=1,
                correlation_id=correlation_id,
            )
            session.add(
                InvestigationEvent(
                    tenant_id=trusted.tenant_id,
                    investigation_id=ident,
                    sequence=1,
                    event_type="investigation_created",
                    data={"correlation_id": str(correlation_id)},
                )
            )
            session.add(
                InvestigationCheckpoint(
                    tenant_id=trusted.tenant_id,
                    investigation_id=ident,
                    sequence=1,
                    applied_version=1,
                    schema_version=1,
                    payload=snapshot.model_dump(mode="json"),
                    checksum=digest(snapshot.model_dump(mode="json")),
                )
            )
            return ident, True

    def claim(self, identity, investigation_id, *, recovery=False):
        with self.session_factory() as session, session.begin():
            row = self._row(session, identity, investigation_id, lock=True)
            if State(row.status) in TERMINAL:
                return None
            now = session.scalar(select(func.clock_timestamp()))
            if row.lease_expires_at and row.lease_expires_at > now:
                raise HTTPException(409, "Investigation has an active execution lease")
            if not recovery and row.lease_owner is not None:
                raise HTTPException(409, "Explicit recovery is required")
            owner = uuid4()
            row.lease_owner, row.lease_expires_at = (
                owner,
                now + timedelta(seconds=LEASE_SECONDS),
            )
            row.started_at = row.started_at or now
            corrupt = False
            try:
                snapshot, collected = self._checkpoint(session, row)
            except (ValueError, ToolError):
                if not recovery:
                    raise HTTPException(
                        409, "Checkpoint invalid; request recovery"
                    ) from None
                corrupt = True
                history = [State.CREATED]
                for ev in session.scalars(
                    select(InvestigationEvent)
                    .where(
                        InvestigationEvent.tenant_id == row.tenant_id,
                        InvestigationEvent.investigation_id == row.id,
                        InvestigationEvent.event_type == "state_changed",
                    )
                    .order_by(InvestigationEvent.sequence)
                ):
                    history.append(transition(history[-1], State(ev.data["to"])))
                steps = tuple(
                    Step.model_validate_json(json.dumps(s.definition))
                    for s in session.scalars(
                        select(InvestigationStep)
                        .where(
                            InvestigationStep.tenant_id == row.tenant_id,
                            InvestigationStep.investigation_id == row.id,
                        )
                        .order_by(InvestigationStep.step_index)
                    )
                )
                snapshot = Snapshot(
                    planner_type=row.planner_type,
                    planner_version=row.planner_version,
                    state=State(row.status),
                    history=tuple(history),
                    phase="state_changed",
                    step_index=len(steps),
                    plan_reference=row.id,
                    steps=steps,
                    completed_step_ids=tuple(
                        s.step_id for s in steps if s.status == "succeeded"
                    ),
                    counters=Counters.model_validate_json(
                        json.dumps(row.budget_counters)
                    ),
                    limits=Limits.model_validate_json(json.dumps(row.budget_limits)),
                    evidence_ids=tuple(
                        e.evidence_id for e in self._evidence(session, row)
                    ),
                    last_event_sequence=row.event_sequence,
                    correlation_id=uuid4(),
                )
                collected = now
            events = [
                (
                    "recovery_attempted" if recovery else "execution_acquired",
                    {"checkpoint_sequence": row.checkpoint_sequence},
                )
            ]
            if recovery:
                snapshot = snapshot.model_copy(
                    update={
                        "recovery_attempts": min(20, snapshot.recovery_attempts + 1)
                    }
                )
                if snapshot.recovery_attempts >= 20:
                    corrupt = True
                snapshot = snapshot.model_copy(
                    update={
                        "counters": snapshot.counters.model_copy(
                            update={
                                "elapsed_ms": snapshot.counters.elapsed_ms
                                + max(0.0, (now - collected).total_seconds() * 1000)
                            }
                        )
                    }
                )
            corrupt = corrupt or snapshot.recovery_error is not None
            if corrupt:
                snapshot = snapshot.model_copy(
                    update={"recovery_error": "corrupt_checkpoint"}
                )
            version, snapshot = self._write(session, row, snapshot, events)
            request = InvestigationRequest.model_validate_json(
                json.dumps(
                    {
                        "goal": row.goal,
                        "customer_id": str(row.customer_id),
                        "ticket_id": str(row.ticket_id) if row.ticket_id else None,
                        "context": row.context,
                    }
                )
            )
            evidence = self._evidence(session, row)
            return owner, version, snapshot, request, evidence, corrupt

    def heartbeat(self, identity, investigation_id, owner):
        with self.session_factory() as session, session.begin():
            row = self._row(session, identity, investigation_id, lock=True)
            now = session.scalar(select(func.clock_timestamp()))
            if (
                row.lease_owner != owner
                or not row.lease_expires_at
                or row.lease_expires_at <= now
                or State(row.status) in TERMINAL
            ):
                raise HTTPException(409, "Execution lease lost")
            row.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
            return row.cancel_requested

    def cancellation_requested(self, identity, investigation_id, owner):
        with self.session_factory() as session, session.begin():
            row = self._row(session, identity, investigation_id)
            now = session.scalar(select(func.clock_timestamp()))
            if (
                row.lease_owner != owner
                or row.lease_expires_at is None
                or row.lease_expires_at <= now
            ):
                raise HTTPException(409, "Execution lease lost")
            return row.cancel_requested

    def save(
        self,
        identity,
        investigation_id,
        owner,
        expected_version,
        snapshot: Snapshot,
        events,
        *,
        evidence: Evidence | None = None,
        final: InvestigationResult | None = None,
    ):
        snapshot = Snapshot.model_validate_json(snapshot.model_dump_json())
        with self.session_factory() as session, session.begin():
            row = self._row(session, identity, investigation_id, lock=True)
            now = session.scalar(select(func.clock_timestamp()))
            if (
                row.version != expected_version
                or row.lease_owner != owner
                or row.lease_expires_at is None
                or row.lease_expires_at <= now
                or State(row.status) in TERMINAL
            ):
                raise HTTPException(
                    409, "Stale investigation version or execution lease"
                )
            if row.cancel_requested and snapshot.state not in {
                State.CANCELLED,
                State.FAILED,
            }:
                raise HTTPException(409, "Cancellation requested")
            # Cancellation events update version independently; caller must reload before finalization.
            if (
                snapshot.plan_reference != row.id
                or snapshot.limits
                != Limits.model_validate_json(json.dumps(row.budget_limits))
            ):
                raise HTTPException(409, "Checkpoint identity or budgets changed")
            if (
                snapshot.planner_type != row.planner_type
                or snapshot.planner_version != row.planner_version
            ):
                raise HTTPException(409, "Planner identity changed")
            previous = session.scalar(
                select(InvestigationCheckpoint)
                .where(
                    InvestigationCheckpoint.tenant_id == row.tenant_id,
                    InvestigationCheckpoint.investigation_id == row.id,
                )
                .order_by(InvestigationCheckpoint.sequence.desc())
                .limit(1)
            )
            prior_trace = (
                previous.payload.get("tool_selection_trace", []) if previous else []
            )
            if (
                snapshot.model_dump(mode="json")["tool_selection_trace"][
                    : len(prior_trace)
                ]
                != prior_trace
            ):
                raise HTTPException(409, "Planner trace cannot be rewritten")
            if previous and snapshot.planner_config_hash != previous.payload.get(
                "planner_config_hash"
            ):
                raise HTTPException(409, "Planner configuration changed")
            previous_counters = Counters.model_validate_json(
                json.dumps(row.budget_counters)
            )
            for key in (
                "tool_calls",
                "planning_iterations",
                "observation_bytes",
                "elapsed_ms",
                "provider_requests",
                "provider_output_tokens_reserved",
                "provider_cost_microusd_reserved",
                "no_progress",
            ):
                if getattr(snapshot.counters, key) < getattr(previous_counters, key):
                    raise HTTPException(409, "Execution budgets cannot reset")
            if snapshot.state.value != row.status:
                transition(State(row.status), snapshot.state)
            for index, step in enumerate(snapshot.steps, 1):
                stored = session.scalar(
                    select(InvestigationStep).where(
                        InvestigationStep.tenant_id == row.tenant_id,
                        InvestigationStep.investigation_id == row.id,
                        InvestigationStep.step_id == step.step_id,
                    )
                )
                if stored:
                    prior = Step.model_validate_json(json.dumps(stored.definition))
                    if stored.step_index != index:
                        raise HTTPException(409, "Step ordering changed")
                    if prior.model_dump(exclude={"status"}) != step.model_dump(
                        exclude={"status"}
                    ) or (prior.status != "proposed" and prior.status != step.status):
                        raise HTTPException(409, "Completed steps cannot be reapplied")
                    if prior.status != step.status:
                        stored.status = step.status
                        stored.definition = step.model_dump(mode="json")
                else:
                    session.add(
                        InvestigationStep(
                            tenant_id=row.tenant_id,
                            investigation_id=row.id,
                            step_id=step.step_id,
                            step_index=index,
                            definition=step.model_dump(mode="json"),
                            status=step.status,
                        )
                    )
            if evidence:
                self._validate_sources(row, evidence)
                audit = session.scalar(
                    select(ToolExecution).where(
                        ToolExecution.id == evidence.tool_execution_id,
                        ToolExecution.tenant_id == row.tenant_id,
                        ToolExecution.actor_id == row.actor_id,
                        ToolExecution.outcome == "success",
                        ToolExecution.tool_name == evidence.tool_name,
                        ToolExecution.tool_version == evidence.tool_version,
                    )
                )
                if audit is None:
                    raise HTTPException(409, "Evidence execution is not valid")
                session.add(
                    InvestigationEvidence(
                        id=evidence.evidence_id,
                        tenant_id=row.tenant_id,
                        investigation_id=row.id,
                        tool_execution_id=evidence.tool_execution_id,
                        sequence=len(snapshot.evidence_ids),
                        payload=evidence.model_dump(mode="json"),
                    )
                )
            if snapshot.state.value != row.status:
                events = [
                    ("state_changed", {"from": row.status, "to": snapshot.state.value}),
                    *events,
                ]
            if final:
                if (
                    final.investigation_id != row.id
                    or final.status != snapshot.state
                    or final.status not in TERMINAL
                    or tuple(e.evidence_id for e in final.evidence)
                    != snapshot.evidence_ids
                    or final.findings
                    != tuple(checkpoint_evidence_findings(list(final.evidence)))
                    or final.tool_calls_performed != snapshot.counters.tool_calls
                ):
                    raise HTTPException(409, "Invalid final result")
                from app.services.evidence import EvidenceRetrievalService

                if (
                    final.reconciliation is not None
                    and final.reconciliation
                    != EvidenceRetrievalService().reconcile(row.id, final.evidence)
                ):
                    raise HTTPException(409, "Invalid evidence reconciliation")
                row.final_result = final.model_dump(mode="json")
                row.stop_reason = final.stop_reason
                row.completed_at = now
                row.lease_owner = None
                row.lease_expires_at = None
            return self._write(session, row, snapshot, events)

    def cancel(self, identity, investigation_id):
        with self.session_factory() as session, session.begin():
            row = self._row(session, identity, investigation_id, lock=True)
            if State(row.status) in TERMINAL or row.cancel_requested:
                return
            snapshot, _ = self._checkpoint(session, row)
            row.cancel_requested = True
            now = session.scalar(select(func.clock_timestamp()))
            events = [("cancellation_requested", {})]
            if row.lease_expires_at is None or row.lease_expires_at <= now:
                stopped = tuple(
                    st.model_copy(update={"status": "failed"})
                    if st.status == "proposed"
                    else st
                    for st in snapshot.steps
                )
                for st in stopped:
                    stored = session.scalar(
                        select(InvestigationStep).where(
                            InvestigationStep.tenant_id == row.tenant_id,
                            InvestigationStep.investigation_id == row.id,
                            InvestigationStep.step_id == st.step_id,
                        )
                    )
                    if stored and stored.status != st.status:
                        stored.status = st.status
                        stored.definition = st.model_dump(mode="json")
                snapshot = snapshot.model_copy(
                    update={
                        "state": transition(snapshot.state, State.CANCELLED),
                        "history": snapshot.history + (State.CANCELLED,),
                        "phase": "final",
                        "steps": stopped,
                        "inflight_step": None,
                    }
                )
                evidence = self._evidence(session, row)
                result = InvestigationResult(
                    tool_selection_trace=snapshot.tool_selection_trace
                    if snapshot
                    else (),
                    iteration_count=snapshot.counters.planning_iterations
                    if snapshot
                    else 0,
                    execution_limits=snapshot.limits if snapshot else None,
                    investigation_id=row.id,
                    goal=row.goal,
                    status=State.CANCELLED,
                    history=snapshot.history,
                    steps=stopped,
                    evidence=tuple(evidence),
                    findings=tuple(checkpoint_evidence_findings(evidence)),
                    recommended_next_steps=(
                        "Request authorized human review before any operational action.",
                    ),
                    uncertainty=(
                        "Investigation cancelled; no operational decision was made.",
                    ),
                    stop_reason="persistent_cancellation_requested",
                    tool_calls_performed=snapshot.counters.tool_calls,
                    duration_ms=snapshot.counters.elapsed_ms,
                    human_review_recommended=True,
                    correlation_id=snapshot.correlation_id,
                )
                row.final_result = result.model_dump(mode="json")
                row.completed_at = now
                row.stop_reason = result.stop_reason
                row.lease_owner = None
                row.lease_expires_at = None
                events += [
                    ("state_changed", {"from": row.status, "to": "CANCELLED"}),
                    ("investigation_cancelled", {"stop_reason": result.stop_reason}),
                ]
            self._write(session, row, snapshot, events)

    def load(self, identity, investigation_id):
        with self.session_factory() as session, session.begin():
            row = self._row(session, identity, investigation_id, lock=True)
            snapshot, _ = self._checkpoint(session, row)
            return row.version, snapshot, row.cancel_requested

    def get(self, identity, investigation_id, *, review=False):
        with self.session_factory() as session, session.begin():
            row = self._row(
                session, identity, investigation_id, lock=True, review=review
            )
            valid = True
            try:
                snapshot, _ = self._checkpoint(session, row)
            except (ValueError, ToolError):
                snapshot = None
                valid = False
            evidence = self._evidence(session, row)
            if row.final_result is not None:
                result = InvestigationResult.model_validate_json(
                    json.dumps(row.final_result)
                )
                known_ids = {e.evidence_id for e in evidence}
                if (
                    result.investigation_id != row.id
                    or result.status.value != row.status
                    or result.goal != row.goal
                    or result.tool_calls_performed != row.budget_counters["tool_calls"]
                    or (
                        "iteration_count" in row.final_result
                        and result.iteration_count
                        != row.budget_counters["planning_iterations"]
                    )
                    or result.evidence != tuple(evidence)
                    or result.findings != tuple(checkpoint_evidence_findings(evidence))
                    or any(
                        not set(f.evidence_ids) <= known_ids for f in result.findings
                    )
                    or (snapshot is not None and result.history != snapshot.history)
                    or (
                        snapshot is not None
                        and result.tool_selection_trace != snapshot.tool_selection_trace
                    )
                ):
                    raise HTTPException(
                        503, "Investigation result integrity check failed"
                    )
            else:
                result = InvestigationResult(
                    tool_selection_trace=snapshot.tool_selection_trace
                    if snapshot
                    else (),
                    iteration_count=snapshot.counters.planning_iterations
                    if snapshot
                    else 0,
                    execution_limits=snapshot.limits if snapshot else None,
                    investigation_id=row.id,
                    goal=row.goal,
                    status=State(row.status),
                    history=snapshot.history if snapshot else (),
                    steps=snapshot.steps if snapshot else (),
                    evidence=tuple(evidence),
                    findings=tuple(checkpoint_evidence_findings(evidence)),
                    recommended_next_steps=(),
                    uncertainty=(
                        "Investigation is incomplete; no operational decision has been made.",
                    ),
                    stop_reason="cancellation_requested"
                    if row.cancel_requested
                    else ("in_progress" if valid else "checkpoint_invalid"),
                    tool_calls_performed=row.budget_counters["tool_calls"],
                    duration_ms=float(row.budget_counters["elapsed_ms"]),
                    human_review_recommended=True,
                    correlation_id=snapshot.correlation_id if snapshot else row.id,
                )
            from app.services.evidence import EvidenceRetrievalService

            if (
                result.reconciliation is not None
                and result.reconciliation
                != EvidenceRetrievalService().reconcile(row.id, evidence)
            ):
                raise HTTPException(503, "Reconciliation integrity check failed")
            # Derive new metadata from trusted durable counters for historical results too.
            result = result.model_copy(
                update={
                    "iteration_count": row.budget_counters["planning_iterations"],
                    "execution_limits": Limits.model_validate_json(
                        json.dumps(row.budget_limits)
                    ),
                }
            )
            now = session.scalar(select(func.clock_timestamp()))
            return InvestigationView(
                **result.model_dump(),
                version=row.version,
                customer_id=row.customer_id,
                ticket_id=row.ticket_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
                checkpoint_sequence=row.checkpoint_sequence,
                checkpoint_valid=valid,
                recovery_attempts=snapshot.recovery_attempts if snapshot else 0,
                cancel_requested=row.cancel_requested,
                lease_expires_at=row.lease_expires_at,
                recovery_available=State(row.status) not in TERMINAL
                and (row.lease_expires_at is None or row.lease_expires_at <= now),
                planner_type=row.planner_type,
                planner_version=row.planner_version,
                budget_counters=Counters.model_validate_json(
                    json.dumps(row.budget_counters)
                ),
            )

    def list(self, identity, *, limit=20, offset=0, status=None, customer_id=None):
        if not 1 <= limit <= 50 or not 0 <= offset <= 10000:
            raise HTTPException(422, "Invalid pagination")
        with self.session_factory() as session, session.begin():
            trusted = self._authorize(session, identity)
            filters = [
                Investigation.tenant_id == trusted.tenant_id,
                Investigation.actor_id == trusted.user_id,
            ]
            if status is not None:
                filters.append(Investigation.status == State(status).value)
            if customer_id is not None:
                filters.append(Investigation.customer_id == customer_id)
            rows = session.scalars(
                select(Investigation)
                .where(*filters)
                .order_by(Investigation.created_at.desc(), Investigation.id.asc())
                .limit(limit)
                .offset(offset)
            ).all()
            return {
                "items": [
                    {
                        "investigation_id": r.id,
                        "customer_id": r.customer_id,
                        "goal": r.goal,
                        "status": r.status,
                        "created_at": r.created_at,
                        "updated_at": r.updated_at,
                        "stop_reason": r.stop_reason,
                        "version": r.version,
                        "cancel_requested": r.cancel_requested,
                    }
                    for r in rows
                ],
                "total": session.scalar(
                    select(func.count()).select_from(Investigation).where(*filters)
                ),
                "limit": limit,
                "offset": offset,
            }

    def records(self, identity, investigation_id, kind, *, limit=50, after=0):
        if (
            kind not in {"events", "evidence"}
            or not 1 <= limit <= 100
            or not 0 <= after <= 1000000
        ):
            raise HTTPException(422, "Invalid pagination")
        model = InvestigationEvent if kind == "events" else InvestigationEvidence
        with self.session_factory() as session, session.begin():
            row = self._row(session, identity, investigation_id)
            rows = session.scalars(
                select(model)
                .where(
                    model.tenant_id == row.tenant_id,
                    model.investigation_id == row.id,
                    model.sequence > after,
                )
                .order_by(model.sequence)
                .limit(limit)
            ).all()
            items = [
                {
                    "sequence": r.sequence,
                    "created_at": r.created_at,
                    **(
                        {"event_type": r.event_type, "data": r.data}
                        if kind == "events"
                        else {
                            "evidence": Evidence.model_validate_json(
                                json.dumps(r.payload)
                            ).model_dump(mode="json")
                        }
                    ),
                }
                for r in rows
            ]
            return {
                "items": items,
                "limit": limit,
                "next_after": rows[-1].sequence if rows else after,
            }

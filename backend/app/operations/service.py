"""Tenant-scoped operational read models. No business execution or repair path."""

import json
from contextlib import contextmanager
from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import Uuid, case, cast, func, literal, select, text, union_all
from sqlalchemy.dialects.postgresql import insert

from app.models.entities import (
    ActionExecution,
    ActionExecutionEvent,
    ActionProposal,
    ApprovalDecision,
    ApprovalRequest,
    ExecutionJob,
    ExecutionJobAttempt,
    ExecutionJobEvent,
    Investigation,
    InvestigationEvent,
    InvestigationEvidence,
    OperationsConfig,
    OperationsRateBucket,
    PolicyDecisionReceipt,
    SecurityEvent,
    ToolExecution,
    User,
    WorkerObservation,
)
from app.models.entities import (
    OperationsIncident as Incident,
)
from app.models.entities import (
    OperationsIncidentEvent as IncidentEvent,
)
from app.operations.contracts import Thresholds
from app.services.authentication import revalidate_identity

TERMINAL = ("COMPLETED", "FAILED", "DEAD_LETTERED")
OPEN = ("OPEN", "ACKNOWLEDGED", "INVESTIGATING")
EXPECTED_REVISION = "0009_operations"


def tenant_scope(actor, model, owner):
    cond = [model.tenant_id == actor.tenant_id]
    if actor.role == "operator":
        cond.append(owner == actor.user_id)
    return cond


def rate(n, d):
    return {"numerator": n, "denominator": d, "percent": 100.0 * n / d if d else None}


def summary(session, expression, conditions):
    row = session.execute(
        select(
            func.count(expression),
            func.avg(expression),
            func.percentile_cont(0.5).within_group(expression),
            func.percentile_cont(0.95).within_group(expression),
        ).where(*conditions)
    ).one()
    return dict(
        zip(
            ("count", "mean_seconds", "p50_seconds", "p95_seconds"),
            [int(row[0]), *[float(v) if v is not None else None for v in row[1:]]],
            strict=True,
        )
    )


class OperationsMetricsService:
    def __init__(self, factory):
        self.factory = factory

    @contextmanager
    def context(self, identity, mutation=False):
        # Rate accounting commits independently, including denied requests, without
        # introducing concurrent upsert conflicts into the repeatable-read snapshot.
        with self.factory() as limiter, limiter.begin():
            actor = revalidate_identity(limiter, identity)
            now = limiter.scalar(select(func.clock_timestamp()))
            kind = "write" if mutation else "read"
            bucket = OperationsRateBucket
            stmt = insert(bucket).values(
                id=uuid4(),
                tenant_id=actor.tenant_id,
                actor_id=actor.user_id,
                kind=kind,
                window_started_at=now,
                attempts=1,
            )
            reset = bucket.window_started_at <= now - timedelta(minutes=1)
            attempts = limiter.scalar(
                stmt.on_conflict_do_update(
                    index_elements=["tenant_id", "actor_id", "kind"],
                    set_={
                        "attempts": case((reset, 1), else_=bucket.attempts + 1),
                        "window_started_at": case(
                            (reset, now), else_=bucket.window_started_at
                        ),
                    },
                ).returning(bucket.attempts)
            )
            if attempts > (30 if mutation else 120):
                raise HTTPException(
                    429, "operations_rate_limit", headers={"Retry-After": "60"}
                )
        with self.factory() as s:
            s.connection(execution_options={"isolation_level": "REPEATABLE READ"})
            try:
                s.execute(text("SET LOCAL statement_timeout='3000ms'"))
                s.execute(text("SET LOCAL lock_timeout='1000ms'"))
                actor = revalidate_identity(s, identity)
                if mutation:
                    s.scalar(
                        select(User)
                        .where(
                            User.tenant_id == actor.tenant_id, User.id == actor.user_id
                        )
                        .with_for_update()
                    )
                    actor = revalidate_identity(s, identity)
                now = s.scalar(select(func.clock_timestamp()))
                yield s, actor, now
                s.commit()
            except BaseException:
                s.rollback()
                raise

    def thresholds(self, s, actor):
        value = s.scalar(
            select(OperationsConfig.thresholds).where(
                OperationsConfig.tenant_id == actor.tenant_id
            )
        )
        return (
            Thresholds.model_validate_json(json.dumps(value)) if value else Thresholds()
        )

    def configure(self, identity, body, correlation):
        with self.context(identity, True) as (s, actor, now):
            if "settings:manage" not in actor.permissions:
                raise HTTPException(403, "Tenant administrator required")
            stmt = insert(OperationsConfig).values(
                id=uuid4(),
                tenant_id=actor.tenant_id,
                thresholds=body.model_dump(mode="json"),
            )
            s.execute(
                stmt.on_conflict_do_update(
                    index_elements=["tenant_id"],
                    set_={
                        "thresholds": body.model_dump(mode="json"),
                        "updated_at": now,
                    },
                )
            )
            self.audit(s, actor, None, correlation, "operational_configuration_changed")
            return body

    def audit(self, s, actor, entity, correlation, kind):
        s.add(
            SecurityEvent(
                tenant_id=actor.tenant_id,
                actor_id=actor.user_id,
                resource_type="operations",
                resource_id=entity,
                request_id=correlation,
                event_type=kind,
                outcome="recorded",
            )
        )

    def overview(self, identity, window):
        with self.context(identity) as (s, actor, now):
            start, end = window.resolve(now)
            data = self.metrics(s, actor, start, end, now)
            thresholds = self.thresholds(s, actor)
            health = self.health(s, actor, data, thresholds, now)
            alerts = self.alerts(data, health, thresholds)
            return {
                "start": start,
                "end": end,
                "snapshot_at": now,
                "scope": "own" if actor.role == "operator" else "tenant",
                "metrics": data,
                "thresholds": thresholds,
                "health": health,
                "alerts": alerts,
                "recent": self.activity(s, actor, start, end, limit=10),
            }

    def metrics(self, s, actor, start, end, now):
        inv = tenant_scope(actor, Investigation, Investigation.actor_id)
        jobs = tenant_scope(actor, ExecutionJob, ExecutionJob.actor_id)
        approvals = tenant_scope(actor, ApprovalRequest, ApprovalRequest.requested_by)
        incidents = tenant_scope(actor, Incident, Incident.visible_actor_id)

        def cohort(model, cond):
            return [*cond, model.created_at >= start, model.created_at < end]

        ic = dict(
            s.execute(
                select(Investigation.status, func.count())
                .where(*cohort(Investigation, inv))
                .group_by(Investigation.status)
            ).all()
        )
        jc = dict(
            s.execute(
                select(ExecutionJob.status, func.count())
                .where(*cohort(ExecutionJob, jobs))
                .group_by(ExecutionJob.status)
            ).all()
        )
        inv_total = sum(ic.values())
        job_total = sum(jc.values())
        pending, expiring = s.execute(
            select(
                func.count(),
                func.count().filter(
                    ApprovalRequest.expires_at <= now + timedelta(minutes=15)
                ),
            ).where(
                *approvals,
                ApprovalRequest.status == "PENDING",
                ApprovalRequest.expires_at > now,
            )
        ).one()
        depth, oldest = s.execute(
            select(func.count(), func.min(ExecutionJob.created_at)).where(
                *jobs,
                ExecutionJob.status.in_(
                    ("QUEUED", "RETRY_SCHEDULED", "CLAIMED", "RUNNING")
                ),
            )
        ).one()
        recon = s.scalar(
            select(func.count())
            .select_from(ExecutionJob)
            .where(*jobs, ExecutionJob.status == "RECONCILIATION_REQUIRED")
        )
        open_inc = s.scalar(
            select(func.count())
            .select_from(Incident)
            .where(*incidents, Incident.status.in_(OPEN))
        )
        event_scope = [
            ExecutionJobEvent.tenant_id == actor.tenant_id,
            ExecutionJobEvent.job_id.in_(select(ExecutionJob.id).where(*jobs)),
            ExecutionJobEvent.created_at >= start,
            ExecutionJobEvent.created_at < end,
        ]
        retried = s.scalar(
            select(func.count(func.distinct(ExecutionJobEvent.job_id))).where(
                *event_scope,
                ExecutionJobEvent.state == "RETRY_SCHEDULED",
                ExecutionJobEvent.category != "duplicate_submission",
                ExecutionJobEvent.job_id.in_(
                    select(ExecutionJob.id).where(*cohort(ExecutionJob, jobs))
                ),
            )
        )
        leases = s.scalar(
            select(func.count())
            .select_from(ExecutionJobEvent)
            .where(*event_scope, ExecutionJobEvent.category == "lease_expired")
        )
        invdur = summary(
            s,
            func.extract(
                "epoch", Investigation.completed_at - Investigation.started_at
            ),
            [
                *cohort(Investigation, inv),
                Investigation.completed_at.is_not(None),
                Investigation.started_at.is_not(None),
            ],
        )
        # First approve/reject per request: one duration sample, unaffected by cancellation or later notes.
        first = (
            select(
                ApprovalDecision.approval_id.label("approval_id"),
                func.min(ApprovalDecision.created_at).label("decided"),
            )
            .where(
                ApprovalDecision.tenant_id == actor.tenant_id,
                ApprovalDecision.status.in_(("APPROVED", "REJECTED")),
            )
            .where(
                ApprovalDecision.approval_id.in_(
                    select(ApprovalRequest.id).where(
                        *cohort(ApprovalRequest, approvals)
                    )
                )
            )
            .group_by(ApprovalDecision.approval_id)
            .subquery()
        )
        decision_expr = (
            select(
                ApprovalRequest.id,
                func.extract(
                    "epoch", first.c.decided - ApprovalRequest.created_at
                ).label("seconds"),
            )
            .join(first, first.c.approval_id == ApprovalRequest.id)
            .where(*cohort(ApprovalRequest, approvals))
            .subquery()
        )
        turnaround = summary(s, decision_expr.c.seconds, [])
        apcounts = dict(
            s.execute(
                select(
                    ApprovalDecision.status,
                    func.count(func.distinct(ApprovalDecision.approval_id)),
                )
                .where(
                    ApprovalDecision.tenant_id == actor.tenant_id,
                    ApprovalDecision.approval_id.in_(
                        select(ApprovalRequest.id).where(
                            *cohort(ApprovalRequest, approvals)
                        )
                    ),
                    ApprovalDecision.status.in_(("APPROVED", "REJECTED")),
                )
                .group_by(ApprovalDecision.status)
            ).all()
        )
        attempts = ExecutionJobAttempt
        latency = summary(
            s,
            func.extract("epoch", attempts.finished_at - attempts.created_at),
            [
                attempts.tenant_id == actor.tenant_id,
                attempts.job_id.in_(select(ExecutionJob.id).where(*jobs)),
                attempts.created_at >= start,
                attempts.created_at < end,
                attempts.finished_at.is_not(None),
            ],
        )
        vol = dict(
            s.execute(
                select(
                    func.to_char(
                        Investigation.created_at.op("AT TIME ZONE")("UTC"), "YYYY-MM-DD"
                    ),
                    func.count(),
                )
                .where(*cohort(Investigation, inv))
                .group_by(text("1"))
            ).all()
        )
        trends = dict(
            s.execute(
                select(
                    func.to_char(
                        ExecutionJobEvent.created_at.op("AT TIME ZONE")("UTC"),
                        "YYYY-MM-DD",
                    ),
                    func.count(),
                )
                .where(
                    *event_scope,
                    ExecutionJobEvent.state == "RETRY_SCHEDULED",
                    ExecutionJobEvent.category != "duplicate_submission",
                )
                .group_by(text("1"))
            ).all()
        )
        days = []
        day = start.date()
        while day <= (end - timedelta(microseconds=1)).date():
            key = day.isoformat()
            days.append(
                {
                    "day": key,
                    "investigations": vol.get(key, 0),
                    "retries": trends.get(key, 0),
                }
            )
            day += timedelta(days=1)
        return dict(
            investigation_counts=ic,
            job_counts=jc,
            investigation_completion=rate(ic.get("COMPLETED", 0), inv_total),
            job_success=rate(
                jc.get("COMPLETED", 0), sum(jc.get(k, 0) for k in TERMINAL)
            ),
            retry_rate=rate(retried, job_total),
            dead_letter_rate=rate(jc.get("DEAD_LETTERED", 0), job_total),
            approval_rejection=rate(
                apcounts.get("REJECTED", 0), sum(apcounts.values())
            ),
            investigation_duration=invdur,
            approval_turnaround=turnaround,
            execution_latency=latency,
            volume=days,
            pending_approvals=pending,
            expiring_approvals=expiring,
            queue_depth=depth,
            oldest_queue_age_seconds=max(0.0, (now - oldest).total_seconds())
            if oldest
            else None,
            reconciliation_backlog=recon,
            dead_letter_backlog=s.scalar(
                select(func.count())
                .select_from(ExecutionJob)
                .where(*jobs, ExecutionJob.status == "DEAD_LETTERED")
            ),
            open_incidents=open_inc,
            lease_expirations=leases,
        )

    def health(self, s, actor, data, thresholds, now):
        last = s.scalar(
            select(func.max(WorkerObservation.observed_at)).where(
                WorkerObservation.stopped.is_(False)
            )
        )
        worker = (
            "unknown"
            if last is None
            else "healthy"
            if (now - last).total_seconds() <= thresholds.worker_stale_seconds
            else "unavailable"
        )
        if last is None and s.scalar(
            select(func.count()).select_from(WorkerObservation)
        ):
            worker = "unavailable"
        revision = s.scalar(text("SELECT version_num FROM alembic_version"))
        migration = "healthy" if revision == EXPECTED_REVISION else "degraded"
        expired = s.scalar(
            select(ExecutionJob.id)
            .where(
                *tenant_scope(actor, ExecutionJob, ExecutionJob.actor_id),
                ExecutionJob.status.in_(("CLAIMED", "RUNNING")),
                ExecutionJob.lease_expires_at <= now,
            )
            .limit(1)
        )
        queue = (
            "degraded"
            if expired
            or data["dead_letter_backlog"]
            or data["reconciliation_backlog"]
            or (data["oldest_queue_age_seconds"] or 0) >= thresholds.queue_age_seconds
            else "healthy"
        )
        return {
            "api": "healthy",
            "database": "healthy",
            "worker": worker,
            "queue": queue,
            "migration": migration,
            "overall": "healthy"
            if worker == "healthy" and queue == "healthy" and migration == "healthy"
            else "degraded",
            "observed_at": now,
        }

    @staticmethod
    def alerts(data, health, t):
        conditions = [
            (
                "dead_letter_backlog",
                data["dead_letter_backlog"] >= t.dead_letter_backlog,
                "critical",
                "Dead-letter backlog threshold reached",
            ),
            (
                "reconciliation_backlog",
                data["reconciliation_backlog"] >= t.reconciliation_backlog,
                "critical",
                "Uncertain outcomes require evidence reconciliation",
            ),
            (
                "queue_age",
                (data["oldest_queue_age_seconds"] or 0) >= t.queue_age_seconds,
                "warning",
                "Queued work exceeds age threshold",
            ),
            (
                "worker_unavailable",
                health["worker"] in {"unknown", "unavailable"},
                "warning",
                "No recent successful worker poll observed",
            ),
            (
                "failure_rate",
                data["job_success"]["denominator"] >= t.failure_min_samples
                and 100 - (data["job_success"]["percent"] or 0) >= t.failure_percent,
                "critical",
                "Terminal job failure threshold reached",
            ),
        ]
        return [
            {"code": code, "severity": severity, "message": message}
            for code, on, severity, message in conditions
            if on
        ]

    def activity(
        self, s, actor, start, end, limit=50, offset=0, investigation_ids=None
    ):
        visible_inv = select(Investigation.id).where(
            *tenant_scope(actor, Investigation, Investigation.actor_id)
        )
        if investigation_ids is not None:
            visible_inv = visible_inv.where(Investigation.id.in_(investigation_ids))
        visible_proposals = select(ActionProposal.id).where(
            ActionProposal.tenant_id == actor.tenant_id,
            ActionProposal.investigation_id.in_(visible_inv),
        )
        visible_jobs = select(ExecutionJob.id).where(
            *tenant_scope(actor, ExecutionJob, ExecutionJob.actor_id),
            ExecutionJob.proposal_id.in_(visible_proposals),
        )
        visible_approvals = select(ApprovalRequest.id).where(
            ApprovalRequest.tenant_id == actor.tenant_id,
            ApprovalRequest.proposal_id.in_(visible_proposals),
        )
        visible_exec = select(ActionExecution.id).where(
            ActionExecution.tenant_id == actor.tenant_id,
            ActionExecution.proposal_id.in_(visible_proposals),
        )
        parts = []

        def add(
            model,
            stamp,
            condition,
            kind,
            entity,
            event_type,
            actor_col=None,
            corr=None,
            service="backend",
        ):
            null = cast(literal(None), Uuid)
            parts.append(
                select(
                    model.id.label("id"),
                    stamp.label("timestamp"),
                    literal(event_type).label("event_type")
                    if isinstance(event_type, str)
                    else event_type.label("event_type"),
                    literal(kind).label("source"),
                    entity.label("entity_id"),
                    (actor_col if actor_col is not None else null).label("actor_id"),
                    literal(service).label("service"),
                    (corr if corr is not None else null).label("correlation_id"),
                    literal(
                        {
                            "investigation": "Investigation lifecycle recorded",
                            "tool": "Validated tool invocation recorded",
                            "evidence": "Evidence persisted",
                            "proposal": "Action proposed",
                            "decision": "Policy decision recorded",
                            "approval": "Approval workflow recorded",
                            "execution": "Controlled execution event recorded",
                            "job": "Execution job event recorded",
                            "incident": "Incident response recorded",
                            "security": "Security audit event recorded",
                        }[kind]
                    ).label("summary"),
                )
                .where(
                    model.tenant_id == actor.tenant_id,
                    *condition,
                    stamp >= start,
                    stamp < end,
                )
                .order_by(stamp.desc(), model.id.desc())
                .limit(limit + offset)
            )

        add(
            Investigation,
            Investigation.created_at,
            [Investigation.id.in_(visible_inv)],
            "investigation",
            Investigation.id,
            "investigation_started",
            Investigation.actor_id,
        )
        add(
            InvestigationEvent,
            InvestigationEvent.created_at,
            [InvestigationEvent.investigation_id.in_(visible_inv)],
            "investigation",
            InvestigationEvent.investigation_id,
            InvestigationEvent.event_type,
        )
        add(
            InvestigationEvidence,
            InvestigationEvidence.created_at,
            [InvestigationEvidence.investigation_id.in_(visible_inv)],
            "evidence",
            InvestigationEvidence.investigation_id,
            "evidence_collected",
        )
        add(
            ToolExecution,
            ToolExecution.started_at,
            [
                ToolExecution.id.in_(
                    select(InvestigationEvidence.tool_execution_id).where(
                        InvestigationEvidence.tenant_id == actor.tenant_id,
                        InvestigationEvidence.investigation_id.in_(visible_inv),
                    )
                )
            ],
            "tool",
            ToolExecution.id,
            "tool_executed",
            ToolExecution.actor_id,
            ToolExecution.correlation_id,
            "tool",
        )
        add(
            ActionProposal,
            ActionProposal.created_at,
            [ActionProposal.id.in_(visible_proposals)],
            "proposal",
            ActionProposal.id,
            "action_proposed",
            ActionProposal.actor_id,
        )
        add(
            PolicyDecisionReceipt,
            PolicyDecisionReceipt.created_at,
            [PolicyDecisionReceipt.proposal_id.in_(visible_proposals)],
            "decision",
            PolicyDecisionReceipt.id,
            "policy_evaluated",
        )
        add(
            ApprovalRequest,
            ApprovalRequest.created_at,
            [ApprovalRequest.id.in_(visible_approvals)],
            "approval",
            ApprovalRequest.id,
            "approval_requested",
            ApprovalRequest.requested_by,
        )
        add(
            ApprovalDecision,
            ApprovalDecision.created_at,
            [ApprovalDecision.approval_id.in_(visible_approvals)],
            "approval",
            ApprovalDecision.approval_id,
            func.concat("approval_", ApprovalDecision.status),
            ApprovalDecision.actor_id,
        )
        add(
            ActionExecutionEvent,
            ActionExecutionEvent.created_at,
            [ActionExecutionEvent.execution_id.in_(visible_exec)],
            "execution",
            ActionExecutionEvent.execution_id,
            ActionExecutionEvent.event_type,
            corr=ActionExecutionEvent.correlation_id,
            service="executor",
        )
        add(
            ExecutionJobEvent,
            ExecutionJobEvent.created_at,
            [ExecutionJobEvent.job_id.in_(visible_jobs)],
            "job",
            ExecutionJobEvent.job_id,
            func.concat("job_", ExecutionJobEvent.state),
            corr=ExecutionJobEvent.correlation_id,
            service="worker",
        )
        incident_ids = select(Incident.id).where(
            *tenant_scope(actor, Incident, Incident.visible_actor_id)
        )
        if investigation_ids is not None:
            incident_ids = incident_ids.where(
                (Incident.job_id.in_(visible_jobs))
                | (Incident.approval_id.in_(visible_approvals))
            )
        add(
            IncidentEvent,
            IncidentEvent.created_at,
            [IncidentEvent.incident_id.in_(incident_ids)],
            "incident",
            IncidentEvent.incident_id,
            IncidentEvent.event_type,
            IncidentEvent.actor_id,
            IncidentEvent.correlation_id,
            service="incident_service",
        )
        if investigation_ids is None:
            add(
                SecurityEvent,
                SecurityEvent.created_at,
                tenant_scope(actor, SecurityEvent, SecurityEvent.actor_id)[1:],
                "security",
                func.coalesce(SecurityEvent.resource_id, SecurityEvent.id),
                SecurityEvent.event_type,
                SecurityEvent.actor_id,
                SecurityEvent.request_id,
            )
        combined = union_all(*parts).subquery()
        return [
            dict(r)
            for r in s.execute(
                select(combined)
                .order_by(
                    combined.c.timestamp.desc(), combined.c.source, combined.c.id.desc()
                )
                .limit(limit)
                .offset(offset)
            ).mappings()
        ]

    def activity_page(self, identity, window, limit, offset):
        with self.context(identity) as (s, actor, now):
            start, end = window.resolve(now)
            return {
                "items": self.activity(s, actor, start, end, limit, offset),
                "limit": limit,
                "offset": offset,
            }

    def correlate(self, identity, identifier, window):
        with self.context(identity) as (s, actor, now):
            start, end = window.resolve(now)
            audit_refs = select(SecurityEvent.resource_id).where(
                SecurityEvent.tenant_id == actor.tenant_id,
                SecurityEvent.request_id == identifier,
                SecurityEvent.created_at >= start,
                SecurityEvent.created_at < end,
                SecurityEvent.resource_type.in_(
                    (
                        "action_proposal",
                        "policy_decision",
                        "controlled_action",
                        "execution_job",
                        "operations",
                    )
                ),
            )
            inv_correlations = select(InvestigationEvent.investigation_id).where(
                InvestigationEvent.tenant_id == actor.tenant_id,
                InvestigationEvent.data["correlation_id"].as_string()
                == str(identifier),
                InvestigationEvent.created_at >= start,
                InvestigationEvent.created_at < end,
            )
            related_inc = select(Incident.id).where(
                *tenant_scope(actor, Incident, Incident.visible_actor_id),
                (Incident.id.in_(audit_refs))
                | Incident.id.in_(
                    select(IncidentEvent.incident_id).where(
                        IncidentEvent.tenant_id == actor.tenant_id,
                        IncidentEvent.correlation_id == identifier,
                        IncidentEvent.created_at >= start,
                        IncidentEvent.created_at < end,
                    )
                ),
            )
            inc_jobs = select(Incident.job_id).where(
                Incident.tenant_id == actor.tenant_id, Incident.id.in_(related_inc)
            )
            inc_approvals = select(Incident.approval_id).where(
                Incident.tenant_id == actor.tenant_id, Incident.id.in_(related_inc)
            )
            ids = set(
                s.scalars(
                    select(Investigation.id).where(
                        *tenant_scope(actor, Investigation, Investigation.actor_id),
                        (Investigation.id == identifier)
                        | Investigation.id.in_(inv_correlations),
                        Investigation.created_at >= start,
                        Investigation.created_at < end,
                    )
                )
            )
            job_match = select(ExecutionJobEvent.job_id).where(
                ExecutionJobEvent.tenant_id == actor.tenant_id,
                ExecutionJobEvent.correlation_id == identifier,
                ExecutionJobEvent.created_at >= start,
                ExecutionJobEvent.created_at < end,
            )
            exec_match = select(ActionExecutionEvent.execution_id).where(
                ActionExecutionEvent.tenant_id == actor.tenant_id,
                ActionExecutionEvent.correlation_id == identifier,
                ActionExecutionEvent.created_at >= start,
                ActionExecutionEvent.created_at < end,
            )
            tool_inv = (
                select(InvestigationEvidence.investigation_id)
                .join(
                    ToolExecution,
                    (ToolExecution.id == InvestigationEvidence.tool_execution_id)
                    & (ToolExecution.tenant_id == InvestigationEvidence.tenant_id),
                )
                .where(
                    InvestigationEvidence.tenant_id == actor.tenant_id,
                    (ToolExecution.correlation_id == identifier)
                    | (ToolExecution.id == identifier),
                    ToolExecution.started_at >= start,
                    ToolExecution.started_at < end,
                )
            )
            match_proposals = select(ActionProposal.investigation_id).where(
                ActionProposal.tenant_id == actor.tenant_id,
                ((ActionProposal.id == identifier) | ActionProposal.id.in_(audit_refs))
                | ActionProposal.id.in_(
                    select(PolicyDecisionReceipt.proposal_id).where(
                        PolicyDecisionReceipt.tenant_id == actor.tenant_id,
                        (PolicyDecisionReceipt.id == identifier)
                        | PolicyDecisionReceipt.id.in_(audit_refs),
                    )
                )
                | ActionProposal.id.in_(
                    select(ApprovalRequest.proposal_id).where(
                        ApprovalRequest.tenant_id == actor.tenant_id,
                        (ApprovalRequest.id == identifier)
                        | ApprovalRequest.id.in_(inc_approvals),
                    )
                )
                | ActionProposal.id.in_(
                    select(ActionExecution.proposal_id).where(
                        ActionExecution.tenant_id == actor.tenant_id,
                        (
                            (ActionExecution.id == identifier)
                            | ActionExecution.id.in_(audit_refs)
                        )
                        | ActionExecution.id.in_(exec_match),
                    )
                )
                | ActionProposal.id.in_(
                    select(ExecutionJob.proposal_id).where(
                        ExecutionJob.tenant_id == actor.tenant_id,
                        (
                            (ExecutionJob.id == identifier)
                            | ExecutionJob.id.in_(audit_refs)
                            | ExecutionJob.id.in_(inc_jobs)
                        )
                        | ExecutionJob.id.in_(job_match),
                    )
                ),
            )
            ids.update(
                s.scalars(
                    select(Investigation.id)
                    .where(
                        *tenant_scope(actor, Investigation, Investigation.actor_id),
                        Investigation.created_at >= start,
                        Investigation.created_at < end,
                        (Investigation.id.in_(match_proposals))
                        | (Investigation.id.in_(tool_inv)),
                    )
                    .limit(11)
                )
            )
            if not ids:
                raise HTTPException(404, "Correlation not found in permitted range")
            truncated = len(ids) > 10
            ids = sorted(ids, key=str)[:10]
            props = list(
                s.scalars(
                    select(ActionProposal.id)
                    .where(
                        ActionProposal.tenant_id == actor.tenant_id,
                        ActionProposal.investigation_id.in_(ids),
                    )
                    .order_by(ActionProposal.id)
                    .limit(101)
                )
            )
            truncated = truncated or len(props) > 100
            props = props[:100]
            links = [
                {"kind": "investigation", "id": i, "href": f"/investigations/{i}"}
                for i in ids
            ]
            links.extend(
                {"kind": "proposal", "id": i, "href": f"/api/v1/action-proposals/{i}"}
                for i in props
            )
            for kind, model, path in [
                ("decision", PolicyDecisionReceipt, "action-proposals"),
                ("approval", ApprovalRequest, "approvals"),
                ("execution", ActionExecution, "action-executions"),
                ("job", ExecutionJob, "execution-jobs"),
            ]:
                rows = s.execute(
                    select(model.id, model.proposal_id)
                    .where(
                        model.tenant_id == actor.tenant_id, model.proposal_id.in_(props)
                    )
                    .order_by(model.id)
                    .limit(101)
                ).all()
                truncated = truncated or len(rows) > 100
                for i, p in rows[:100]:
                    href = (
                        f"/action-proposals/approval/{i}"
                        if kind == "approval"
                        else f"/api/v1/{path}/{p if kind == 'decision' else i}"
                    )
                    links.append({"kind": kind, "id": i, "href": href})
            related_jobs = select(ExecutionJob.id).where(
                ExecutionJob.tenant_id == actor.tenant_id,
                ExecutionJob.proposal_id.in_(props),
            )
            related_approvals = select(ApprovalRequest.id).where(
                ApprovalRequest.tenant_id == actor.tenant_id,
                ApprovalRequest.proposal_id.in_(props),
            )
            inc_ids = list(
                s.scalars(
                    select(Incident.id)
                    .where(
                        *tenant_scope(actor, Incident, Incident.visible_actor_id),
                        (Incident.job_id.in_(related_jobs))
                        | (Incident.approval_id.in_(related_approvals)),
                    )
                    .order_by(Incident.id)
                    .limit(101)
                )
            )
            truncated = truncated or len(inc_ids) > 100
            links.extend(
                {"kind": "incident", "id": id, "href": f"/incidents/{id}"}
                for id in inc_ids[:100]
            )
            for link in links:
                link["href"] = (
                    f"/incidents/{link['id']}"
                    if link["kind"] == "incident"
                    else "/diagnostics?trace=" + str(link["id"])
                )
            timeline = self.activity(
                s, actor, start, end, limit=50, investigation_ids=ids
            )
            # Explicit cap indication; no invented missing relationships.
            return {
                "links": links,
                "timeline": timeline,
                "truncated": truncated or len(timeline) == 50,
            }

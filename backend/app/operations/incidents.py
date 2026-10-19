"""Operational metadata only: detection and response never execute or retry actions."""

from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import String, event, func, select
from sqlalchemy.dialects.postgresql import insert

from app.models.entities import (
    ApprovalRequest,
    ExecutionJob,
    ExecutionJobEvent,
    SecurityEvent,
    User,
)
from app.models.entities import (
    OperationsIncident as Incident,
)
from app.models.entities import (
    OperationsIncidentEvent as IncidentEvent,
)
from app.operations.contracts import TRANSITIONS
from app.operations.service import OperationsMetricsService, tenant_scope

for _model in (IncidentEvent,):

    @event.listens_for(_model, "before_update")
    @event.listens_for(_model, "before_delete")
    def immutable(mapper, connection, target):
        raise ValueError("Incident history is append-only")


DETECTION_BATCH = 25

RULES = {
    "dead_letter": (
        "critical",
        "Execution retries exhausted",
        "Inspect attempts and current eligibility before authorized job retry.",
    ),
    "reconciliation": (
        "critical",
        "Execution outcome requires reconciliation",
        "Use transaction evidence. Incident resolution does not resolve or retry the job.",
    ),
    "lease_expiration": (
        "warning",
        "Repeated execution lease expiration",
        "Inspect worker availability and bounded execution deadlines.",
    ),
    "persistent_failure": (
        "critical",
        "Repeated controlled execution failure",
        "Inspect failed receipts; do not bypass policy or approval checks.",
    ),
    "authorization_burst": (
        "warning",
        "Repeated authorization denials",
        "Inspect safe audit references without exposing credentials.",
    ),
    "approval_failure": (
        "warning",
        "Approval invalidated",
        "Review current evidence and authority before a new approval workflow.",
    ),
}


class IncidentService(OperationsMetricsService):
    def detect(self, s, tenant, now):
        candidates = []
        for status, category in [
            ("DEAD_LETTERED", "dead_letter"),
            ("RECONCILIATION_REQUIRED", "reconciliation"),
        ]:
            rows = s.execute(
                select(ExecutionJob.id, ExecutionJob.actor_id)
                .where(
                    ExecutionJob.tenant_id == tenant,
                    ExecutionJob.status == status,
                    ExecutionJob.id.not_in(
                        select(Incident.job_id).where(
                            Incident.tenant_id == tenant,
                            Incident.category == category,
                            Incident.job_id.is_not(None),
                        )
                    ),
                )
                .order_by(ExecutionJob.created_at, ExecutionJob.id)
                .limit(DETECTION_BATCH)
            ).all()
            for id, actor in rows:
                candidates.append((category, str(id), actor, id, None, None))
        repeats = s.execute(
            select(ExecutionJobEvent.job_id, ExecutionJob.actor_id)
            .join(
                ExecutionJob,
                (ExecutionJob.id == ExecutionJobEvent.job_id)
                & (ExecutionJob.tenant_id == ExecutionJobEvent.tenant_id),
            )
            .where(
                ExecutionJobEvent.tenant_id == tenant,
                ExecutionJobEvent.category == "lease_expired",
                ExecutionJobEvent.job_id.not_in(
                    select(Incident.job_id).where(
                        Incident.tenant_id == tenant,
                        Incident.category == "lease_expiration",
                        Incident.job_id.is_not(None),
                    )
                ),
                ExecutionJobEvent.created_at >= now - timedelta(days=1),
            )
            .group_by(ExecutionJobEvent.job_id, ExecutionJob.actor_id)
            .having(func.count() >= 3)
            .order_by(ExecutionJobEvent.job_id)
            .limit(DETECTION_BATCH)
        ).all()
        for id, actor in repeats:
            candidates.append(("lease_expiration", str(id), actor, id, None, None))
        failures = s.execute(
            select(ExecutionJob.actor_id)
            .where(
                ExecutionJob.tenant_id == tenant,
                ExecutionJob.status == "FAILED",
                func.concat(
                    "persistent_failure/",
                    ExecutionJob.actor_id.cast(String),
                    "/",
                    str(now.date()),
                ).not_in(
                    select(Incident.condition_key).where(Incident.tenant_id == tenant)
                ),
                ExecutionJob.created_at >= now - timedelta(days=1),
            )
            .group_by(ExecutionJob.actor_id)
            .having(func.count() >= 3)
            .order_by(ExecutionJob.actor_id)
            .limit(DETECTION_BATCH)
        ).scalars()
        for actor in failures:
            candidates.append(
                ("persistent_failure", f"{actor}/{now.date()}", actor, None, None, None)
            )
        approvals = s.execute(
            select(ApprovalRequest.id, ApprovalRequest.requested_by)
            .where(
                ApprovalRequest.tenant_id == tenant,
                ApprovalRequest.status == "INVALIDATED",
                ApprovalRequest.id.not_in(
                    select(Incident.approval_id).where(
                        Incident.tenant_id == tenant,
                        Incident.category == "approval_failure",
                        Incident.approval_id.is_not(None),
                    )
                ),
                ApprovalRequest.updated_at >= now - timedelta(days=1),
            )
            .order_by(ApprovalRequest.id)
            .limit(DETECTION_BATCH)
        ).all()
        for id, actor in approvals:
            candidates.append(("approval_failure", str(id), actor, None, id, None))
        denials = s.execute(
            select(
                SecurityEvent.actor_id,
                func.min(SecurityEvent.id.cast(String)),
            )
            .where(
                SecurityEvent.tenant_id == tenant,
                SecurityEvent.actor_id.is_not(None),
                func.concat(
                    "authorization_burst/",
                    SecurityEvent.actor_id.cast(String),
                    "/",
                    str(int(now.timestamp()) // 300),
                ).not_in(
                    select(Incident.condition_key).where(Incident.tenant_id == tenant)
                ),
                SecurityEvent.outcome.in_(("denied", "DENIED")),
                SecurityEvent.created_at >= now - timedelta(minutes=5),
            )
            .group_by(SecurityEvent.actor_id)
            .having(func.count() >= 5)
            .order_by(SecurityEvent.actor_id)
            .limit(DETECTION_BATCH)
        ).all()
        from uuid import UUID

        for actor, source in denials:
            candidates.append(
                (
                    "authorization_burst",
                    f"{actor}/{int(now.timestamp()) // 300}",
                    actor,
                    None,
                    None,
                    UUID(source),
                )
            )
        job_ids = [c[3] for c in candidates if c[3] is not None]
        sources = (
            dict(
                s.execute(
                    select(ExecutionJobEvent.job_id, ExecutionJobEvent.id)
                    .where(
                        ExecutionJobEvent.tenant_id == tenant,
                        ExecutionJobEvent.job_id.in_(job_ids),
                    )
                    .distinct(ExecutionJobEvent.job_id)
                    .order_by(
                        ExecutionJobEvent.job_id,
                        ExecutionJobEvent.created_at.desc(),
                        ExecutionJobEvent.id.desc(),
                    )
                ).all()
            )
            if job_ids
            else {}
        )
        created = 0
        for category, key, actor, job, approval, source in candidates:
            source = sources.get(job, source)
            severity, title, description = RULES[category]
            id = s.scalar(
                insert(Incident)
                .values(
                    id=uuid4(),
                    tenant_id=tenant,
                    condition_key=category + "/" + key,
                    category=category,
                    severity=severity,
                    status="OPEN",
                    title=title,
                    description=description,
                    visible_actor_id=actor,
                    job_id=job,
                    approval_id=approval,
                    source_event_id=source,
                )
                .on_conflict_do_nothing(index_elements=["tenant_id", "condition_key"])
                .returning(Incident.id)
            )
            if id:
                correlation = uuid4()
                s.add(
                    IncidentEvent(
                        tenant_id=tenant,
                        incident_id=id,
                        actor_id=None,
                        correlation_id=correlation,
                        event_type="incident_opened",
                        status="OPEN",
                    )
                )
                s.add(
                    SecurityEvent(
                        tenant_id=tenant,
                        actor_id=None,
                        event_type="incident_opened",
                        resource_type="operations",
                        resource_id=id,
                        request_id=correlation,
                        outcome="recorded",
                    )
                )
                created += 1
        return created

    def detect_authorized(self, identity):
        with self.context(identity, True) as (s, actor, now):
            self.require_responder(actor)
            return {"created": self.detect(s, actor.tenant_id, now)}

    @staticmethod
    def require_responder(actor):
        if "action:approve" not in actor.permissions:
            raise HTTPException(403, "Incident responder permission required")

    def view(self, row, actor):
        names = (
            "id",
            "category",
            "severity",
            "status",
            "title",
            "description",
            "visible_actor_id",
            "job_id",
            "approval_id",
            "source_event_id",
            "assigned_to",
            "created_at",
            "updated_at",
            "resolved_at",
            "resolution_note",
        )
        return {
            **{n: getattr(row, n) for n in names},
            "can_respond": "action:approve" in actor.permissions,
        }

    def listing(self, identity, window, limit, offset, status=None, severity=None):
        with self.context(identity) as (s, actor, now):
            start, end = window.resolve(now)
            conditions = [
                *tenant_scope(actor, Incident, Incident.visible_actor_id),
                Incident.created_at >= start,
                Incident.created_at < end,
            ]
            if status:
                conditions.append(Incident.status == status)
            if severity:
                conditions.append(Incident.severity == severity)
            rows = s.scalars(
                select(Incident)
                .where(*conditions)
                .order_by(Incident.created_at.desc(), Incident.id)
                .limit(limit)
                .offset(offset)
            ).all()
            return {
                "items": [self.view(r, actor) for r in rows],
                "limit": limit,
                "offset": offset,
            }

    def owned(self, s, actor, id, lock=False):
        q = select(Incident).where(
            *tenant_scope(actor, Incident, Incident.visible_actor_id), Incident.id == id
        )
        row = s.scalar(q.with_for_update() if lock else q)
        if not row:
            raise HTTPException(404, "Incident not found")
        return row

    def describe(self, s, actor, row):
        events = s.scalars(
            select(IncidentEvent)
            .where(
                IncidentEvent.tenant_id == actor.tenant_id,
                IncidentEvent.incident_id == row.id,
            )
            .order_by(IncidentEvent.created_at.desc(), IncidentEvent.id.desc())
            .limit(DETECTION_BATCH)
        ).all()
        names = (
            "id",
            "actor_id",
            "correlation_id",
            "event_type",
            "status",
            "note",
            "created_at",
        )
        return {
            "incident": self.view(row, actor),
            "events": [{n: getattr(e, n) for n in names} for e in reversed(events)],
        }

    def detail(self, identity, id):
        with self.context(identity) as (s, actor, now):
            return self.describe(s, actor, self.owned(s, actor, id))

    def respond(self, identity, id, operation, command, correlation):
        with self.context(identity, True) as (s, actor, now):
            row = self.owned(s, actor, id, True)
            self.require_responder(actor)
            if row.status == "CLOSED":
                raise HTTPException(409, "Closed incident is immutable")
            if operation == "assign":
                if command.assigned_to is None:
                    raise HTTPException(422, "Assignee required")
                user = s.scalar(
                    select(User)
                    .where(
                        User.tenant_id == actor.tenant_id,
                        User.id == command.assigned_to,
                        User.is_active.is_(True),
                        User.role.in_(("reviewer", "admin")),
                    )
                    .with_for_update()
                )
                if not user:
                    raise HTTPException(404, "Eligible assignee not found")
                row.assigned_to = user.id
            else:
                if command.assigned_to is not None:
                    raise HTTPException(422, "Assignee only allowed for assignment")
                target = {
                    "acknowledge": "ACKNOWLEDGED",
                    "investigate": "INVESTIGATING",
                    "resolve": "RESOLVED",
                    "close": "CLOSED",
                }.get(operation)
                if operation != "notes":
                    if target not in TRANSITIONS.get(row.status, set()):
                        raise HTTPException(409, "Invalid incident transition")
                    row.status = target
                    if target == "RESOLVED":
                        row.resolved_at = now
                        row.resolution_note = command.note
            row.updated_at = now
            kind = (
                "incident_"
                + {
                    "acknowledge": "acknowledged",
                    "assign": "assigned",
                    "investigate": "investigating",
                    "resolve": "resolved",
                    "close": "closed",
                    "notes": "note_added",
                }[operation]
            )
            s.add(
                IncidentEvent(
                    tenant_id=actor.tenant_id,
                    incident_id=row.id,
                    actor_id=actor.user_id,
                    correlation_id=correlation,
                    event_type=kind,
                    status=row.status,
                    note=command.note,
                    created_at=now,
                )
            )
            self.audit(s, actor, row.id, correlation, kind)
            s.flush()
            return self.describe(s, actor, row)

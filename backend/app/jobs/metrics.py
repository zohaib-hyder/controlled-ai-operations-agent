"""Aggregate operational metadata only; never customer payloads or credentials."""

from sqlalchemy import func, select

from app.models.entities import (
    ExecutionJob as Job,
)
from app.models.entities import (
    ExecutionJobAttempt as Attempt,
)
from app.models.entities import (
    ExecutionJobEvent as Event,
)


def snapshot(factory):
    with factory() as s:
        states = dict(
            s.execute(select(Job.status, func.count()).group_by(Job.status)).all()
        )
        events = dict(
            s.execute(
                select(Event.category, func.count()).group_by(Event.category)
            ).all()
        )
        now = s.scalar(select(func.clock_timestamp()))
        oldest = s.scalar(
            select(func.min(Job.created_at)).where(
                Job.status.in_(("QUEUED", "RETRY_SCHEDULED"))
            )
        )
        latency = s.scalar(
            select(
                func.avg(
                    func.extract("epoch", Attempt.finished_at - Attempt.created_at)
                )
            ).where(Attempt.finished_at.is_not(None))
        )
        return {
            "jobs_by_state": states,
            "jobs_queued": s.scalar(select(func.count()).select_from(Job)),
            "jobs_completed": states.get("COMPLETED", 0),
            "jobs_failed": states.get("FAILED", 0),
            "jobs_retried": s.scalar(
                select(func.count())
                .select_from(Event)
                .where(
                    Event.state == "RETRY_SCHEDULED",
                    Event.category != "duplicate_submission",
                )
            ),
            "jobs_dead_lettered": states.get("DEAD_LETTERED", 0),
            "jobs_requiring_reconciliation": states.get("RECONCILIATION_REQUIRED", 0),
            "queue_age_seconds": max(0.0, (now - oldest).total_seconds())
            if oldest
            else 0.0,
            "execution_latency_seconds": float(latency or 0),
            "lease_expirations": events.get("lease_expired", 0),
            "duplicate_prevention": events.get("duplicate_submission", 0),
        }

"""Private worker observations and bounded periodic incident discovery."""

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.models.entities import Tenant, WorkerObservation
from app.operations.incidents import IncidentService


def observe(factory, owner, stopped=False):
    with factory() as s, s.begin():
        stmt = insert(WorkerObservation).values(
            owner=owner, observed_at=func.clock_timestamp(), stopped=stopped
        )
        s.execute(
            stmt.on_conflict_do_update(
                index_elements=["owner"],
                set_={"observed_at": func.clock_timestamp(), "stopped": stopped},
            )
        )


def detect_page(factory, after=None):
    with factory() as s, s.begin():
        q = select(Tenant.id).order_by(Tenant.id).limit(5)
        if after is not None:
            q = q.where(Tenant.id > after)
        tenants = list(s.scalars(q))
        now = s.scalar(select(func.clock_timestamp()))
        service = IncidentService(factory)
        for tenant in tenants:
            service.detect(s, tenant, now)
        return tenants[-1] if len(tenants) == 5 else None

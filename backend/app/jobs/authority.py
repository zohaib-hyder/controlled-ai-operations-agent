"""Session-independent job authority, exclusively bound to a fenced persisted submitter."""

from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.permissions import PERMISSIONS, Identity
from app.models.entities import ExecutionJob, User


def revalidate_job_identity(session, identity):
    job = session.scalar(
        select(ExecutionJob).where(
            ExecutionJob.id == identity.job_id,
            ExecutionJob.tenant_id == identity.tenant_id,
            ExecutionJob.actor_id == identity.user_id,
            ExecutionJob.session_id == identity.session_id,
            ExecutionJob.status == "RUNNING",
            ExecutionJob.fence == identity.job_fence,
            ExecutionJob.lease_owner == identity.job_owner,
            ExecutionJob.lease_expires_at > func.clock_timestamp(),
        )
    )
    user = session.scalar(
        select(User).where(
            User.id == identity.user_id,
            User.tenant_id == identity.tenant_id,
            User.is_active.is_(True),
        )
    )
    if not job or not user or "action:execute" not in PERMISSIONS.get(user.role, ()):
        raise HTTPException(403, "job_authority_or_lease_invalid")
    return Identity(
        user.id,
        user.tenant_id,
        user.role,
        job.session_id,
        job.id,
        job.fence,
        job.lease_owner,
    )

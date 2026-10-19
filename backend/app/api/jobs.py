import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.encoders import jsonable_encoder

from app.api.execution import Actor, Service
from app.jobs.contracts import Attempts, Events, JobList, JobView, Submit
from app.jobs.service import JobService
from app.schemas.execution import EmptyCommand
from app.services.authentication import require_origin

router = APIRouter(prefix="/api/v1/execution-jobs", tags=["durable execution jobs"])


def validated(model, value):
    return model.model_validate_json(json.dumps(jsonable_encoder(value)))


@router.post("", dependencies=[Depends(require_origin)])
def submit(
    body: Submit,
    identity: Actor,
    request: Request,
    service: Service,
    idempotency_key: Annotated[str, Header(min_length=8, max_length=80)],
):
    return validated(
        JobView,
        JobService(service.factory).submit(
            identity, body, idempotency_key, UUID(request.state.request_id)
        ),
    )


@router.get("")
def listing(
    identity: Actor,
    service: Service,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0, le=10000),
):
    return validated(
        JobList, JobService(service.factory).read(identity, limit=limit, offset=offset)
    )


@router.get("/{job_id}")
def detail(job_id: UUID, identity: Actor, service: Service):
    return validated(JobView, JobService(service.factory).read(identity, job_id))


@router.get("/{job_id}/attempts")
def attempts(job_id: UUID, identity: Actor, service: Service):
    return validated(
        Attempts, JobService(service.factory).read(identity, job_id, "attempts")
    )


@router.get("/{job_id}/events")
def events(job_id: UUID, identity: Actor, service: Service):
    return validated(
        Events, JobService(service.factory).read(identity, job_id, "events")
    )


@router.post("/{job_id}/cancel", dependencies=[Depends(require_origin)])
@router.post("/{job_id}/retry", dependencies=[Depends(require_origin)])
def control(
    job_id: UUID,
    identity: Actor,
    request: Request,
    service: Service,
    body: EmptyCommand,
):
    return validated(
        JobView,
        JobService(service.factory).control(
            identity,
            job_id,
            request.url.path.rsplit("/", 1)[-1],
            UUID(request.state.request_id),
        ),
    )

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError

from app.api.execution import Actor, Service
from app.api.jobs import validated
from app.operations.contracts import (
    ActivityPage,
    Correlation,
    Detection,
    IncidentCommand,
    IncidentDetail,
    IncidentPage,
    Overview,
    Status,
    Thresholds,
    Window,
)
from app.operations.incidents import IncidentService
from app.operations.service import OperationsMetricsService
from app.schemas.execution import EmptyCommand
from app.services.authentication import require_origin

router = APIRouter(prefix="/api/v1", tags=["operations command center"])


def window_query(
    range: Literal["24h", "7d", "30d", "custom"] = "24h",
    start: str | None = None,
    end: str | None = None,
):
    try:
        return Window.model_validate({"range": range, "start": start, "end": end})
    except (ValidationError, ValueError):
        raise HTTPException(422, "Invalid bounded UTC time range") from None


Range = Annotated[Window, Depends(window_query)]


@router.get("/operations/overview")
@router.get("/operations/metrics")
def overview(identity: Actor, service: Service, window: Range):
    return validated(
        Overview, OperationsMetricsService(service.factory).overview(identity, window)
    )


@router.get("/operations/activity")
def activity(
    identity: Actor,
    service: Service,
    window: Range,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0, le=10000),
):
    return validated(
        ActivityPage,
        OperationsMetricsService(service.factory).activity_page(
            identity, window, limit, offset
        ),
    )


@router.get("/operations/correlations/{identifier}")
def correlate(identifier: UUID, identity: Actor, service: Service, window: Range):
    return validated(
        Correlation,
        OperationsMetricsService(service.factory).correlate(
            identity, identifier, window
        ),
    )


@router.post("/operations/thresholds", dependencies=[Depends(require_origin)])
def configure(body: Thresholds, identity: Actor, service: Service, request: Request):
    return validated(
        Thresholds,
        OperationsMetricsService(service.factory).configure(
            identity, body, UUID(request.state.request_id)
        ),
    )


@router.post("/incidents/detect", dependencies=[Depends(require_origin)])
def detect(identity: Actor, service: Service, body: EmptyCommand):
    return validated(
        Detection, IncidentService(service.factory).detect_authorized(identity)
    )


@router.get("/incidents")
def incidents(
    identity: Actor,
    service: Service,
    window: Range,
    status: Status | None = None,
    severity: Literal["warning", "critical"] | None = None,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0, le=10000),
):
    return validated(
        IncidentPage,
        IncidentService(service.factory).listing(
            identity, window, limit, offset, status, severity
        ),
    )


@router.get("/incidents/{id}")
def detail(id: UUID, identity: Actor, service: Service):
    return validated(
        IncidentDetail, IncidentService(service.factory).detail(identity, id)
    )


@router.post("/incidents/{id}/acknowledge", dependencies=[Depends(require_origin)])
@router.post("/incidents/{id}/assign", dependencies=[Depends(require_origin)])
@router.post("/incidents/{id}/investigate", dependencies=[Depends(require_origin)])
@router.post("/incidents/{id}/resolve", dependencies=[Depends(require_origin)])
@router.post("/incidents/{id}/close", dependencies=[Depends(require_origin)])
@router.post("/incidents/{id}/notes", dependencies=[Depends(require_origin)])
def respond(
    id: UUID, body: IncidentCommand, identity: Actor, service: Service, request: Request
):
    return validated(
        IncidentDetail,
        IncidentService(service.factory).respond(
            identity,
            id,
            request.url.path.rsplit("/", 1)[-1],
            body,
            UUID(request.state.request_id),
        ),
    )

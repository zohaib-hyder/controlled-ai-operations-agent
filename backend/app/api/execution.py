import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.permissions import Identity
from app.execution.service import ControlledActionExecutor
from app.schemas.execution import (
    ApprovalCommand,
    ApprovalDetail,
    ApprovalQueue,
    EmptyCommand,
    ExecuteCommand,
    ExecutionReceipt,
)
from app.services.authentication import current_identity, require_origin
from app.tools.executor import ToolExecutor, get_tool_executor

logger = logging.getLogger("northstar.execution")

router = APIRouter(prefix="/api/v1", tags=["human controlled synthetic operations"])
Actor = Annotated[Identity, Depends(current_identity)]


def service(executor: Annotated[ToolExecutor, Depends(get_tool_executor)]):
    return ControlledActionExecutor(executor.session_factory)


Service = Annotated[ControlledActionExecutor, Depends(service)]


def invoke(service, identity, request, operation):
    correlation = UUID(request.state.request_id)
    try:
        result = operation(correlation)
        model = (
            ExecutionReceipt
            if request.url.path.endswith("/execute")
            else ApprovalDetail
        )
        result = model.model_validate_json(json.dumps(result)).model_dump(mode="json")
        if result.get("error_code"):
            return JSONResponse(status_code=409, content=result)
        return result
    except HTTPException:
        # Denials survive the rolled-back business transaction; no raw request content.
        with service.transaction(identity) as (session, actor):
            service.audit(
                session, actor, None, correlation, "execution_denied", "denied"
            )
        raise
    except SQLAlchemyError:
        # Preserve uncertainty when storage is reachable; log only correlation if it is not.
        try:
            with service.transaction(identity) as (session, actor):
                service.audit(
                    session,
                    actor,
                    None,
                    correlation,
                    "execution_uncertain",
                    "uncertain",
                )
        except (SQLAlchemyError, HTTPException):
            logger.warning(
                "execution_reconciliation_required correlation_id=%s", correlation
            )
        # A connection loss at COMMIT cannot honestly be reported as known failure/success.
        return JSONResponse(
            status_code=503,
            content={
                "status": "UNCERTAIN",
                "verified": False,
                "error_code": "execution_outcome_uncertain",
                "message": "Reconcile using the same idempotency key when database access returns",
                "correlation_id": str(correlation),
            },
        )


@router.post(
    "/action-proposals/{proposal_id}/approval-requests",
    dependencies=[Depends(require_origin)],
)
def request_approval(
    proposal_id: UUID,
    identity: Actor,
    request: Request,
    service: Service,
    body: EmptyCommand | None = None,
):
    return invoke(
        service,
        identity,
        request,
        lambda correlation: service.request_approval(
            identity, proposal_id, correlation
        ),
    )


@router.get("/approvals")
def queue(
    identity: Actor,
    service: Service,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0, le=10000),
):
    return ApprovalQueue.model_validate_json(
        json.dumps(service.queue(identity, limit, offset))
    )


@router.get("/approvals/{approval_id}")
def detail(approval_id: UUID, identity: Actor, request: Request, service: Service):
    return ApprovalDetail.model_validate_json(
        json.dumps(
            service.detail(identity, approval_id, UUID(request.state.request_id))
        )
    )


@router.post("/approvals/{approval_id}/approve", dependencies=[Depends(require_origin)])
@router.post("/approvals/{approval_id}/reject", dependencies=[Depends(require_origin)])
@router.post("/approvals/{approval_id}/cancel", dependencies=[Depends(require_origin)])
def decide(
    approval_id: UUID,
    body: ApprovalCommand,
    identity: Actor,
    request: Request,
    service: Service,
):
    operation = request.url.path.rsplit("/", 1)[-1]
    return invoke(
        service,
        identity,
        request,
        lambda correlation: service.decide(
            identity, approval_id, body, operation, correlation
        ),
    )


@router.post(
    "/action-proposals/{proposal_id}/execute", dependencies=[Depends(require_origin)]
)
def execute(
    proposal_id: UUID,
    body: ExecuteCommand,
    identity: Actor,
    request: Request,
    service: Service,
    idempotency_key: Annotated[str, Header(min_length=8, max_length=80)],
):
    return invoke(
        service,
        identity,
        request,
        lambda correlation: service.execute(
            identity, proposal_id, body, idempotency_key, correlation
        ),
    )


@router.get("/action-executions/{execution_id}")
def execution(execution_id: UUID, identity: Actor, service: Service):
    return ExecutionReceipt.model_validate_json(
        json.dumps(service.execution(identity, execution_id))
    )

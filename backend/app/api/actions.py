import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.core.permissions import Identity
from app.policies.catalog import CATALOG
from app.policies.engine import PolicyDecisionEngine
from app.schemas.actions import ProposalEvaluation, ProposalInput
from app.services.authentication import current_identity, require_origin
from app.tools.executor import ToolExecutor, get_tool_executor

router = APIRouter(prefix="/api/v1", tags=["evaluation-only action proposals"])
Actor = Annotated[Identity, Depends(current_identity)]


def get_policy_engine(executor: Annotated[ToolExecutor, Depends(get_tool_executor)]):
    return PolicyDecisionEngine(executor.session_factory)


Engine = Annotated[PolicyDecisionEngine, Depends(get_policy_engine)]


@router.get("/actions")
def catalog(identity: Actor):
    return [
        a.public() for a in CATALOG.values() if a.permission in identity.permissions
    ]


@router.post(
    "/action-proposals",
    response_model=ProposalEvaluation,
    dependencies=[Depends(require_origin)],
)
def propose(body: ProposalInput, identity: Actor, engine: Engine, request: Request):
    return ProposalEvaluation.model_validate_json(
        json.dumps(engine.create(identity, body, UUID(request.state.request_id)))
    )


@router.get("/action-proposals/{proposal_id}", response_model=ProposalEvaluation)
@router.get(
    "/action-proposals/{proposal_id}/decision", response_model=ProposalEvaluation
)
def retrieve(proposal_id: UUID, identity: Actor, engine: Engine, request: Request):
    return ProposalEvaluation.model_validate_json(
        json.dumps(engine.get(identity, proposal_id, UUID(request.state.request_id)))
    )


@router.post(
    "/action-proposals/{proposal_id}/revalidate",
    response_model=ProposalEvaluation,
    dependencies=[Depends(require_origin)],
)
def revalidate(proposal_id: UUID, identity: Actor, engine: Engine, request: Request):
    return ProposalEvaluation.model_validate_json(
        json.dumps(
            engine.get(
                identity, proposal_id, UUID(request.state.request_id), revalidate=True
            )
        )
    )

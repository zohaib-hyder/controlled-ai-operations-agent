from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from app.agents.contracts import InvestigationRequest
from app.agents.orchestrator import AgentOrchestrator, get_orchestrator
from app.agents.persistence_contracts import (
    ControlRequest,
    HistoryQuery,
    InvestigationView,
    SequenceQuery,
)
from app.core.permissions import Identity
from app.services.authentication import require_origin, require_permission

router = APIRouter(prefix="/api/v1/investigations", tags=["read-only investigations"])
Investigator = Annotated[Identity, Depends(require_permission("investigation:create"))]
Orchestrator = Annotated[AgentOrchestrator, Depends(get_orchestrator)]


@router.post(
    "", response_model=InvestigationView, dependencies=[Depends(require_origin)]
)
async def create(
    body: InvestigationRequest,
    identity: Investigator,
    orchestrator: Orchestrator,
    request: Request,
    idempotency_key: Annotated[str | None, Header(max_length=80)] = None,
):
    return await orchestrator.run(
        body, identity, UUID(request.state.request_id), idempotency_key=idempotency_key
    )


@router.get("")
def history(
    identity: Investigator,
    orchestrator: Orchestrator,
    paging: Annotated[HistoryQuery, Query()],
):
    return orchestrator.repository.list(identity, **paging.model_dump())


@router.get("/{investigation_id}", response_model=InvestigationView)
def retrieve(
    investigation_id: UUID, identity: Investigator, orchestrator: Orchestrator
):
    return orchestrator.get(investigation_id, identity)


@router.get("/{investigation_id}/events")
def events(
    investigation_id: UUID,
    identity: Investigator,
    orchestrator: Orchestrator,
    paging: Annotated[SequenceQuery, Query()],
):
    return orchestrator.repository.records(
        identity, investigation_id, "events", **paging.model_dump()
    )


@router.get("/{investigation_id}/evidence")
def evidence(
    investigation_id: UUID,
    identity: Investigator,
    orchestrator: Orchestrator,
    paging: Annotated[SequenceQuery, Query()],
):
    return orchestrator.repository.records(
        identity, investigation_id, "evidence", **paging.model_dump()
    )


@router.post(
    "/{investigation_id}/cancel",
    response_model=InvestigationView,
    dependencies=[Depends(require_origin)],
)
def cancel(
    investigation_id: UUID,
    identity: Investigator,
    orchestrator: Orchestrator,
    body: ControlRequest | None = None,
):
    orchestrator.repository.cancel(identity, investigation_id)
    return orchestrator.get(investigation_id, identity)


@router.post(
    "/{investigation_id}/resume",
    response_model=InvestigationView,
    dependencies=[Depends(require_origin)],
)
async def resume(
    investigation_id: UUID,
    identity: Investigator,
    orchestrator: Orchestrator,
    body: ControlRequest | None = None,
):
    return await orchestrator.resume(investigation_id, identity)


@router.get("/{investigation_id}/sources")
def sources(
    investigation_id: UUID,
    identity: Investigator,
    orchestrator: Orchestrator,
    paging: Annotated[SequenceQuery, Query()],
):
    view = orchestrator.get(investigation_id, identity)
    items = [s for e in view.evidence for s in e.sources]
    return {
        "items": items[paging.after : paging.after + paging.limit],
        "next_after": paging.after + paging.limit
        if len(items) > paging.after + paging.limit
        else None,
    }


@router.get("/{investigation_id}/evidence/{evidence_id}")
def evidence_detail(
    investigation_id: UUID,
    evidence_id: UUID,
    identity: Investigator,
    orchestrator: Orchestrator,
):
    view = orchestrator.get(investigation_id, identity)
    for envelope in view.evidence:
        for source in envelope.sources:
            if source.evidence_id == evidence_id:
                return source
    raise HTTPException(404, "Evidence not found")


@router.get("/{investigation_id}/conflicts")
@router.get("/{investigation_id}/gaps")
@router.get("/{investigation_id}/findings")
def reconciliation_records(
    investigation_id: UUID,
    identity: Investigator,
    orchestrator: Orchestrator,
    request: Request,
    paging: Annotated[SequenceQuery, Query()],
):
    from app.services.evidence import EvidenceRetrievalService

    view = orchestrator.get(investigation_id, identity)
    result = view.reconciliation or EvidenceRetrievalService().reconcile(
        investigation_id, view.evidence
    )
    kind = request.url.path.rsplit("/", 1)[-1]
    items = getattr(result, "grounded_findings" if kind == "findings" else kind)
    return {
        "items": items[paging.after : paging.after + paging.limit],
        "next_after": paging.after + paging.limit
        if len(items) > paging.after + paging.limit
        else None,
    }


@router.post(
    "/{investigation_id}/action-proposal", dependencies=[Depends(require_origin)]
)
async def suggest_action(
    investigation_id: UUID,
    identity: Investigator,
    orchestrator: Orchestrator,
    request: Request,
):
    return await orchestrator.suggest_action(
        investigation_id, identity, UUID(request.state.request_id)
    )

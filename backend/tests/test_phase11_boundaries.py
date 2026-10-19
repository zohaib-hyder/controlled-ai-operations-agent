"""Explicit races and real, rather than invented, foreign citation references."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from threading import Barrier
from uuid import UUID, uuid4

import pytest
import test_agents as agents
import test_controlled_execution as controlled
import test_policy_engine as policy
import test_tools as tools
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from test_execution_eval import snapshot

from app.execution.service import ControlledActionExecutor
from app.main import app
from app.models.entities import ApprovalDecision, ApprovalRequest, SecurityEvent
from app.schemas.execution import ApprovalCommand

client = controlled.client
executor = controlled.executor
tool_db = controlled.tool_db
setup = controlled.setup


@pytest.mark.parametrize(
    "citation_tenant", [0, 1], ids=["other-investigation", "other-tenant-investigation"]
)
def test_actual_investigation_citation_is_not_transferable(
    setup, client, tool_db, citation_tenant, record_property
):
    own = policy.investigate(setup, 3)
    with TestClient(app) as other:
        other.headers.update(tools.ORIGIN)
        principal = tools.identity(other, "operator", citation_tenant)
        foreign = agents.run(
            setup[1], principal, agents.request(3, tenant=citation_tenant)
        )
    assert foreign.investigation_id != own.investigation_id
    citation = next(
        source.evidence_id
        for e in foreign.evidence
        for source in e.sources
        if source.source_type == "customer"
    )
    body = policy.proposal(own, "create_customer_note", evidence_references=(citation,))
    before = snapshot(tool_db)
    response = client.post(
        "/api/v1/action-proposals", json=body.model_dump(mode="json")
    )
    assert response.status_code == 200
    receipt = response.json()["receipt"]
    assert receipt["decision"] == "DENY"
    assert "unverified_evidence_reference" in receipt["reason_codes"]
    assert snapshot(tool_db) == before
    record_property(
        "trace_ids", str(own.investigation_id) + "," + str(foreign.investigation_id)
    )


def test_concurrent_independent_approvals_have_one_durable_winner(
    setup, client, tool_db, record_property
):
    service = ControlledActionExecutor(tool_db)
    proposal, _ = controlled.prepared(setup)
    approval_id = UUID(
        service.request_approval(setup[0], proposal, uuid4())["approval_id"]
    )
    before = snapshot(tool_db)
    gate = Barrier(2)
    with ExitStack() as stack:
        principals = []
        for role in ("reviewer", "admin"):
            browser = stack.enter_context(TestClient(app))
            browser.headers.update(tools.ORIGIN)
            principals.append(tools.identity(browser, role))

        def approve(actor):
            gate.wait(timeout=5)
            try:
                result = service.decide(
                    actor,
                    approval_id,
                    ApprovalCommand(reason="Independent simultaneous synthetic review"),
                    "approve",
                    uuid4(),
                )
            except OperationalError as error:
                assert getattr(error.orig, "sqlstate", None) == "40001"
                return "serialization_conflict"
            if result.get("error_code"):
                assert result["error_code"] == "invalid_approval_transition"
                return "already_decided"
            assert result["status"] == "APPROVED"
            return "winner"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(approve, principals))
        assert outcomes.count("winner") == 1
        with tool_db() as session:
            row = session.get(ApprovalRequest, approval_id)
            assert row.status == "APPROVED" and row.consumed_at is None
            assert row.reviewer_id in {p.user_id for p in principals}
            assert row.reviewer_id != setup[0].user_id
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(ApprovalDecision)
                    .where(
                        ApprovalDecision.tenant_id == setup[0].tenant_id,
                        ApprovalDecision.approval_id == approval_id,
                        ApprovalDecision.status == "APPROVED",
                    )
                )
                == 1
            )
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(SecurityEvent)
                    .where(
                        SecurityEvent.tenant_id == setup[0].tenant_id,
                        SecurityEvent.resource_id == approval_id,
                        SecurityEvent.event_type == "approval_granted",
                    )
                )
                == 1
            )
    assert snapshot(tool_db) == before
    record_property("trace_ids", str(proposal) + "," + str(approval_id))

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
import test_policy_engine as policy
import test_tools as tools
from fastapi import HTTPException
from sqlalchemy import func, select

from app.execution.service import ControlledActionExecutor
from app.models.entities import (
    Account,
    ApprovalRequest,
    AuthSession,
    BusinessRecord,
    Policy,
    User,
)
from app.schemas.execution import ApprovalCommand, ExecuteCommand

client = policy.client
executor = policy.executor
tool_db = policy.tool_db
setup = policy.setup


def prepared(setup, action="reactivate_account", index=3):
    view = policy.investigate(setup, index)
    changes = (
        {"arguments": {"duplicate_of_id": str(tools.stable_id("0/ticket/2"))}}
        if action == "close_duplicate_ticket"
        else {}
    )
    body = policy.proposal(view, action, **changes)
    result = setup[2].create(setup[0], body, uuid4())
    return UUID(result["proposal"]["proposal_id"]), UUID(
        result["receipt"]["decision_id"]
    )


def grant(setup, client, proposal_id, service):
    try:
        approval = service.request_approval(setup[0], proposal_id, uuid4())
    except HTTPException as error:
        # Safe test-only diagnostics before teardown; keep the original failure.
        with service.factory() as session:
            proposal = service._proposal(session, setup[0], proposal_id, owner=True)
            receipt = service._receipt(session, setup[0], proposal)
            view = service._view(setup[0], proposal)
            error.add_note(
                str(
                    {
                        "proposal_id": str(proposal_id),
                        "decision": receipt["decision"],
                        "reason_codes": receipt["reason_codes"],
                        "current_reasons": service._current(
                            session, setup[0], proposal, receipt, view
                        ),
                        "investigation_status": view.status.value,
                        "stop_reason": view.stop_reason,
                    }
                )
            )
        raise
    # Keep creator session live: a separate authenticated browser session for reviewer.
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as reviewer_client:
        reviewer_client.headers.update(tools.ORIGIN)
        reviewer = tools.identity(reviewer_client, "reviewer")
        decided = service.decide(
            reviewer,
            UUID(approval["approval_id"]),
            ApprovalCommand(reason="Synthetic independent evidence review"),
            "approve",
            uuid4(),
        )
    assert decided["status"] == "APPROVED", decided
    return UUID(approval["approval_id"]), reviewer


@pytest.mark.parametrize(
    "action,index",
    [
        ("create_customer_note", 3),
        ("add_ticket_note", 3),
        ("request_account_reactivation", 3),
        ("reactivate_account", 3),
        ("close_duplicate_ticket", 2),
    ],
)
def test_authorized_actions_and_replay(setup, client, tool_db, action, index):
    p, d = prepared(setup, action, index)
    service = ControlledActionExecutor(tool_db)
    approval = (
        grant(setup, client, p, service)[0]
        if action not in {"create_customer_note", "add_ticket_note"}
        else None
    )
    command = ExecuteCommand(decision_id=d, approval_id=approval)
    key = "synthetic-" + uuid4().hex
    result = service.execute(setup[0], p, command, key, uuid4())
    assert result["status"] == "COMMITTED", result
    assert result["verified"]
    replay = service.execute(setup[0], p, command, key, uuid4())
    assert replay["execution_id"] == result["execution_id"] and replay["replayed"]
    with pytest.raises(HTTPException) as conflict:
        service.execute(setup[0], p, command, key + "new", uuid4())
    assert conflict.value.status_code == 409


@pytest.mark.parametrize(
    "failure",
    [
        "self",
        "foreign",
        "operator",
        "duplicate",
        "expiry",
        "cancel",
        "resource",
        "policy",
        "reviewer_role",
        "reviewer_session",
        "actor_role",
        "missing_approval",
        "forged_approval",
        "verification",
        "mutation",
        "stale_evidence",
    ],
)
def test_fail_closed(setup, client, tool_db, monkeypatch, failure):
    p, d = prepared(setup)
    service = ControlledActionExecutor(tool_db)
    approval = service.request_approval(setup[0], p, uuid4())
    approval_id = UUID(approval["approval_id"])
    command = ApprovalCommand(reason="Independent synthetic review")
    if failure in {"self", "foreign", "operator"}:
        actor = (
            setup[0] if failure != "foreign" else tools.identity(client, "reviewer", 1)
        )
        with pytest.raises(HTTPException) as error:
            service.decide(actor, approval_id, command, "approve", uuid4())
        assert error.value.status_code in {403, 404}
        return
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as other:
        other.headers.update(tools.ORIGIN)
        reviewer = tools.identity(other, "reviewer")
        approved = service.decide(reviewer, approval_id, command, "approve", uuid4())
        assert approved["status"] == "APPROVED"
        if failure == "duplicate":
            assert (
                service.decide(reviewer, approval_id, command, "approve", uuid4())[
                    "error_code"
                ]
                == "invalid_approval_transition"
            )
            return
    if failure == "cancel":
        assert (
            service.decide(setup[0], approval_id, command, "cancel", uuid4())["status"]
            == "CANCELLED"
        )
    with tool_db() as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        if failure == "expiry":
            session.get(ApprovalRequest, approval_id).expires_at = now - timedelta(
                seconds=1
            )
        elif failure == "resource":
            session.get(Account, tools.stable_id("0/account/3")).evidence_version += 1
        elif failure == "policy":
            session.get(Policy, tools.stable_id("0/policy/reactivation/2")).version += 1
        elif failure == "reviewer_role":
            session.get(User, reviewer.user_id).role = "auditor"
        elif failure == "reviewer_session":
            session.get(AuthSession, reviewer.session_id).revoked_at = now
        elif failure == "actor_role":
            session.get(User, setup[0].user_id).role = "auditor"
        elif failure == "stale_evidence":
            session.get(Account, tools.stable_id("0/account/3")).updated_at = (
                now - timedelta(days=3)
            )
    if failure == "verification":
        monkeypatch.setattr(service, "_verify", lambda *args: False)
    if failure == "mutation":

        def fail(*args):
            raise ValueError("synthetic failure")

        monkeypatch.setattr(service, "_mutate", fail)
    with tool_db() as session:
        before = session.get(Account, tools.stable_id("0/account/3")).status
    try:
        result = service.execute(
            setup[0],
            p,
            ExecuteCommand(
                decision_id=d,
                approval_id=None
                if failure == "missing_approval"
                else uuid4()
                if failure == "forged_approval"
                else approval_id,
            ),
            "synthetic-" + uuid4().hex,
            uuid4(),
        )
        assert result["status"] in {"DENIED", "FAILED"}, result
        assert not result["verified"]
    except HTTPException as error:
        assert error.status_code in {403, 404, 409}
    with tool_db() as session:
        assert session.get(Account, tools.stable_id("0/account/3")).status == before


def test_concurrent_duplicate(setup, tool_db):
    p, d = prepared(setup, "create_customer_note")
    service = ControlledActionExecutor(tool_db)
    key = "synthetic-" + uuid4().hex

    def attempt(_):
        try:
            return service.execute(
                setup[0], p, ExecuteCommand(decision_id=d), key, uuid4()
            )
        except Exception as error:
            # PostgreSQL serializable conflicts are safe rollbacks, reconciled by same key.
            from sqlalchemy.exc import DBAPIError

            if not isinstance(error, DBAPIError):
                raise
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    replay = service.execute(setup[0], p, ExecuteCommand(decision_id=d), key, uuid4())
    assert replay["status"] == "COMMITTED"
    with tool_db() as session:
        rows = session.scalars(
            select(BusinessRecord).where(
                BusinessRecord.execution_id == UUID(replay["execution_id"])
            )
        ).all()
        assert len(rows) == 1
    assert any(r and r["status"] == "COMMITTED" for r in results)


def test_http_approval_and_execution(setup, client, tool_db):
    p, d = prepared(setup)
    response = client.post(f"/api/v1/action-proposals/{p}/approval-requests", json={})
    assert response.status_code == 200, response.text
    approval_id = response.json()["approval_id"]
    assert (
        client.post(
            f"/api/v1/action-proposals/{p}/approval-requests",
            json={"tenant_id": str(uuid4())},
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            json={"reason": "Synthetic self approval"},
        ).status_code
        == 403
    )
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as reviewer_client:
        reviewer_client.headers.update(tools.ORIGIN)
        tools.identity(reviewer_client, "reviewer")
        assert reviewer_client.get("/api/v1/approvals").status_code == 200
        detail = reviewer_client.get(f"/api/v1/approvals/{approval_id}")
        assert detail.status_code == 200 and detail.json()["sources"]
        assert (
            reviewer_client.post(
                f"/api/v1/approvals/{approval_id}/approve",
                json={
                    "reason": "Independent synthetic review",
                    "reviewer_id": str(uuid4()),
                },
            ).status_code
            == 422
        )
        approval = reviewer_client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            json={"reason": "Independent synthetic review"},
        )
        assert approval.status_code == 200, approval.text
        headers = {"Idempotency-Key": "http-" + uuid4().hex}
        body = {"decision_id": str(d), "approval_id": approval_id}
        result = client.post(
            f"/api/v1/action-proposals/{p}/execute", json=body, headers=headers
        )
        assert result.status_code == 200, result.text
        assert result.json()["verified"] and result.json()["status"] == "COMMITTED"
        receipt = client.get(
            f"/api/v1/action-executions/{result.json()['execution_id']}"
        )
        assert receipt.status_code == 200 and len(receipt.json()["events"]) == 4
        replay = client.post(
            f"/api/v1/action-proposals/{p}/execute", json=body, headers=headers
        )
        assert replay.status_code == 200 and replay.json()["replayed"]


def test_deadline_crossing_rolls_back(setup, tool_db, monkeypatch):
    from datetime import UTC, datetime

    p, d = prepared(setup, "create_customer_note")
    service = ControlledActionExecutor(tool_db)
    original = service._mutate

    def expired(session, actor, proposal, execution_id, deadline):
        return original(
            session,
            actor,
            proposal,
            execution_id,
            datetime.now(UTC) - timedelta(seconds=1),
        )

    monkeypatch.setattr(service, "_mutate", expired)
    result = service.execute(
        setup[0], p, ExecuteCommand(decision_id=d), "deadline-" + uuid4().hex, uuid4()
    )
    assert result["status"] == "FAILED" and not result["verified"]
    with tool_db() as session:
        assert not session.scalars(select(BusinessRecord)).all()


def test_database_statement_failure_rolls_back(setup, tool_db, monkeypatch):
    from sqlalchemy import text

    p, d = prepared(setup, "create_customer_note")
    service = ControlledActionExecutor(tool_db)
    original = service._mutate

    def broken(session, *args):
        original(session, *args)
        session.execute(text("SELECT 1 / 0"))

    monkeypatch.setattr(service, "_mutate", broken)
    result = service.execute(
        setup[0], p, ExecuteCommand(decision_id=d), "rollback-" + uuid4().hex, uuid4()
    )
    assert result["status"] == "FAILED"
    with tool_db() as session:
        assert not session.scalars(select(BusinessRecord)).all()


@pytest.mark.parametrize(
    "field", ["tenant_id", "actor_id", "reviewer_id", "permissions"]
)
def test_forged_execution_fields_rejected(setup, client, field):
    p, d = prepared(setup, "create_customer_note")
    result = client.post(
        f"/api/v1/action-proposals/{p}/execute",
        json={"decision_id": str(d), field: str(uuid4())},
        headers={"Idempotency-Key": "forged-" + uuid4().hex},
    )
    assert result.status_code == 422


def test_changed_proposal_invalidates_approval(setup, client, tool_db):
    from sqlalchemy import update

    from app.models.entities import ActionProposal

    p, d = prepared(setup)
    service = ControlledActionExecutor(tool_db)
    approval, _ = grant(setup, client, p, service)
    # Explicit privileged corruption fixture; application records are immutable.
    with tool_db() as session, session.begin():
        row = session.get(ActionProposal, p)
        changed = {**row.payload, "arguments": {"unexpected": "changed after grant"}}
        session.execute(
            update(ActionProposal)
            .where(
                ActionProposal.id == p, ActionProposal.tenant_id == setup[0].tenant_id
            )
            .values(payload=changed)
        )
    result = service.execute(
        setup[0],
        p,
        ExecuteCommand(decision_id=d, approval_id=approval),
        "changed-" + uuid4().hex,
        uuid4(),
    )
    assert result["status"] == "DENIED"
    with tool_db() as session:
        assert session.get(ApprovalRequest, approval).status == "INVALIDATED"
        assert session.get(Account, tools.stable_id("0/account/3")).status == "blocked"


def test_response_lost_after_commit_reconciles_by_same_key(setup, client, tool_db):
    from sqlalchemy.exc import OperationalError

    from app.api.execution import service as dependency
    from app.main import app

    p, d = prepared(setup, "create_customer_note")
    real = ControlledActionExecutor(tool_db)

    class LostResponse(ControlledActionExecutor):
        def execute(self, *args, **kwargs):
            real.execute(*args, **kwargs)
            raise OperationalError("COMMIT", {}, OSError("synthetic response loss"))

    app.dependency_overrides[dependency] = lambda: LostResponse(tool_db)
    body = {"decision_id": str(d)}
    headers = {"Idempotency-Key": "lost-" + uuid4().hex}
    try:
        response = client.post(
            f"/api/v1/action-proposals/{p}/execute", json=body, headers=headers
        )
        assert response.status_code == 503 and response.json()["status"] == "UNCERTAIN"
    finally:
        app.dependency_overrides.pop(dependency, None)
    replay = client.post(
        f"/api/v1/action-proposals/{p}/execute", json=body, headers=headers
    )
    assert (
        replay.status_code == 200
        and replay.json()["replayed"]
        and replay.json()["verified"]
    )
    with tool_db() as session:
        assert len(session.scalars(select(BusinessRecord)).all()) == 1


@pytest.mark.parametrize("fault", ["unintended_customer_change", "wrong_record_kind"])
def test_verifier_rejects_unintended_effects(setup, tool_db, monkeypatch, fault):
    from app.models.entities import Customer

    p, d = prepared(setup, "create_customer_note")
    service = ControlledActionExecutor(tool_db)
    original = service._mutate
    with tool_db() as session:
        original_name = session.get(Customer, tools.stable_id("0/customer/3")).name

    def corrupted(session, actor, proposal, execution_id, deadline):
        before, after = original(session, actor, proposal, execution_id, deadline)
        if fault == "unintended_customer_change":
            from sqlalchemy import update

            customer = session.get(Customer, tools.stable_id("0/customer/3"))
            session.execute(
                update(Customer)
                .where(
                    Customer.id == customer.id, Customer.tenant_id == actor.tenant_id
                )
                .values(
                    name="Synthetic unintended change", updated_at=customer.updated_at
                )
            )
        else:
            row = session.scalar(
                select(BusinessRecord).where(
                    BusinessRecord.tenant_id == actor.tenant_id,
                    BusinessRecord.execution_id == execution_id,
                )
            )
            # Explicit fault injection bypasses immutable application history only in the disposable test DB.
            from sqlalchemy import update

            session.execute(
                update(BusinessRecord)
                .where(
                    BusinessRecord.id == row.id,
                    BusinessRecord.tenant_id == actor.tenant_id,
                )
                .values(kind="ticket_note")
            )
        session.flush()
        return before, after

    monkeypatch.setattr(service, "_mutate", corrupted)
    result = service.execute(
        setup[0], p, ExecuteCommand(decision_id=d), "effect-" + uuid4().hex, uuid4()
    )
    assert result["status"] == "FAILED" and not result["verified"]
    with tool_db() as session:
        assert (
            session.get(Customer, tools.stable_id("0/customer/3")).name == original_name
        )
        assert not session.scalars(select(BusinessRecord)).all()


@pytest.mark.parametrize(
    "states,expected", [(["active"], "REQUIRE_APPROVAL"), (["blocked"], "DENY")]
)
def test_duplicate_policy_checks_parent_account_state(setup, tool_db, states, expected):
    with tool_db() as session, session.begin():
        session.get(
            Policy, tools.stable_id("0/policy/duplicate_ticket/1")
        ).account_states = states
    view = policy.investigate(setup, 2, ticket=12)
    body = policy.proposal(
        view,
        "close_duplicate_ticket",
        arguments={"duplicate_of_id": str(tools.stable_id("0/ticket/2"))},
    )
    result = setup[2].create(setup[0], body, uuid4())
    assert result["receipt"]["decision"] == expected, result["receipt"]
    assert (
        f"account:{tools.stable_id('0/account/2')}"
        in result["receipt"]["resource_versions"]
    )

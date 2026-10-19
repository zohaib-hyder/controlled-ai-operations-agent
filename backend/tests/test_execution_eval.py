"""Independent expected outcomes over 52 real PostgreSQL synthetic operations."""

import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import test_controlled_execution as execution
import test_tools as tools
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.execution.service import ControlledActionExecutor
from app.main import app
from app.models.entities import (
    Account,
    ActionExecution,
    ApprovalRequest,
    BusinessRecord,
    Customer,
    Policy,
    Ticket,
    Transaction,
)
from app.schemas.execution import ExecuteCommand

client = execution.client
executor = execution.executor
tool_db = execution.tool_db
setup = execution.setup
ACTIONS = [
    ("create_customer_note", 3),
    ("add_ticket_note", 3),
    ("request_account_reactivation", 3),
    ("reactivate_account", 3),
    ("close_duplicate_ticket", 2),
]
CASES = (
    [("authorized", role, a, i) for role in ("operator", "admin") for a, i in ACTIONS]
    + [
        ("unauthorized", role, a, i)
        for role in ("reviewer", "auditor")
        for a, i in ACTIONS
    ]
    + [("foreign", "operator", a, i) for a, i in ACTIONS]
    + [("resource", "operator", a, i) for a, i in ACTIONS]
    + [("verification", "operator", a, i) for a, i in ACTIONS]
    + [("replay", "operator", a, i) for a, i in ACTIONS]
    + [("expiry", "operator", a, i) for a, i in ACTIONS[2:]]
    + [("policy", "operator", a, i) for a, i in ACTIONS[2:]]
    + [
        ("security", role, "override_security_block", 1)
        for role in ("operator", "reviewer", "admin", "auditor")
    ]
    + [("self", role, "reactivate_account", 3) for role in ("reviewer", "admin")]
)


def snapshot(factory):
    with factory() as session:
        return {
            m.__tablename__: [
                tuple(str(getattr(r, c.name)) for c in m.__table__.columns)
                for r in session.scalars(select(m).order_by(m.id))
            ]
            for m in (Account, Customer, Ticket, Policy, Transaction, BusinessRecord)
        }


@pytest.mark.parametrize(
    "kind,role,action,index", CASES, ids=["-".join(map(str, c)) for c in CASES]
)
def test_execution_security_case(
    setup, client, tool_db, monkeypatch, kind, role, action, index
):
    actor, orchestrator, pdp = setup
    # Auditors never create investigations; unauthorized attempts use a real operator's proposal.
    if kind in {"authorized", "self"} and role != "operator":
        actor = tools.identity(client, role)
        setup = (actor, orchestrator, pdp)
    p, d = execution.prepared(setup, action, index)
    service = ControlledActionExecutor(tool_db)
    approval = None
    if kind not in {"security", "unauthorized", "foreign", "self"} and action not in {
        "create_customer_note",
        "add_ticket_note",
    }:
        approval = execution.grant(setup, client, p, service)[0]
    if kind == "self":
        approval = UUID(service.request_approval(actor, p, uuid4())["approval_id"])
    with tool_db() as session, session.begin():
        if kind == "expiry":
            from datetime import timedelta

            session.get(ApprovalRequest, approval).expires_at = session.scalar(
                select(func.clock_timestamp())
            ) - timedelta(seconds=1)
        elif kind == "policy":
            key = (
                "duplicate_ticket/1"
                if action == "close_duplicate_ticket"
                else "reactivation/2"
            )
            policy = session.get(Policy, tools.stable_id(f"0/policy/{key}"))
            policy.version += 1
        elif kind == "resource":
            model = (
                Customer
                if action == "create_customer_note"
                else Ticket
                if "ticket" in action
                else Account
            )
            # Derive exact target from immutable proposal, including duplicate target ticket12.
            from app.models.entities import ActionProposal

            target = UUID(session.get(ActionProposal, p).payload["target_resource_id"])
            session.get(model, target).updated_at = session.scalar(
                select(func.clock_timestamp())
            )
    if kind == "verification":
        monkeypatch.setattr(service, "_verify", lambda *args: False)
    before = snapshot(tool_db)
    result = None
    blocked = False
    with TestClient(app) as other:
        other.headers.update(tools.ORIGIN)
        runner = (
            tools.identity(other, role, 1 if kind == "foreign" else 0)
            if kind in {"foreign", "unauthorized", "security"}
            else actor
        )
        try:
            if kind == "self":
                from app.schemas.execution import ApprovalCommand

                service.decide(
                    actor,
                    approval,
                    ApprovalCommand(reason="Synthetic self approval attempt"),
                    "approve",
                    uuid4(),
                )
            else:
                command = ExecuteCommand(decision_id=d, approval_id=approval)
                key = "eval-" + uuid4().hex
                result = service.execute(runner, p, command, key, uuid4())
                if kind == "replay" and result["status"] == "COMMITTED":
                    replay = service.execute(runner, p, command, key, uuid4())
                    assert (
                        replay["replayed"]
                        and replay["execution_id"] == result["execution_id"]
                    )
                blocked = result["status"] != "COMMITTED"
        except HTTPException as error:
            assert error.status_code in {403, 404, 409}
            blocked = True
    if kind == "self":
        with tool_db() as session:
            assert session.get(ApprovalRequest, approval).status == "PENDING"
    expected = kind in {"authorized", "replay"}
    committed = bool(result and result["status"] == "COMMITTED" and result["verified"])
    after = snapshot(tool_db)
    unchanged = after == before
    unexpected_effect = False
    if expected:
        from app.models.entities import ActionProposal

        with tool_db() as session:
            target = session.get(ActionProposal, p).payload["target_resource_id"]
        expected_table = (
            "customers"
            if action == "create_customer_note"
            else "tickets"
            if "ticket" in action
            else "accounts"
        )
        for model in (Account, Customer, Ticket, Policy, Transaction, BusinessRecord):
            name = model.__tablename__
            position = list(model.__table__.columns.keys()).index("id")
            old = {row[position]: row for row in before[name]}
            new = {row[position]: row for row in after[name]}
            changed = {
                key for key in old.keys() | new.keys() if old.get(key) != new.get(key)
            }
            if name == expected_table:
                unexpected_effect |= changed != {target}
            elif name == "business_records" and action in {
                "create_customer_note",
                "add_ticket_note",
                "request_account_reactivation",
            }:
                unexpected_effect |= (
                    len(changed) != 1
                    or not set(old) <= set(new)
                    or len(new) != len(old) + 1
                )
            else:
                unexpected_effect |= bool(changed)
    with tool_db() as session:
        count = session.scalar(
            select(func.count())
            .select_from(ActionExecution)
            .where(ActionExecution.proposal_id == p)
        )
    unsafe_mutation = int((not expected and not unchanged) or unexpected_effect)
    record = dict(
        case="-".join(map(str, (kind, role, action, index))),
        kind=kind,
        expected_success=expected,
        success=committed,
        blocked=blocked,
        unsafe_mutations=unsafe_mutation,
        duplicate_mutations=max(0, count - 1),
        verified=bool(result and result["verified"]),
    )
    if directory := os.environ.get("PHASE8_EVALUATION_DIR"):
        folder = Path(directory)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (record["case"] + ".json")).write_text(json.dumps(record))
    assert committed == expected, record
    assert unsafe_mutation == 0 and count <= 1, record
    if expected:
        assert not unchanged

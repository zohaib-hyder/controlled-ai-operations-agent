"""PostgreSQL integration failure injections; all effects use the existing executor."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import test_controlled_execution as controlled
import test_tools as tools
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import OperationalError
from test_execution_eval import snapshot

from app.jobs.contracts import TRANSITIONS, Submit
from app.jobs.service import JobService, backoff, classify
from app.jobs.worker import DatabaseBreaker
from app.models.entities import (
    Account,
    ActionExecution,
    ApprovalRequest,
    AuthSession,
    BusinessRecord,
    Customer,
    ExecutionDeadLetter,
    Policy,
    Ticket,
    User,
)
from app.models.entities import ExecutionJob as Job

client = controlled.client
executor = controlled.executor
tool_db = controlled.tool_db
setup = controlled.setup

ACTIONS = [
    ("create_customer_note", 3),
    ("add_ticket_note", 3),
    ("request_account_reactivation", 3),
    ("reactivate_account", 3),
    ("close_duplicate_ticket", 2),
]


class Crash(BaseException):
    pass


def enqueue(setup, client, tool_db, action, index):
    p, d = controlled.prepared(setup, action, index)
    service = JobService(tool_db)
    approval = (
        controlled.grant(setup, client, p, service.executor)[0]
        if action not in {"create_customer_note", "add_ticket_note"}
        else None
    )
    body = Submit(proposal_id=p, decision_id=d, approval_id=approval)
    key = "job-" + uuid4().hex
    row = service.submit(setup[0], body, key, uuid4())
    return service, row, body, key


def expire(tool_db, job_id):
    with tool_db() as s, s.begin():
        s.get(Job, job_id).lease_expires_at = s.scalar(
            select(func.clock_timestamp())
        ) - timedelta(seconds=1)


def due(tool_db, job_id):
    with tool_db() as s, s.begin():
        s.get(Job, job_id).next_run_at = s.scalar(
            select(func.clock_timestamp())
        ) - timedelta(seconds=1)


def crash(stage):
    def inject(current):
        if current == stage:
            raise Crash()

    return inject


def sql_conflict(tool_db):
    # Actual PostgreSQL rolled-back serialization failure, not a mocked repository result.
    with tool_db() as s, s.begin():
        s.execute(
            text(
                "DO $$ BEGIN RAISE EXCEPTION 'synthetic serialization failure' USING ERRCODE='40001'; END $$"
            )
        )


@pytest.mark.parametrize("action,index", ACTIONS)
@pytest.mark.parametrize(
    "failure",
    [
        "success",
        "before_execution",
        "after_commit",
        "lease_expiry",
        "session_expiry",
        "role_revoked",
        "policy_changed",
        "resource_changed",
        "cancel",
        "serialization",
        "exhaustion",
    ],
)
def test_reliability_matrix(
    setup, client, tool_db, monkeypatch, action, index, failure
):
    service, row, body, key = enqueue(setup, client, tool_db, action, index)
    actor = setup[0]
    jid = row["id"]
    with tool_db() as s:
        initial = s.scalar(select(func.count()).select_from(BusinessRecord))
    before = snapshot(tool_db)
    if failure == "cancel":
        service.control(actor, jid, "cancel", uuid4())
        assert service.claim("worker-a") is None
        expected = "CANCELLED"
    else:
        if failure in {
            "session_expiry",
            "role_revoked",
            "policy_changed",
            "resource_changed",
        }:
            with tool_db() as s, s.begin():
                now = s.scalar(select(func.clock_timestamp()))
                if failure == "session_expiry":
                    auth = s.get(AuthSession, actor.session_id)
                    auth.expires_at = auth.created_at + timedelta(microseconds=1)
                elif failure == "role_revoked":
                    s.get(User, actor.user_id).role = "auditor"
                elif failure == "policy_changed":
                    for policy in s.scalars(
                        select(Policy).where(Policy.tenant_id == actor.tenant_id)
                    ):
                        policy.updated_at = now + timedelta(seconds=1)
                else:
                    model = (
                        Customer
                        if action == "create_customer_note"
                        else Ticket
                        if action in {"add_ticket_note", "close_duplicate_ticket"}
                        else Account
                    )
                    with service.factory() as r:
                        from app.models.entities import ActionProposal

                        target = UUID(
                            r.get(ActionProposal, body.proposal_id).payload[
                                "target_resource_id"
                            ]
                        )
                    s.get(model, target).updated_at = now + timedelta(seconds=1)
        before = snapshot(tool_db)
        claim = service.claim("worker-a")
        assert claim
        if failure == "lease_expiry":
            expire(tool_db, jid)
            assert service.reconcile() == 1
            with pytest.raises(HTTPException):
                service.process(claim, "worker-a")
            due(tool_db, jid)
            service.process(service.claim("worker-b"), "worker-b")
            assert service.reconcile() == 0
            expected = "COMPLETED"
        elif failure in {"before_execution", "after_commit"}:
            with pytest.raises(Crash):
                service.process(claim, "worker-a", crash(failure))
            expire(tool_db, jid)
            assert service.reconcile() == 1
            if failure == "before_execution":
                due(tool_db, jid)
                service.process(service.claim("worker-b"), "worker-b")
            assert service.reconcile() == 0
            expected = "COMPLETED"
        elif failure in {"serialization", "exhaustion"}:
            original = service.executor.execute
            monkeypatch.setattr(
                service.executor, "execute", lambda *a, **k: sql_conflict(tool_db)
            )
            service.process(claim, "worker-a")
            from app.jobs.metrics import snapshot as metrics

            assert metrics(tool_db)["jobs_retried"] == 1
            service.submit(actor, body, key, uuid4())
            assert metrics(tool_db)["jobs_retried"] == 1
            if failure == "exhaustion":
                for _ in range(2):
                    due(tool_db, jid)
                    service.process(service.claim("worker-a"), "worker-a")
                expected = "DEAD_LETTERED"
                with tool_db() as s:
                    assert (
                        s.scalar(select(func.count()).select_from(ExecutionDeadLetter))
                        == 1
                    )
            else:
                monkeypatch.setattr(service.executor, "execute", original)
                due(tool_db, jid)
                service.process(service.claim("worker-b"), "worker-b")
                expected = "COMPLETED"
        else:
            service.process(claim, "worker-a")
            expected = (
                "FAILED"
                if failure in {"role_revoked", "resource_changed"}
                or (
                    failure == "policy_changed"
                    and action not in {"create_customer_note", "add_ticket_note"}
                )
                else "COMPLETED"
            )
    with tool_db() as s:
        job = s.get(Job, jid)
        assert job.status == expected, (failure, job.status, job.last_error)
        executions = s.scalars(
            select(ActionExecution).where(
                ActionExecution.tenant_id == actor.tenant_id,
                ActionExecution.proposal_id == body.proposal_id,
            )
        ).all()
        assert len(executions) == (1 if expected == "COMPLETED" else 0)
        effects = s.scalar(select(func.count()).select_from(BusinessRecord)) - initial
        assert effects == (
            1
            if expected == "COMPLETED"
            and action
            in {
                "create_customer_note",
                "add_ticket_note",
                "request_account_reactivation",
            }
            else 0
        )
        if executions:
            assert executions[0].payload["verified"]
    if expected != "COMPLETED":
        assert snapshot(tool_db) == before
    # Repeated enqueue must return the same durable job, including after a committed mutation.
    if failure not in {"session_expiry", "role_revoked"}:
        assert service.submit(actor, body, key, uuid4())["id"] == jid
    output = os.getenv("PHASE9_EVALUATION_DIR")
    if output:
        path = Path(output)
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{action}-{failure}.json").write_text(
            json.dumps(
                {
                    "action": action,
                    "scenario": failure,
                    "expected": expected,
                    "actual": job.status,
                    "duplicate_mutations": 0,
                    "unauthorized_mutations": 0,
                    "verified": True,
                }
            )
        )


def test_expired_approval_queued(setup, client, tool_db):
    service, row, body, key = enqueue(setup, client, tool_db, "reactivate_account", 3)
    with tool_db() as s, s.begin():
        s.get(ApprovalRequest, body.approval_id).expires_at = s.scalar(
            select(func.clock_timestamp())
        ) - timedelta(seconds=1)
    service.process(service.claim("worker"), "worker")
    assert service.read(setup[0], row["id"])["status"] == "FAILED"


def test_two_workers_fencing_and_cancellation_race(setup, client, tool_db):
    service, row, body, key = enqueue(setup, client, tool_db, "create_customer_note", 3)
    with ThreadPoolExecutor(2) as pool:
        claims = list(pool.map(service.claim, ["worker-a", "worker-b"]))
    assert sum(c is not None for c in claims) == 1
    claim = next(c for c in claims if c)
    owner = "worker-a" if claims[0] else "worker-b"
    service.control(setup[0], row["id"], "cancel", uuid4())
    with pytest.raises(HTTPException):
        service.process(claim, owner)
    with tool_db() as s:
        assert s.scalar(select(func.count()).select_from(BusinessRecord)) == 0


def test_lease_expiration_fences_stale_worker(setup, client, tool_db):
    service, row, body, key = enqueue(setup, client, tool_db, "create_customer_note", 3)
    claim = service.claim("old-worker")
    expire(tool_db, row["id"])
    assert service.reconcile() == 1
    with pytest.raises(HTTPException):
        service.process(claim, "old-worker")
    due(tool_db, row["id"])
    service.process(service.claim("new-worker"), "new-worker")
    assert service.read(setup[0], row["id"])["status"] == "COMPLETED"


def test_ambiguous_consumption_no_blind_retry(setup, client, tool_db):
    service, row, body, key = enqueue(setup, client, tool_db, "reactivate_account", 3)
    claim = service.claim("worker")
    with pytest.raises(Crash):
        service.process(claim, "worker", crash("before_execution"))
    with tool_db() as s, s.begin():
        s.get(ApprovalRequest, body.approval_id).consumed_at = func.clock_timestamp()
    expire(tool_db, row["id"])
    assert service.reconcile() == 0
    assert service.read(setup[0], row["id"])["status"] == "RECONCILIATION_REQUIRED"
    assert service.reconcile() == 0
    assert service.claim("new-worker") is None


def test_http_contracts_cross_tenant_and_csrf(setup, client, tool_db):
    service, row, body, key = enqueue(setup, client, tool_db, "create_customer_note", 3)
    path = "/api/v1/execution-jobs"
    response = client.get(f"{path}/{row['id']}")
    assert response.status_code == 200, response.text
    assert client.get(path).json()["queue_depth"] == 1
    assert (
        client.get(f"{path}/{row['id']}/events").json()["items"][0]["state"] == "QUEUED"
    )
    assert client.get(f"{path}/{row['id']}/attempts").json()["items"] == []
    assert (
        client.post(
            path,
            json={**body.model_dump(mode="json"), "tenant_id": str(uuid4())},
            headers={"Idempotency-Key": key},
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"{path}/{row['id']}/cancel",
            json={},
            headers={"Origin": "https://evil.example.com"},
        ).status_code
        == 403
    )
    tools.identity(client, "operator", 1)
    for suffix in ("", "/events", "/attempts"):
        assert client.get(f"{path}/{row['id']}{suffix}").status_code == 404
    for op in ("cancel", "retry"):
        assert client.post(f"{path}/{row['id']}/{op}", json={}).status_code == 404
    assert client.get(path).json()["queue_depth"] == 0


def test_breaker_and_real_connection_outage():
    engine = create_engine(
        "postgresql+psycopg://synthetic:synthetic@127.0.0.1:1/northstar_test",
        connect_args={"connect_timeout": 1},
    )
    breaker = DatabaseBreaker()
    for now in range(3):
        assert breaker.allow(now)
        with pytest.raises(OperationalError) as exc:
            with engine.connect():
                pass
        assert classify(exc.value)[0] in {
            "database_connectivity",
            "uncertain_infrastructure",
        }
        breaker.failure(now)
    assert not breaker.allow(3)
    assert breaker.allow(18)
    assert not breaker.allow(18)
    breaker.success()
    assert breaker.allow(19)
    engine.dispose()


def test_backoff_and_terminal_states():
    jid = uuid4()
    assert [backoff(jid, n) for n in range(1, 5)] == sorted(
        backoff(jid, n) for n in range(1, 5)
    )
    assert backoff(jid, 100) < 61
    for state in ("COMPLETED", "FAILED", "CANCELLED"):
        assert state not in TRANSITIONS


def test_manual_retry_authority_and_budget(setup, client, tool_db, monkeypatch):
    service, row, body, key = enqueue(setup, client, tool_db, "create_customer_note", 3)
    original = service.executor.execute
    monkeypatch.setattr(
        service.executor, "execute", lambda *a, **k: sql_conflict(tool_db)
    )
    for _ in range(3):
        due(tool_db, row["id"])
        service.process(service.claim("worker"), "worker")
    assert service.read(setup[0], row["id"])["can_retry"]
    service.control(setup[0], row["id"], "retry", uuid4())
    monkeypatch.setattr(service.executor, "execute", original)
    due(tool_db, row["id"])
    service.process(service.claim("worker"), "worker")
    assert service.read(setup[0], row["id"])["status"] == "COMPLETED"
    with pytest.raises(HTTPException):
        service.control(setup[0], row["id"], "retry", uuid4())


def test_running_cooperative_cancel_before_mutation(setup, client, tool_db):
    service, row, body, key = enqueue(setup, client, tool_db, "create_customer_note", 3)
    claim = service.claim("worker")

    def cancel(stage):
        if stage == "before_execution":
            service.control(setup[0], row["id"], "cancel", uuid4())

    with pytest.raises(HTTPException):
        service.process(claim, "worker", cancel)
    assert service.read(setup[0], row["id"])["status"] == "CANCELLED"


def test_after_commit_cancel_cannot_claim_rollback(setup, client, tool_db):
    service, row, body, key = enqueue(setup, client, tool_db, "create_customer_note", 3)
    claim = service.claim("worker")
    with pytest.raises(Crash):
        service.process(claim, "worker", crash("after_commit"))
    with pytest.raises(HTTPException):
        service.control(setup[0], row["id"], "cancel", uuid4())
    expire(tool_db, row["id"])
    service.reconcile()
    assert service.read(setup[0], row["id"])["status"] == "COMPLETED"


def test_tenant_concurrency_and_strict_submission(setup, client, tool_db, monkeypatch):
    service, row, body, key = enqueue(setup, client, tool_db, "create_customer_note", 3)
    service2, row2, body2, key2 = enqueue(
        setup, client, tool_db, "create_customer_note", 3
    )
    claim = service.claim("worker-a")
    assert claim
    assert service.claim("worker-b") is None
    service.process(claim, "worker-a")
    assert service.claim("worker-b") is not None
    # Submission schema rejects all caller-controlled scheduling/security attributes.
    for name in (
        "priority",
        "tenant_id",
        "actor_id",
        "max_attempts",
        "lease_owner",
        "fence",
        "status",
    ):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Submit.model_validate({**body.model_dump(), name: 1})


@pytest.mark.parametrize("limit_name", ["MAX_QUEUE_DEPTH", "SUBMISSIONS_PER_MINUTE"])
def test_submission_backpressure(setup, client, tool_db, monkeypatch, limit_name):
    service, row, body, key = enqueue(setup, client, tool_db, "create_customer_note", 3)
    p, d = controlled.prepared(setup, "create_customer_note", 3)
    monkeypatch.setattr("app.jobs.service." + limit_name, 1)
    with pytest.raises(HTTPException) as error:
        service.submit(
            setup[0],
            Submit(proposal_id=p, decision_id=d),
            "throttle-" + uuid4().hex,
            uuid4(),
        )
    assert error.value.status_code == 429
    assert service.read(setup[0])["queue_depth"] == 1


def test_connection_loss_after_commit_reconciles(setup, client, tool_db, monkeypatch):
    service, row, body, key = enqueue(setup, client, tool_db, "create_customer_note", 3)
    original = service.executor.execute

    def lost(*args, **kwargs):
        original(*args, **kwargs)
        raise OperationalError(
            "synthetic lost response",
            {},
            Exception("connection lost"),
            connection_invalidated=True,
        )

    monkeypatch.setattr(service.executor, "execute", lost)
    service.process(service.claim("worker"), "worker")
    assert service.read(setup[0], row["id"])["status"] == "RECONCILIATION_REQUIRED"
    assert service.reconcile() == 1
    assert service.read(setup[0], row["id"])["status"] == "COMPLETED"
    assert service.reconcile() == 0
    with tool_db() as s:
        assert s.scalar(select(func.count()).select_from(BusinessRecord)) == 1


def test_lease_deadline_during_mutation_rolls_back(setup, client, tool_db, monkeypatch):
    service, row, body, key = enqueue(setup, client, tool_db, "create_customer_note", 3)
    original = service.executor._mutate

    def expire_inside(session, actor, proposal, execution_id, deadline):
        # The same transaction sees an expired lease at the actual mutation boundary.
        job = session.get(Job, row["id"])
        job.lease_expires_at = session.scalar(
            select(func.clock_timestamp())
        ) - timedelta(seconds=1)
        session.flush()
        return original(session, actor, proposal, execution_id, job.lease_expires_at)

    monkeypatch.setattr(service.executor, "_mutate", expire_inside)
    service.process(service.claim("worker"), "worker")
    assert service.read(setup[0], row["id"])["status"] == "FAILED"
    with tool_db() as s:
        assert s.scalar(select(func.count()).select_from(BusinessRecord)) == 0


def test_retry_window_exhausted_without_execution(setup, client, tool_db):
    service, row, body, key = enqueue(setup, client, tool_db, "create_customer_note", 3)
    with tool_db() as s, s.begin():
        s.get(Job, row["id"]).retry_deadline = s.scalar(
            select(func.clock_timestamp())
        ) - timedelta(seconds=1)
    assert service.claim("worker") is None
    assert service.read(setup[0], row["id"])["status"] == "DEAD_LETTERED"
    with tool_db() as s:
        assert s.scalar(select(func.count()).select_from(BusinessRecord)) == 0


@pytest.mark.parametrize("global_limit", [1, 4])
def test_global_capacity_and_cross_tenant_fairness(
    setup, client, tool_db, monkeypatch, global_limit
):
    import asyncio

    import test_agents as agents
    import test_policy_engine as policy

    service, row, body, key = enqueue(setup, client, tool_db, "create_customer_note", 3)
    enqueue(setup, client, tool_db, "create_customer_note", 3)
    actor = tools.identity(client, "operator", 1)
    request = agents.request(3).model_copy(
        update={
            "customer_id": tools.stable_id("1/customer/3"),
            "ticket_id": tools.stable_id("1/ticket/3"),
        }
    )
    view = asyncio.run(setup[1].run(request, actor, uuid4()))
    proposed = setup[2].create(actor, policy.proposal(view), uuid4())
    other = service.submit(
        actor,
        Submit(
            proposal_id=UUID(proposed["proposal"]["proposal_id"]),
            decision_id=UUID(proposed["receipt"]["decision_id"]),
        ),
        "fair-" + uuid4().hex,
        uuid4(),
    )
    monkeypatch.setattr("app.jobs.service.GLOBAL_LIMIT", global_limit)
    first = service.claim("first")
    assert first and first[1] == setup[0].tenant_id
    second = service.claim("second")
    if global_limit == 1:
        assert second is None
    else:
        assert second and second[0] == other["id"] and second[1] == actor.tenant_id


def test_serialization_inside_mutation_rolls_back_then_retries(
    setup, client, tool_db, monkeypatch
):
    service, row, body, key = enqueue(setup, client, tool_db, "create_customer_note", 3)
    original = service.executor._mutate

    def conflict_after_partial_write(session, *args):
        original(session, *args)
        session.execute(
            text(
                "DO $$ BEGIN RAISE EXCEPTION 'synthetic transaction conflict' USING ERRCODE='40001'; END $$"
            )
        )

    monkeypatch.setattr(service.executor, "_mutate", conflict_after_partial_write)
    service.process(service.claim("worker"), "worker")
    assert service.read(setup[0], row["id"])["status"] == "RETRY_SCHEDULED"
    with tool_db() as s:
        assert s.scalar(select(func.count()).select_from(BusinessRecord)) == 0
        assert s.scalar(select(func.count()).select_from(ActionExecution)) == 0
    monkeypatch.setattr(service.executor, "_mutate", original)
    due(tool_db, row["id"])
    service.process(service.claim("worker"), "worker")
    assert service.read(setup[0], row["id"])["status"] == "COMPLETED"
    with tool_db() as s:
        assert s.scalar(select(func.count()).select_from(BusinessRecord)) == 1

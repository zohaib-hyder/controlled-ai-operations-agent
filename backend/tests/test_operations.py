"""Real PostgreSQL operations correctness, authorization, bounds and evaluation."""

import json
import os
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import test_durable_jobs as jobs
import test_tools as tools
from fastapi import HTTPException
from sqlalchemy import event, func, select, text
from test_execution_eval import snapshot

from app.models.entities import (
    ExecutionJob,
    ExecutionJobEvent,
    Investigation,
    SecurityEvent,
    User,
    WorkerObservation,
)
from app.models.entities import (
    OperationsIncidentEvent as IncidentEvent,
)
from app.operations.contracts import IncidentCommand, Window
from app.operations.incidents import IncidentService
from app.operations.service import OperationsMetricsService
from app.operations.worker import observe

client = jobs.client
executor = jobs.executor
tool_db = jobs.tool_db
setup = jobs.setup

CASES = [
    "dead",
    "recon",
    "queued",
    "completed",
    "failed",
    "retry",
    "empty",
    "foreign",
    "response",
    "denials",
]


@pytest.mark.parametrize("role", ["operator", "reviewer", "admin", "auditor"])
@pytest.mark.parametrize("kind", CASES)
def test_operations_evaluation(setup, client, tool_db, role, kind):
    service, row, body, key = jobs.enqueue(
        setup, client, tool_db, "create_customer_note", 3
    )
    state = {
        "dead": "DEAD_LETTERED",
        "recon": "RECONCILIATION_REQUIRED",
        "queued": "QUEUED",
        "failed": "FAILED",
        "retry": "RETRY_SCHEDULED",
    }.get(kind, "QUEUED")
    if kind == "completed":
        service.process(service.claim("ops-worker"), "ops-worker")
        state = "COMPLETED"
    else:
        with tool_db() as s, s.begin():
            job = s.get(ExecutionJob, row["id"])
            job.status = state
            if kind == "retry":
                s.add(
                    ExecutionJobEvent(
                        tenant_id=job.tenant_id,
                        job_id=job.id,
                        state=state,
                        category="transaction_conflict",
                        correlation_id=uuid4(),
                    )
                )
            if kind == "denials":
                for _ in range(5):
                    s.add(
                        SecurityEvent(
                            tenant_id=job.tenant_id,
                            actor_id=job.actor_id,
                            event_type="execution_denied",
                            outcome="denied",
                            request_id=uuid4(),
                            resource_type="controlled_action",
                        )
                    )
    incidents = IncidentService(tool_db)
    with tool_db() as s, s.begin():
        now = s.scalar(select(func.clock_timestamp()))
        first = incidents.detect(s, setup[0].tenant_id, now)
    with tool_db() as s, s.begin():
        assert (
            incidents.detect(
                s, setup[0].tenant_id, s.scalar(select(func.clock_timestamp()))
            )
            == 0
        )
    expected_incident = kind in {"dead", "recon", "denials"}
    assert first == int(expected_incident)
    actor = (
        setup[0]
        if role == "operator" and kind != "foreign"
        else tools.identity(client, role, 1 if kind == "foreign" else 0)
    )
    window = Window()
    if kind == "empty":
        with tool_db() as s:
            now = s.scalar(select(func.clock_timestamp()))
        window = Window(
            range="custom", start=now + timedelta(days=1), end=now + timedelta(days=2)
        )
    ops = OperationsMetricsService(tool_db)
    result = ops.overview(actor, window)
    visible = kind not in {"empty", "foreign"}
    assert result["metrics"]["job_counts"] == ({state: 1} if visible else {})
    assert result["metrics"]["investigation_counts"] == (
        {"COMPLETED": 1} if visible else {}
    )
    assert result["metrics"]["job_success"]["denominator"] == (
        1 if visible and state in {"FAILED", "COMPLETED", "DEAD_LETTERED"} else 0
    )
    assert result["metrics"]["job_success"]["percent"] == (
        100.0
        if visible and state == "COMPLETED"
        else 0.0
        if visible and state in {"FAILED", "DEAD_LETTERED"}
        else None
    )
    assert result["metrics"]["open_incidents"] == (
        int(expected_incident) if kind != "foreign" else 0
    )  # current backlog, independent of cohort
    codes = {a["code"] for a in result["alerts"]}
    assert ("dead_letter_backlog" in codes) == (kind == "dead")
    assert ("reconciliation_backlog" in codes) == (kind == "recon")
    if kind == "foreign":
        with pytest.raises(HTTPException) as error:
            ops.correlate(actor, body.proposal_id, Window())
        assert error.value.status_code == 404
        assert incidents.listing(actor, Window(), 20, 0)["items"] == []
        assert all(e["actor_id"] == actor.user_id for e in result["recent"])
        assert all(
            e["entity_id"] not in {row["id"], body.proposal_id}
            for e in result["recent"]
        )
    else:
        trace = ops.correlate(actor, body.proposal_id, Window())
        kinds = {link["kind"] for link in trace["links"]}
        assert {"investigation", "proposal", "decision", "job"} <= kinds
        assert ("execution" in kinds) == (kind == "completed")
        assert all(e["summary"] for e in trace["timeline"])
    before = snapshot(tool_db)
    if kind == "response":
        with tool_db() as s, s.begin():
            job = s.get(ExecutionJob, row["id"])
            job.status = "DEAD_LETTERED"
            incidents.detect(
                s, actor.tenant_id, s.scalar(select(func.clock_timestamp()))
            )
        incident = incidents.listing(actor, Window(), 20, 0)["items"][0]
        if role in {"admin", "reviewer"}:
            for op in ("acknowledge", "investigate", "resolve", "close"):
                detail = incidents.respond(
                    actor,
                    incident["id"],
                    op,
                    IncidentCommand(note="Synthetic operational review"),
                    uuid4(),
                )
            assert detail["incident"]["status"] == "CLOSED"
            with tool_db() as s:
                assert s.get(ExecutionJob, row["id"]).status == "DEAD_LETTERED"
        else:
            with pytest.raises(HTTPException) as err:
                incidents.respond(
                    actor,
                    incident["id"],
                    "acknowledge",
                    IncidentCommand(note="Synthetic review attempt"),
                    uuid4(),
                )
            assert err.value.status_code == 403
    assert snapshot(tool_db) == before
    if output := os.getenv("PHASE10_EVALUATION_DIR"):
        path = Path(output)
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{kind}-{role}.json").write_text(
            json.dumps(
                {
                    "case": f"{kind}-{role}",
                    "kind": kind,
                    "role": role,
                    "metrics_correct": True,
                    "detection_correct": True,
                    "dedup_correct": True,
                    "correlation_correct": True,
                    "authorization_correct": True,
                    "leaks": 0,
                    "alerts_correct": True,
                }
            )
        )


def test_empty_and_http_bounds(client, tool_db):
    tools.identity(client)
    r = client.get("/api/v1/operations/overview")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["metrics"]["investigation_completion"]["percent"] is None
    for name in ("investigation_duration", "approval_turnaround", "execution_latency"):
        assert data["metrics"][name] == dict(
            count=0, mean_seconds=None, p50_seconds=None, p95_seconds=None
        )
    assert data["health"]["worker"] == "unknown"
    for query in (
        "range=custom",
        "range=custom&start=2026-01-01&end=2026-01-02",
        "range=custom&start=2026-01-01T00:00:00Z&end=2026-03-01T00:00:00Z",
        "range=forever",
    ):
        assert client.get("/api/v1/operations/overview?" + query).status_code == 422
    for query in ("limit=51", "offset=10001", "limit=0"):
        assert client.get("/api/v1/operations/activity?" + query).status_code == 422
    assert client.post("/api/v1/incidents/detect", json={}).status_code == 403
    assert client.post("/api/v1/operations/thresholds", json={}).status_code == 403


def test_worker_health_thresholds_and_config(client, tool_db):
    actor = tools.identity(client, "admin")
    ops = OperationsMetricsService(tool_db)
    observe(tool_db, "worker-test")
    assert ops.overview(actor, Window())["health"]["worker"] == "healthy"
    observe(tool_db, "worker-test", True)
    assert ops.overview(actor, Window())["health"]["worker"] == "unavailable"
    observe(tool_db, "worker-test")
    with tool_db() as s, s.begin():
        s.get(WorkerObservation, "worker-test").observed_at = s.scalar(
            select(func.clock_timestamp())
        ) - timedelta(minutes=10)
    assert ops.overview(actor, Window())["health"]["overall"] == "degraded"
    assert (
        client.post(
            "/api/v1/operations/thresholds",
            json={"queue_age_seconds": 12},
            headers={"Origin": "https://evil.example.com"},
        ).status_code
        == 403
    )
    r = client.post("/api/v1/operations/thresholds", json={"queue_age_seconds": 12})
    assert r.status_code == 200, r.text
    assert ops.overview(actor, Window())["thresholds"].queue_age_seconds == 12
    assert (
        client.post(
            "/api/v1/operations/thresholds", json={"queue_age_seconds": 0}
        ).status_code
        == 422
    )


def test_incident_assignment_immutability_and_foreign(setup, client, tool_db):
    service, row, body, key = jobs.enqueue(
        setup, client, tool_db, "create_customer_note", 3
    )
    with tool_db() as s, s.begin():
        s.get(ExecutionJob, row["id"]).status = "DEAD_LETTERED"
    actor = tools.identity(client, "reviewer")
    svc = IncidentService(tool_db)
    assert svc.detect_authorized(actor)["created"] == 1
    incident = svc.listing(actor, Window(), 20, 0)["items"][0]
    id = incident["id"]
    bad = client.post(
        f"/api/v1/incidents/{id}/assign",
        json={
            "note": "Synthetic assignment",
            "assigned_to": str(tools.stable_id("1/user/reviewer")),
        },
    )
    assert bad.status_code == 404
    good = client.post(
        f"/api/v1/incidents/{id}/assign",
        json={"note": "Synthetic assignment", "assigned_to": str(actor.user_id)},
    )
    assert good.status_code == 200, good.text
    assert (
        client.post(
            f"/api/v1/incidents/{id}/resolve", json={"note": "Too early resolution"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/incidents/{id}/notes", json={"note": "password=never-submit"}
        ).status_code
        == 422
    )
    with tool_db() as s:
        ev = s.scalar(select(IncidentEvent))
        ev.note = "tamper"
        with pytest.raises(ValueError):
            s.flush()
    foreign = tools.identity(client, "admin", 1)
    assert client.get(f"/api/v1/incidents/{id}").status_code == 404
    assert (
        client.post(
            f"/api/v1/incidents/{id}/acknowledge",
            json={"note": "Foreign operation blocked"},
        ).status_code
        == 404
    )
    assert svc.listing(foreign, Window(), 20, 0)["items"] == []


def test_query_budget_ordering_windows_and_pagination(setup, client, tool_db):
    service, row, body, key = jobs.enqueue(
        setup, client, tool_db, "create_customer_note", 3
    )
    ops = OperationsMetricsService(tool_db)
    actor = setup[0]
    queries = []
    engine = tool_db.kw["bind"]

    def count(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        result = ops.overview(actor, Window())
    finally:
        event.remove(engine, "before_cursor_execute", count)
    assert len(queries) <= 35, len(queries)
    a = ops.activity_page(actor, Window(), 5, 0)["items"]
    b = ops.activity_page(actor, Window(), 5, 5)["items"]
    assert not {x["id"] for x in a} & {x["id"] for x in b}
    assert [x["id"] for x in a] == [
        x["id"] for x in ops.activity_page(actor, Window(), 5, 0)["items"]
    ]
    assert len(result["metrics"]["volume"]) <= 32
    with tool_db() as s, s.begin():
        row = s.get(
            Investigation,
            next(
                link["id"]
                for link in ops.correlate(actor, body.proposal_id, Window())["links"]
                if link["kind"] == "investigation"
            ),
        )
        end = row.created_at
        start = end - timedelta(days=1)
    custom = ops.overview(actor, Window(range="custom", start=start, end=end))
    assert custom["metrics"]["investigation_counts"] == {}  # half-open end exclusion
    with tool_db() as s:
        plan = (
            s.execute(
                text(
                    "EXPLAIN SELECT id FROM execution_jobs WHERE tenant_id=:tenant AND status='QUEUED' ORDER BY created_at LIMIT 50"
                ),
                {"tenant": actor.tenant_id},
            )
            .scalars()
            .all()
        )
        assert plan


def test_repeated_lease_detection_uses_durable_events(setup, client, tool_db):
    service, row, body, key = jobs.enqueue(
        setup, client, tool_db, "create_customer_note", 3
    )
    for _ in range(3):
        jobs.due(tool_db, row["id"])
        assert service.claim("crashing-worker")
        jobs.expire(tool_db, row["id"])
        service.reconcile()
    svc = IncidentService(tool_db)
    with tool_db() as s, s.begin():
        assert (
            svc.detect(s, setup[0].tenant_id, s.scalar(select(func.clock_timestamp())))
            == 2
        )
    actor = tools.identity(client, "admin")
    items = svc.listing(actor, Window(), 20, 0)["items"]
    assert {i["category"] for i in items} == {"dead_letter", "lease_expiration"}
    assert all(i["source_event_id"] is not None for i in items)


def test_persistent_failure_detection_does_not_change_business(setup, client, tool_db):
    service = None
    for _ in range(3):
        service, _, _, _ = jobs.enqueue(
            setup, client, tool_db, "create_customer_note", 3
        )
    with tool_db() as s, s.begin():
        s.get(User, setup[0].user_id).is_active = False
    before = snapshot(tool_db)
    for _ in range(3):
        service.process(service.claim("worker"), "worker")
    actor = tools.identity(client, "admin")
    svc = IncidentService(tool_db)
    assert svc.detect_authorized(actor)["created"] == 1
    assert (
        svc.listing(actor, Window(), 20, 0)["items"][0]["category"]
        == "persistent_failure"
    )
    assert snapshot(tool_db) == before


def test_invalidated_approval_detection(setup, client, tool_db):
    service, row, body, key = jobs.enqueue(
        setup, client, tool_db, "reactivate_account", 3
    )
    from app.models.entities import Account

    with tool_db() as s, s.begin():
        s.get(Account, tools.stable_id("0/account/3")).evidence_version += 1
    assert (
        service.executor.detail(setup[0], body.approval_id, uuid4())["status"]
        == "INVALIDATED"
    )
    svc = IncidentService(tool_db)
    with tool_db() as s, s.begin():
        assert (
            svc.detect(s, setup[0].tenant_id, s.scalar(select(func.clock_timestamp())))
            == 1
        )
    assert (
        svc.listing(setup[0], Window(), 20, 0)["items"][0]["category"]
        == "approval_failure"
    )


def test_operations_rate_limit(client, tool_db):
    actor = tools.identity(client)
    from app.models.entities import OperationsRateBucket

    with tool_db() as s, s.begin():
        s.add(
            OperationsRateBucket(
                tenant_id=actor.tenant_id,
                actor_id=actor.user_id,
                kind="read",
                attempts=120,
                window_started_at=func.clock_timestamp(),
            )
        )
    r = client.get("/api/v1/operations/overview")
    assert r.status_code == 429 and r.headers["Retry-After"] == "60"
    with tool_db() as s, s.begin():
        bucket = s.scalar(select(OperationsRateBucket))
        bucket.window_started_at = s.scalar(select(func.clock_timestamp())) - timedelta(
            seconds=61
        )
    assert client.get("/api/v1/operations/overview").status_code == 200


def test_live_role_revalidation_and_migration_signal(
    setup, client, tool_db, monkeypatch
):
    from dataclasses import replace

    from app.operations.contracts import Thresholds

    actor = replace(setup[0], role="admin")
    svc = OperationsMetricsService(tool_db)
    assert svc.overview(actor, Window())["scope"] == "own"
    with pytest.raises(HTTPException):
        svc.configure(actor, Thresholds(), uuid4())
    with pytest.raises(HTTPException):
        IncidentService(tool_db).detect_authorized(actor)
    monkeypatch.setattr(
        "app.operations.service.EXPECTED_REVISION", "unsupported_binary"
    )
    assert svc.overview(actor, Window())["health"]["migration"] == "degraded"


def test_numeric_duration_samples_and_read_only_metrics(setup, client, tool_db):
    service, row, body, key = jobs.enqueue(
        setup, client, tool_db, "reactivate_account", 3
    )
    service.process(service.claim("worker"), "worker")
    before = snapshot(tool_db)
    result = OperationsMetricsService(tool_db).overview(setup[0], Window())
    for name in ("investigation_duration", "approval_turnaround", "execution_latency"):
        summary = result["metrics"][name]
        assert summary["count"] == 1
        assert (
            0
            <= summary["mean_seconds"]
            == summary["p50_seconds"]
            == summary["p95_seconds"]
        )
    assert result["metrics"]["job_success"]["percent"] == 100.0
    assert snapshot(tool_db) == before


def test_bounded_detection_progress_and_incident_trace(
    setup, client, tool_db, monkeypatch
):
    records = [
        jobs.enqueue(setup, client, tool_db, "create_customer_note", 3)
        for _ in range(2)
    ]
    with tool_db() as s, s.begin():
        for _service, row, _body, _key in records:
            s.get(ExecutionJob, row["id"]).status = "DEAD_LETTERED"
    monkeypatch.setattr("app.operations.incidents.DETECTION_BATCH", 1)
    svc = IncidentService(tool_db)
    for expected in (1, 1, 0):
        with tool_db() as s, s.begin():
            assert (
                svc.detect(
                    s, setup[0].tenant_id, s.scalar(select(func.clock_timestamp()))
                )
                == expected
            )
    trace = svc.correlate(setup[0], records[0][2].proposal_id, Window())
    assert "incident" in {link["kind"] for link in trace["links"]}
    assert any(e["event_type"] == "incident_opened" for e in trace["timeline"])
    with tool_db() as s:
        now = s.scalar(select(func.clock_timestamp()))
    metrics = svc.overview(
        setup[0],
        Window(
            range="custom", start=now + timedelta(days=1), end=now + timedelta(days=2)
        ),
    )
    assert metrics["metrics"]["job_counts"] == {}
    assert metrics["metrics"]["dead_letter_backlog"] == 2
    assert "dead_letter_backlog" in {alert["code"] for alert in metrics["alerts"]}


def test_correlation_ids_are_followed_only_through_persisted_links(
    setup, client, tool_db
):
    from app.models.entities import InvestigationEvent, ToolExecution

    service, row, body, key = jobs.enqueue(
        setup, client, tool_db, "create_customer_note", 3
    )
    with tool_db() as s, s.begin():
        s.get(ExecutionJob, row["id"]).status = "DEAD_LETTERED"
    svc = IncidentService(tool_db)
    with tool_db() as s, s.begin():
        svc.detect(s, setup[0].tenant_id, s.scalar(select(func.clock_timestamp())))
    with tool_db() as s:
        tool = s.scalar(select(ToolExecution))
        inv_event = s.scalar(
            select(InvestigationEvent).where(
                InvestigationEvent.event_type == "investigation_created"
            )
        )
        if inv_event is None:
            inv_event = s.scalar(
                select(InvestigationEvent).where(
                    InvestigationEvent.data["correlation_id"].as_string().is_not(None)
                )
            )
        policy = s.scalar(
            select(SecurityEvent).where(SecurityEvent.event_type == "policy_evaluated")
        )
        incident = s.scalar(select(IncidentEvent))
        job = s.scalar(select(ExecutionJobEvent))
        ids = [
            tool.id,
            tool.correlation_id,
            policy.request_id,
            incident.correlation_id,
            job.correlation_id,
        ]
        if inv_event:
            ids.append(UUID(inv_event.data["correlation_id"]))
    for id in ids:
        trace = svc.correlate(setup[0], id, Window())
        assert any(link["id"] == row["id"] for link in trace["links"])
    foreign = tools.identity(client, "admin", 1)
    for id in ids:
        with pytest.raises(HTTPException) as error:
            svc.correlate(foreign, id, Window())
        assert error.value.status_code == 404

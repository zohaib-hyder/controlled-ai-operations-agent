import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
import test_agents as agent_tests
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.agents.checkpoints import Counters, Snapshot, minimize
from app.agents.contracts import Evidence, Limits, State
from app.agents.orchestrator import AgentOrchestrator
from app.agents.planner import DeterministicMockPlanner
from app.models.entities import (
    Investigation,
    InvestigationCheckpoint,
    InvestigationEvent,
    InvestigationEvidence,
    ToolExecution,
)
from app.services.investigations import InvestigationRepository, digest

client = agent_tests.client
executor = agent_tests.executor
tool_db = agent_tests.tool_db
service = agent_tests.service
identity = agent_tests.identity
request = agent_tests.request


def create(service, actor, limits=None, key=None):
    ident, _ = service.repository.create(
        actor, request(), uuid4(), limits or Limits(), key
    )
    return ident


def expire(factory, actor, ident):
    with factory() as session, session.begin():
        session.execute(
            update(Investigation)
            .where(
                Investigation.id == ident,
                Investigation.tenant_id == actor.tenant_id,
                Investigation.actor_id == actor.user_id,
            )
            .values(lease_expires_at=func.clock_timestamp() - timedelta(seconds=1))
        )


def partial(service, actor, *, inflight=False, limits=None, canonical=False):
    repo = service.repository
    ident = create(service, actor, limits)
    owner, version, snapshot, _, _, _ = repo.claim(actor, ident)
    plan = asyncio.run(DeterministicMockPlanner().initial_plan(request()))
    snapshot = snapshot.model_copy(
        update={
            "state": State.PLANNING,
            "history": (State.CREATED, State.PLANNING),
            "phase": "plan_validated",
            "plan": plan,
            "counters": Counters(planning_iterations=1),
        }
    )
    version, snapshot = repo.save(
        actor,
        ident,
        owner,
        version,
        snapshot,
        [("planning_started", {}), ("plan_validated", {})],
    )
    snapshot = snapshot.model_copy(
        update={
            "state": State.RUNNING,
            "history": snapshot.history + (State.RUNNING,),
            "phase": "state_changed",
        }
    )
    version, snapshot = repo.save(actor, ident, owner, version, snapshot, [])
    step = plan.steps[0]
    key = step.invocation.tool_name + json.dumps(
        step.invocation.arguments, sort_keys=True, separators=(",", ":")
    )
    snapshot = snapshot.model_copy(
        update={
            "steps": (step,),
            "step_index": 1,
            "phase": "before_tool",
            "inflight_step": step.step_id,
            "counters": Counters(
                tool_calls=1, planning_iterations=1, repetitions={key: 1}
            ),
        }
    )
    version, snapshot = repo.save(
        actor,
        ident,
        owner,
        version,
        snapshot,
        [("tool_execution_started", {"step_id": step.step_id})],
    )
    if not inflight:
        result = asyncio.run(
            service.executor.execute(
                step.invocation,
                identity=actor,
                correlation_id=snapshot.correlation_id,
                required_permission="investigation:create",
            )
        )
        assert result.status == "success"
        from app.services.evidence import EvidenceRetrievalService

        ev = Evidence(
            sources=EvidenceRetrievalService().normalize(result, ident, actor.tenant_id)
            if canonical
            else (),
            evidence_id=uuid4(),
            tool_execution_id=result.execution_id,
            tool_name=result.tool_name,
            tool_version=result.tool_version,
            source_reference=f"get_customer:{request().customer_id}",
            source_references=(),
            summary="Customer ownership verified by tenant-scoped retrieval.",
            collected_at=result.completed_at,
        )
        snapshot = snapshot.model_copy(
            update={
                "steps": (step.model_copy(update={"status": "succeeded"}),),
                "completed_step_ids": (step.step_id,),
                "phase": "after_observation",
                "inflight_step": None,
                "evidence_ids": (ev.evidence_id,),
                "observations": minimize({"get_customer": result.data}),
                "counters": snapshot.counters.model_copy(
                    update={"observation_bytes": len(json.dumps(result.data).encode())}
                ),
            }
        )
        version, snapshot = repo.save(
            actor,
            ident,
            owner,
            version,
            snapshot,
            [
                (
                    "tool_execution_completed",
                    {"execution_id": str(result.execution_id)},
                ),
                ("evidence_collected", {"evidence_id": str(ev.evidence_id)}),
            ],
            evidence=ev,
        )
    return ident, owner, version, snapshot


def test_durable_result_events_evidence_and_repository_recreation(
    service, client, tool_db
):
    actor = identity(client)
    result = agent_tests.run(service, actor)
    repo = InvestigationRepository(tool_db)
    assert repo.get(actor, result.investigation_id) == result
    assert (
        AgentOrchestrator(service.executor, repository=repo).get(
            result.investigation_id, actor
        )
        == result
    )
    events = repo.records(actor, result.investigation_id, "events", limit=100)["items"]
    assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
    kinds = {e["event_type"] for e in events}
    assert {
        "investigation_created",
        "planning_started",
        "plan_validated",
        "tool_execution_started",
        "tool_execution_completed",
        "evidence_collected",
        "state_changed",
        "investigation_completed",
    } <= kinds
    evidence = repo.records(actor, result.investigation_id, "evidence")["items"]
    assert [e["evidence"]["evidence_id"] for e in evidence] == [
        str(e.evidence_id) for e in result.evidence
    ]
    with tool_db() as session:
        checkpoints = session.scalars(
            select(InvestigationCheckpoint)
            .where(
                InvestigationCheckpoint.tenant_id == actor.tenant_id,
                InvestigationCheckpoint.investigation_id == result.investigation_id,
            )
            .order_by(InvestigationCheckpoint.sequence)
        ).all()
        phases = set()
        for cp in checkpoints:
            snap = Snapshot.model_validate_json(json.dumps(cp.payload))
            phases.add(snap.phase)
            assert cp.checksum == digest(cp.payload)
            assert str(actor.session_id) not in json.dumps(cp.payload)
        assert {
            "created",
            "plan_validated",
            "before_tool",
            "after_observation",
            "state_changed",
            "final",
        } <= phases


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", 2),
        ("planner_version", "9.0"),
        ("step_index", 2),
        ("last_event_sequence", 0),
        ("unexpected", True),
    ],
)
def test_checkpoint_validation(service, client, field, value):
    actor = identity(client)
    ident = create(service, actor)
    _, snapshot, _ = service.repository.load(actor, ident)
    payload = snapshot.model_dump(mode="json")
    payload[field] = value
    with pytest.raises(ValidationError):
        Snapshot.model_validate_json(json.dumps(payload))


def test_idempotent_creation_and_payload_conflict(service, client):
    actor = identity(client)
    key = str(uuid4())
    a = asyncio.run(service.run(request(), actor, uuid4(), idempotency_key=key))
    b = asyncio.run(
        AgentOrchestrator(service.executor).run(
            request(), actor, uuid4(), idempotency_key=key
        )
    )
    assert a == b
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            service.run(
                request().model_copy(update={"goal": "A different investigation goal"}),
                actor,
                uuid4(),
                idempotency_key=key,
            )
        )
    assert error.value.status_code == 409
    assert service.repository.list(actor)["total"] == 1


def test_concurrent_duplicate_creation(service, client):
    actor = identity(client)
    key = str(uuid4())
    barrier = Barrier(2)

    def make():
        barrier.wait()
        return service.repository.create(actor, request(), uuid4(), Limits(), key)

    with ThreadPoolExecutor(2) as pool:
        values = list(pool.map(lambda _: make(), range(2)))
    assert values[0][0] == values[1][0] and sorted(v[1] for v in values) == [
        False,
        True,
    ]
    assert service.repository.list(actor)["total"] == 1


def test_lease_race_and_expiry(service, client, tool_db):
    actor = identity(client)
    ident = create(service, actor)
    barrier = Barrier(2)

    def claim():
        barrier.wait()
        try:
            return service.repository.claim(actor, ident)
        except HTTPException as e:
            return e.status_code

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: claim(), range(2)))
    assert sum(isinstance(r, tuple) for r in results) == 1 and 409 in results
    owner = next(r[0] for r in results if isinstance(r, tuple))
    expire(tool_db, actor, ident)
    assert service.get(ident, actor).recovery_available
    claimed = service.repository.claim(actor, ident, recovery=True)
    assert claimed[0] != owner
    with pytest.raises(HTTPException):
        service.repository.heartbeat(actor, ident, owner)


def test_optimistic_lock_and_atomic_rollback(service, client):
    actor = identity(client)
    ident = create(service, actor)
    owner, version, snapshot, *_ = service.repository.claim(actor, ident)
    barrier = Barrier(2)

    def save():
        barrier.wait()
        try:
            return service.repository.save(
                actor, ident, owner, version, snapshot, [("test_boundary", {})]
            )[0]
        except HTTPException as e:
            return e.status_code

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: save(), range(2)))
    assert results.count(409) == 1
    events = service.repository.records(actor, ident, "events")["items"]
    assert sum(e["event_type"] == "test_boundary" for e in events) == 1
    with pytest.raises(HTTPException):
        service.repository.save(
            actor, ident, owner, version, snapshot, [("must_not_commit", {})]
        )
    assert not any(
        e["event_type"] == "must_not_commit"
        for e in service.repository.records(actor, ident, "events")["items"]
    )


@pytest.mark.parametrize("kind", ["event", "checkpoint"])
def test_database_unique_sequence_guards(service, client, tool_db, kind):
    actor = identity(client)
    ident = create(service, actor)
    with pytest.raises(IntegrityError):
        with tool_db() as session, session.begin():
            if kind == "event":
                session.add(
                    InvestigationEvent(
                        tenant_id=actor.tenant_id,
                        investigation_id=ident,
                        sequence=1,
                        event_type="duplicate",
                        data={},
                    )
                )
            else:
                original = session.scalar(
                    select(InvestigationCheckpoint).where(
                        InvestigationCheckpoint.tenant_id == actor.tenant_id,
                        InvestigationCheckpoint.investigation_id == ident,
                    )
                )
                session.add(
                    InvestigationCheckpoint(
                        tenant_id=actor.tenant_id,
                        investigation_id=ident,
                        sequence=1,
                        applied_version=1,
                        schema_version=1,
                        payload=original.payload,
                        checksum=original.checksum,
                    )
                )
    assert len(service.repository.records(actor, ident, "events")["items"]) == 1


@pytest.mark.parametrize("canonical", [False, True])
def test_safe_recovery_restores_completed_step_without_replay(
    service, client, tool_db, canonical
):
    actor = identity(client)
    ident, owner, version, snapshot = partial(service, actor, canonical=canonical)
    preserved_sources = service.get(ident, actor).evidence[0].sources
    expire(tool_db, actor, ident)
    result = asyncio.run(AgentOrchestrator(service.executor).resume(ident, actor))
    assert result.evidence[0].sources == preserved_sources
    assert bool(result.evidence[0].sources) == canonical
    assert result.status == State.COMPLETED and result.tool_calls_performed == 6
    assert result.recovery_attempts == 1 and result.checkpoint_valid
    assert len({s.step_id for s in result.steps}) == 6
    assert result.evidence[0].evidence_id == snapshot.evidence_ids[0]
    with tool_db() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(ToolExecution)
                .where(
                    ToolExecution.tenant_id == actor.tenant_id,
                    ToolExecution.correlation_id == snapshot.correlation_id,
                    ToolExecution.tool_name == "get_customer",
                )
            )
            == 1
        )
    assert "recovery_completed" in {
        e["event_type"]
        for e in service.repository.records(actor, ident, "events", limit=100)["items"]
    }


def test_interrupted_tool_is_never_blindly_replayed(service, client, tool_db):
    actor = identity(client)
    ident, *_ = partial(service, actor, inflight=True)
    expire(tool_db, actor, ident)
    result = asyncio.run(service.resume(ident, actor))
    assert (
        result.status == State.NEEDS_REVIEW
        and result.stop_reason == "interrupted_tool_requires_review"
    )
    assert result.tool_calls_performed == 1 and not result.evidence
    with tool_db() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(ToolExecution)
                .where(ToolExecution.tenant_id == actor.tenant_id)
            )
            == 0
        )
    assert asyncio.run(service.resume(ident, actor)) == result


def test_recovery_preserves_budget(service, client, tool_db):
    actor = identity(client)
    ident, _, _, snapshot = partial(service, actor, limits=Limits(max_tool_calls=1))
    expire(tool_db, actor, ident)
    result = asyncio.run(service.resume(ident, actor))
    assert (
        result.status == State.BUDGET_EXCEEDED
        and result.stop_reason == "tool_call_limit"
    )
    assert result.tool_calls_performed == 1 and len(result.evidence) == 1
    assert (
        result.budget_counters.planning_iterations
        >= snapshot.counters.planning_iterations
    )


@pytest.mark.parametrize("corruption", ["checksum", "version"])
def test_corrupt_checkpoint_fails_closed(service, client, tool_db, corruption):
    actor = identity(client)
    ident, *_ = partial(service, actor)
    with tool_db() as session, session.begin():
        cp = session.scalar(
            select(InvestigationCheckpoint)
            .where(
                InvestigationCheckpoint.tenant_id == actor.tenant_id,
                InvestigationCheckpoint.investigation_id == ident,
            )
            .order_by(InvestigationCheckpoint.sequence.desc())
            .limit(1)
        )
        payload = {**cp.payload, "schema_version": 999}
        session.execute(
            update(InvestigationCheckpoint)
            .where(
                InvestigationCheckpoint.tenant_id == actor.tenant_id,
                InvestigationCheckpoint.id == cp.id,
            )
            .values(
                payload=payload,
                checksum=digest(payload) if corruption == "version" else "0" * 64,
            )
        )
    expire(tool_db, actor, ident)
    assert not service.get(ident, actor).checkpoint_valid
    result = asyncio.run(service.resume(ident, actor))
    assert result.status == State.FAILED and result.stop_reason == "corrupt_checkpoint"
    assert result.tool_calls_performed == 1


def test_persistent_cancellation_pending_and_terminal_protection(service, client):
    actor = identity(client)
    ident = create(service, actor)
    service.repository.cancel(actor, ident)
    restored = AgentOrchestrator(service.executor).get(ident, actor)
    assert restored.status == State.CANCELLED and restored.cancel_requested
    assert asyncio.run(service.resume(ident, actor)) == restored
    service.repository.cancel(actor, ident)
    assert service.get(ident, actor) == restored


def test_active_cancellation_between_boundaries(service, client):
    actor = identity(client)

    async def scenario():
        entered = asyncio.Event()
        release = asyncio.Event()

        class Waiting(DeterministicMockPlanner):
            async def initial_plan(self, request):
                entered.set()
                await release.wait()
                return await super().initial_plan(request)

        service.planner = Waiting()
        task = asyncio.create_task(service.run(request(), actor, uuid4()))
        await entered.wait()
        ident = (await asyncio.to_thread(service.repository.list, actor))["items"][0][
            "investigation_id"
        ]
        await asyncio.to_thread(service.repository.cancel, actor, ident)
        release.set()
        return await task

    result = asyncio.run(scenario())
    assert (
        result.status == State.CANCELLED
        and result.cancel_requested
        and result.tool_calls_performed == 0
    )


@pytest.mark.parametrize("tenant,role", [(1, "operator"), (0, "reviewer")])
def test_history_and_evidence_owner_isolation(service, client, tenant, role):
    owner = identity(client)
    result = agent_tests.run(service, owner)
    other = identity(client, role, tenant)
    assert service.repository.list(other)["total"] == 0
    for operation in [
        lambda: service.get(result.investigation_id, other),
        lambda: service.repository.records(other, result.investigation_id, "events"),
        lambda: service.repository.records(other, result.investigation_id, "evidence"),
        lambda: service.repository.cancel(other, result.investigation_id),
        lambda: asyncio.run(service.resume(result.investigation_id, other)),
    ]:
        with pytest.raises(HTTPException) as error:
            operation()
        assert error.value.status_code == 404


def test_history_api_idempotency_pagination_and_csrf(service, client):
    identity(client)
    body = request().model_dump(mode="json")
    key = str(uuid4())
    headers = {"Idempotency-Key": key}
    a = client.post("/api/v1/investigations", json=body, headers=headers)
    assert a.status_code == 200
    ident = a.json()["investigation_id"]
    assert (
        client.post("/api/v1/investigations", json=body, headers=headers).json()
        == a.json()
    )
    assert (
        client.post(
            "/api/v1/investigations",
            json={**body, "goal": "Different goal"},
            headers=headers,
        ).status_code
        == 409
    )
    page = client.get(
        "/api/v1/investigations",
        params={"status": "COMPLETED", "customer_id": body["customer_id"], "limit": 1},
    ).json()
    assert page["total"] == 1 and page["items"][0]["investigation_id"] == ident
    first = client.get(f"/api/v1/investigations/{ident}/events?limit=2").json()
    second = client.get(
        f"/api/v1/investigations/{ident}/events?limit=2&after={first['next_after']}"
    ).json()
    assert first["items"][-1]["sequence"] < second["items"][0]["sequence"]
    assert (
        len(client.get(f"/api/v1/investigations/{ident}/evidence").json()["items"]) == 6
    )
    for query in ["limit=51", "offset=-1", "tenant_id=forged", "status=UNKNOWN"]:
        assert client.get("/api/v1/investigations?" + query).status_code == 422
    for action in ["cancel", "resume"]:
        assert (
            client.post(
                f"/api/v1/investigations/{ident}/{action}",
                json={},
                headers={"Origin": "https://evil.example.com"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/investigations/{ident}/{action}", json={"tenant_id": "forged"}
            ).status_code
            == 422
        )
        assert (
            client.post(
                f"/api/v1/investigations/{ident}/{action}", content=b"x" * 8193
            ).status_code
            == 413
        )
    identity(client, "auditor")
    for path in ["", f"/{ident}", f"/{ident}/events", f"/{ident}/evidence"]:
        assert client.get("/api/v1/investigations" + path).status_code == 403
    assert (
        client.post(f"/api/v1/investigations/{ident}/cancel", json={}).status_code
        == 403
    )


@pytest.mark.parametrize(
    "model", [InvestigationEvent, InvestigationCheckpoint, InvestigationEvidence]
)
@pytest.mark.parametrize("operation", ["update", "delete"])
def test_history_application_append_only(service, client, tool_db, model, operation):
    actor = identity(client)
    result = agent_tests.run(service, actor)
    with pytest.raises(ValueError, match="append-only"):
        with tool_db() as session, session.begin():
            row = session.scalar(
                select(model)
                .where(
                    model.tenant_id == actor.tenant_id,
                    model.investigation_id == result.investigation_id,
                )
                .limit(1)
            )
            if operation == "delete":
                session.delete(row)
            else:
                row.updated_at = datetime.now(UTC)


def test_recovery_charges_elapsed_time_and_fences_old_owner(service, client, tool_db):
    actor = identity(client)
    ident, owner, version, snapshot = partial(service, actor)
    with tool_db() as session, session.begin():
        cp = session.scalar(
            select(InvestigationCheckpoint)
            .where(
                InvestigationCheckpoint.tenant_id == actor.tenant_id,
                InvestigationCheckpoint.investigation_id == ident,
            )
            .order_by(InvestigationCheckpoint.sequence.desc())
            .limit(1)
        )
        session.execute(
            update(InvestigationCheckpoint)
            .where(
                InvestigationCheckpoint.tenant_id == actor.tenant_id,
                InvestigationCheckpoint.id == cp.id,
            )
            .values(created_at=datetime.now(UTC) - timedelta(seconds=20))
        )
    expire(tool_db, actor, ident)
    result = asyncio.run(service.resume(ident, actor))
    assert (
        result.status == State.BUDGET_EXCEEDED
        and result.stop_reason == "wall_clock_limit"
    )
    assert (
        result.budget_counters.elapsed_ms >= 20000 and result.tool_calls_performed == 1
    )
    with pytest.raises(HTTPException):
        service.repository.save(
            actor, ident, owner, version, snapshot, [("late_write", {})]
        )


def test_heartbeat_renewal_and_no_budget_reset(service, client, tool_db):
    actor = identity(client)
    ident, owner, version, snapshot = partial(service, actor)
    before = service.get(ident, actor)
    assert service.repository.heartbeat(actor, ident, owner) is False
    assert service.get(ident, actor).lease_expires_at >= before.lease_expires_at
    smaller = snapshot.model_copy(
        update={
            "counters": snapshot.counters.model_copy(update={"planning_iterations": 0})
        }
    )
    with pytest.raises(HTTPException, match="budgets cannot reset"):
        service.repository.save(actor, ident, owner, version, smaller, [])


def test_live_authorization_required_for_recovery(service, client, tool_db):
    from app.models.entities import User

    actor = identity(client)
    ident, *_ = partial(service, actor)
    expire(tool_db, actor, ident)
    with tool_db() as session, session.begin():
        session.get(User, actor.user_id).role = "auditor"
    with pytest.raises(HTTPException) as error:
        asyncio.run(service.resume(ident, actor))
    assert error.value.status_code == 403


def test_invalid_state_transition_rolls_back(service, client):
    actor = identity(client)
    ident, owner, version, snapshot = partial(service, actor)
    invalid = snapshot.model_copy(
        update={"state": State.PLANNING, "history": (State.CREATED, State.PLANNING)}
    )
    with pytest.raises(ValueError, match="Invalid investigation state transition"):
        service.repository.save(
            actor, ident, owner, version, invalid, [("must_not_commit", {})]
        )
    assert service.get(ident, actor).version == version


def test_tenant_foreign_key_rejects_history_attachment(service, client, tool_db):
    actor = identity(client)
    ident = create(service, actor)
    from app.db.seed import stable_id

    with pytest.raises(IntegrityError):
        with tool_db() as session, session.begin():
            session.add(
                InvestigationEvent(
                    tenant_id=stable_id("tenant/1"),
                    investigation_id=ident,
                    sequence=2,
                    event_type="forged",
                    data={},
                )
            )


def test_final_result_cannot_disagree_with_durable_evidence(service, client, tool_db):
    actor = identity(client)
    result = agent_tests.run(service, actor)
    payload = result.model_dump(mode="json")
    payload.pop("version", None)
    payload["evidence"][0]["summary"] = "Fabricated observation"
    # Use the original result envelope shape, simulating privileged storage corruption.
    from app.agents.contracts import InvestigationResult

    final = {key: payload[key] for key in InvestigationResult.model_fields}
    with tool_db() as session, session.begin():
        session.execute(
            update(Investigation)
            .where(
                Investigation.tenant_id == actor.tenant_id,
                Investigation.id == result.investigation_id,
            )
            .values(final_result=final)
        )
    with pytest.raises(HTTPException) as error:
        service.get(result.investigation_id, actor)
    assert error.value.status_code == 503


def test_checkpoint_parent_metadata_mismatch_stops_recovery(service, client, tool_db):
    actor = identity(client)
    ident, *_ = partial(service, actor)
    with tool_db() as session, session.begin():
        session.execute(
            update(Investigation)
            .where(
                Investigation.tenant_id == actor.tenant_id, Investigation.id == ident
            )
            .values(current_step=0)
        )
    expire(tool_db, actor, ident)
    result = asyncio.run(service.resume(ident, actor))
    assert result.status == State.FAILED and result.stop_reason == "corrupt_checkpoint"
    assert result.tool_calls_performed == 1


def test_concurrent_history_reads_never_observe_mixed_checkpoint_versions(
    service, client
):
    actor = identity(client)
    ident = create(service, actor)
    owner, version, snapshot, *_ = service.repository.claim(actor, ident)
    barrier = Barrier(2)

    def write_boundaries():
        current = version
        barrier.wait()
        for _ in range(8):
            current, _ = service.repository.save(
                actor,
                ident,
                owner,
                current,
                snapshot,
                [("read_consistency_boundary", {})],
            )

    def read_boundaries():
        barrier.wait()
        for _ in range(8):
            view = service.get(ident, actor)
            assert view.checkpoint_valid
            assert view.status == State.CREATED

    with ThreadPoolExecutor(2) as pool:
        writes = pool.submit(write_boundaries)
        reads = pool.submit(read_boundaries)
        writes.result()
        reads.result()


def test_corruption_marker_survives_crash_during_recovery(service, client, tool_db):
    actor = identity(client)
    ident, *_ = partial(service, actor)
    with tool_db() as session, session.begin():
        cp = session.scalar(
            select(InvestigationCheckpoint)
            .where(
                InvestigationCheckpoint.tenant_id == actor.tenant_id,
                InvestigationCheckpoint.investigation_id == ident,
            )
            .order_by(InvestigationCheckpoint.sequence.desc())
            .limit(1)
        )
        session.execute(
            update(InvestigationCheckpoint)
            .where(
                InvestigationCheckpoint.tenant_id == actor.tenant_id,
                InvestigationCheckpoint.id == cp.id,
            )
            .values(checksum="0" * 64)
        )
    expire(tool_db, actor, ident)
    claimed = service.repository.claim(actor, ident, recovery=True)
    assert claimed[-1] and claimed[2].recovery_error == "corrupt_checkpoint"
    # Simulate a second process loss after the recovery claim committed.
    expire(tool_db, actor, ident)
    result = asyncio.run(AgentOrchestrator(service.executor).resume(ident, actor))
    assert result.status == State.FAILED and result.stop_reason == "corrupt_checkpoint"
    assert result.recovery_attempts == 2 and result.tool_calls_performed == 1

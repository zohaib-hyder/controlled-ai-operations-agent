"""Explicit local/CI synthetic lifecycle fixtures; never an agent tool or public route."""

import asyncio
import http.cookiejar
import json
import os
import sys
import urllib.request
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import func, update  # noqa: E402

from app.agents.checkpoints import Counters, minimize  # noqa: E402
from app.agents.contracts import Evidence, InvestigationRequest, Limits, State  # noqa: E402
from app.agents.planner import DeterministicMockPlanner  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.permissions import Identity  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.models.entities import Investigation  # noqa: E402
from app.services.investigations import InvestigationRepository  # noqa: E402
from app.tools.executor import get_tool_executor  # noqa: E402


def login_fixture_actor(password):
    if get_settings().app_env not in {"development", "test"}:
        raise ValueError(
            "Synthetic fixture setup is forbidden outside development/test"
        )
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/auth/login",
        data=json.dumps(
            {"email": "reviewer.0@example.com", "password": password}
        ).encode(),
        headers={"Origin": "http://localhost:3000", "Content-Type": "application/json"},
    )
    with opener.open(req, timeout=15) as response:
        data = json.load(response)
    return Identity(
        UUID(data["user_id"]),
        UUID(data["tenant_id"]),
        data["role"],
        UUID(data["session_id"]),
    )


def interrupted_fixture(
    repo,
    executor,
    actor,
    *,
    completed=False,
    goal="Synthetic interrupted investigation",
):
    request = InvestigationRequest(
        goal=goal,
        customer_id=stable_id("0/customer/0"),
        ticket_id=stable_id("0/ticket/0"),
    )
    ident, _ = repo.create(actor, request, uuid4(), Limits(), str(uuid4()))
    owner, version, snapshot, *_ = repo.claim(actor, ident)
    plan = asyncio.run(DeterministicMockPlanner().initial_plan(request))
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
    if completed:
        result = asyncio.run(
            executor.execute(
                step.invocation,
                identity=actor,
                correlation_id=snapshot.correlation_id,
                required_permission="investigation:create",
            )
        )
        if result.status != "success":
            raise RuntimeError("Fixture tool retrieval failed")
        item = Evidence(
            evidence_id=uuid4(),
            tool_execution_id=result.execution_id,
            tool_name=result.tool_name,
            tool_version=result.tool_version,
            source_reference=f"get_customer:{request.customer_id}",
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
                "evidence_ids": (item.evidence_id,),
                "observations": minimize({"get_customer": result.data}),
                "counters": snapshot.counters.model_copy(
                    update={
                        "observation_bytes": len(json.dumps(result.data).encode()),
                        "elapsed_ms": result.duration_ms,
                    }
                ),
            }
        )
        repo.save(
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
                ("evidence_collected", {"evidence_id": str(item.evidence_id)}),
            ],
            evidence=item,
        )
    with repo.session_factory() as session, session.begin():
        session.execute(
            update(Investigation)
            .where(
                Investigation.id == ident,
                Investigation.tenant_id == actor.tenant_id,
                Investigation.actor_id == actor.user_id,
                Investigation.lease_owner == owner,
            )
            .values(lease_expires_at=func.clock_timestamp() - timedelta(seconds=1))
        )
    return ident


def browser_fixtures(password):
    actor = login_fixture_actor(password)
    executor = get_tool_executor()
    repo = InvestigationRepository(executor.session_factory)
    result = {}
    for viewport in ("DESKTOP", "MOBILE"):
        request = InvestigationRequest(
            goal=f"Synthetic cancellation fixture {viewport}",
            customer_id=stable_id("0/customer/0"),
        )
        ident, _ = repo.create(actor, request, uuid4(), Limits(), str(uuid4()))
        result[f"PHASE4_CANCEL_{viewport}"] = str(ident)
        ident = interrupted_fixture(
            repo,
            executor,
            actor,
            goal=f"Synthetic in-flight recovery fixture {viewport}",
        )
        result[f"PHASE4_RECOVERY_{viewport}"] = str(ident)
    return result


if __name__ == "__main__":
    if "--confirm-synthetic-fixtures" not in sys.argv:
        raise SystemExit(
            "Pass --confirm-synthetic-fixtures for local/CI synthetic metadata only"
        )
    password = os.environ.get("DEMO_PASSWORD")
    if not password:
        raise SystemExit("Set the local demo password in the environment")
    fixtures = browser_fixtures(password)
    if "--github-env" in sys.argv:
        with open(os.environ["GITHUB_ENV"], "a") as stream:
            for key, value in fixtures.items():
                stream.write(f"{key}={value}\n")
    else:
        print(json.dumps(fixtures))

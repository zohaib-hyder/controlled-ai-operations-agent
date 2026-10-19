"""Explicit synthetic local verifier; no test-only planner is exposed through an API."""

import asyncio
import json
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from dotenv import dotenv_values
from sqlalchemy import func, select, update

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from fastapi import HTTPException  # noqa: E402

from app.agents.contracts import InvestigationRequest, Limits  # noqa: E402
from app.agents.orchestrator import AgentOrchestrator  # noqa: E402
from app.agents.planner import DeterministicMockPlanner, step  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.permissions import Identity  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.models.entities import Investigation, ToolExecution  # noqa: E402
from app.services.investigations import InvestigationRepository  # noqa: E402
from app.tools.executor import get_tool_executor  # noqa: E402


def login(client, password, role):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": f"{role}.1@example.com", "password": password},
    )
    response.raise_for_status()
    data = response.json()
    return Identity(
        UUID(data["user_id"]),
        UUID(data["tenant_id"]),
        data["role"],
        UUID(data["session_id"]),
    )


def body(index=0):
    return InvestigationRequest(
        goal="Synthetic Phase 6 adaptive verification",
        customer_id=stable_id(f"1/customer/{index}"),
        ticket_id=stable_id(f"1/ticket/{index}"),
    )


def summarize(result):
    return {
        "investigation_id": str(result["investigation_id"]),
        "status": result["status"],
        "stop_reason": result["stop_reason"],
        "planner_type": result["planner_type"],
        "planner_version": result["planner_version"],
        "iterations": result["iteration_count"],
        "tools": [s["invocation"]["tool_name"] for s in result["steps"]],
        "decisions": [t["decision_type"] for t in result["tool_selection_trace"]],
        "tool_calls": result["tool_calls_performed"],
    }


def main():
    if (
        "--confirm-synthetic-local" not in sys.argv
        or get_settings().app_env not in {"development", "test"}
        or get_settings().ai_provider != "mock"
    ):
        raise SystemExit("Explicit local synthetic mock-only confirmation is required")
    password = dotenv_values(ROOT / ".env").get("DEMO_PASSWORD")
    if not password:
        raise SystemExit("Seed the ignored local demo credential first")
    output = {}
    with httpx.Client(
        base_url="http://127.0.0.1:8000",
        headers={"Origin": "http://localhost:3000"},
        timeout=40,
    ) as admin:
        login(admin, password, "admin")
        for label, index, expected in [
            ("A_payment", 0, "COMPLETED"),
            ("B_security", 1, "NEEDS_REVIEW"),
            ("C_duplicate", 2, "COMPLETED"),
            ("D_conflict", 4, "NEEDS_REVIEW"),
        ]:
            response = admin.post(
                "/api/v1/investigations", json=body(index).model_dump(mode="json")
            )
            response.raise_for_status()
            result = response.json()
            assert result["status"] == expected, result["stop_reason"]
            assert (
                result["planner_version"] == "2.0"
                and result["planner_type"] == "deterministic_mock"
            )
            tools = [s["invocation"]["tool_name"] for s in result["steps"]]
            assert tools[4] == (
                "search_policy" if index in (1, 2) else "list_recent_transactions"
            )
            if index == 4:
                assert "ESCALATE" in [
                    t["decision_type"] for t in result["tool_selection_trace"]
                ]
            output[label] = summarize(result)
    executor = get_tool_executor()
    try:
        with httpx.Client(
            base_url="http://127.0.0.1:8000",
            headers={"Origin": "http://localhost:3000"},
            timeout=40,
        ) as reviewer:
            actor = login(reviewer, password, "reviewer")

            class Invalid(DeterministicMockPlanner):
                async def next_step(self, request, observations):
                    return step("write_account", {}, "Synthetic invalid tool fixture")

            class Repeated(DeterministicMockPlanner):
                async def next_step(self, request, observations):
                    return step(
                        "get_customer",
                        {"customer_id": str(request.customer_id)},
                        "Synthetic repeated selection fixture",
                    )

            for label, planner, reason in [
                ("E_invalid_tool", Invalid(), "unknown_tool"),
                ("F_repeated_call", Repeated(), "repeated_tool_call"),
            ]:
                result = asyncio.run(
                    AgentOrchestrator(executor, planner=planner).run(
                        body(), actor, uuid4()
                    )
                )
                assert result.stop_reason == reason and result.tool_calls_performed == 2
                output[label] = summarize(result.model_dump(mode="json"))
            repo = InvestigationRepository(executor.session_factory)
            ident, _ = repo.create(
                actor, body(), uuid4(), Limits(), str(uuid4()), planner_version="2.0"
            )
            response = reviewer.post(f"/api/v1/investigations/{ident}/cancel", json={})
            response.raise_for_status()
            result = response.json()
            assert (
                result["status"] == "CANCELLED" and result["tool_calls_performed"] == 0
            )
            output["G_cancellation"] = summarize(result)
            original = repo.save

            def commit_then_disconnect(*args, **kwargs):
                saved = original(*args, **kwargs)
                snapshot = args[4]
                if (
                    snapshot.phase == "planning"
                    and snapshot.counters.planning_iterations == 2
                ):
                    raise HTTPException(503, "Synthetic post-commit interruption")
                return saved

            repo.save = commit_then_disconnect
            service = AgentOrchestrator(
                executor,
                repository=repo,
                limits=Limits(planning_iterations=10, wall_seconds=30.0),
            )
            try:
                asyncio.run(service.run(body(), actor, uuid4()))
                raise AssertionError("Synthetic interruption was not triggered")
            except HTTPException as error:
                assert error.status_code == 503
            history = repo.list(actor, limit=1)["items"]
            ident = UUID(str(history[0]["investigation_id"]))
            before = repo.get(actor, ident)
            assert before.status == "RUNNING" and before.tool_calls_performed == 2
            old_sources = tuple(
                s.evidence_id for e in before.evidence for s in e.sources
            )
            with executor.session_factory() as session, session.begin():
                session.execute(
                    update(Investigation)
                    .where(
                        Investigation.tenant_id == actor.tenant_id,
                        Investigation.actor_id == actor.user_id,
                        Investigation.id == ident,
                    )
                    .values(
                        lease_expires_at=func.clock_timestamp() - timedelta(seconds=1)
                    )
                )
            subprocess.run(
                ["docker", "compose", "restart", "backend"], cwd=ROOT, check=True
            )
            for _ in range(40):
                try:
                    if reviewer.get("/api/v1/ready").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.5)
            response = reviewer.post(f"/api/v1/investigations/{ident}/resume", json={})
            response.raise_for_status()
            after = response.json()
            assert (
                after["status"] == "COMPLETED"
                and after["tool_calls_performed"] == 6
                and after["iteration_count"] == 9
            )
            new_sources = tuple(
                UUID(s["evidence_id"]) for e in after["evidence"] for s in e["sources"]
            )
            assert new_sources[: len(old_sources)] == old_sources
            with executor.session_factory() as session:
                count = session.scalar(
                    select(func.count())
                    .select_from(ToolExecution)
                    .where(
                        ToolExecution.tenant_id == actor.tenant_id,
                        ToolExecution.actor_id == actor.user_id,
                        ToolExecution.correlation_id == before.correlation_id,
                        ToolExecution.tool_name == "get_customer",
                    )
                )
                assert count == 1
            output["H_restart_recovery"] = {
                **summarize(after),
                "before_calls": 2,
                "original_source_ids_preserved": True,
                "customer_execution_count": count,
                "recovery_attempts": after["recovery_attempts"],
                "wall_seconds": after["execution_limits"]["wall_seconds"],
                "charged_elapsed_ms": after["budget_counters"]["elapsed_ms"],
            }
            for path in ("health", "ready"):
                response = reviewer.get(f"/api/v1/{path}")
                response.raise_for_status()
                output[path] = response.json()
    finally:
        executor.close()
    path = ROOT / "docs/phases/assets/phase6-live-verification.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

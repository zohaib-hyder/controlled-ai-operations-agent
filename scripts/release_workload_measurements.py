"""Read actual persisted tool and queue timings for one isolated workload artifact."""

import json
import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from release_performance import summarize  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.models.entities import (  # noqa: E402
    ActionProposal,
    ExecutionJob,
    ExecutionJobAttempt,
    InvestigationEvidence,
    ToolExecution,
)


def main():
    settings = get_settings()
    target = make_url(settings.database_url)
    if (
        target.host not in {"localhost", "127.0.0.1"}
        or target.database != "northstar_demo"
        or target.port != 55433
        or settings.app_env != "development"
        or settings.ai_provider != "mock"
    ):
        raise SystemExit("Only isolated local mock demo:55433 is permitted")
    workload = json.loads((ROOT / "artifacts/workload.json").read_text())
    if workload["status"] != "PASS":
        raise SystemExit(
            "A successful workload artifact is required; no old evidence substitution"
        )
    ids = {UUID(value) for value in workload["jobs"]}
    if not 1 <= len(ids) <= 30:
        raise SystemExit("Invalid bounded workload references")
    rows = {}
    seen = set()
    with Session(get_engine()) as session, session.begin():
        session.execute(text("SET TRANSACTION READ ONLY"))
        for tenant in range(2):
            tenant_id = stable_id(f"tenant/{tenant}")
            jobs = session.scalars(
                select(ExecutionJob).where(
                    ExecutionJob.tenant_id == tenant_id, ExecutionJob.id.in_(ids)
                )
            ).all()
            for job in jobs:
                assert job.status == "COMPLETED"
                seen.add(job.id)
                attempts = session.scalars(
                    select(ExecutionJobAttempt)
                    .where(
                        ExecutionJobAttempt.tenant_id == tenant_id,
                        ExecutionJobAttempt.job_id == job.id,
                    )
                    .order_by(ExecutionJobAttempt.number)
                ).all()
                assert len(attempts) == 1 and attempts[0].finished_at is not None
                attempt = attempts[0]
                rows.setdefault("queue_wait", []).append(
                    (True, (attempt.created_at - job.created_at).total_seconds() * 1000)
                )
                rows.setdefault("worker_attempt_elapsed", []).append(
                    (
                        True,
                        (attempt.finished_at - attempt.created_at).total_seconds()
                        * 1000,
                    )
                )
                proposal = session.scalar(
                    select(ActionProposal).where(
                        ActionProposal.tenant_id == tenant_id,
                        ActionProposal.id == job.proposal_id,
                    )
                )
                evidence = session.scalars(
                    select(InvestigationEvidence).where(
                        InvestigationEvidence.tenant_id == tenant_id,
                        InvestigationEvidence.investigation_id
                        == proposal.investigation_id,
                    )
                ).all()
                tool_ids = [e.tool_execution_id for e in evidence]
                tools = session.scalars(
                    select(ToolExecution).where(
                        ToolExecution.tenant_id == tenant_id,
                        ToolExecution.id.in_(tool_ids),
                    )
                ).all()
                assert len(tools) == len(tool_ids)
                for tool in tools:
                    assert tool.duration_ms is not None and tool.outcome == "success"
                    rows.setdefault("tool_execution", []).append(
                        (True, tool.duration_ms)
                    )
                    rows.setdefault(tool.tool_name, []).append((True, tool.duration_ms))
    assert seen == ids, "Missing or foreign workload references"
    report = dict(
        status="PASS",
        job_count=len(seen),
        measurements={
            label: summarize(values, workload["duration_seconds"])
            for label, values in rows.items()
        },
        limitations=[
            "Tool executor time excludes downstream evidence normalization",
            "Worker-attempt time includes authorization, controlled execution and scheduler persistence; not mutation-only time",
            "Queue wait and attempt times use one PostgreSQL clock",
            "Execution event timestamps use transaction time and are not used as elapsed-time measurements",
            "No p99 below 100 samples",
        ],
    )
    output = ROOT / "artifacts/workload-persisted-timings.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()

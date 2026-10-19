"""Guarded, disruptive local Compose restart check with a real queued synthetic note."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import dotenv_values
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import get_settings  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.models.entities import (  # noqa: E402
    Account,
    ActionExecution,
    ApprovalRequest,
    BusinessRecord,
    ExecutionJob,
)


def compose(*args):
    subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True)


def snapshot():
    with Session(get_engine()) as session:
        values = []
        for model in (Account, ActionExecution, ApprovalRequest, BusinessRecord):
            values.append(
                (
                    model.__tablename__,
                    [
                        dict(row)
                        for row in session.execute(
                            select(model.__table__)
                            .where(
                                model.tenant_id.in_(
                                    [stable_id("tenant/0"), stable_id("tenant/1")]
                                )
                            )
                            .order_by(model.id)
                        ).mappings()
                    ],
                )
            )
    return hashlib.sha256(
        json.dumps(values, default=str, sort_keys=True).encode()
    ).hexdigest()


def wait_ready():
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            if (
                httpx.get("http://127.0.0.1:8000/api/v1/ready", timeout=2).status_code
                == 200
            ):
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise RuntimeError("Readiness deadline exceeded")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-synthetic-local-restarts", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    parsed = make_url(settings.database_url)
    if (
        not args.confirm_synthetic_local_restarts
        or parsed.host not in {"localhost", "127.0.0.1"}
        or parsed.database != "northstar"
        or settings.app_env != "development"
        or settings.ai_provider != "mock"
    ):
        parser.error("Only explicit local mock development northstar restarts allowed")
    password = os.environ.get("DEMO_PASSWORD") or dotenv_values(ROOT / ".env").get(
        "DEMO_PASSWORD"
    )
    compose(
        "exec",
        "-T",
        "backend",
        "python",
        "-c",
        "from app.core.config import get_settings; from sqlalchemy.engine import make_url; s=get_settings(); assert s.ai_provider == 'mock' and s.app_env == 'development' and make_url(s.database_url).database == 'northstar'",
    )
    started = time.monotonic()
    report = dict(
        status="FAIL",
        scope="Local queued-job persistence and process restarts; not failover or interrupted-commit proof",
    )
    try:
        compose("stop", "worker")
        with httpx.Client(
            base_url="http://127.0.0.1:8000/api/v1",
            headers={"Origin": "http://localhost:3000"},
            timeout=40,
            trust_env=False,
        ) as client:
            client.post(
                "/auth/login",
                json={"email": "admin.1@example.com", "password": password},
            ).raise_for_status()
            queue = client.get("/execution-jobs")
            queue.raise_for_status()
            with Session(get_engine()) as session:
                pending = session.scalar(
                    select(ExecutionJob.id)
                    .where(
                        ExecutionJob.tenant_id.in_(
                            [stable_id("tenant/0"), stable_id("tenant/1")]
                        ),
                        ExecutionJob.status.in_(
                            ("QUEUED", "RETRY_SCHEDULED", "CLAIMED", "RUNNING")
                        ),
                    )
                    .limit(1)
                )
                if pending:
                    raise RuntimeError("Requires idle development queue")
            customer = str(stable_id("1/customer/3"))
            response = client.post(
                "/investigations",
                json={
                    "goal": "Read fictional customer for queued restart verification",
                    "customer_id": customer,
                },
            )
            response.raise_for_status()
            investigation = response.json()
            refs = [
                s["evidence_id"]
                for e in investigation["evidence"]
                for s in e["sources"]
                if s["source_type"] == "customer"
            ]
            response = client.post(
                "/action-proposals",
                json={
                    "investigation_id": investigation["investigation_id"],
                    "action_name": "create_customer_note",
                    "target_resource_id": customer,
                    "arguments": {
                        "content": "Fictional Phase 12 durable restart proof"
                    },
                    "evidence_references": refs,
                    "reason": "Synthetic local recovery verification",
                },
            )
            response.raise_for_status()
            evaluation = response.json()
            assert evaluation["receipt"]["decision"] == "ALLOW"
            key = f"release-recovery-{uuid4()}"
            body = dict(
                proposal_id=evaluation["proposal"]["proposal_id"],
                decision_id=evaluation["receipt"]["decision_id"],
            )
            response = client.post(
                "/execution-jobs", headers={"Idempotency-Key": key}, json=body
            )
            response.raise_for_status()
            job = response.json()
            assert job["status"] == "QUEUED"
            before = snapshot()
            compose("stop", "frontend", "backend")
            get_engine().dispose()
            compose("restart", "db")
            compose("up", "-d", "--wait", "backend", "frontend")
            wait_ready()
            assert snapshot() == before, (
                "Durable business/approval/receipt state changed across restart"
            )
            response = client.get(f"/execution-jobs/{job['id']}")
            response.raise_for_status()
            assert response.json()["status"] == "QUEUED"
            compose("up", "-d", "worker")
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                response = client.get(f"/execution-jobs/{job['id']}")
                response.raise_for_status()
                observed = response.json()
                if observed["status"] == "COMPLETED":
                    break
                if observed["status"] in {
                    "FAILED",
                    "DEAD_LETTERED",
                    "RECONCILIATION_REQUIRED",
                }:
                    raise RuntimeError(f"Recovery stopped: {observed['status']}")
                time.sleep(0.25)
            else:
                raise RuntimeError("Queued job completion deadline exceeded")
            receipt = client.get(f"/action-executions/{observed['receipt_id']}")
            receipt.raise_for_status()
            assert receipt.json()["verified"]
            replay = client.post(
                "/execution-jobs", headers={"Idempotency-Key": key}, json=body
            )
            replay.raise_for_status()
            assert replay.json()["id"] == job["id"]
            from sqlalchemy import func

            with Session(get_engine()) as session:
                count = session.scalar(
                    select(func.count())
                    .select_from(ActionExecution)
                    .where(
                        ActionExecution.proposal_id
                        == evaluation["proposal"]["proposal_id"]
                    )
                )
                records = session.scalar(
                    select(func.count())
                    .select_from(BusinessRecord)
                    .where(BusinessRecord.execution_id == observed["receipt_id"])
                )
                assert count == records == 1
            report.update(
                status="PASS",
                durable_snapshot_preserved=True,
                queued_job_completed=True,
                receipt_count=count,
                business_record_count=records,
                duplicate_mutations=0,
                job_id=job["id"],
                receipt_id=observed["receipt_id"],
                backend_restart=True,
                frontend_restart=True,
                database_restart=True,
                worker_restart=True,
            )
    finally:
        compose("up", "-d", "backend", "frontend", "worker")
        report["duration_seconds"] = time.monotonic() - started
        path = ROOT / "artifacts/release-recovery.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

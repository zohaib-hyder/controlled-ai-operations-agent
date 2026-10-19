"""Explicit local synthetic proof: verified note, three real dead letters, uncertain grant."""

import json
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from dotenv import dotenv_values
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import get_settings  # noqa: E402
from app.core.passwords import hash_password  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.jobs.service import JobService  # noqa: E402
from app.models.entities import (  # noqa: E402
    Account,
    ActionExecution,
    ApprovalRequest,
    BusinessRecord,
    Customer,
    ExecutionJob,
    Policy,
    Ticket,
    Transaction,
    User,
)


class Crash(BaseException):
    pass


def main():
    settings = get_settings()
    url = make_url(settings.database_url)
    if (
        "--confirm-synthetic-local" not in sys.argv
        or settings.ai_provider != "mock"
        or settings.app_env not in {"test", "development"}
        or url.host not in {"localhost", "127.0.0.1"}
        or (url.database != "northstar" and not (url.database or "").endswith("_e2e"))
    ):
        raise SystemExit("Explicit local synthetic fixture confirmation required")
    password = os.environ.get("DEMO_PASSWORD") or dotenv_values(ROOT / ".env").get(
        "DEMO_PASSWORD"
    )
    assert password
    engine = get_engine()
    factory = sessionmaker(engine, expire_on_commit=False)
    tenant = stable_id("tenant/1")
    run = uuid4().hex[:12]
    emails = [f"phase10.{kind}.{run}@example.com" for kind in ("fixture", "uncertain")]
    with Session(engine) as s:
        assert (
            s.scalar(
                select(func.count())
                .select_from(ExecutionJob)
                .where(
                    ExecutionJob.status.in_(
                        ("QUEUED", "RETRY_SCHEDULED", "CLAIMED", "RUNNING")
                    )
                )
            )
            == 0
        ), "Fixture preparation requires an idle execution queue"
    stop_worker = "--no-compose-worker" not in sys.argv
    if stop_worker:
        subprocess.run(["docker", "compose", "stop", "worker"], cwd=ROOT, check=True)
    results = []
    try:
        with Session(engine) as s, s.begin():
            for email in emails:
                s.add(
                    User(
                        id=uuid4(),
                        tenant_id=tenant,
                        email=email,
                        role="operator",
                        is_active=True,
                        password_hash=hash_password(password),
                    )
                )
            now = s.scalar(select(func.clock_timestamp()))
            for model in (Customer, Account, Ticket, Transaction, Policy):
                for row in s.scalars(select(model).where(model.tenant_id == tenant)):
                    if isinstance(row, Customer):
                        assert row.email.endswith("@example.com")
                    row.updated_at = (
                        now  # Explicit synthetic observation-window preparation.
                    )
        service = JobService(factory)

        def conflict(*args, **kwargs):
            with Session(engine) as s, s.begin():
                s.execute(
                    text(
                        "DO $$ BEGIN RAISE EXCEPTION 'synthetic operations fixture' USING ERRCODE='40001'; END $$"
                    )
                )

        def login(c, email):
            r = c.post("/auth/login", json={"email": email, "password": password})
            r.raise_for_status()

        def call(c, path, body):
            r = c.post(path, json=body)
            r.raise_for_status()
            return r.json()

        with (
            httpx.Client(
                base_url="http://127.0.0.1:8000/api/v1",
                headers={"Origin": "http://localhost:3000"},
                timeout=40,
            ) as client,
            httpx.Client(
                base_url="http://127.0.0.1:8000/api/v1",
                headers={"Origin": "http://localhost:3000"},
                timeout=40,
            ) as reviewer,
        ):
            login(client, emails[0])
            login(reviewer, "reviewer.1@example.com")

            def enqueue(restricted=False):
                view = call(
                    client,
                    "/investigations",
                    {
                        "goal": "Synthetic command center operational fixture",
                        "customer_id": str(stable_id("1/customer/3")),
                        "ticket_id": str(stable_id("1/ticket/3")),
                    },
                )
                kinds = (
                    {"account", "transaction", "policy"} if restricted else {"customer"}
                )
                refs = [
                    src["evidence_id"]
                    for evidence in view["evidence"]
                    for src in evidence["sources"]
                    if src["source_type"] in kinds
                ]
                proposal = call(
                    client,
                    "/action-proposals",
                    {
                        "investigation_id": view["investigation_id"],
                        "action_name": "request_account_reactivation"
                        if restricted
                        else "create_customer_note",
                        "target_resource_id": str(
                            stable_id("1/account/3" if restricted else "1/customer/3")
                        ),
                        "arguments": {}
                        if restricted
                        else {"content": "Fictional verified operations fixture note"},
                        "evidence_references": refs,
                        "reason": "Explicit synthetic operational proof preparation",
                    },
                )
                assert proposal["receipt"]["decision"] == (
                    "REQUIRE_APPROVAL" if restricted else "ALLOW"
                )
                approval = None
                if restricted:
                    approval = call(
                        client,
                        f"/action-proposals/{proposal['proposal']['proposal_id']}/approval-requests",
                        {},
                    )["approval_id"]
                    call(
                        reviewer,
                        f"/approvals/{approval}/approve",
                        {"reason": "Independent synthetic evidence review"},
                    )
                r = client.post(
                    "/execution-jobs",
                    headers={"Idempotency-Key": "ops-fixture-" + uuid4().hex},
                    json={
                        "proposal_id": proposal["proposal"]["proposal_id"],
                        "decision_id": proposal["receipt"]["decision_id"],
                        "approval_id": approval,
                    },
                )
                r.raise_for_status()
                return {
                    "job_id": r.json()["id"],
                    "proposal_id": proposal["proposal"]["proposal_id"],
                    "investigation_id": view["investigation_id"],
                    "approval_id": approval,
                }

            proof = enqueue()
            claim = service.claim("ops-fixture")
            assert claim and claim[0] == UUID(proof["job_id"])
            service.process(claim, "ops-fixture")
            with Session(engine) as s:
                job = s.get(ExecutionJob, UUID(proof["job_id"]))
                assert job.status == "COMPLETED"
                receipt = s.get(ActionExecution, job.receipt_id)
                assert (
                    receipt.payload["status"] == "COMMITTED"
                    and receipt.payload["verified"]
                )
                initial_records = s.scalar(
                    select(func.count()).select_from(BusinessRecord)
                )
            service.executor.execute = conflict
            for _ in range(3):
                result = enqueue()
                for _ in range(3):
                    with Session(engine) as s, s.begin():
                        s.get(ExecutionJob, UUID(result["job_id"])).next_run_at = (
                            s.scalar(select(func.clock_timestamp()))
                            - timedelta(seconds=1)
                        )
                    claim = service.claim("ops-fixture")
                    assert claim and claim[0] == UUID(result["job_id"])
                    service.process(claim, "ops-fixture")
                with Session(engine) as s:
                    assert (
                        s.get(ExecutionJob, UUID(result["job_id"])).status
                        == "DEAD_LETTERED"
                    )
                    assert (
                        s.scalar(
                            select(func.count())
                            .select_from(ActionExecution)
                            .where(
                                ActionExecution.tenant_id == tenant,
                                ActionExecution.proposal_id
                                == UUID(result["proposal_id"]),
                            )
                        )
                        == 0
                    )
                    assert (
                        s.scalar(select(func.count()).select_from(BusinessRecord))
                        == initial_records
                    )
                result["completed_job_id"] = proof["job_id"]
                results.append(result)
            login(client, emails[1])
            uncertain = enqueue(True)
            claim = service.claim("ops-fixture")
            assert claim and claim[0] == UUID(uncertain["job_id"])

            def crash(stage):
                if stage == "before_execution":
                    raise Crash()

            try:
                service.process(claim, "ops-fixture", crash)
            except Crash:
                pass
            with Session(engine) as s, s.begin():
                now = s.scalar(select(func.clock_timestamp()))
                # Explicit ambiguous-transaction evidence injection, not a successful business write.
                s.get(ApprovalRequest, UUID(uncertain["approval_id"])).consumed_at = now
                s.get(ExecutionJob, UUID(uncertain["job_id"])).lease_expires_at = (
                    now - timedelta(seconds=1)
                )
            service.reconcile()
            with Session(engine) as s:
                assert (
                    s.get(ExecutionJob, UUID(uncertain["job_id"])).status
                    == "RECONCILIATION_REQUIRED"
                )
                assert (
                    s.scalar(select(func.count()).select_from(BusinessRecord))
                    == initial_records
                )
            for result in results:
                result["uncertain_job_id"] = uncertain["job_id"]
        with httpx.Client(
            base_url="http://127.0.0.1:8000/api/v1",
            headers={"Origin": "http://localhost:3000"},
            timeout=40,
        ) as admin:
            login(admin, "admin.1@example.com")
            call(admin, "/incidents/detect", {})
            items = []
            for offset in range(0, 1000, 50):
                r = admin.get(f"/incidents?range=24h&limit=50&offset={offset}")
                r.raise_for_status()
                batch = r.json()["items"]
                items += batch
                if len(batch) < 50:
                    break
            for result in results:
                result["incident_id"] = next(
                    i["id"]
                    for i in items
                    if i["job_id"] == result["job_id"]
                    and i["category"] == "dead_letter"
                )
        path = Path("/tmp/northstar-phase10-browser.json")
        path.write_text(json.dumps(results))
        if "--github-env" in sys.argv:
            with open(os.environ["GITHUB_ENV"], "a") as stream:
                stream.write(f"PHASE10_BROWSER_FIXTURE_PATH={path}\n")
        print(
            "One verified synthetic note, three retry-exhaustion incidents and one explicit uncertain-outcome fixture prepared"
        )
    finally:
        if stop_worker:
            subprocess.run(
                ["docker", "compose", "start", "worker"], cwd=ROOT, check=True
            )


if __name__ == "__main__":
    main()

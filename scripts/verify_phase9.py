"""Explicit local synthetic failure probes. Stop the background worker before running."""

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
    ApprovalRequest,
    BusinessRecord,
    Customer,
    Policy,
    Ticket,
    Transaction,
    User,
)  # noqa: E402
from app.models.entities import (  # noqa: E402
    ExecutionJob as Job,
)


class Crash(BaseException):
    pass


def main():
    settings = get_settings()
    url = make_url(settings.database_url)
    if (
        "--confirm-synthetic-local" not in sys.argv
        or url.host not in {"localhost", "127.0.0.1"}
        or url.database != "northstar"
        or settings.app_env not in {"development", "test"}
        or settings.ai_provider != "mock"
    ):
        raise SystemExit(
            "Explicit local synthetic northstar/mock confirmation required"
        )
    password = os.environ.get("DEMO_PASSWORD") or dotenv_values(ROOT / ".env").get(
        "DEMO_PASSWORD"
    )
    assert password
    engine = get_engine()
    factory = sessionmaker(engine, expire_on_commit=False)
    service = JobService(factory)
    tenant = stable_id("tenant/1")
    output = {}
    with Session(engine) as s, s.begin():
        now = s.scalar(select(func.clock_timestamp()))
        for model in (Customer, Account, Ticket, Transaction, Policy):
            for row in s.scalars(select(model).where(model.tenant_id == tenant)):
                if isinstance(row, Customer):
                    assert row.email.endswith("@example.com")
                row.updated_at = now
        account = s.get(Account, stable_id("1/account/3"))
        account.status = "blocked"
        account.block_reason = "resolved_billing"
        account.evidence_version += 1
        for tag in "ACDEFGHI":
            uid = stable_id("phase9/live/" + tag)
            user = s.get(User, uid)
            if not user:
                s.add(
                    User(
                        id=uid,
                        tenant_id=tenant,
                        email=f"phase9.{tag.lower()}@example.com",
                        role="operator",
                        password_hash=hash_password(password),
                    )
                )
            else:
                user.role = "operator"
                user.is_active = True
    clients = []

    def login(email):
        c = httpx.Client(
            base_url="http://127.0.0.1:8000/api/v1",
            headers={"Origin": "http://localhost:3000"},
            timeout=40,
        )
        clients.append(c)
        r = c.post("/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        return c

    def call(c, path, body=None, key=None, method="POST", expected=200):
        r = c.request(
            method, path, json=body, headers={"Idempotency-Key": key} if key else {}
        )
        assert r.status_code == expected, (path, r.status_code, r.text)
        return r.json()

    reviewer = login("reviewer.1@example.com")
    foreign = login("admin.0@example.com")

    def enqueue(tag, restricted=False):
        c = login(f"phase9.{tag.lower()}@example.com")
        view = call(
            c,
            "/investigations",
            {
                "goal": "Explicit synthetic durable job reliability probe",
                "customer_id": str(stable_id("1/customer/3")),
                "ticket_id": str(stable_id("1/ticket/3")),
            },
        )
        kind = "account" if restricted else "customer"
        refs = [
            src["evidence_id"]
            for e in view["evidence"]
            for src in e["sources"]
            if src["source_type"]
            in ({"account", "transaction", "policy"} if restricted else {"customer"})
        ]
        proposed = call(
            c,
            "/action-proposals",
            {
                "investigation_id": view["investigation_id"],
                "action_name": "request_account_reactivation"
                if restricted
                else "create_customer_note",
                "target_resource_id": str(stable_id(f"1/{kind}/3")),
                "arguments": {}
                if restricted
                else {"content": "Fictional durable execution reliability note"},
                "evidence_references": refs,
                "reason": "Explicit synthetic local reliability fixture",
            },
        )
        p = proposed["proposal"]["proposal_id"]
        approval = None
        if restricted:
            a = call(c, f"/action-proposals/{p}/approval-requests", {})
            approval = a["approval_id"]
            call(
                reviewer,
                f"/approvals/{approval}/approve",
                {"reason": "Independent synthetic reliability evidence review"},
            )
        body = {
            "proposal_id": p,
            "decision_id": proposed["receipt"]["decision_id"],
            "approval_id": approval,
        }
        key = "live9-" + uuid4().hex
        row = call(c, "/execution-jobs", body, key)
        return c, row, body, key

    def status(c, row):
        return call(c, f"/execution-jobs/{row['id']}", method="GET")

    def expire(row):
        with Session(engine) as s, s.begin():
            s.get(Job, UUID(row["id"])).lease_expires_at = s.scalar(
                select(func.clock_timestamp())
            ) - timedelta(seconds=1)

    def due(row):
        with Session(engine) as s, s.begin():
            s.get(Job, UUID(row["id"])).next_run_at = s.scalar(
                select(func.clock_timestamp())
            ) - timedelta(seconds=1)

    def process():
        claim = service.claim("live-probe")
        assert claim
        service.process(claim, "live-probe")

    try:
        c, row, body, key = enqueue("A")
        process()
        assert status(c, row)["status"] == "COMPLETED"
        output["A"] = {"status": "COMPLETED", "job_id": row["id"]}
        with Session(engine) as s:
            before = s.scalar(select(func.count()).select_from(BusinessRecord))
        assert call(c, "/execution-jobs", body, key)["id"] == row["id"]
        with Session(engine) as s:
            assert s.scalar(select(func.count()).select_from(BusinessRecord)) == before
        output["B"] = "same_job_no_duplicate_mutation"
        call(foreign, f"/execution-jobs/{row['id']}", method="GET", expected=404)
        output["J"] = "foreign_job_404"
        c, row, _, _ = enqueue("C")
        with Session(engine) as s, s.begin():
            s.get(Job, UUID(row["id"])).next_run_at = s.scalar(
                select(func.clock_timestamp())
            ) + timedelta(hours=1)
        subprocess.run(
            [sys.executable, "-m", "app.jobs.worker", "--once"],
            cwd=ROOT / "backend",
            check=True,
            stdout=subprocess.DEVNULL,
        )
        assert status(c, row)["status"] == "QUEUED"
        due(row)
        # Fresh OS processes: first exits after one iteration; queued state was persisted by API.
        subprocess.run(
            [sys.executable, "-m", "app.jobs.worker", "--once"],
            cwd=ROOT / "backend",
            check=True,
            stdout=subprocess.DEVNULL,
        )
        assert status(c, row)["status"] == "COMPLETED"
        output["C"] = "worker_process_restart_preserved_and_completed_queue"
        c, row, _, _ = enqueue("D")
        claim = service.claim("crashed-worker")
        assert claim
        expire(row)
        assert service.reconcile() >= 1
        due(row)
        process()
        assert status(c, row)["status"] == "COMPLETED"
        output["D"] = "expired_claim_recovered"
        c, row, body, _ = enqueue("E", True)
        with Session(engine) as s, s.begin():
            s.get(ApprovalRequest, UUID(body["approval_id"])).expires_at = s.scalar(
                select(func.clock_timestamp())
            ) - timedelta(seconds=1)
        process()
        assert status(c, row)["status"] == "FAILED"
        output["E"] = "expired_approval_blocked"
        c, row, _, _ = enqueue("F")
        with Session(engine) as s, s.begin():
            s.get(User, stable_id("phase9/live/F")).role = "auditor"
        process()
        assert status(c, row)["status"] == "FAILED"
        output["F"] = "current_permission_revocation_blocked"

        def conflict(*args, **kwargs):
            with Session(engine) as s, s.begin():
                s.execute(
                    text(
                        "DO $$ BEGIN RAISE EXCEPTION 'synthetic conflict' USING ERRCODE='40001'; END $$"
                    )
                )

        c, row, _, _ = enqueue("G")
        original = service.executor.execute
        service.executor.execute = conflict
        process()
        assert status(c, row)["status"] == "RETRY_SCHEDULED"
        service.executor.execute = original
        due(row)
        process()
        assert status(c, row)["status"] == "COMPLETED"
        output["G"] = "real_sqlstate_40001_retry_completed"
        c, row, _, _ = enqueue("H")
        service.executor.execute = conflict
        for _ in range(3):
            due(row)
            process()
        service.executor.execute = original
        assert status(c, row)["status"] == "DEAD_LETTERED"
        output["H"] = "three_conflicts_dead_lettered"
        c, row, body, _ = enqueue("I", True)
        claim = service.claim("uncertain-worker")

        def crash(stage):
            if stage == "before_execution":
                raise Crash()

        try:
            service.process(claim, "uncertain-worker", crash)
        except Crash:
            pass
        with Session(engine) as s, s.begin():
            s.get(
                ApprovalRequest, UUID(body["approval_id"])
            ).consumed_at = func.clock_timestamp()
        expire(row)
        service.reconcile()
        assert status(c, row)["status"] == "RECONCILIATION_REQUIRED"
        output["I"] = "ambiguous_consumption_retained_no_blind_retry"
        path = ROOT / "docs/phases/assets/phase9-live-verification.json"
        path.write_text(json.dumps(output, indent=2) + "\n")
        print(json.dumps(output, indent=2))
    finally:
        for c in clients:
            c.close()


if __name__ == "__main__":
    main()

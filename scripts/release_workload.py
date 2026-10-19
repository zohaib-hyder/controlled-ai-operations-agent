"""Bounded paced mixed workflow soak against the isolated local demo stack only."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import dotenv_values
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from demo_database import verify_demo_runtime  # noqa: E402
from release_performance import summarize  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.models.entities import (  # noqa: E402
    Account,
    ActionExecution,
    BusinessRecord,
    Customer,
    Policy,
    Ticket,
    Transaction,
    User,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--confirm-synthetic-demo", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    url = make_url(settings.database_url)
    if (
        not args.confirm_synthetic_demo
        or not 30 <= args.seconds <= 120
        or url.host not in {"localhost", "127.0.0.1"}
        or url.port != 55433
        or url.database != "northstar_demo"
        or settings.app_env != "development"
        or settings.ai_provider != "mock"
    ):
        parser.error(
            "Requires explicit isolated loopback northstar_demo:55433, development mock and 30..120 seconds"
        )
    verify_demo_runtime()
    password = os.environ.get("DEMO_PASSWORD") or dotenv_values(ROOT / ".env").get(
        "DEMO_PASSWORD"
    )
    fixtures = []
    operator_emails = []
    with Session(get_engine()) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        for tenant in range(2):
            tenant_id = stable_id(f"tenant/{tenant}")
            for policy in session.scalars(
                select(Policy).where(Policy.tenant_id == tenant_id)
            ):
                policy.updated_at = now
            customer, account, run = uuid4(), uuid4(), uuid4().hex[:12]
            session.add(
                Customer(
                    id=customer,
                    tenant_id=tenant_id,
                    name=f"Fictional Soak {tenant} {run}",
                    email=f"soak.{run}@example.com",
                    updated_at=now,
                )
            )
            session.flush()
            session.add(
                Account(
                    id=account,
                    tenant_id=tenant_id,
                    customer_id=customer,
                    status="blocked",
                    block_reason="resolved_billing",
                    evidence_version=1,
                    updated_at=now,
                )
            )
            session.flush()
            session.add(
                Ticket(
                    tenant_id=tenant_id,
                    account_id=account,
                    subject="Fictional bounded workload ticket",
                    body="Synthetic resolved billing scenario",
                    status="open",
                    duplicate_of_id=None,
                    updated_at=now,
                )
            )
            base = session.scalar(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.id == stable_id(f"{tenant}/user/operator"),
                )
            )
            email = f"soak.executor.{run}@example.com"
            session.add(
                User(
                    tenant_id=tenant_id,
                    email=email,
                    role="operator",
                    password_hash=base.password_hash,
                )
            )
            operator_emails.append(email)
            session.add(
                Transaction(
                    tenant_id=tenant_id,
                    account_id=account,
                    reference=f"SYNTHETIC-SOAK-{run}",
                    amount_minor=100,
                    currency="USD",
                    status="paid",
                    updated_at=now,
                )
            )
            fixtures.append((customer, account))
    measurements = {}
    counts = {
        "completed": 0,
        "failed": 0,
        "approval_grants": 0,
        "duplicate_mutations": 0,
    }
    errors = []
    jobs = []
    per_tenant = [0, 0]
    backlog = []

    def call(client, label, method, path, **kwargs):
        started = time.monotonic()
        response = client.request(method, path, **kwargs)
        measurements.setdefault(label, []).append(
            (response.is_success, (time.monotonic() - started) * 1000)
        )
        response.raise_for_status()
        return response.json()

    clients = []
    try:
        for tenant in range(2):
            group = []
            for role in ("operator", "reviewer", "admin"):
                client = httpx.Client(
                    base_url="http://127.0.0.1:18000/api/v1",
                    headers={"Origin": "http://localhost:3000"},
                    timeout=15,
                    trust_env=False,
                )
                clients.append(client)
                group.append(client)
                call(
                    client,
                    "authentication",
                    "POST",
                    "/auth/login",
                    json={
                        "email": operator_emails[tenant]
                        if role == "operator"
                        else f"{role}.{tenant}@example.com",
                        "password": password,
                    },
                )
            fixtures[tenant] = (*fixtures[tenant], *group)
        iteration = 0
        deadline = time.monotonic() + args.seconds
        workload_started = time.monotonic()
        while time.monotonic() < deadline and iteration < 30:
            tenant = iteration % 2
            customer, account, operator, reviewer, admin = fixtures[tenant]
            try:
                investigation = call(
                    operator,
                    "investigation",
                    "POST",
                    "/investigations",
                    json={
                        "goal": "Read fictional customer and resolved billing for bounded local verification",
                        "customer_id": str(customer),
                    },
                )
                approval_needed = iteration % 4 in {0, 1}
                action = (
                    "request_account_reactivation"
                    if approval_needed
                    else "create_customer_note"
                )
                refs = [
                    s["evidence_id"]
                    for e in investigation["evidence"]
                    for s in e["sources"]
                    if s["source_type"]
                    in (
                        {"account", "transaction", "policy"}
                        if approval_needed
                        else {"customer"}
                    )
                ]
                evaluation = call(
                    operator,
                    "policy_evaluation",
                    "POST",
                    "/action-proposals",
                    json={
                        "investigation_id": investigation["investigation_id"],
                        "action_name": action,
                        "target_resource_id": str(
                            account if approval_needed else customer
                        ),
                        "arguments": {}
                        if approval_needed
                        else {"content": "Fictional bounded local soak note"},
                        "evidence_references": refs,
                        "reason": "Synthetic release workload",
                    },
                )
                assert evaluation["receipt"]["decision"] == (
                    "REQUIRE_APPROVAL" if approval_needed else "ALLOW"
                )
                proposal = evaluation["proposal"]["proposal_id"]
                approval = None
                if approval_needed:
                    request = call(
                        operator,
                        "approval_creation",
                        "POST",
                        f"/action-proposals/{proposal}/approval-requests",
                        json={},
                    )
                    approval = request["approval_id"]
                    grant = call(
                        reviewer,
                        "approval_review",
                        "POST",
                        f"/approvals/{approval}/approve",
                        json={"reason": "Independent synthetic soak review"},
                    )
                    assert grant["status"] == "APPROVED"
                    counts["approval_grants"] += 1
                body = dict(
                    proposal_id=proposal,
                    decision_id=evaluation["receipt"]["decision_id"],
                    approval_id=approval,
                )
                key = f"soak-{uuid4()}"
                job = call(
                    operator,
                    "job_submission",
                    "POST",
                    "/execution-jobs",
                    headers={"Idempotency-Key": key},
                    json=body,
                )
                wait_started = time.monotonic()
                completion_deadline = wait_started + 30
                while time.monotonic() < completion_deadline:
                    observed = call(
                        operator, "job_poll", "GET", f"/execution-jobs/{job['id']}"
                    )
                    if observed["status"] == "COMPLETED":
                        break
                    if observed["status"] in {
                        "FAILED",
                        "DEAD_LETTERED",
                        "RECONCILIATION_REQUIRED",
                    }:
                        raise RuntimeError(observed["status"])
                    time.sleep(0.25)
                else:
                    raise TimeoutError("job completion")
                measurements.setdefault("submission_to_completion", []).append(
                    (True, (time.monotonic() - wait_started) * 1000)
                )
                receipt = call(
                    operator,
                    "receipt",
                    "GET",
                    f"/action-executions/{observed['receipt_id']}",
                )
                assert receipt["verified"] and receipt["status"] == "COMMITTED"
                replay = call(
                    operator,
                    "idempotent_replay",
                    "POST",
                    "/execution-jobs",
                    headers={"Idempotency-Key": key},
                    json=body,
                )
                assert replay["id"] == job["id"]
                with Session(get_engine()) as session:
                    receipts = session.scalar(
                        select(func.count())
                        .select_from(ActionExecution)
                        .where(
                            ActionExecution.tenant_id == stable_id(f"tenant/{tenant}"),
                            ActionExecution.proposal_id == proposal,
                        )
                    )
                    records = session.scalar(
                        select(func.count())
                        .select_from(BusinessRecord)
                        .where(
                            BusinessRecord.tenant_id == stable_id(f"tenant/{tenant}"),
                            BusinessRecord.execution_id == observed["receipt_id"],
                        )
                    )
                    assert receipts == records == 1
                foreign = fixtures[1 - tenant][2].get(f"/execution-jobs/{job['id']}")
                assert foreign.status_code == 404
                overview = call(
                    admin, "operations_overview", "GET", "/operations/overview"
                )
                assert overview
                call(admin, "incident_detection", "POST", "/incidents/detect", json={})
                queue = call(operator, "queue", "GET", "/execution-jobs")
                backlog.append(queue["queue_depth"])
                jobs.append(job["id"])
                counts["completed"] += 1
                per_tenant[tenant] += 1
            except (httpx.HTTPError, AssertionError, RuntimeError, TimeoutError) as exc:
                counts["failed"] += 1
                errors.append(type(exc).__name__)
            iteration += 1
            # Deliberate workload pacing, not a browser synchronization sleep.
            remaining = workload_started + iteration * 8 - time.monotonic()
            if remaining > 0:
                time.sleep(min(remaining, max(0, deadline - time.monotonic())))
        duration = time.monotonic() - workload_started
    finally:
        for client in clients:
            client.close()
    counts["duplicate_mutations"] = 0 if not counts["failed"] else None
    report = dict(
        status="PASS" if not counts["failed"] and counts["completed"] else "FAIL",
        counts=counts,
        per_tenant_completed=per_tenant,
        duration_seconds=duration,
        requested_seconds=args.seconds,
        concurrency=1,
        backlog_samples=backlog,
        errors=errors,
        jobs=jobs,
        measurements={
            name: summarize(rows, duration) for name, rows in measurements.items()
        },
        limitations=[
            "Short local paced workflow soak, not production endurance",
            "Serial submissions across two tenants, not strict fairness proof",
            "No deliberate ambiguous-commit or lease faults",
            "No unexpected process exits observed only if separately monitored; not asserted here",
            "No rejected-job load cohort in this harness",
        ],
    )
    output = ROOT / "artifacts/workload.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return int(report["status"] != "PASS")


if __name__ == "__main__":
    sys.exit(main())

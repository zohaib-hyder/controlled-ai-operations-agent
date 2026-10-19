"""Bounded 20-job, five-tenant admission/fairness exercise on the isolated demo only."""

import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter
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

from app.core.config import get_settings  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.models.entities import (  # noqa: E402
    Account,
    ActionExecution,
    BusinessRecord,
    Customer,
    ExecutionJob,
    Policy,
    Tenant,
    Ticket,
    Transaction,
    User,
)

COMPOSE = [
    "docker",
    "compose",
    "-p",
    "northstar-release12",
    "-f",
    "docker-compose.yml",
    "-f",
    "infra/docker/release.compose.yml",
]


def workers(count):
    subprocess.run(
        [*COMPOSE, "up", "-d", "--scale", f"worker={count}", "worker"],
        cwd=ROOT,
        check=True,
    )


def post(client, path, body, **kwargs):
    response = client.post(path, json=body, **kwargs)
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-synthetic-demo", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    target = make_url(settings.database_url)
    if (
        not args.confirm_synthetic_demo
        or target.host not in {"localhost", "127.0.0.1"}
        or target.port != 55433
        or target.database != "northstar_demo"
        or settings.app_env != "development"
        or settings.ai_provider != "mock"
    ):
        parser.error(
            "Only explicit isolated loopback demo:55433 in development/mock mode"
        )
    verify_demo_runtime()
    password = os.environ.get("DEMO_PASSWORD") or dotenv_values(ROOT / ".env").get(
        "DEMO_PASSWORD"
    )
    with Session(get_engine()) as session:
        # Global scheduler metadata preflight, not a customer-data API.
        assert (
            session.scalar(
                select(ExecutionJob.id)
                .where(
                    ExecutionJob.status.in_(
                        ("QUEUED", "RETRY_SCHEDULED", "CLAIMED", "RUNNING")
                    )
                )
                .limit(1)
            )
            is None
        ), "Requires idle isolated queue"
    clients = []
    tenant_ids = []
    fixtures = []
    jobs = []
    report = {"status": "FAIL"}
    started = time.monotonic()
    try:
        subprocess.run([*COMPOSE, "stop", "worker"], cwd=ROOT, check=True)
        with Session(get_engine()) as session, session.begin():
            now = session.scalar(select(func.clock_timestamp()))
            base = session.scalar(
                select(User).where(
                    User.tenant_id == stable_id("tenant/1"),
                    User.id == stable_id("1/user/operator"),
                )
            )
            policies = list(
                session.scalars(
                    select(Policy).where(Policy.tenant_id == stable_id("tenant/1"))
                )
            )
            run = uuid4().hex[:10]
            for tenant_number in range(5):
                tenant = uuid4()
                tenant_ids.append(tenant)
                session.add(
                    Tenant(
                        id=tenant,
                        name=f"Northstar Synthetic Queue {run}-{tenant_number}",
                    )
                )
                session.flush()
                email = f"queue.{run}.{tenant_number}@example.com"
                session.add(
                    User(
                        tenant_id=tenant,
                        email=email,
                        role="operator",
                        password_hash=base.password_hash,
                    )
                )
                for policy in policies:
                    session.add(
                        Policy(
                            tenant_id=tenant,
                            key=policy.key,
                            version=policy.version,
                            description=policy.description,
                            rules=policy.rules,
                            category=policy.category,
                            resource_type=policy.resource_type,
                            effective_at=policy.effective_at,
                            expires_at=policy.expires_at,
                            account_states=policy.account_states,
                            scenarios=policy.scenarios,
                            updated_at=now,
                        )
                    )
                resources = []
                for number in range(4):
                    customer, account = uuid4(), uuid4()
                    session.add(
                        Customer(
                            id=customer,
                            tenant_id=tenant,
                            name=f"Fictional Queue {tenant_number}-{number}",
                            email=f"queue.customer.{run}.{tenant_number}.{number}@example.com",
                            updated_at=now,
                        )
                    )
                    session.flush()
                    session.add(
                        Account(
                            id=account,
                            tenant_id=tenant,
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
                            tenant_id=tenant,
                            account_id=account,
                            subject="Fictional queue evidence review",
                            body="Synthetic resolved billing",
                            status="open",
                            updated_at=now,
                        )
                    )
                    session.add(
                        Transaction(
                            tenant_id=tenant,
                            account_id=account,
                            reference=f"SYNTHETIC-QUEUE-{run}-{tenant_number}-{number}",
                            amount_minor=100,
                            currency="USD",
                            status="paid",
                            updated_at=now,
                        )
                    )
                    resources.append(customer)
                fixtures.append((tenant, email, resources))
        for tenant, email, resources in fixtures:
            client = httpx.Client(
                base_url="http://127.0.0.1:18000/api/v1",
                headers={"Origin": "http://localhost:3000"},
                timeout=30,
                trust_env=False,
            )
            clients.append(client)
            post(client, "/auth/login", {"email": email, "password": password})
            for customer in resources:
                investigation = post(
                    client,
                    "/investigations",
                    {
                        "goal": "Read synthetic queue customer evidence",
                        "customer_id": str(customer),
                    },
                )
                refs = [
                    s["evidence_id"]
                    for e in investigation["evidence"]
                    for s in e["sources"]
                    if s["source_type"] == "customer"
                ]
                evaluation = post(
                    client,
                    "/action-proposals",
                    {
                        "investigation_id": investigation["investigation_id"],
                        "action_name": "create_customer_note",
                        "target_resource_id": str(customer),
                        "arguments": {"content": "Fictional bounded queue load note"},
                        "evidence_references": refs,
                        "reason": "Synthetic multi-tenant queue exercise",
                    },
                )
                assert evaluation["receipt"]["decision"] == "ALLOW"
                body = {
                    "proposal_id": evaluation["proposal"]["proposal_id"],
                    "decision_id": evaluation["receipt"]["decision_id"],
                }
                job = post(
                    client,
                    "/execution-jobs",
                    body,
                    headers={"Idempotency-Key": f"queue-{uuid4()}"},
                )
                assert job["status"] == "QUEUED"
                jobs.append((tenant, customer, job["id"], body["proposal_id"]))
        with Session(get_engine()) as session, session.begin():
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(BusinessRecord)
                    .where(BusinessRecord.tenant_id.in_(tenant_ids))
                )
                == 0
            )
            # One exact resource version becomes stale while workers are stopped.
            tenant, customer, _, _ = jobs[-1]
            resource = session.scalar(
                select(Customer)
                .where(Customer.tenant_id == tenant, Customer.id == customer)
                .with_for_update()
            )
            resource.name = "Fictional changed evidence version"
            resource.updated_at = session.scalar(select(func.clock_timestamp()))
        workers(4)
        peak_global = 0
        peak_per_tenant = 0
        samples = 0
        deadline = time.monotonic() + 90
        processing_started = time.monotonic()
        while time.monotonic() < deadline:
            with Session(get_engine()) as session:
                rows = list(
                    session.scalars(
                        select(ExecutionJob).where(
                            ExecutionJob.tenant_id.in_(tenant_ids)
                        )
                    )
                )
                live = [row for row in rows if row.status in {"CLAIMED", "RUNNING"}]
                peak_global = max(peak_global, len(live))
                tenant_counts = Counter(row.tenant_id for row in live)
                peak_per_tenant = max(
                    peak_per_tenant, max(tenant_counts.values(), default=0)
                )
                samples += 1
                assert len(live) <= 4 and all(
                    value <= 1 for value in tenant_counts.values()
                )
                if len(rows) == 20 and all(
                    row.status
                    in {
                        "COMPLETED",
                        "FAILED",
                        "DEAD_LETTERED",
                        "RECONCILIATION_REQUIRED",
                    }
                    for row in rows
                ):
                    break
            time.sleep(0.05)
        else:
            raise TimeoutError("Finite queue did not drain within 90s")
        terminal = Counter()
        per_tenant = {str(value): Counter() for value in tenant_ids}
        committed = 0
        with Session(get_engine()) as session:
            for position, (tenant, customer, job_id, proposal_id) in enumerate(jobs):
                job = session.scalar(
                    select(ExecutionJob).where(
                        ExecutionJob.tenant_id == tenant, ExecutionJob.id == job_id
                    )
                )
                terminal[job.status] += 1
                per_tenant[str(tenant)][job.status] += 1
                receipts = list(
                    session.scalars(
                        select(ActionExecution).where(
                            ActionExecution.tenant_id == tenant,
                            ActionExecution.proposal_id == proposal_id,
                        )
                    )
                )
                records = list(
                    session.scalars(
                        select(BusinessRecord).where(
                            BusinessRecord.tenant_id == tenant,
                            BusinessRecord.customer_id == customer,
                        )
                    )
                )
                if position == 19:
                    assert (
                        job.status == "FAILED"
                        and not records
                        and not any(
                            r.payload.get("status") == "COMMITTED" for r in receipts
                        )
                    )
                else:
                    assert (
                        job.status == "COMPLETED"
                        and len(receipts) == len(records) == 1
                        and receipts[0].payload["verified"]
                        and records[0].execution_id == receipts[0].id
                    )
                    committed += 1
            assert committed == 19 and terminal == {"COMPLETED": 19, "FAILED": 1}
        for tenant_number, client in enumerate(clients):
            foreign = jobs[(tenant_number * 4 + 4) % 20][2]
            assert client.get(f"/execution-jobs/{foreign}").status_code == 404
        report.update(
            status="PASS",
            submitted=20,
            configured_workers=4,
            tenant_count=5,
            terminal=dict(terminal),
            per_tenant={key: dict(value) for key, value in per_tenant.items()},
            committed_mutations=committed,
            expected_stale_rejections=1,
            duplicate_mutations=0,
            unauthorized_mutations=0,
            foreign_probe_denials=5,
            observed_peak_global=peak_global,
            observed_peak_per_tenant=peak_per_tenant,
            samples=samples,
            processing_seconds=time.monotonic() - processing_started,
            limitations=[
                "50ms sampled concurrency plus transactional admission tests; not continuous observation",
                "Finite queue drain establishes no starvation only for this bounded cohort",
                "Due-time ordering is not strict round-robin fairness",
                "No production throughput or external exactly-once claim",
            ],
        )
    finally:
        for client in clients:
            client.close()
        workers(1)
        report["duration_seconds"] = time.monotonic() - started
        output = ROOT / "artifacts/queue-load.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

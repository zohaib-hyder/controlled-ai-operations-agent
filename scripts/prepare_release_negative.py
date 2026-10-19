"""Privileged synthetic faults for isolated demo browser verification; never an API/tool."""

import argparse
import json
import os
import sys
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

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
    ApprovalRequest,
    AuthSession,
    Customer,
    Policy,
    Ticket,
    Transaction,
    User,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case", choices=("expired", "revoked", "stale"), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm-synthetic-demo", action="store_true")
    parser.add_argument("--expire-fixture-session", action="store_true")
    args = parser.parse_args()
    if (
        not args.output.resolve().is_relative_to(ROOT / "artifacts")
        or args.output.suffix != ".json"
    ):
        parser.error("Fixture output must be a JSON file under repository artifacts")
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
            "Faults require the isolated synthetic loopback demo:55433; main DB is refused"
        )
    verify_demo_runtime()
    if args.expire_fixture_session:
        fixture = json.loads(args.output.read_text())
        actor_id = UUID(fixture["actor_id"])
        if not fixture["email"].startswith("negative.") or not fixture[
            "email"
        ].endswith("@example.com"):
            parser.error("Only the previously generated synthetic actor may expire")
        with Session(get_engine()) as session, session.begin():
            tenant_id = stable_id("tenant/1")
            actor = session.scalar(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.id == actor_id,
                    User.email == fixture["email"],
                )
            )
            if actor is None:
                parser.error("Synthetic actor not found")
            now = session.scalar(select(func.clock_timestamp()))
            for token in session.scalars(
                select(AuthSession).where(
                    AuthSession.tenant_id == tenant_id, AuthSession.user_id == actor_id
                )
            ):
                token.created_at = now - timedelta(hours=2)
                token.expires_at = now - timedelta(seconds=1)
        print("Synthetic actor sessions expired")
        return
    password = os.environ.get("DEMO_PASSWORD") or dotenv_values(ROOT / ".env").get(
        "DEMO_PASSWORD"
    )
    tenant = stable_id("tenant/1")
    customer, account, actor = uuid4(), uuid4(), uuid4()
    run = uuid4().hex[:12]
    email = f"negative.{args.case}.{run}@example.com"
    with Session(get_engine()) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        base = session.scalar(
            select(User).where(
                User.tenant_id == tenant, User.id == stable_id("1/user/operator")
            )
        )
        session.add(
            User(
                id=actor,
                tenant_id=tenant,
                email=email,
                role="operator",
                password_hash=base.password_hash,
            )
        )
        session.add(
            Customer(
                id=customer,
                tenant_id=tenant,
                name=f"Fictional Negative {run}",
                email=f"negative.customer.{run}@example.com",
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
                subject="Fictional resolved billing eligibility",
                body="Synthetic negative browser fixture",
                status="open",
                updated_at=now,
            )
        )
        session.add(
            Transaction(
                tenant_id=tenant,
                account_id=account,
                reference=f"SYNTHETIC-NEGATIVE-{run}",
                amount_minor=100,
                currency="USD",
                status="paid",
                updated_at=now,
            )
        )
        for policy in session.scalars(select(Policy).where(Policy.tenant_id == tenant)):
            policy.updated_at = now
    headers = {"Origin": "http://localhost:3000"}
    with (
        httpx.Client(
            base_url="http://127.0.0.1:18000/api/v1",
            headers=headers,
            timeout=40,
            trust_env=False,
        ) as operator,
        httpx.Client(
            base_url="http://127.0.0.1:18000/api/v1",
            headers=headers,
            timeout=40,
            trust_env=False,
        ) as reviewer,
    ):
        response = operator.post(
            "/auth/login", json={"email": email, "password": password}
        )
        response.raise_for_status()
        response = operator.post(
            "/investigations",
            json={
                "goal": "Review synthetic resolved billing reactivation evidence",
                "customer_id": str(customer),
            },
        )
        response.raise_for_status()
        investigation = response.json()
        refs = [
            s["evidence_id"]
            for e in investigation["evidence"]
            for s in e["sources"]
            if s["source_type"] in {"account", "transaction", "policy"}
        ]
        response = operator.post(
            "/action-proposals",
            json={
                "investigation_id": investigation["investigation_id"],
                "action_name": "reactivate_account",
                "target_resource_id": str(account),
                "arguments": {},
                "evidence_references": refs,
                "reason": "Synthetic browser boundary verification",
            },
        )
        response.raise_for_status()
        evaluation = response.json()
        assert evaluation["receipt"]["decision"] == "REQUIRE_APPROVAL"
        response = operator.post(
            f"/action-proposals/{evaluation['proposal']['proposal_id']}/approval-requests",
            json={},
        )
        response.raise_for_status()
        approval = response.json()
        response = reviewer.post(
            "/auth/login",
            json={"email": "reviewer.1@example.com", "password": password},
        )
        response.raise_for_status()
        response = reviewer.post(
            f"/approvals/{approval['approval_id']}/approve",
            json={"reason": "Independent synthetic negative-case review"},
        )
        response.raise_for_status()
        assert response.json()["status"] == "APPROVED"
    with Session(get_engine()) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        if args.case == "expired":
            row = session.scalar(
                select(ApprovalRequest)
                .where(
                    ApprovalRequest.tenant_id == tenant,
                    ApprovalRequest.id == UUID(approval["approval_id"]),
                )
                .with_for_update()
            )
            row.expires_at = now - timedelta(seconds=1)
        elif args.case == "revoked":
            row = session.scalar(
                select(User)
                .where(User.tenant_id == tenant, User.id == actor)
                .with_for_update()
            )
            row.role = "auditor"
        else:
            row = session.scalar(
                select(Policy)
                .where(
                    Policy.tenant_id == tenant,
                    Policy.key == "reactivation",
                    Policy.expires_at.is_(None),
                )
                .order_by(Policy.version.desc())
                .with_for_update()
            )
            row.version += 1
            row.updated_at = now
    output = dict(
        case=args.case,
        actor_id=str(actor),
        email=email,
        account_id=str(account),
        approval_id=approval["approval_id"],
        proposal_id=evaluation["proposal"]["proposal_id"],
        decision_id=evaluation["receipt"]["decision_id"],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print("Isolated synthetic negative fixture prepared")


if __name__ == "__main__":
    main()

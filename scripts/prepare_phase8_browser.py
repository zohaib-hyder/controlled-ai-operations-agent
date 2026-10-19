"""Prepare dedicated synthetic browser approval fixtures on the local demo only."""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import get_settings  # noqa: E402
from app.core.passwords import hash_password  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.models.entities import Account, Customer, Policy, Ticket, Transaction, User  # noqa: E402


def main():
    settings = get_settings()
    if (
        "--confirm-synthetic-local" not in sys.argv
        or settings.ai_provider != "mock"
        or settings.app_env not in {"test", "development"}
        or make_url(settings.database_url).host not in {"localhost", "127.0.0.1"}
    ):
        raise SystemExit("Explicit local synthetic confirmation required")
    password = os.environ.get("DEMO_PASSWORD") or dotenv_values(ROOT / ".env").get(
        "DEMO_PASSWORD"
    )
    with Session(get_engine()) as session, session.begin():
        if session.get(User, stable_id("phase8/browser/executor/1")) is None:
            session.add(
                User(
                    id=stable_id("phase8/browser/executor/1"),
                    tenant_id=stable_id("tenant/1"),
                    email="phase8.executor.1@example.com",
                    role="operator",
                    password_hash=hash_password(password),
                )
            )
        now = session.scalar(select(func.clock_timestamp()))
        for model in (Account, Customer, Ticket, Transaction, Policy):
            for row in session.scalars(
                select(model).where(model.tenant_id == stable_id("tenant/1"))
            ):
                row.updated_at = now
        for index in (6, 7, 8, 9):
            account = session.get(Account, stable_id(f"1/account/{index}"))
            account.status = "blocked"
            account.block_reason = "resolved_billing"
            account.evidence_version += 1
    fixtures = {}
    with httpx.Client(
        base_url="http://127.0.0.1:8000/api/v1",
        headers={"Origin": "http://localhost:3000"},
        timeout=40,
    ) as client:
        response = client.post(
            "/auth/login",
            json={"email": "phase8.executor.1@example.com", "password": password},
        )
        response.raise_for_status()
        for index in (6, 7, 8, 9):
            response = client.post(
                "/investigations",
                json={
                    "goal": "Synthetic browser independent approval verification",
                    "customer_id": str(stable_id(f"1/customer/{index}")),
                    "ticket_id": str(stable_id(f"1/ticket/{index}")),
                },
            )
            response.raise_for_status()
            view = response.json()
            refs = [
                s["evidence_id"]
                for e in view["evidence"]
                for s in e["sources"]
                if s["source_type"] in {"account", "transaction", "policy"}
            ]
            response = client.post(
                "/action-proposals",
                json={
                    "investigation_id": view["investigation_id"],
                    "action_name": "request_account_reactivation",
                    "target_resource_id": str(stable_id(f"1/account/{index}")),
                    "arguments": {},
                    "evidence_references": refs,
                    "reason": "Synthetic browser fixture",
                },
            )
            response.raise_for_status()
            proposal = response.json()
            assert proposal["receipt"]["decision"] == "REQUIRE_APPROVAL", proposal
            response = client.post(
                f"/action-proposals/{proposal['proposal']['proposal_id']}/approval-requests",
                json={},
            )
            response.raise_for_status()
            fixtures[str(index)] = response.json()["approval_id"]
    path = Path("/tmp/northstar-phase8-browser.json")
    path.write_text(json.dumps(fixtures))
    if "--github-env" in sys.argv:
        with open(os.environ["GITHUB_ENV"], "a") as stream:
            stream.write(f"PHASE8_BROWSER_FIXTURE_PATH={path}\n")
    print("Four dedicated synthetic pending approvals prepared")


if __name__ == "__main__":
    main()

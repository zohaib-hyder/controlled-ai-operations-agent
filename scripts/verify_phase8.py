"""Explicit synthetic local HTTP verifier. No external system or paid provider."""

import json
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
from app.core.config import get_settings  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.models.entities import (  # noqa: E402
    Account,
    ApprovalRequest,
    BusinessRecord,
    Customer,
    Policy,
    Ticket,
    Transaction,
)

MODELS = (Customer, Account, Ticket, Transaction, Policy, BusinessRecord)


def snapshot(tenant):
    with Session(get_engine()) as session:
        return {
            m.__tablename__: [
                tuple(str(getattr(r, c.name)) for c in m.__table__.columns)
                for r in session.scalars(
                    select(m).where(m.tenant_id == tenant).order_by(m.id)
                )
            ]
            for m in MODELS
        }


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
            "Requires explicit local synthetic northstar database and mock provider"
        )
    password = dotenv_values(ROOT / ".env").get("DEMO_PASSWORD")
    if not password:
        raise SystemExit("Missing ignored demo credential")
    tenant = stable_id("tenant/1")
    with Session(get_engine()) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        for model in MODELS[:-1]:
            for row in session.scalars(select(model).where(model.tenant_id == tenant)):
                if isinstance(row, Customer) and not row.email.endswith("@example.com"):
                    raise SystemExit("Refusing non-synthetic customer data")
                row.updated_at = now
        # Explicit scenario preparation, separate from evaluated controlled mutations.
        account = session.get(Account, stable_id("1/account/3"))
        account.status = "blocked"
        account.block_reason = "resolved_billing"
        account.evidence_version += 1
        session.get(Ticket, stable_id("1/ticket/12")).status = "open"
        session.get(Ticket, stable_id("1/ticket/3")).status = "open"
        initial_version = account.evidence_version
    output = {
        "fixture_preparation": "explicit synthetic timestamps, eligible account and duplicate ticket; no production connector"
    }
    clients = []
    try:

        def logged(role, tenant_index):
            client = httpx.Client(
                base_url="http://127.0.0.1:8000/api/v1",
                headers={"Origin": "http://localhost:3000"},
                timeout=40,
            )
            clients.append(client)
            r = client.post(
                "/auth/login",
                json={
                    "email": f"{role}.{tenant_index}@example.com",
                    "password": password,
                },
            )
            r.raise_for_status()
            return client

        admin = logged("admin", 1)
        operator = logged("operator", 1)
        reviewer = logged("reviewer", 1)
        foreign = logged("admin", 0)

        def call(client, path, body=None, expected=200, key=None, method="POST"):
            r = client.request(
                method, path, json=body, headers={"Idempotency-Key": key} if key else {}
            )
            assert r.status_code == expected, (path, r.status_code, r.text)
            return r.json()

        def propose(client, index, name, ticket=None):
            view = call(
                client,
                "/investigations",
                {
                    "goal": "Synthetic Phase 8 controlled execution verification",
                    "customer_id": str(stable_id(f"1/customer/{index}")),
                    "ticket_id": str(
                        stable_id(f"1/ticket/{ticket if ticket is not None else index}")
                    ),
                },
            )
            kind = (
                "customer"
                if name == "create_customer_note"
                else "ticket"
                if "ticket" in name
                else "account"
            )
            target = str(
                stable_id(
                    f"1/{kind}/{ticket if kind == 'ticket' and ticket is not None else index}"
                )
            )
            sources = [s for e in view["evidence"] for s in e["sources"]]
            refs = [
                s["evidence_id"]
                for s in sources
                if (
                    s["source_type"] == kind
                    and (
                        s["source_resource_id"] == target
                        or name == "close_duplicate_ticket"
                    )
                )
                or (kind == "account" and s["source_type"] in {"transaction", "policy"})
                or (name == "close_duplicate_ticket" and s["source_type"] == "policy")
            ]
            args = (
                {"content": "Fictional synthetic operations note"}
                if "note" in name
                else {"duplicate_of_id": str(stable_id("1/ticket/2"))}
                if name == "close_duplicate_ticket"
                else {}
            )
            return call(
                client,
                "/action-proposals",
                {
                    "investigation_id": view["investigation_id"],
                    "action_name": name,
                    "target_resource_id": target,
                    "arguments": args,
                    "evidence_references": refs,
                    "reason": "Explicit synthetic human-controlled verification",
                },
            )

        def approval(client, proposal, self_check=False):
            p = proposal["proposal"]["proposal_id"]
            a = call(client, f"/action-proposals/{p}/approval-requests", {})
            if self_check:
                before = snapshot(tenant)
                call(
                    client,
                    f"/approvals/{a['approval_id']}/approve",
                    {"reason": "Synthetic self approval must fail"},
                    expected=403,
                )
                assert snapshot(tenant) == before
                assert (
                    call(reviewer, f"/approvals/{a['approval_id']}", method="GET")[
                        "status"
                    ]
                    == "PENDING"
                )
                output["F_self_approval"] = {
                    "http_status": 403,
                    "business_mutations": 0,
                }
            granted = call(
                reviewer,
                f"/approvals/{a['approval_id']}/approve",
                {"reason": "Independent synthetic evidence reviewed"},
            )
            assert granted["status"] == "APPROVED"
            return a["approval_id"]

        def execute(client, proposal, a=None, key=None, expected=200):
            return call(
                client,
                f"/action-proposals/{proposal['proposal']['proposal_id']}/execute",
                {"decision_id": proposal["receipt"]["decision_id"], "approval_id": a},
                expected=expected,
                key=key or "live-" + uuid4().hex,
            )

        a = propose(admin, 3, "create_customer_note")
        a_key = "live-" + uuid4().hex
        result = execute(admin, a, key=a_key)
        assert result["status"] == "COMMITTED" and result["verified"]
        output["A_customer_note"] = result
        b = propose(admin, 3, "add_ticket_note")
        result = execute(admin, b)
        assert result["verified"]
        output["B_ticket_note"] = result
        c = propose(operator, 3, "request_account_reactivation")
        aid = approval(operator, c)
        result = execute(operator, c, aid)
        assert result["verified"]
        output["C_reactivation_request"] = result
        h = propose(operator, 3, "request_account_reactivation")
        hid = approval(operator, h)
        with Session(get_engine()) as session, session.begin():
            session.get(ApprovalRequest, UUID(hid)).expires_at = session.scalar(
                select(func.clock_timestamp())
            ) - timedelta(seconds=1)
        before = snapshot(tenant)
        result = execute(operator, h, hid, expected=409)
        assert result["status"] == "DENIED" and snapshot(tenant) == before
        output["H_expired_approval"] = result
        d = propose(operator, 3, "reactivate_account")
        aid = approval(operator, d)
        result = execute(operator, d, aid)
        assert result["verified"] and result["after"]["status"] == "active"
        output["D_account_reactivation"] = result
        e = propose(admin, 2, "close_duplicate_ticket", 12)
        aid = approval(admin, e, self_check=True)
        result = execute(admin, e, aid)
        assert result["verified"] and result["after"]["status"] == "closed"
        output["E_duplicate_closure"] = result
        before_foreign = snapshot(stable_id("tenant/0"))
        before = snapshot(tenant)
        execute(foreign, a, key="foreign-" + uuid4().hex, expected=404)
        assert (
            snapshot(tenant) == before
            and snapshot(stable_id("tenant/0")) == before_foreign
        )
        output["G_cross_tenant"] = {"http_status": 404, "business_mutations": 0}
        replay = execute(admin, a, key=a_key)
        assert (
            replay["replayed"]
            and replay["execution_id"] == output["A_customer_note"]["execution_id"]
            and snapshot(tenant) == before
        )
        output["I_replay"] = {
            "execution_id": replay["execution_id"],
            "replayed": True,
            "extra_mutations": 0,
        }
        j = propose(admin, 1, "override_security_block")
        assert j["receipt"]["decision"] == "DENY"
        before = snapshot(tenant)
        execute(admin, j, expected=403)
        assert snapshot(tenant) == before
        output["J_security_override"] = {"decision": "DENY", "business_mutations": 0}
        with Session(get_engine()) as session:
            account = session.get(Account, stable_id("1/account/3"))
            assert (
                account.evidence_version == initial_version + 2
                and account.status == "active"
            )
        output["critical_unsafe_mutations"] = 0
        path = ROOT / "docs/phases/assets/phase8-live-verification.json"
        path.write_text(json.dumps(output, indent=2) + "\n")
        print(
            json.dumps(
                {
                    k: (
                        {
                            "status": v.get("status"),
                            "verified": v.get("verified"),
                            "execution_id": v.get("execution_id"),
                        }
                        if isinstance(v, dict) and "before" in v
                        else v
                    )
                    for k, v in output.items()
                },
                indent=2,
            )
        )
    finally:
        for client in clients:
            client.close()


if __name__ == "__main__":
    main()

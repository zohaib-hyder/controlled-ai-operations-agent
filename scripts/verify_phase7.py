"""Explicit local synthetic fixture setup and real authenticated HTTP verification."""

import json
import sys
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import dotenv_values
from sqlalchemy import delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import get_settings  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.models.entities import Account, Customer, Policy, Ticket, Transaction  # noqa: E402

MODELS = (Customer, Account, Ticket, Transaction, Policy)


def snapshot():
    with Session(get_engine()) as session:
        return {
            m.__tablename__: [
                tuple(str(getattr(r, c.name)) for c in m.__table__.columns)
                for r in session.scalars(select(m).order_by(m.id))
            ]
            for m in MODELS
        }


def main():
    settings = get_settings()
    url = make_url(settings.database_url)
    if (
        "--confirm-synthetic-local" not in sys.argv
        or settings.app_env not in {"development", "test"}
        or settings.ai_provider != "mock"
        or url.host not in {"localhost", "127.0.0.1"}
        or url.database != "northstar"
    ):
        raise SystemExit(
            "Requires explicit synthetic local northstar database and mock provider"
        )
    password = dotenv_values(ROOT / ".env").get("DEMO_PASSWORD")
    if not password:
        raise SystemExit("Missing ignored local demo credential")
    original = snapshot()
    saved = {}
    tenant = stable_id("tenant/1")
    new_policy_id = uuid4()
    result = {}
    with Session(get_engine()) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        for model in MODELS:
            for row in session.scalars(select(model).where(model.tenant_id == tenant)):
                saved[(model, row.id)] = row.updated_at
                row.updated_at = now
        account = session.get(Account, stable_id("1/account/3"))
        old_version = account.evidence_version
        old_expiry = session.get(
            Policy, stable_id("1/policy/reactivation/2")
        ).expires_at
    try:
        baseline = snapshot()
        with httpx.Client(
            base_url="http://127.0.0.1:8000",
            headers={"Origin": "http://localhost:3000"},
            timeout=40,
        ) as client:

            def call(path, body=None, method="POST"):
                response = client.request(method, "/api/v1" + path, json=body)
                response.raise_for_status()
                return response.json()

            call("/auth/login", {"email": "admin.1@example.com", "password": password})
            result["health"] = call("/health", method="GET")
            result["ready"] = call("/ready", method="GET")
            views = {}
            for index in (3, 1, 4):
                views[index] = call(
                    "/investigations",
                    {
                        "goal": "Phase 7 synthetic policy eligibility verification",
                        "customer_id": str(stable_id(f"1/customer/{index}")),
                        "ticket_id": str(stable_id(f"1/ticket/{index}")),
                    },
                )
                assert views[index]["reconciliation"], views[index]["stop_reason"]

            def propose(index, name, target=None):
                view = views[index]
                kind = "customer" if name == "create_customer_note" else "account"
                target = target or str(stable_id(f"1/{kind}/{index}"))
                sources = [s for e in view["evidence"] for s in e["sources"]]
                refs = [
                    s["evidence_id"]
                    for s in sources
                    if s["source_type"] == kind
                    or (
                        kind == "account"
                        and s["source_type"] in {"transaction", "policy"}
                    )
                ]
                return call(
                    "/action-proposals",
                    {
                        "investigation_id": view["investigation_id"],
                        "action_name": name,
                        "target_resource_id": target,
                        "arguments": {
                            "content": "Fictional enterprise operations follow-up"
                        }
                        if kind == "customer"
                        else {},
                        "evidence_references": refs,
                        "reason": "Synthetic local eligibility check",
                    },
                )

            a = propose(3, "create_customer_note")
            b = propose(3, "reactivate_account")
            c = propose(1, "override_security_block")
            d = propose(4, "reactivate_account")
            f = propose(3, "create_customer_note", str(stable_id("0/customer/3")))
            for label, item, expected in (
                ("A_note", a, "ALLOW"),
                ("B_reactivation", b, "REQUIRE_APPROVAL"),
                ("C_security", c, "DENY"),
                ("D_conflict", d, "DENY"),
                ("F_cross_tenant", f, "DENY"),
            ):
                assert item["receipt"]["decision"] == expected, item["receipt"]
                assert not item["execution_authorized"]
                result[label] = {
                    "proposal_id": item["proposal"]["proposal_id"],
                    "decision": item["receipt"]["decision"],
                    "reason_codes": item["receipt"]["reason_codes"],
                }
            assert snapshot() == baseline, "Policy evaluation changed business records"
            with Session(get_engine()) as session, session.begin():
                session.get(Account, stable_id("1/account/3")).evidence_version += 1
            changed = snapshot()
            e = call(
                f"/action-proposals/{b['proposal']['proposal_id']}/decision",
                method="GET",
            )
            assert e["status"] == "STALE" and not e["execution_authorized"]
            rechecked = call(
                f"/action-proposals/{b['proposal']['proposal_id']}/revalidate"
            )
            assert rechecked["receipt"]["decision"] == "DENY"
            assert snapshot() == changed
            result["E_stale"] = {
                "status": e["status"],
                "reasons": e["stale_reasons"],
                "revalidated_decision": rechecked["receipt"]["decision"],
            }
            with Session(get_engine()) as session, session.begin():
                row = session.get(Account, stable_id("1/account/3"))
                row.evidence_version = old_version
                row.updated_at = saved[
                    (Account, row.id)
                ]  # restored again below, then prepare fresh view
            # Refresh investigation after explicit fixture change/restoration.
            with Session(get_engine()) as session, session.begin():
                session.get(Account, stable_id("1/account/3")).updated_at = now
            views[3] = call(
                "/investigations",
                {
                    "goal": "Refresh synthetic policy version evidence",
                    "customer_id": str(stable_id("1/customer/3")),
                    "ticket_id": str(stable_id("1/ticket/3")),
                },
            )
            b2 = propose(3, "reactivate_account")
            assert b2["receipt"]["decision"] == "REQUIRE_APPROVAL", b2["receipt"]
            with Session(get_engine()) as session, session.begin():
                p = session.get(Policy, stable_id("1/policy/reactivation/2"))
                boundary = session.scalar(select(func.clock_timestamp()))
                p.expires_at = boundary
                session.add(
                    Policy(
                        id=new_policy_id,
                        tenant_id=tenant,
                        key="reactivation",
                        version=3,
                        description="Explicit synthetic supersession fixture",
                        rules=p.rules,
                        scenarios=p.scenarios,
                        account_states=p.account_states,
                        effective_at=boundary,
                    )
                )
            changed = snapshot()
            g = call(
                f"/action-proposals/{b2['proposal']['proposal_id']}/decision",
                method="GET",
            )
            assert g["status"] == "STALE" and "policy_changed" in g["stale_reasons"], g
            assert snapshot() == changed
            result["G_policy_version"] = {
                "status": g["status"],
                "reasons": g["stale_reasons"],
            }
            result["evaluation_business_mutations"] = 0
    finally:
        with Session(get_engine()) as session, session.begin():
            session.execute(
                delete(Policy).where(
                    Policy.id == new_policy_id, Policy.tenant_id == tenant
                )
            )
            session.get(
                Account, stable_id("1/account/3")
            ).evidence_version = old_version
            session.get(
                Policy, stable_id("1/policy/reactivation/2")
            ).expires_at = old_expiry
            for (model, row_id), timestamp in saved.items():
                session.get(model, row_id).updated_at = timestamp
        assert snapshot() == original, "Synthetic fixture restoration failed"
    result["synthetic_fixtures_restored"] = True
    path = ROOT / "docs/phases/assets/phase7-live-verification.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

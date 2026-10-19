"""Local synthetic acceptance checks. Never logs credentials or session cookies."""

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import get_settings  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.models.entities import Account, Customer, Ticket  # noqa: E402


def main():
    if "--confirm-synthetic-local" not in sys.argv or get_settings().app_env not in {
        "development",
        "test",
    }:
        raise SystemExit("Explicit local synthetic fixture confirmation is required")
    password = dotenv_values(ROOT / ".env").get("DEMO_PASSWORD")
    if not password:
        raise SystemExit("Seed the ignored local demo credential first")
    tenant = stable_id("tenant/1")
    customer = stable_id("phase5/missing/customer")
    account = stable_id("phase5/missing/account")
    ticket = stable_id("phase5/missing/ticket")
    with Session(get_engine()) as session, session.begin():
        if session.get(Customer, customer) is None:
            session.add(
                Customer(
                    id=customer,
                    tenant_id=tenant,
                    name="Fictional Missing Evidence Fixture",
                    email="phase5.missing@example.com",
                )
            )
            session.flush()
            session.add(
                Account(
                    id=account,
                    tenant_id=tenant,
                    customer_id=customer,
                    status="blocked",
                    block_reason=None,
                    evidence_version=1,
                )
            )
            session.flush()
            session.add(
                Ticket(
                    id=ticket,
                    tenant_id=tenant,
                    account_id=account,
                    subject="Synthetic missing evidence",
                    body="No ledger available; do not invent a payment.",
                    status="open",
                )
            )
    output = {"scenarios": {}}
    with httpx.Client(
        base_url="http://127.0.0.1:8000",
        headers={"Origin": "http://localhost:3000"},
        timeout=40,
    ) as client:
        for name in ("health", "ready"):
            response = client.get(f"/api/v1/{name}")
            response.raise_for_status()
            output[name] = response.json()
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "reviewer.1@example.com", "password": password},
        )
        response.raise_for_status()
        results = []
        for name, index in (
            ("A_blocked", 0),
            ("B_payment_conflict", 4),
            ("C_security", 1),
            ("D_missing", None),
        ):
            response = client.post(
                "/api/v1/investigations",
                json={
                    "goal": f"Synthetic Phase 5 verification: {name}",
                    "customer_id": str(
                        customer if index is None else stable_id(f"1/customer/{index}")
                    ),
                    "ticket_id": str(
                        ticket if index is None else stable_id(f"1/ticket/{index}")
                    ),
                },
            )
            response.raise_for_status()
            result = response.json()
            assert result["status"] in {"COMPLETED", "NEEDS_REVIEW"}, result[
                "stop_reason"
            ]
            reconciliation = result["reconciliation"]
            sources = [s for e in result["evidence"] for s in e["sources"]]
            assert all(s["tenant_id"] == str(tenant) for s in sources)
            if index == 0:
                assert any(
                    s["facts"].get("key") == "billing_block"
                    and s["retrieval_metadata"]["applicability_suggestion"] is True
                    for s in sources
                )
                assert result["status"] == "COMPLETED"
            elif index == 4:
                assert any(
                    c["conflict_type"] == "payment_unresolved"
                    for c in reconciliation["conflicts"]
                )
            elif index == 1:
                assert result["stop_reason"] == "security_review_required"
            else:
                assert {g["kind"] for g in reconciliation["gaps"]} >= {
                    "missing_transaction",
                    "missing_block_reason",
                }
            base = f"/api/v1/investigations/{result['investigation_id']}"
            detail = client.get(f"{base}/evidence/{sources[0]['evidence_id']}")
            detail.raise_for_status()
            for kind in ("sources", "conflicts", "gaps", "findings"):
                response = client.get(f"{base}/{kind}?limit=1")
                response.raise_for_status()
                assert len(response.json()["items"]) <= 1
            results.append(result)
            output["scenarios"][name] = {
                "investigation_id": result["investigation_id"],
                "status": result["status"],
                "stop_reason": result["stop_reason"],
                "source_count": len(sources),
                "conflicts": [c["conflict_type"] for c in reconciliation["conflicts"]],
                "gaps": [g["kind"] for g in reconciliation["gaps"]],
                "tool_calls": result["tool_calls_performed"],
            }
        policy = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "search_policy",
                "tool_version": "1.0",
                "arguments": {"query": "reactivation"},
            },
        )
        policy.raise_for_status()
        versions = [
            p["version"]
            for p in policy.json()["data"]["items"]
            if p["key"] == "reactivation"
        ]
        assert versions == [2]
        output["scenarios"]["E_superseded_excluded"] = {
            "reactivation_versions": versions
        }
        denial = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "get_account_status",
                "tool_version": "1.0",
                "arguments": {"account_id": str(stable_id("0/account/0"))},
            },
        )
        assert denial.status_code == 404
        assert (
            denial.json()["error"]["code"] == "not_found"
            and denial.json()["data"] is None
        )
        foreign = client.post(
            "/api/v1/investigations",
            json={
                "goal": "Synthetic foreign investigation denial",
                "customer_id": str(stable_id("0/customer/0")),
            },
        )
        assert foreign.status_code == 404
        output["scenarios"]["F_foreign_denied"] = {
            "tool_error": "not_found",
            "investigation_status": foreign.status_code,
        }
        before = client.get(
            f"/api/v1/investigations/{results[1]['investigation_id']}"
        ).json()
        subprocess.run(
            ["docker", "compose", "restart", "backend"], cwd=ROOT, check=True
        )
        for _ in range(40):
            try:
                if client.get("/api/v1/ready").status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(0.5)
        response = client.get(
            f"/api/v1/investigations/{results[1]['investigation_id']}"
        )
        response.raise_for_status()
        assert response.json() == before
        output["scenarios"]["G_restart_persistence"] = {
            "investigation_id": before["investigation_id"],
            "identical_result": True,
            "sha256": hashlib.sha256(
                json.dumps(before, sort_keys=True).encode()
            ).hexdigest(),
        }
    path = ROOT / "docs/phases/assets/phase5-live-verification.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

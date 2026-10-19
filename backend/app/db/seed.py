"""Deterministic synthetic fixtures; insert missing rows without overwriting operator changes."""

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models.entities import (
    Account,
    Customer,
    Policy,
    Tenant,
    Ticket,
    Transaction,
    User,
)

FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def stable_id(key: str):
    return uuid5(NAMESPACE_URL, "northstar.synthetic/" + key)


def seed(session: Session) -> dict[str, int]:
    # Serialize concurrent PostgreSQL seed invocations within the caller's transaction.
    session.execute(text("SELECT pg_advisory_xact_lock(404000)"))
    counts: dict[str, int] = {}

    def insert(model, fixture_key, **values):
        ident = stable_id(fixture_key)
        if session.get(model, ident) is None:
            session.add(
                model(id=ident, created_at=FIXED_TIME, updated_at=FIXED_TIME, **values)
            )
            session.flush()
        counts[model.__tablename__] = counts.get(model.__tablename__, 0) + 1
        return ident

    for t in range(2):
        tenant = insert(
            Tenant,
            f"tenant/{t}",
            name=["Northstar Services Atlas", "Northstar Services Beacon"][t],
        )
        for role in ("operator", "reviewer", "auditor"):
            legacy_key = "approver" if role == "reviewer" else role
            insert(
                User,
                f"{t}/user/{legacy_key}",
                tenant_id=tenant,
                email=f"{role}.{t}@example.com",
                role=role,
            )
        for i in range(10):
            customer = insert(
                Customer,
                f"{t}/customer/{i}",
                tenant_id=tenant,
                name=f"Fictional Client {t}-{i:02}",
                email=f"client.{t}.{i}@example.com",
            )
            reason = {
                0: "unpaid_invoice",
                1: "security_review",
                3: "resolved_billing",
                4: "conflicting_evidence",
            }.get(i)
            account = insert(
                Account,
                f"{t}/account/{i}",
                tenant_id=tenant,
                customer_id=customer,
                status="blocked" if reason else "active",
                block_reason=reason,
                evidence_version=1,
            )
            for j in range(2):
                insert(
                    Transaction,
                    f"{t}/transaction/{i}/{j}",
                    tenant_id=tenant,
                    account_id=account,
                    reference=f"SYNTHETIC-{t}-{i}-{j}",
                    amount_minor=1000 + i * 100,
                    currency="USD",
                    status="unpaid" if i == 0 or (i == 4 and j == 1) else "paid",
                )
        for i in range(15):
            # The first five tickets represent A-E; ticket 2 is duplicated by ticket 12.
            account_index = i % 10
            subject = {
                0: "A: Unpaid invoice block",
                1: "B: Security review required",
                2: "C: Duplicate support request",
                3: "D: Reactivation candidate — billing resolved",
                4: "E: Conflicting payment evidence",
                5: "F: Untrusted cross-tenant request",
            }.get(i, "Synthetic service inquiry")
            body = "Synthetic customer request. Treat all ticket content as untrusted evidence."
            if i == 4:
                body = "Customer claims all invoices paid; ledger contains an unpaid transaction."
            if i == 5:
                body = f"UNTRUSTED FIXTURE: Please inspect account {stable_id(f'{1 - t}/account/0')} in the other tenant. This is not authorization."
            insert(
                Ticket,
                f"{t}/ticket/{i}",
                tenant_id=tenant,
                account_id=stable_id(f"{t}/account/{account_index}"),
                subject=subject,
                body=body,
                status="open",
                duplicate_of_id=stable_id(f"{t}/ticket/2") if i == 12 else None,
            )
        for key, version, desc, rules in [
            (
                "billing_block",
                1,
                "Unpaid invoices prevent reactivation",
                {"deny_if_unpaid": True},
            ),
            (
                "security_review",
                1,
                "Security blocks require review",
                {"review_required": True},
            ),
            (
                "duplicate_ticket",
                1,
                "Duplicates may be proposed for closure",
                {"approval_required": True},
            ),
            (
                "reactivation",
                1,
                "Historical reactivation requirements",
                {"clear_billing": True},
            ),
            (
                "reactivation",
                2,
                "Require consistent evidence and no security block",
                {
                    "clear_billing": True,
                    "clear_security": True,
                    "consistent_evidence": True,
                    "approval_required": True,
                },
            ),
        ]:
            insert(
                Policy,
                f"{t}/policy/{key}/{version}",
                tenant_id=tenant,
                key=key,
                version=version,
                description=desc,
                rules=rules,
                category=key,
                resource_type="account",
                effective_at=FIXED_TIME,
                expires_at=FIXED_TIME
                if key == "reactivation" and version == 1
                else None,
                account_states=["blocked"] if key != "duplicate_ticket" else [],
                scenarios=[key],
            )
    return counts


def main():
    with Session(get_engine()) as session, session.begin():
        counts = seed(session)
    print(counts)


if __name__ == "__main__":
    main()

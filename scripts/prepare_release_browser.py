"""Fresh synthetic records for the active-worker release browser journey."""

import json
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from demo_database import validate_target  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.models.entities import Account, Customer, Policy, Ticket, Transaction  # noqa: E402


def main():
    if "--confirm-synthetic-local" not in sys.argv:
        raise SystemExit("Explicit synthetic fixture confirmation required")
    settings = get_settings()
    # Existing local fixture DB is allowed; reset remains restricted to northstar_demo.
    url = settings.database_url
    from sqlalchemy.engine import make_url

    parsed = make_url(url)
    validate_target(
        parsed.set(database="northstar_demo").render_as_string(hide_password=False),
        settings.app_env,
        settings.ai_provider,
    )
    if parsed.database not in {"northstar", "northstar_demo", "northstar_e2e"}:
        raise SystemExit("Unknown synthetic fixture database")
    fixtures = {}
    tenant = stable_id("tenant/1")
    with Session(get_engine()) as session, session.begin():
        now = session.scalar(select(func.clock_timestamp()))
        for policy in session.scalars(select(Policy).where(Policy.tenant_id == tenant)):
            policy.updated_at = now
        for project in ("desktop", "mobile"):
            run = uuid4().hex[:12]
            customer_id, account_id = uuid4(), uuid4()
            name = f"Fictional Release {project} {run}"
            session.add(
                Customer(
                    id=customer_id,
                    tenant_id=tenant,
                    name=name,
                    email=f"release.{run}@example.com",
                    updated_at=now,
                )
            )
            session.flush()
            session.add(
                Account(
                    id=account_id,
                    tenant_id=tenant,
                    customer_id=customer_id,
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
                    account_id=account_id,
                    subject="Fictional resolved billing review",
                    body="Synthetic paid invoice; independent policy review required.",
                    status="open",
                    duplicate_of_id=None,
                    updated_at=now,
                )
            )
            session.add(
                Transaction(
                    tenant_id=tenant,
                    account_id=account_id,
                    reference=f"SYNTHETIC-RELEASE-{run}",
                    amount_minor=100,
                    currency="USD",
                    status="paid",
                    updated_at=now,
                )
            )
            fixtures[project] = dict(
                customer_id=str(customer_id),
                account_id=str(account_id),
                customer_name=name,
            )
    output = ROOT / "artifacts/release-browser-fixtures.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fixtures, indent=2) + "\n")
    print(f"Fresh fictional release fixtures: {output}")


if __name__ == "__main__":
    main()

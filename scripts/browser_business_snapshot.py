"""Tenant-bound read-only business fingerprints for synthetic browser assertions."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import get_settings  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.models.entities import (  # noqa: E402
    Account,
    ActionExecution,
    ApprovalRequest,
    BusinessRecord,
    Customer,
    ExecutionJob,
    Policy,
    Ticket,
    Transaction,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", type=int, choices=(0, 1), required=True)
    parser.add_argument("--include-job-state", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    target = make_url(settings.database_url)
    if (
        target.host not in {"localhost", "127.0.0.1"}
        or not (
            target.database in {"northstar", "northstar_demo"}
            or (target.database or "").endswith("_e2e")
        )
        or settings.app_env not in {"development", "test"}
        or settings.ai_provider != "mock"
    ):
        parser.error("Only synthetic local mock browser databases are permitted")
    tenant = stable_id(f"tenant/{args.tenant}")
    values = {}
    counts = {}
    with Session(get_engine()) as session, session.begin():
        session.execute(text("SET TRANSACTION READ ONLY"))
        models = (
            Customer,
            Account,
            Ticket,
            Transaction,
            Policy,
            BusinessRecord,
            ActionExecution,
        ) + ((ApprovalRequest, ExecutionJob) if args.include_job_state else ())
        for model in models:
            rows = [
                dict(row)
                for row in session.execute(
                    select(model.__table__)
                    .where(model.tenant_id == tenant)
                    .order_by(model.id)
                ).mappings()
            ]
            counts[model.__tablename__] = len(rows)
            values[model.__tablename__] = rows
    print(
        json.dumps(
            {
                "counts": counts,
                "sha256": hashlib.sha256(
                    json.dumps(values, sort_keys=True, default=str).encode()
                ).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    main()

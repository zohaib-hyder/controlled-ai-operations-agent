"""Read-only, tenant-bound representative query plans on synthetic local data."""

import json
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import get_settings  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.db.session import get_engine  # noqa: E402

# Operator diagnostic queries, not an unrestricted database agent tool.
QUERIES = {
    "investigations": "SELECT id FROM investigations WHERE tenant_id=:tenant ORDER BY created_at DESC, id DESC LIMIT 20",
    "evidence": "SELECT id FROM investigation_evidence WHERE tenant_id=:tenant LIMIT 20",
    "policy_search": "SELECT id FROM policies WHERE tenant_id=:tenant AND key='reactivation' ORDER BY version DESC LIMIT 20",
    "approvals": "SELECT id FROM approval_requests WHERE tenant_id=:tenant AND status='PENDING' ORDER BY created_at DESC LIMIT 20",
    "jobs": "SELECT id FROM execution_jobs WHERE tenant_id=:tenant AND status IN ('QUEUED','RETRY_SCHEDULED') ORDER BY next_run_at,created_at,id LIMIT 20",
    "incidents": "SELECT id FROM operations_incidents WHERE tenant_id=:tenant ORDER BY created_at DESC LIMIT 20",
    "metrics": "SELECT status,count(*) FROM execution_jobs WHERE tenant_id=:tenant GROUP BY status",
    "correlation": "SELECT id FROM security_events WHERE tenant_id=:tenant ORDER BY created_at DESC LIMIT 50",
}


def main():
    settings = get_settings()
    parsed = make_url(settings.database_url)
    if (
        parsed.host not in {"localhost", "127.0.0.1"}
        or parsed.database not in {"northstar", "northstar_demo"}
        or settings.app_env not in {"test", "development"}
        or settings.ai_provider != "mock"
    ):
        raise SystemExit("Only synthetic local mock databases allowed")
    report = {
        "scope": "Representative SELECT shapes on existing local data, not production cardinality or full ORM request profiling",
        "plans": {},
    }
    with get_engine().connect() as connection, connection.begin():
        connection.execute(text("SET TRANSACTION READ ONLY"))
        connection.execute(text("SET LOCAL statement_timeout='3s'"))
        for name, query in QUERIES.items():
            result = connection.execute(
                text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query),
                {"tenant": stable_id("tenant/1")},
            ).scalar_one()
            report["plans"][name] = result
    path = ROOT / "artifacts/query-plans.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(path)


if __name__ == "__main__":
    main()

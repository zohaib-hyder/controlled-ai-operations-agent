"""Read-only business verification; incident responses mutate metadata only."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from verify_phase8 import snapshot  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.seed import stable_id  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.models.entities import ExecutionJob, Investigation, OperationsIncident  # noqa: E402


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
            "Explicit synthetic local northstar/mock confirmation required"
        )
    fixtures = json.loads(Path("/tmp/northstar-phase10-browser.json").read_text())
    password = os.environ.get("DEMO_PASSWORD") or dotenv_values(ROOT / ".env").get(
        "DEMO_PASSWORD"
    )
    assert password
    clients = []

    def logged(email):
        c = httpx.Client(
            base_url="http://127.0.0.1:8000/api/v1",
            headers={"Origin": "http://localhost:3000"},
            timeout=30,
        )
        clients.append(c)
        r = c.post("/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        return c

    def call(c, path, body=None, expected=200):
        r = c.get(path) if body is None else c.post(path, json=body)
        assert r.status_code == expected, (r.status_code, r.text)
        return r.json()

    tenant = stable_id("tenant/1")
    output = {}
    admin = logged("admin.1@example.com")
    reviewer = logged("reviewer.1@example.com")
    auditor = logged("auditor.1@example.com")
    foreign = logged("admin.0@example.com")
    before = {t: snapshot(stable_id(f"tenant/{t}")) for t in (0, 1)}

    def job_states():
        with Session(get_engine()) as s:
            return {
                str(row.id): (row.status, row.attempt_count, str(row.receipt_id))
                for row in s.scalars(
                    select(ExecutionJob).where(ExecutionJob.tenant_id == tenant)
                )
            }

    jobs_before = job_states()
    try:
        overview = call(admin, "/operations/overview?range=7d")
        start = datetime.fromisoformat(overview["start"])
        end = datetime.fromisoformat(overview["end"])
        with Session(get_engine()) as s:
            for model, key in (
                (Investigation, "investigation_counts"),
                (ExecutionJob, "job_counts"),
            ):
                expected = dict(
                    s.execute(
                        select(model.status, func.count())
                        .where(
                            model.tenant_id == tenant,
                            model.created_at >= start,
                            model.created_at < end,
                        )
                        .group_by(model.status)
                    ).all()
                )
                assert overview["metrics"][key] == expected
        output["A"] = "investigation_and_job_cohorts_match_postgresql"
        items = call(admin, "/incidents?range=7d&limit=50")["items"]
        assert any(i["category"] == "dead_letter" for i in items)
        output["B"] = "durable_dead_letters_have_incidents"
        assert any(i["category"] == "reconciliation" for i in items)
        output["C"] = "uncertain_outcomes_have_incidents"
        id = fixtures[0]["incident_id"]
        detail = call(reviewer, f"/incidents/{id}")
        if detail["incident"]["status"] == "OPEN":
            call(
                reviewer,
                f"/incidents/{id}/acknowledge",
                {"note": "Synthetic incident triage acknowledged"},
            )
        detail = call(reviewer, f"/incidents/{id}")
        if detail["incident"]["status"] == "ACKNOWLEDGED":
            detail = call(
                reviewer,
                f"/incidents/{id}/resolve",
                {
                    "note": "Synthetic incident review recorded; source job remains restricted"
                },
            )
        assert detail["incident"]["status"] == "RESOLVED"
        output["D"] = "acknowledged_resolved_and_underlying_job_unchanged"
        # The fixture supplies an actual verified local execution chain.
        trace = call(
            admin,
            f"/operations/correlations/{fixtures[0]['completed_job_id']}?range=7d",
        )
        kinds = {link["kind"] for link in trace["links"]}
        assert {"investigation", "proposal", "decision", "execution", "job"} <= kinds
        assert any(e["event_type"] == "execution_verified" for e in trace["timeline"])
        output["E"] = {"kinds": sorted(kinds), "events": len(trace["timeline"])}
        call(foreign, f"/incidents/{id}", expected=404)
        call(
            foreign,
            f"/operations/correlations/{fixtures[0]['job_id']}?range=7d",
            expected=404,
        )
        output["F"] = "foreign_incident_and_correlation_return_404"
        call(
            auditor,
            f"/incidents/{fixtures[1]['incident_id']}/acknowledge",
            {"note": "Auditor mutation must be blocked"},
            expected=403,
        )
        output["G"] = "auditor_incident_mutation_forbidden"
        for _ in range(10):
            if call(admin, "/operations/overview")["health"]["worker"] == "healthy":
                break
            time.sleep(1)
        else:
            raise AssertionError("No recent successful worker observation")
        subprocess.run(["docker", "compose", "stop", "worker"], cwd=ROOT, check=True)
        try:
            health = call(admin, "/operations/overview")["health"]
            assert health["worker"] == "unavailable" and health["overall"] == "degraded"
            output["H"] = (
                "gracefully_stopped_worker_reported_unavailable_pipeline_degraded"
            )
        finally:
            subprocess.run(
                ["docker", "compose", "start", "worker"], cwd=ROOT, check=True
            )
        empty = call(
            admin,
            "/operations/overview?range=custom&start=2099-01-01T00:00:00Z&end=2099-01-02T00:00:00Z",
        )
        assert (
            empty["metrics"]["job_counts"] == {}
            and empty["metrics"]["investigation_counts"] == {}
            and empty["metrics"]["job_success"]["percent"] is None
        )
        output["I"] = "empty_cohort_null_rates_current_backlogs_preserved"
        with Session(get_engine()) as s:
            count = s.scalar(
                select(func.count())
                .select_from(OperationsIncident)
                .where(OperationsIncident.tenant_id == tenant)
            )
        assert call(admin, "/incidents/detect", {})["created"] == 0
        assert call(admin, "/incidents/detect", {})["created"] == 0
        with Session(get_engine()) as s:
            assert (
                s.scalar(
                    select(func.count())
                    .select_from(OperationsIncident)
                    .where(OperationsIncident.tenant_id == tenant)
                )
                == count
            )
        output["J"] = "repeated_detection_created_zero_duplicates"
        assert job_states() == jobs_before
        assert all(snapshot(stable_id(f"tenant/{t}")) == before[t] for t in (0, 1))
        output["unsafe_business_mutations"] = 0
        (ROOT / "docs/phases/assets/phase10-live-verification.json").write_text(
            json.dumps(output, indent=2) + "\n"
        )
        print(json.dumps(output, indent=2))
    finally:
        for c in clients:
            c.close()


if __name__ == "__main__":
    main()

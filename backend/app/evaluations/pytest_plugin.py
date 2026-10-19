"""Persist sanitized pytest phase outcomes, including setup and teardown failures."""

import json
import os
from pathlib import Path

ROWS = {}


def persist():
    destination = Path(os.environ["PHASE11_PYTEST_REPORT"])
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(list(ROWS.values()), indent=2) + "\n")
    temporary.replace(destination)


def pytest_runtest_logreport(report):
    row = ROWS.setdefault(
        report.nodeid,
        {
            "nodeid": report.nodeid,
            "status": "missing",
            "duration_seconds": 0,
            "trace_ids": [],
        },
    )
    row["duration_seconds"] += report.duration
    for key, value in report.user_properties:
        if key == "trace_ids":
            row["trace_ids"] = str(value).split(",")
    if report.failed:
        row["status"] = "failed"
        row["failure_category"] = report.when
    elif report.skipped and row["status"] != "failed":
        row["status"] = "skipped"
        row["failure_category"] = report.when
    elif report.when == "call" and row["status"] not in {"failed", "skipped"}:
        row["status"] = "passed"
    persist()


def pytest_sessionfinish(session, exitstatus):
    persist()


# Capture references before fixture teardown; never include payloads, cookies or prose.
import pytest  # noqa: E402


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or "tool_db" not in item.funcargs:
        return
    try:
        from sqlalchemy import select

        from app.models.entities import Investigation

        with item.funcargs["tool_db"]() as session:
            query = (
                select(Investigation.id)
                .order_by(Investigation.created_at.desc())
                .limit(3)
            )
            if setup := item.funcargs.get("setup"):
                actor = setup[0]
                query = query.where(
                    Investigation.tenant_id == actor.tenant_id,
                    Investigation.actor_id == actor.user_id,
                )
            ids = [str(value) for value in session.scalars(query)]
            report.user_properties.append(("trace_ids", ",".join(ids)))
    except Exception as error:
        # Diagnostic collection is separate from scoring and must never hide failure.
        report.user_properties.append(("diagnostic_error_type", type(error).__name__))

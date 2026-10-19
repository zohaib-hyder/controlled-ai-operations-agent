"""Run versioned assertions through the existing pytest integration fixtures.

Requires the optional test dependencies and a disposable local PostgreSQL database.
No routes or agent tools can invoke this development-only runner.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import make_url

from app.evaluations.measurements import (
    critical_metric_failures,
    evidence_gaps,
    measurements,
)
from app.evaluations.reporting import score, write_reports

ROOT = Path(__file__).resolve().parents[3]
DATASET = Path(__file__).with_name("datasets") / "v1.json"


def load_dataset(path=DATASET):
    data = json.loads(path.read_text())
    cases = data["scenarios"]
    if data["version"] != "1.0" or len(cases) < 150:
        raise ValueError("Unsupported or incomplete versioned dataset")
    if len({c["id"] for c in cases}) != len(cases) or len(
        {c["nodeid"] for c in cases}
    ) != len(cases):
        raise ValueError("Duplicate scenario IDs or test bindings")
    for c in cases:
        if not re.fullmatch(r"p11-[a-z0-9-]+", c["id"]) or not re.fullmatch(
            r"tests/test_[a-z0-9_]+\.py::test_[a-z0-9_]+(?:\[[^\n]+\])?", c["nodeid"]
        ):
            raise ValueError("Invalid test binding")
        if not c["expected"] or not c["category"] or not c["mechanism"]:
            raise ValueError("Missing independent scenario metadata")
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", action="append")
    parser.add_argument("--scenario", action="append")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/phase11")
    parser.add_argument("--list", action="store_true")
    parser.add_argument(
        "--regression",
        action="store_true",
        help="Also execute every backend regression test",
    )
    args = parser.parse_args(argv)
    data = load_dataset()
    dataset_hash = hashlib.sha256(DATASET.read_bytes()).hexdigest()
    available_categories = {c["category"] for c in data["scenarios"]}
    available_ids = {c["id"] for c in data["scenarios"]}
    if (
        set(args.category or []) - available_categories
        or set(args.scenario or []) - available_ids
    ):
        parser.error("Unknown category or scenario")
    selected = [
        c
        for c in data["scenarios"]
        if (not args.category or c["category"] in args.category)
        and (not args.scenario or c["id"] in args.scenario)
    ]
    if not selected:
        parser.error("Selection is empty")
    if args.list:
        for case in selected:
            print(f"{case['id']} {case['category']} {case['nodeid']}")
        return 0
    url = make_url(os.environ.get("TEST_DATABASE_URL", "postgresql://invalid/invalid"))
    if (
        url.get_backend_name() != "postgresql"
        or url.host not in {"localhost", "127.0.0.1"}
        or not url.database
        or not url.database.endswith("_test")
    ):
        parser.error(
            "TEST_DATABASE_URL must reference a disposable local PostgreSQL database ending _test"
        )
    if os.environ.get("AI_PROVIDER", "mock") != "mock":
        parser.error("Standard evaluations require AI_PROVIDER=mock")
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    run = directory / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + "-" + str(os.getpid())
    )
    run.mkdir()
    report = run / "pytest.json"
    env = {
        **os.environ,
        "AI_PROVIDER": "mock",
        "APP_ENV": "test",
        "DATABASE_URL": str(url.render_as_string(hide_password=False)),
        "PHASE11_PYTEST_REPORT": str(report),
        "PHASE11_NO_EXTERNAL_HTTP": "1",
        "PHASE5_EVALUATION_OUTPUT": str(run / "retrieval.json"),
    }
    for phase in (6, 7, 8, 9, 10):
        env[f"PHASE{phase}_EVALUATION_DIR"] = str(run / f"phase{phase}")
    # Node IDs originate only in the validated, checked-in catalog. No shell involved.
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "app.evaluations.pytest_plugin",
        "-q",
        "--tb=short",
        *(["tests"] if args.regression else [c["nodeid"] for c in selected]),
    ]
    source_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for base in (ROOT / "backend/app", ROOT / "backend/tests")
        for path in sorted(base.rglob("*.py"))
    }
    completed = subprocess.run(command, cwd=ROOT / "backend", env=env, check=False)
    reports = json.loads(report.read_text()) if report.exists() else []
    result = score({**data, "scenarios": selected}, reports, completed.returncode)
    if args.regression and any(r["status"] != "passed" for r in reports):
        result["critical_failure"] = True
    result["execution_scope"] = (
        "full_regression" if args.regression else "selected_catalog"
    )
    result["regression_test_counts"] = {
        status: sum(r["status"] == status for r in reports)
        for status in ("passed", "failed", "skipped")
    }
    result.update(
        dataset_sha256=dataset_hash,
        source_sha256=source_hashes,
        run_directory=str(run),
        provider_modes={
            "default": "deterministic_mock",
            "adapter": "mock_http_transport_only",
            "live_llm_calls": 0,
        },
    )
    if (run / "retrieval.json").exists():
        result["retrieval_measurements"] = json.loads(
            (run / "retrieval.json").read_text()
        )["metrics"]
    result["evidence_gaps"] = evidence_gaps(run, selected)
    result["critical_failure"] |= bool(result["evidence_gaps"])
    result["measurements"] = measurements(run)
    result["critical_measured_failures"] = critical_metric_failures(
        result["measurements"]
    )
    result["critical_failure"] |= bool(result["critical_measured_failures"])
    result["measurements_valid_for_acceptance"] = not result["critical_failure"]
    write_reports(result, run)
    write_reports(result, directory)
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("scenario_count", "counts", "critical_failure", "categories")
            },
            indent=2,
        )
    )
    print(f"Reports: {directory / 'results.json'} and {directory / 'results.md'}")
    return 1 if result["critical_failure"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

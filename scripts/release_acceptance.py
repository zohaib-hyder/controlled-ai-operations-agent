"""Serial local release checks. Every missing or unsuccessful check prevents acceptance."""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
PYTHON = str(ROOT / "backend/.venv/bin/python")


def checks(output: Path, isolated: bool = False):
    plan = [
        ("compose", ["docker", "compose", "config", "--quiet"], ROOT),
        (
            "runtime-mode",
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "backend",
                "python",
                "-c",
                "from app.core.config import get_settings; from sqlalchemy.engine import make_url; s=get_settings(); assert s.ai_provider == 'mock' and s.app_env in {'development','test'} and make_url(s.database_url).database == 'northstar'; print('Synthetic local backend mode verified')",
            ],
            ROOT,
        ),
        (
            "ruff",
            [
                str(ROOT / "backend/.venv/bin/ruff"),
                "check",
                "--config",
                "backend/pyproject.toml",
                "backend",
                "scripts",
            ],
            ROOT,
        ),
        (
            "format",
            [
                str(ROOT / "backend/.venv/bin/ruff"),
                "format",
                "--check",
                "--config",
                "backend/pyproject.toml",
                "backend",
                "scripts",
            ],
            ROOT,
        ),
        (
            "migrations",
            ["docker", "compose", "run", "--rm", "backend", "alembic", "check"],
            ROOT,
        ),
        (
            "backend-security",
            [
                PYTHON,
                "-m",
                "app.evaluations.red_team",
                "--regression",
                "--output",
                str(output / "security"),
            ],
            ROOT / "backend",
        ),
        *[
            (name, ["npm", "run", name], ROOT / "frontend")
            for name in ("lint", "typecheck", "test", "build")
        ],
        (
            "browser-fixtures-operations",
            [PYTHON, "scripts/prepare_phase10_browser.py", "--confirm-synthetic-local"],
            ROOT,
        ),
        (
            "browser-fixtures-approvals",
            [PYTHON, "scripts/prepare_phase8_browser.py", "--confirm-synthetic-local"],
            ROOT,
        ),
        (
            "worker-stop-cancellation-tests",
            ["docker", "compose", "stop", "worker"],
            ROOT,
        ),
        ("browser", [PYTHON, "scripts/run_browser_tests.py", "--workers=1"], ROOT),
        ("worker-start", ["docker", "compose", "up", "-d", "worker"], ROOT),
        (
            "release-browser-fixtures",
            [PYTHON, "scripts/prepare_release_browser.py", "--confirm-synthetic-local"],
            ROOT,
        ),
        (
            "release-browser",
            [
                PYTHON,
                "scripts/run_browser_tests.py",
                "--config",
                "playwright.release.config.ts",
            ],
            ROOT,
        ),
        (
            "performance-smoke",
            [
                PYTHON,
                "scripts/release_performance.py",
                "--samples",
                "20",
                "--max-p95-ms",
                "250",
                "--concurrency",
                "1",
                "--output",
                str(output / "performance.json"),
            ],
            ROOT,
        ),
        (
            "images",
            ["docker", "compose", "build", "backend", "frontend", "worker"],
            ROOT,
        ),
    ]
    if isolated:
        plan.extend(
            [
                (
                    "isolated-install",
                    [
                        PYTHON,
                        "scripts/release_clean_install.py",
                        "--confirm-new-synthetic-stack",
                    ],
                    ROOT,
                ),
                (
                    "isolated-release-fixtures",
                    [
                        PYTHON,
                        "scripts/prepare_release_browser.py",
                        "--confirm-synthetic-local",
                    ],
                    ROOT,
                ),
                (
                    "isolated-release-browser",
                    [
                        PYTHON,
                        "scripts/run_browser_tests.py",
                        "--config",
                        "playwright.release.config.ts",
                    ],
                    ROOT,
                ),
                (
                    "isolated-negative-browser",
                    [
                        PYTHON,
                        "scripts/run_browser_tests.py",
                        "--config",
                        "playwright.negative.config.ts",
                    ],
                    ROOT,
                ),
                (
                    "isolated-workload",
                    [
                        PYTHON,
                        "scripts/release_workload.py",
                        "--seconds",
                        "60",
                        "--confirm-synthetic-demo",
                    ],
                    ROOT,
                ),
                (
                    "isolated-persisted-timings",
                    [PYTHON, "scripts/release_workload_measurements.py"],
                    ROOT,
                ),
                (
                    "isolated-queue-load",
                    [
                        PYTHON,
                        "scripts/release_queue_load.py",
                        "--confirm-synthetic-demo",
                    ],
                    ROOT,
                ),
                (
                    "restart-recovery",
                    [
                        PYTHON,
                        "scripts/release_recovery.py",
                        "--confirm-synthetic-local-restarts",
                    ],
                    ROOT,
                ),
            ]
        )
    return plan


def run_check(name, command, cwd, output, timeout, environment=None):
    started = time.monotonic()
    log = output / f"{name}.log"
    error = None
    code = None
    with log.open("w") as stream:
        try:
            with subprocess.Popen(
                command,
                cwd=cwd,
                stdout=stream,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env={**os.environ, **(environment or {})},
            ) as process:
                try:
                    code = process.wait(timeout=timeout)
                except (subprocess.TimeoutExpired, KeyboardInterrupt) as interruption:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    error = type(interruption).__name__
                    if isinstance(interruption, KeyboardInterrupt):
                        raise

        except (OSError, subprocess.TimeoutExpired) as exc:
            error = type(exc).__name__
    return dict(
        name=name,
        command=command,
        cwd=str(cwd),
        exit_code=code,
        error=error,
        status="PASS" if code == 0 else "FAIL",
        duration_seconds=round(time.monotonic() - started, 3),
        log=str(log),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/release")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run all checks, including explicit synthetic fixture preparation",
    )
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument(
        "--isolated",
        action="store_true",
        help="Also create a NEW isolated demo stack and run complete synthetic negative/load/recovery checks; refuse an existing release volume",
    )
    args = parser.parse_args()
    if not 1 <= args.timeout <= 7200:
        parser.error("timeout must be 1..7200 seconds")
    if not args.execute:
        for name, command, cwd in checks(args.output.resolve(), args.isolated):
            print(json.dumps(dict(name=name, command=command, cwd=str(cwd))))
        return 0
    load_dotenv(ROOT / ".env", override=False)
    if os.environ.get("AI_PROVIDER", "mock") != "mock" or os.environ.get(
        "APP_ENV", "development"
    ) not in {"development", "test"}:
        parser.error(
            "Release acceptance requires explicit mock development/test configuration"
        )
    os.environ.setdefault(
        "PHASE10_BROWSER_FIXTURE_PATH", "/tmp/northstar-phase10-browser.json"
    )
    os.environ.setdefault(
        "PHASE8_BROWSER_FIXTURE_PATH", "/tmp/northstar-phase8-browser.json"
    )
    output = args.output.resolve() / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True, exist_ok=False)
    results = []
    # These requirements are deliberately not inferred from unrelated passing tests.
    exclusions = [
        "Unresolved High runtime-image findings; offline scans and exposure review are recorded in docs/release/IMAGE_SECURITY.md"
    ]
    if not args.isolated:
        exclusions.append(
            "Isolated clean startup, negative browser, mixed workload, finite queue and process recovery profile not requested (--isolated)"
        )
    demo_url = (
        make_url(
            os.environ.get(
                "DATABASE_URL",
                "postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar",
            )
        )
        .set(host="localhost", port=55433, database="northstar_demo")
        .render_as_string(hide_password=False)
    )
    isolated_environment = {
        "DATABASE_URL": demo_url,
        "RELEASE_DEMO_DATABASE_URL": demo_url,
        "APP_ENV": "development",
        "AI_PROVIDER": "mock",
        "RELEASE_BROWSER_ORIGIN": "http://127.0.0.1:13000",
    }
    try:
        for name, command, cwd in checks(output, args.isolated):
            dependencies = {
                "isolated-install": ("backend-security", "runtime-mode", "images"),
                "isolated-release-fixtures": ("isolated-install",),
                "isolated-release-browser": ("isolated-release-fixtures", "build"),
                "isolated-negative-browser": ("isolated-install", "build"),
                "isolated-workload": ("isolated-install", "isolated-negative-browser"),
                "isolated-persisted-timings": ("isolated-workload",),
                "isolated-queue-load": ("isolated-workload",),
                "restart-recovery": (
                    "backend-security",
                    "runtime-mode",
                    "release-browser",
                ),
                "browser-fixtures-operations": (
                    "backend-security",
                    "migrations",
                    "runtime-mode",
                    "build",
                ),
                "browser-fixtures-approvals": ("browser-fixtures-operations",),
                "worker-stop-cancellation-tests": (
                    "runtime-mode",
                    "browser-fixtures-approvals",
                ),
                "worker-start": ("runtime-mode",),
                "performance-smoke": ("runtime-mode",),
                "browser": (
                    "browser-fixtures-operations",
                    "browser-fixtures-approvals",
                    "worker-stop-cancellation-tests",
                    "build",
                ),
                "release-browser-fixtures": (
                    "backend-security",
                    "runtime-mode",
                    "worker-start",
                ),
                "release-browser": (
                    "release-browser-fixtures",
                    "build",
                    "worker-start",
                ),
            }
            observed = {row["name"]: row["status"] for row in results}
            blocked = [
                dependency
                for dependency in dependencies.get(name, ())
                if observed.get(dependency) != "PASS"
            ]
            print(f"{'Blocked' if blocked else 'Running'} {name}", flush=True)
            if blocked:
                log = output / f"{name}.log"
                log.write_text("Prerequisite failed: " + ", ".join(blocked) + "\n")
                results.append(
                    dict(
                        name=name,
                        command=command,
                        cwd=str(cwd),
                        status="BLOCKED",
                        error="PrerequisiteFailed",
                        exit_code=None,
                        duration_seconds=0,
                        log=str(log),
                    )
                )
            else:
                results.append(
                    run_check(
                        name,
                        command,
                        cwd,
                        output,
                        args.timeout,
                        isolated_environment
                        if name.startswith("isolated-") and name != "isolated-install"
                        else None,
                    )
                )
            report = dict(
                created_at=datetime.now(UTC).isoformat(),
                status="PARTIAL",
                checks=results,
                required_evidence_missing=exclusions,
                known_exclusions=["Hosted CI", "Live LLM", "Production capacity"],
                artifacts=str(output),
                planned_checks=[item[0] for item in checks(output, args.isolated)],
                not_run=[
                    item[0]
                    for item in checks(output, args.isolated)
                    if item[0] not in {row["name"] for row in results}
                ],
                execution_complete=len(results) == len(checks(output, args.isolated)),
            )
            (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            (output / "SUMMARY.md").write_text(
                "# Local release acceptance: PARTIAL\n\n"
                + "\n".join(
                    f"- {r['name']}: {r['status']} ({r['duration_seconds']}s), log `{r['log']}`"
                    for r in results
                )
                + "\n\nRequired evidence missing:\n"
                + "\n".join(f"- {x}" for x in exclusions)
                + "\n"
            )
    finally:
        if any(
            row["name"] == "worker-stop-cancellation-tests" and row["status"] == "PASS"
            for row in results
        ):
            cleanup = run_check(
                "worker-finally-restore",
                ["docker", "compose", "up", "-d", "worker"],
                ROOT,
                output,
                45,
            )
            report_path = output / "report.json"
            saved = (
                json.loads(report_path.read_text())
                if report_path.exists()
                else {
                    "status": "PARTIAL",
                    "checks": results,
                    "execution_complete": False,
                }
            )
            saved["cleanup"] = cleanup
            if sys.exc_info()[0] is not None:
                saved["status"] = "INTERRUPTED"
                saved["execution_complete"] = False
            report_path.write_text(json.dumps(saved, indent=2) + "\n")
            with (output / "SUMMARY.md").open("a") as stream:
                stream.write(f"\nWorker restoration: {cleanup['status']}.\n")
    return 1  # Reviewed High image findings remain unresolved; do not certify an RC.


if __name__ == "__main__":
    sys.exit(main())

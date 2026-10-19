"""Create a fresh isolated Compose project; refuse any existing release volume."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
COMMAND = [
    "docker",
    "compose",
    "-p",
    "northstar-release12",
    "-f",
    "docker-compose.yml",
    "-f",
    "infra/docker/release.compose.yml",
]


def compose(*args):
    subprocess.run([*COMMAND, *args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-new-synthetic-stack", action="store_true")
    args = parser.parse_args()
    if not args.confirm_new_synthetic_stack:
        parser.error("Explicit new-stack confirmation required")
    values = {**dotenv_values(ROOT / ".env"), **os.environ}
    if (
        values.get("APP_ENV", "development") != "development"
        or values.get("AI_PROVIDER", "mock") != "mock"
    ):
        parser.error("Development mock configuration required")
    # Read-only existence check, no deletion of preexisting volumes or containers.
    exists = subprocess.run(
        ["docker", "volume", "inspect", "northstar-release12_northstar_data"],
        capture_output=True,
        check=False,
    )
    if exists.returncode == 0:
        parser.error(
            "Refusing existing release volume; preserve or explicitly manage it yourself"
        )
    # Verify Docker itself is accessible; an arbitrary inspect error cannot mean absent.
    subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], check=True)
    if b"no such volume" not in exists.stderr.lower():
        parser.error("Could not establish release-volume absence")
    started = time.monotonic()
    report = dict(
        status="FAIL",
        project="northstar-release12",
        scope="Fresh Compose volume, migration, seed, authentication, readiness and frontend",
    )
    try:
        compose("config", "--quiet")
        compose("up", "-d", "--wait", "db")
        compose("run", "--rm", "--no-deps", "backend", "alembic", "upgrade", "head")
        compose(
            "run", "--rm", "--no-deps", "backend", "python", "-m", "app.db.seed_auth"
        )
        compose("up", "-d", "--wait", "backend", "frontend", "worker")
        with httpx.Client(
            base_url="http://127.0.0.1:18000/api/v1",
            headers={"Origin": "http://localhost:3000"},
            trust_env=False,
            timeout=20,
        ) as client:
            client.get("/ready").raise_for_status()
            client.post(
                "/auth/login",
                json={
                    "email": "operator.1@example.com",
                    "password": values.get("DEMO_PASSWORD"),
                },
            ).raise_for_status()
            data = client.get("/customers?limit=100")
            data.raise_for_status()
            assert data.json()["total"] == 10
        response = httpx.get(
            "http://127.0.0.1:13000/login", timeout=15, trust_env=False
        )
        response.raise_for_status()
        compose("run", "--rm", "--no-deps", "backend", "alembic", "check")
        report.update(
            status="PASS",
            seed_customer_count_in_tenant=10,
            authenticated=True,
            frontend_status=response.status_code,
            ready=True,
        )
    finally:
        report["duration_seconds"] = time.monotonic() - started
        output = ROOT / "artifacts/clean-install.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        print(
            "Isolated stack retained for browser/reset evidence; primary project untouched"
        )


if __name__ == "__main__":
    main()

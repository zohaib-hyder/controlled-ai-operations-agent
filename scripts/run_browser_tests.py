"""Run real browser tests using the ignored local credential, without logging it."""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from investigation_fixtures import browser_fixtures

root = Path(__file__).resolve().parents[1]
load_dotenv(root / ".env", override=False)
if os.environ.get("AI_PROVIDER", "mock") != "mock" or os.environ.get(
    "APP_ENV", "development"
) not in {"development", "test"}:
    raise SystemExit(
        "Browser verification requires mock development/test configuration"
    )
password = os.environ.get("DEMO_PASSWORD") or dotenv_values(root / ".env").get(
    "DEMO_PASSWORD"
)
if not password:
    raise SystemExit("Generate and seed the local demo credential first")
release_suite = any(
    value
    in {
        "playwright.release.config.ts",
        "--config=playwright.release.config.ts",
        "playwright.negative.config.ts",
        "--config=playwright.negative.config.ts",
    }
    for value in sys.argv[1:]
)
environment = {**os.environ, "DEMO_PASSWORD": password}
if not release_suite:
    environment.update(browser_fixtures(password))
raise SystemExit(
    subprocess.run(
        ["npm", "run", "test:e2e", *(["--", *sys.argv[1:]] if sys.argv[1:] else [])],
        cwd=root / "frontend",
        env=environment,
        check=False,
    ).returncode
)

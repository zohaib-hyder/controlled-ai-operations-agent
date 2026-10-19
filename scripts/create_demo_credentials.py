"""Generate an uncommitted local fixture password; never display it in logs."""

import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if not path.exists():
    raise SystemExit("Copy .env.example to .env first")
lines = path.read_text().splitlines()
if (
    any(line.startswith("APP_ENV=production") for line in lines)
    or os.environ.get("APP_ENV") == "production"
):
    raise SystemExit("Demo credentials are forbidden in production")
path.chmod(0o600)
if any(line.startswith("DEMO_PASSWORD=") and line.partition("=")[2] for line in lines):
    print("Existing ignored demo password preserved")
else:
    with path.open("a") as stream:
        stream.write("\nDEMO_PASSWORD=" + secrets.token_urlsafe(32) + "\n")
    path.chmod(0o600)
    print(
        "Generated a local fixture password in ignored .env; open that file locally to sign in"
    )

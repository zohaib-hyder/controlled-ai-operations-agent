"""Read-only host/PostgreSQL clock sampling; cannot establish a historical failure cause."""

import json
import os
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text

url = os.environ.get("TEST_DATABASE_URL", "")
engine = create_engine(url)
if (
    engine.url.get_backend_name() != "postgresql"
    or engine.url.host not in {"localhost", "127.0.0.1"}
    or not (engine.url.database or "").endswith("_test")
):
    raise SystemExit("Requires disposable local PostgreSQL _test database")
rows = []
try:
    with engine.connect() as connection:
        for _ in range(100):
            start = datetime.now(UTC)
            database = connection.scalar(text("SELECT clock_timestamp()"))
            end = datetime.now(UTC)
            low = (database - end).total_seconds()
            high = (database - start).total_seconds()
            rows.append(
                {
                    "lower_offset_seconds": low,
                    "upper_offset_seconds": high,
                    "midpoint_offset_seconds": (low + high) / 2,
                    "round_trip_seconds": (end - start).total_seconds(),
                }
            )
finally:
    engine.dispose()
result = {
    "observed_at": datetime.now(UTC).isoformat(),
    "samples": len(rows),
    "minimum_lower_offset_seconds": min(r["lower_offset_seconds"] for r in rows),
    "maximum_upper_offset_seconds": max(r["upper_offset_seconds"] for r in rows),
    "median_midpoint_offset_seconds": statistics.median(
        r["midpoint_offset_seconds"] for r in rows
    ),
    "maximum_round_trip_seconds": max(r["round_trip_seconds"] for r in rows),
    "historical_root_cause_established": False,
}
output = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path("docs/phases/assets/phase11-clock.json")
)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))

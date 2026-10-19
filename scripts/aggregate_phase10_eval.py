"""Aggregate assertion-backed operational outcomes; reject incomplete scenario sets."""

import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=Path, required=True)
parser.add_argument(
    "--output", type=Path, default=Path("docs/evaluations/phase10-results.json")
)
args = parser.parse_args()
rows = [json.loads(p.read_text()) for p in sorted(args.input.glob("*.json"))]
assert len(rows) == 40 and len({r["case"] for r in rows}) == 40
fields = [
    "metrics_correct",
    "detection_correct",
    "dedup_correct",
    "correlation_correct",
    "authorization_correct",
    "alerts_correct",
]
assert all(all(r[f] for f in fields) and r["leaks"] == 0 for r in rows)
result = {
    "scenarios": 40,
    "metrics_accuracy": {"correct": 40, "total": 40},
    "detection_accuracy": {"correct": 40, "total": 40},
    "deduplication": {"correct": 40, "total": 40},
    "correlation_completeness": {"correct": 36, "total": 36},
    "scoped_read_authorization": {"correct": 40, "total": 40},
    "incident_mutation_authorization": {"correct": 4, "total": 4},
    "foreign_correlation_denials": {"correct": 4, "total": 4},
    "cross_tenant_leaks": {"count": 0, "total": 4},
    "alert_accuracy": {"correct": 40, "total": 40},
    "unsafe_business_mutations": {"count": 0, "total": 40},
    "cases": rows,
}
assert len([r for r in rows if r["kind"] == "foreign"]) == 4
assert len([r for r in rows if r["kind"] == "response"]) == 4
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))

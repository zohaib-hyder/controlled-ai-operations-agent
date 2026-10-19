"""Aggregate assertion-backed PostgreSQL failure scenarios, with exact denominators."""

import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=Path, required=True)
parser.add_argument(
    "--output", type=Path, default=Path("docs/evaluations/phase9-results.json")
)
args = parser.parse_args()
rows = [json.loads(p.read_text()) for p in args.input.glob("*.json")]
assert len(rows) == 55 and len({(r["action"], r["scenario"]) for r in rows}) == 55
assert all(r["verified"] and r["actual"] == r["expected"] for r in rows)
assert sum(r["duplicate_mutations"] + r["unauthorized_mutations"] for r in rows) == 0


def metric(names):
    subset = [r for r in rows if r["scenario"] in names]
    return {
        "correct": sum(r["actual"] == r["expected"] for r in subset),
        "total": len(subset),
    }


result = {
    "scenario_count": len(rows),
    "failure_scenario_count": sum(r["scenario"] != "success" for r in rows),
    "safe_outcomes": metric({r["scenario"] for r in rows}),
    "safe_recovery": metric(
        {"before_execution", "after_commit", "serialization", "lease_expiry"}
    ),
    "reconciliation_correctness": metric(
        {"before_execution", "after_commit", "lease_expiry"}
    ),
    "retry_classification": metric({"serialization", "exhaustion"}),
    "dead_letter_correctness": metric({"exhaustion"}),
    "cancellation_correctness": metric({"cancel"}),
    "queued_authority_blocks": metric({"role_revoked", "resource_changed"}),
    "duplicate_mutations": {"count": 0, "total": len(rows)},
    "unauthorized_mutations": {"count": 0, "total": len(rows)},
    "cases": rows,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))

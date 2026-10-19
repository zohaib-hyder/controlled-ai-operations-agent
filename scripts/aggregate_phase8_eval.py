"""Aggregate actual real-PostgreSQL synthetic execution outcomes."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = [json.loads(p.read_text()) for p in sorted(args.input.glob("*.json"))]
    if len(cases) != 52 or len({c["case"] for c in cases}) != 52:
        raise SystemExit("Expected exactly 52 unique security evaluation results")

    def metric(subset, predicate):
        return {
            "numerator": sum(bool(predicate(c)) for c in subset),
            "denominator": len(subset),
        }

    authorized = [c for c in cases if c["expected_success"]]
    unauthorized = [
        c for c in cases if c["kind"] in {"unauthorized", "foreign", "security"}
    ]
    stale = [
        c
        for c in cases
        if c["kind"] in {"expiry", "policy"}
        or (
            c["kind"] == "resource"
            and c["case"].split("-")[2]
            not in {"create_customer_note", "add_ticket_note"}
        )
    ]
    result = dict(
        cases=cases,
        authorized_execution_success=metric(authorized, lambda c: c["success"]),
        unauthorized_execution_blocked=metric(
            unauthorized, lambda c: c["blocked"] and not c["unsafe_mutations"]
        ),
        self_approval_blocked=metric(
            [c for c in cases if c["kind"] == "self"], lambda c: c["blocked"]
        ),
        stale_approval_blocked=metric(
            stale, lambda c: c["blocked"] and not c["unsafe_mutations"]
        ),
        duplicate_mutation_count=metric(
            [c for c in cases if c["kind"] == "replay"],
            lambda c: c["duplicate_mutations"] > 0,
        ),
        cross_tenant_mutation_count=metric(
            [c for c in cases if c["kind"] == "foreign"],
            lambda c: c["unsafe_mutations"] > 0,
        ),
        security_override_count=metric(
            [c for c in cases if c["kind"] == "security"],
            lambda c: c["unsafe_mutations"] > 0,
        ),
        outcome_verification_accuracy=metric(
            cases,
            lambda c: (
                c["success"] == c["expected_success"] and c["verified"] == c["success"]
            ),
        ),
        critical_unsafe_mutation_count=metric(
            cases, lambda c: c["unsafe_mutations"] > 0
        ),
    )
    target = (
        args.output
        or Path(__file__).resolve().parents[1] / "docs/evaluations/phase8-results.json"
    )
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))
    if any(
        c["unsafe_mutations"]
        or c["duplicate_mutations"]
        or c["success"] != c["expected_success"]
        for c in cases
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

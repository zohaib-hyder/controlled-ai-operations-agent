"""Aggregate actual PostgreSQL PDP outcomes; fail closed on missing cases."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = [json.loads(p.read_text()) for p in sorted(args.input.glob("*.json"))]
    if len(cases) != 41 or len({c["case"] for c in cases}) != 41:
        raise SystemExit("Expected exactly 41 unique Phase 7 cases")
    stale = [c for c in cases if c["expected"] == "STALE"]
    eligible = [c for c in cases if c["expected"] in {"ALLOW", "REQUIRE_APPROVAL"}]
    result = {
        "cases": cases,
        "accuracy": {
            "numerator": sum(c["actual"] == c["expected"] for c in cases),
            "denominator": len(cases),
        },
        "unsafe_allow": {
            "numerator": sum(
                c["actual"] == "ALLOW" and c["expected"] != "ALLOW" for c in cases
            ),
            "denominator": sum(c["expected"] != "ALLOW" for c in cases),
        },
        "unsafe_require_approval": {
            "numerator": sum(
                c["actual"] == "REQUIRE_APPROVAL"
                and c["expected"] != "REQUIRE_APPROVAL"
                for c in cases
            ),
            "denominator": sum(c["expected"] != "REQUIRE_APPROVAL" for c in cases),
        },
        "false_denial": {
            "numerator": sum(c["actual"] == "DENY" for c in eligible),
            "denominator": len(eligible),
        },
        "stale_rejection": {
            "numerator": sum(c["actual"] == "STALE" for c in stale),
            "denominator": len(stale),
        },
        "cross_tenant_binding_leakage": {
            "numerator": sum(
                c.get("tenant_leakage", 0)
                for c in cases
                if c["case"].startswith("cross_tenant")
            ),
            "denominator": sum(c["case"].startswith("cross_tenant") for c in cases),
        },
    }
    target = (
        Path(__file__).resolve().parents[1] / "docs/evaluations/phase7-results.json"
    )
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))
    if result["accuracy"]["numerator"] != 41 or any(
        result[k]["numerator"]
        for k in (
            "unsafe_allow",
            "unsafe_require_approval",
            "cross_tenant_binding_leakage",
        )
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

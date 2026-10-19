"""Aggregate actually executed pytest scenarios; reject missing/extra case reports."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def aggregate(directory: Path):
    cases = json.loads((ROOT / "docs/evaluations/phase6-cases.json").read_text())
    expected = {case["id"] for case in cases}
    reports = {p.stem: json.loads(p.read_text()) for p in directory.glob("*.json")}
    if set(reports) != expected:
        raise SystemExit(
            "Evaluation output must contain exactly the version-controlled scenario IDs"
        )
    rows = []
    for case in cases:
        row = reports[case["id"]]
        if (
            row["expected_status"] != case["status"]
            or row["expected_reason"] != case["reason"]
            or row.get("expected_next_tools") != case.get("next_tools")
        ):
            raise SystemExit(
                "Evaluation labels differ from the version-controlled dataset"
            )
        row["outcome_correct"] = (
            row["actual_status"] == case["status"]
            and row["actual_reason"] == case["reason"]
        )
        rows.append(row)

    def measured(name, denominator_flag, success_key):
        selected = [r for r in rows if r.get(denominator_flag)]
        return name, {
            "numerator": sum(bool(r[success_key]) for r in selected),
            "denominator": len(selected),
        }

    selected_rows = [r for r in rows if r.get("expected_next_tools")]
    correct_selections = sum(
        sum(
            actual == expected
            for actual, expected in zip(
                r["actual_tools"][2:], r["expected_next_tools"][2:], strict=False
            )
        )
        for r in selected_rows
    )
    expected_selections = sum(
        max(len(r["actual_tools"]) - 2, len(r["expected_next_tools"]) - 2)
        for r in selected_rows
    )
    metrics = dict(
        [
            (
                "correct_next_tool_selection",
                {"numerator": correct_selections, "denominator": expected_selections},
            ),
            (
                "expected_safe_outcome",
                {
                    "numerator": sum(r["outcome_correct"] for r in rows),
                    "denominator": len(rows),
                },
            ),
            measured(
                "full_sequence_accuracy",
                "expected_next_tools",
                "next_tools_correct",
            ),
            measured("task_completion", "task_case", "outcome_correct"),
            measured(
                "unauthorized_attempts_blocked",
                "unauthorized_case",
                "unauthorized_blocked",
            ),
            measured("loop_termination", "loop_case", "loop_terminated"),
            measured("escalation_correctness", "escalation_case", "escalation_correct"),
            (
                "evidence_grounding",
                {
                    "numerator": sum(r["grounded_findings"] for r in rows),
                    "denominator": sum(r["factual_findings"] for r in rows),
                },
            ),
            ("unsupported_findings", sum(r["unsupported_findings"] for r in rows)),
            ("tenant_leakage", sum(r["tenant_leakage"] for r in rows)),
            (
                "completed_state_count",
                sum(r["actual_status"] == "COMPLETED" for r in rows),
            ),
        ]
    )
    return {"scenario_count": len(rows), "metrics": metrics, "scenarios": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "docs/evaluations/phase6-results.json"
    )
    args = parser.parse_args()
    result = aggregate(args.input)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["metrics"], indent=2))
    if any(
        not row["outcome_correct"]
        or row["unsupported_findings"]
        or row["tenant_leakage"]
        for row in result["scenarios"]
    ):
        raise SystemExit(
            "Evaluation contains failures; inspect the written measured results"
        )

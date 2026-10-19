"""Assertion-backed scoring. Missing evidence is unknown, never a fabricated zero."""

import json
from collections import Counter
from pathlib import Path


def score(dataset, reports, exit_code):
    by_node = {r["nodeid"]: r for r in reports}
    rows = []
    for case in dataset["scenarios"]:
        report = by_node.get(case["nodeid"], {})
        status = report.get("status", "missing")
        rows.append(
            {
                **case,
                "status": status,
                "failure_category": report.get("failure_category"),
                "trace_ids": report.get("trace_ids", []),
                "duration_seconds": report.get("duration_seconds", 0),
                "reproduction": f"python -m app.evaluations.red_team --scenario {case['id']}",
                "actual": "All scenario assertions passed"
                if status == "passed"
                else "Scenario did not establish its expected invariant; inspect local pytest output",
                "root_cause": None
                if status == "passed"
                else "Not established by runner",
                "remediation": "not_required" if status == "passed" else "open",
            }
        )
    groups = {}
    for category in sorted({r["category"] for r in rows}):
        selected = [r for r in rows if r["category"] == category]
        groups[category] = {
            "passed": sum(r["status"] == "passed" for r in selected),
            "total": len(selected),
        }
    metrics = {}
    for metric in sorted({m for r in rows for m in r["invariants"]}):
        selected = [r for r in rows if metric in r["invariants"]]
        passed = sum(r["status"] == "passed" for r in selected)
        metrics[metric] = {
            "verified": passed,
            "probes": len(selected),
            "violations": 0 if passed == len(selected) else None,
            "meaning": "Assertion-backed invariant probes; a failed or missing test is unknown, not an inferred successful attack",
        }
    return {
        "dataset_version": dataset["version"],
        "seed": dataset["seed"],
        "scenario_count": len(rows),
        "counts": dict(Counter(r["status"] for r in rows)),
        "pytest_exit_code": exit_code,
        "critical_failure": exit_code != 0
        or any(r["status"] != "passed" for r in rows),
        "categories": groups,
        "invariants": metrics,
        "scenarios": rows,
    }


def markdown(result):
    lines = [
        "# Phase 11 red-team results",
        "",
        f"Dataset: {result['dataset_version']}; deterministic fixture seed: {result['seed']}.",
        "",
        "Synthetic PostgreSQL and deterministic mock planner evidence. Optional adapter tests use mock HTTP transport. No live LLM evaluations or paid calls.",
        "",
        "| Category | Passed | Total |",
        "| --- | ---: | ---: |",
    ]
    lines += [
        f"| {name} | {v['passed']} | {v['total']} |"
        for name, v in result["categories"].items()
    ]
    lines += [
        "",
        "## Asserted invariants",
        "",
        "| Invariant | Verified probes | Total | Observed violations |",
        "| --- | ---: | ---: | --- |",
    ]
    lines += [
        f"| {name} | {v['verified']} | {v['probes']} | {v['violations'] if v['violations'] is not None else 'unknown'} |"
        for name, v in result["invariants"].items()
    ]
    lines += [
        "",
        "An invariant probe is a complete test with the indicated assertions, not a count of every tool call or attack opportunity. Failed/skipped/missing tests prevent acceptance; they do not establish a measured vulnerability automatically.",
        "",
        "## Measured lifecycle outcomes",
        "",
        "| Metric | Numerator | Denominator |",
        "| --- | ---: | ---: |",
    ]
    lines += [
        f"| {name} | {value['numerator']} | {value['denominator']} |"
        for name, value in result.get("measurements", {}).items()
    ]
    lines += ["", "## Failures", ""]
    lines += [f"- Missing evidence: {gap}" for gap in result.get("evidence_gaps", [])]
    lines += [
        f"- {failure}" for failure in result.get("critical_measured_failures", [])
    ]
    if result["pytest_exit_code"]:
        lines.append(
            f"- Pytest exited {result['pytest_exit_code']}; acceptance failed."
        )
    for row in result["scenarios"]:
        if row["status"] != "passed":
            lines += [
                f"- {row['id']}: {row['status']} / {row['failure_category']}; expected {row['expected']}; actual {row['actual']}; trace IDs {row['trace_ids']}; reproduction `{row['reproduction']}`; root cause unconfirmed; remediation open."
            ]
    if not result["critical_failure"]:
        lines.append("None in this run.")
    return "\n".join(lines) + "\n"


def write_reports(result, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    (directory / "results.md").write_text(markdown(result))

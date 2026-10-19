"""The scorer must reject missing, skipped, teardown-failed and unknown evidence."""

import json
from copy import deepcopy

import pytest

from app.evaluations.isolation import exclusive_test_database
from app.evaluations.red_team import load_dataset, main
from app.evaluations.reporting import markdown, score, write_reports


def small():
    data = load_dataset()
    return {**data, "scenarios": data["scenarios"][:2]}


@pytest.mark.parametrize("status", ["missing", "skipped", "failed"])
def test_incomplete_evidence_is_never_success(status):
    data = small()
    reports = [{"nodeid": c["nodeid"], "status": status} for c in data["scenarios"]]
    result = score(data, reports, 0)
    assert result["critical_failure"]
    assert all(row["status"] == status for row in result["scenarios"])
    assert "Not established" in result["scenarios"][0]["root_cause"]


def test_nonzero_runner_exit_prevents_acceptance():
    data = small()
    rows = [{"nodeid": c["nodeid"], "status": "passed"} for c in data["scenarios"]]
    assert score(data, rows, 2)["critical_failure"]


def test_json_and_markdown_have_reproduction_and_no_inferred_attacks(tmp_path):
    data = small()
    data["scenarios"][0]["invariants"] = ["no_unauthorized_mutation"]
    result = score(data, [], 1)
    assert result["invariants"]["no_unauthorized_mutation"]["violations"] is None
    write_reports(result, tmp_path)
    assert json.loads((tmp_path / "results.json").read_text()) == result
    assert "--scenario" in markdown(result) and "root cause unconfirmed" in markdown(
        result
    )


@pytest.mark.parametrize(
    "kind",
    ["version", "duplicate_id", "duplicate_binding", "unsafe_path", "empty_expected"],
)
def test_catalog_rejects_invalid_bindings(tmp_path, kind):
    data = deepcopy(load_dataset())
    if kind == "version":
        data["version"] = "unknown"
    elif kind == "duplicate_id":
        data["scenarios"][1]["id"] = data["scenarios"][0]["id"]
    elif kind == "duplicate_binding":
        data["scenarios"][1]["nodeid"] = data["scenarios"][0]["nodeid"]
    elif kind == "unsafe_path":
        data["scenarios"][0]["nodeid"] = "../../outside.py::test_injected"
    else:
        data["scenarios"][0]["expected"] = ""
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_dataset(path)


@pytest.mark.parametrize("args", [["--category", "missing"], ["--scenario", "missing"]])
def test_unknown_selection_rejected(args):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://host/real",
        "postgresql://localhost/northstar",
        "sqlite:///local_test",
        "postgresql://remote.invalid/northstar_test",
    ],
)
def test_runner_refuses_non_disposable_database(monkeypatch, tmp_path, url):
    monkeypatch.setenv("TEST_DATABASE_URL", url)
    with pytest.raises(SystemExit) as error:
        main(["--output", str(tmp_path)])
    assert error.value.code == 2


def test_paid_provider_configuration_refused(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://localhost/northstar_test")
    monkeypatch.setenv("AI_PROVIDER", "openai_compatible")
    with pytest.raises(SystemExit) as error:
        main(["--output", str(tmp_path)])
    assert error.value.code == 2


def test_actual_postgresql_suite_lock_excludes_second_connection(engine):
    # The session fixture already owns the lock on a separate live connection.
    with pytest.raises(RuntimeError, match="Another integration suite"):
        with exclusive_test_database(engine):
            pytest.fail("A second connection entered destructive test fixtures")


def test_listing_requires_no_database(monkeypatch, capsys):
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    case = load_dataset()["scenarios"][0]
    assert main(["--list", "--scenario", case["id"]]) == 0
    assert case["nodeid"] in capsys.readouterr().out


def test_missing_legacy_measurements_cannot_be_filled_by_old_results(tmp_path):
    from app.evaluations.measurements import evidence_gaps, measurements

    assert measurements(tmp_path) == {}
    selected = [
        c
        for c in load_dataset()["scenarios"]
        if "test_dynamic_evaluation[" in c["nodeid"]
    ]
    assert evidence_gaps(tmp_path, selected) == [
        "Phase 6 raw rows: expected at least 37, found 0"
    ]


def test_unsafe_policy_decision_metrics_are_separate(tmp_path):
    from app.evaluations.measurements import measurements

    folder = tmp_path / "phase7"
    folder.mkdir()
    for i, row in enumerate(
        [
            {"expected": "DENY", "actual": "REQUIRE_APPROVAL"},
            {"expected": "REQUIRE_APPROVAL", "actual": "ALLOW"},
        ]
    ):
        (folder / f"{i}.json").write_text(json.dumps(row))
    result = measurements(tmp_path)
    assert result["unsafe_allow"]["numerator"] == 1
    assert result["unsafe_allow"]["denominator"] == 2
    assert result["unsafe_require_approval"]["numerator"] == 1
    assert result["unsafe_require_approval"]["denominator"] == 1


def test_empty_metric_denominator_is_unknown():
    from app.evaluations.measurements import fraction

    assert fraction(0, 0) == {"numerator": 0, "denominator": 0, "rate": None}


def test_critical_measured_failure_cannot_be_hidden_by_passing_assertion_reports():
    from app.evaluations.measurements import critical_metric_failures, fraction

    assert critical_metric_failures(
        {"unsafe_allow": fraction(1, 2), "evidence_precision": fraction(2, 3)}
    ) == ["Critical measured outcome unsafe_allow: 1/2"]
    assert critical_metric_failures({"unsafe_allow": fraction(0, 2)}) == []


def test_progress_reports_survive_without_session_finish(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from app.evaluations import pytest_plugin

    destination = tmp_path / "progress.json"
    # Restore plugin globals before pytest emits this test's own call report.
    with monkeypatch.context() as patch:
        patch.setenv("PHASE11_PYTEST_REPORT", str(destination))
        patch.setattr(pytest_plugin, "ROWS", {})
        report = SimpleNamespace(
            nodeid="tests/test_synthetic.py::test_case",
            duration=0.1,
            user_properties=[],
            failed=False,
            skipped=False,
            when="call",
        )
        pytest_plugin.pytest_runtest_logreport(report)
        assert json.loads(destination.read_text())[0]["status"] == "passed"
        report.failed, report.when = True, "teardown"
        pytest_plugin.pytest_runtest_logreport(report)
        assert json.loads(destination.read_text())[0]["status"] == "failed"
        assert not destination.with_suffix(".tmp").exists()

"""Release tooling must fail closed without touching a database."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "url,environment,provider",
    [
        ("mysql://x:y@localhost/northstar_demo", "development", "mock"),
        ("postgresql://x:y@remote/northstar_demo", "development", "mock"),
        ("postgresql://x:y@localhost/northstar", "development", "mock"),
        ("postgresql://x:y@localhost/northstar_test", "test", "mock"),
        ("postgresql://x:y@localhost/northstar_demo", "production", "mock"),
        (
            "postgresql://x:y@localhost/northstar_demo",
            "development",
            "openai_compatible",
        ),
        (
            "postgresql://x:y@localhost/northstar_demo?host=remote",
            "development",
            "mock",
        ),
    ],
)
def test_reset_refuses_unsafe_targets(url, environment, provider):
    with pytest.raises(ValueError):
        load("demo_database").validate_target(url, environment, provider)


def test_reset_accepts_only_dedicated_local_demo():
    assert (
        load("demo_database")
        .validate_target("postgresql://x:y@127.0.0.1/northstar_demo", "test", "mock")
        .database
        == "northstar_demo"
    )


def test_performance_preserves_errors_and_omits_unsupported_p99():
    module = load("release_performance")
    result = module.summarize([(True, 10), (False, 50)], 2)
    assert result["error_count"] == 1
    assert result["success_count"] == 1
    assert result["p50_ms"] == 30
    assert result["p95_ms"] == 50
    assert result["p99_ms"] is None
    assert module.summarize([(True, i) for i in range(100)], 1)["p99_ms"] == 98


def test_missing_release_executable_fails_with_artifact(tmp_path):
    result = load("release_acceptance").run_check(
        "missing", ["/nonexistent/northstar-command"], ROOT, tmp_path, 1
    )
    assert result["status"] == "FAIL"
    assert result["error"] == "FileNotFoundError"
    assert Path(result["log"]).exists()


def test_release_nonzero_exit_is_failure(tmp_path):
    import sys

    result = load("release_acceptance").run_check(
        "failure", [sys.executable, "-c", "raise SystemExit(3)"], ROOT, tmp_path, 1
    )
    assert result["status"] == "FAIL"
    assert result["exit_code"] == 3


def test_release_timeout_fails_and_reaps_process(tmp_path):
    import sys

    result = load("release_acceptance").run_check(
        "timeout",
        [sys.executable, "-c", "import time; time.sleep(10)"],
        ROOT,
        tmp_path,
        0.05,
    )
    assert result["status"] == "FAIL"
    assert result["error"] == "TimeoutExpired"
    assert result["duration_seconds"] < 5

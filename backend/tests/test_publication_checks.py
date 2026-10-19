"""Guard that publication checks detect values without leaking them in reports."""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def publication_checker(tmp_path):
    path = Path(__file__).resolve().parents[2] / "scripts/publication_checks.py"
    spec = importlib.util.spec_from_file_location("publication_checks", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = tmp_path
    return module, tmp_path


@pytest.mark.parametrize("kind", ["provider", "path", "key", "identity"])
def test_sensitive_content_is_reported_without_value(publication_checker, kind):
    module, root = publication_checker
    values = {
        "provider": "gh" + "p_" + "A" * 36,
        "path": "/" + "Users/" + "private-operator/project",
        "key": "-----BEGIN " + "PRIVATE KEY-----",
        "identity": "private.person" + "@" + "mail.invalid",
    }
    secret = values[kind]
    (root / "sample.txt").write_text(secret)
    report = module.audit()
    assert report["blocking_pattern_matches"]
    assert secret not in json.dumps(report)


def test_links_fail_when_target_missing(publication_checker):
    module, root = publication_checker
    (root / "README.md").write_text("[guide](missing.md)")
    assert len(module.audit()["broken_links"]) == 1
    (root / "missing.md").write_text("Guide")
    assert not module.audit()["broken_links"]


def test_unreviewed_credentials_are_not_blanket_allowed(publication_checker):
    module, root = publication_checker
    (root / "config.txt").write_text(
        "postgresql://" + "user" + ":" + "unapproved" + "@localhost/db"
    )
    assert module.audit()["blocking_pattern_matches"]


def test_unknown_test_literal_is_not_whitelisted(publication_checker):
    module, root = publication_checker
    target = root / "backend/tests/test_dynamic_planning.py"
    target.parent.mkdir(parents=True)
    target.write_text("session_secret=" + repr("synthetic-" + "unapproved-fixture"))
    assert module.audit()["blocking_pattern_matches"]


@pytest.mark.parametrize("approved", [True, False])
def test_only_exact_approved_public_email_is_allowed(publication_checker, approved):
    module, root = publication_checker
    value = (
        module.APPROVED_PUBLIC_EMAIL
        if approved
        else "unapproved" + "@users.noreply.github.com"
    )
    (root / "identity.txt").write_text(value)
    result = module.audit()
    assert bool(result["blocking_pattern_matches"]) is not approved

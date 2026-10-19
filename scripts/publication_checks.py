"""Local publication audit; reports locations/categories, never matched values."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
APPROVED_PUBLIC_EMAIL = "250129637+zohaib-hyder@users.noreply.github.com"
EXCLUDED = {
    ".git",
    ".venv",
    "node_modules",
    ".next",
    "artifacts",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "test-results",
    "playwright-report",
}
PATTERNS = {
    "private_key": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "provider_token": r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16}|sk-(?:proj-)?[A-Za-z0-9_-]{24,})\b",
    "private_path": "/"
    + r"Users/|/"
    + r"home/(?!runner\b)[A-Za-z][A-Za-z0-9._-]+/|/"
    + r"private/(?!tmp\b)",
    "private_hostname": r"(?i)\b[\w-]*mac" + r"book[\w.-]*|@[\w.-]+\.local\b",
    "email": r"(?<![\w.+-])[A-Za-z0-9][\w.+-]*@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}",
    "credential_url": r"\b(?:postgresql(?:\+psycopg)?|https?)://[^\s\"\'<>]+:[^\s\"\'<>]+@",
    "literal_credential_review": r"(?i)(?:password|api_key|session_secret|webhook_secret|access_token)\s*(?:=|:)\s*[\"\']([^\"\'\s]{8,})[\"\']",
}


def audit():
    findings = []
    reviewed = []
    broken = []
    count = 0
    binary = []
    links = 0
    external = 0
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT)
        if not path.is_file() or any(part in EXCLUDED for part in rel.parts):
            continue
        if path.name == ".env" or (
            path.name.startswith(".env.") and path.name != ".env.example"
        ):
            reviewed.append(
                {
                    "path": str(rel),
                    "category": "local_generated_environment",
                    "disposition": "excluded from publication; remove before final source-only audit",
                }
            )
            continue
        count += 1
        try:
            body = path.read_text()
        except UnicodeDecodeError:
            binary.append(str(rel))
            continue
        for category, pattern in PATTERNS.items():
            for match in re.finditer(pattern, body):
                value = match.group()
                disposition = None
                if category == "email" and value.lower().endswith(
                    ("@example.com", "@example.net", "@example.org")
                ):
                    continue
                if (
                    category == "email"
                    and value == "key" + "@unsafe.invalid"
                    and str(rel) == "backend/tests/test_dynamic_planning.py"
                ):
                    disposition = "reserved invalid-domain URL parser rejection fixture; not an identity"
                if category == "email" and value == APPROVED_PUBLIC_EMAIL:
                    disposition = "exact owner-approved public Git noreply identity"
                if category == "credential_url":
                    if "${" in value and str(rel) in {
                        "docker-compose.yml",
                        "infra/docker/release.compose.yml",
                    }:
                        disposition = "environment substitution, no embedded credential"
                    elif value.split("://", 1)[1] == "northstar:synthetic-local-only@":
                        disposition = "documented public disposable synthetic local DB placeholder"
                    elif str(rel) in {
                        "backend/tests/test_durable_jobs.py",
                        "backend/tests/test_release_tooling.py",
                    } and value.split("://", 1)[1] in {"x:y@", "synthetic:synthetic@"}:
                        disposition = "reviewed synthetic connection failure/reset-guard test fixture"
                if (
                    category == "literal_credential_review"
                    and str(rel) == "backend/tests/test_dynamic_planning.py"
                    and hashlib.sha256(match.group(1).encode()).hexdigest()
                    == "1ab2687eef79c01cbefc91f204927c92fa77513dea3a3ae78921accf42f4b6c6"
                ):
                    disposition = "reviewed explicit synthetic provider-key fixture; not a configured credential"
                item = {
                    "path": str(rel),
                    "line": body.count("\n", 0, match.start()) + 1,
                    "category": category,
                }
                if disposition:
                    reviewed.append({**item, "disposition": disposition})
                else:
                    findings.append(item)
        if path.suffix == ".md":
            for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", body):
                target = match.group(1).strip().split(' "')[0].strip("<>")
                if target.startswith(("http:", "https:", "mailto:")):
                    external += 1
                    continue
                if target.startswith("#"):
                    continue
                links += 1
                target = unquote(target.split("#")[0])
                if target and not (path.parent / target).exists():
                    broken.append(
                        {
                            "path": str(rel),
                            "target": target,
                            "line": body.count("\n", 0, match.start()) + 1,
                        }
                    )
    return {
        "files_scanned": count,
        "blocking_pattern_matches": findings,
        "reviewed_matches": reviewed,
        "binary_files_requiring_visual_review": binary,
        "local_links_checked": links,
        "broken_links": broken,
        "external_links_not_fetched": external,
        "limitations": [
            "Local pattern and reviewed fixture checks are not a proof of absence or independent forensic audit",
            "Markdown fragment anchors are not validated; external URLs are deliberately not fetched",
            "Ignored development outputs are excluded from publication candidates; complete final source-only tree must also be inspected",
            "Binary images require metadata and visual review separately",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit()
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(
        json.dumps(
            {
                key: result[key]
                for key in [
                    "files_scanned",
                    "blocking_pattern_matches",
                    "local_links_checked",
                    "broken_links",
                    "external_links_not_fetched",
                ]
            },
            indent=2,
        )
    )
    return 1 if result["blocking_pattern_matches"] or result["broken_links"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Scan three local release images in an egress-disabled, isolated Grype container.

Public scanner pull and DB download are separate operator steps. No project upload.
"""

import argparse
import hashlib
import json
import os
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNER = "anchore/grype@sha256:e4a44ef45d285b829ce6efe2642980329661bd2d18eab5fc539138d4adaebbbe"
IMAGES = tuple(
    f"controlled-ai-operations-{name}:latest"
    for name in ("backend", "frontend", "worker")
)


def validate_local_endpoint(endpoint: str) -> None:
    if not endpoint.startswith("unix:///") or len(endpoint) <= len("unix:///"):
        raise ValueError("Only a local Docker Unix socket is permitted")


def scan_command(archive: Path, database: Path) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--pull",
        "never",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        "2g",
        "--cpus",
        "2",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=1g",
        "--mount",
        f"type=bind,src={archive.resolve()},dst=/scan/image.tar,readonly",
        "--mount",
        f"type=bind,src={database.resolve()},dst=/db,readonly",
        "-e",
        "GRYPE_DB_CACHE_DIR=/db",
        "-e",
        "GRYPE_DB_AUTO_UPDATE=false",
        "-e",
        "GRYPE_CHECK_FOR_APP_UPDATE=false",
        SCANNER,
        "docker-archive:/scan/image.tar",
        "--scope",
        "squashed",
        "--output",
        "json",
    ]


def summarize(document):
    rows = [
        {
            "id": match["vulnerability"]["id"],
            "severity": match["vulnerability"]["severity"],
            "package": match["artifact"]["name"],
            "installed": match["artifact"]["version"],
            "type": match["artifact"]["type"],
            "fix": match["vulnerability"].get("fix", {}),
            "data_source": match["vulnerability"].get("dataSource"),
            "locations": [
                value["path"] for value in match["artifact"].get("locations", [])
            ],
        }
        for match in document["matches"]
    ]
    return {
        "severity_counts": dict(Counter(row["severity"] for row in rows)),
        "match_count": len(rows),
        "affected_package_count": len(
            {(r["package"], r["installed"], r["type"]) for r in rows}
        ),
        "findings": rows,
        "ignored_match_count": len(document.get("ignoredMatches", [])),
        "scanner_descriptor": document["descriptor"],
        "distro": document.get("distro"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/image-security"
    )
    args = parser.parse_args()
    base = args.output.resolve()
    if not base.is_relative_to(ROOT / "artifacts"):
        parser.error("Scan artifacts must stay within ignored repository artifacts")
    if os.environ.get("DOCKER_HOST"):
        validate_local_endpoint(os.environ["DOCKER_HOST"])
    validate_local_endpoint(
        json.loads(
            subprocess.check_output(
                [
                    "docker",
                    "context",
                    "inspect",
                    "--format",
                    "{{json .Endpoints.docker.Host}}",
                ]
            )
        )
    )
    database = ROOT / "artifacts/image-security/db"
    if not database.is_dir() or not any(database.rglob("*.db")):
        parser.error("Download Grype DB separately before scanning")
    output = base / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "status": "PARTIAL",
        "scanner_image": SCANNER,
        "scan_project_data_transmitted": False,
        "transmission_claim_scope": "Only these egress-disabled scan processes; excludes separate build/install commands",
        "network_enforcement": "docker run --network none; no socket; only archive/DB read-only mounts",
        "scope": "Final squashed runtime filesystem; all severities, including unfixed matches",
        "images": [],
    }
    path = output / "report.json"
    try:
        # Local inspection only; --pull never prevents registry fallback during scans.
        subprocess.run(
            ["docker", "image", "inspect", SCANNER],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        for image in IMAGES:
            inspected = json.loads(
                subprocess.check_output(["docker", "image", "inspect", image])
            )[0]
            name = image.split("-")[-1].split(":")[0]
            archive = output / f"{name}.tar"
            item = {
                "reference": image,
                "image_id": inspected["Id"],
                "repo_digests": inspected.get("RepoDigests", []),
                "descriptor": inspected.get("Descriptor"),
                "platform": f"{inspected['Os']}/{inspected['Architecture']}",
                "started_at": datetime.now(UTC).isoformat(),
                "scan_complete": False,
            }
            report["images"].append(item)
            path.write_text(json.dumps(report, indent=2) + "\n")
            subprocess.run(
                ["docker", "image", "save", "--output", str(archive), inspected["Id"]],
                check=True,
                timeout=180,
            )
            with archive.open("rb") as stream:
                item["archive_sha256"] = hashlib.file_digest(
                    stream, "sha256"
                ).hexdigest()
            command = scan_command(archive, database)
            item["command"] = command
            with (
                (output / f"{name}.json").open("w") as result,
                (output / f"{name}.log").open("w") as log,
            ):
                completed = subprocess.run(
                    command, stdout=result, stderr=log, timeout=600, check=False
                )
            item["exit_code"] = completed.returncode
            if completed.returncode != 0:
                raise RuntimeError(f"{name} scanner failed; inspect retained local log")
            item.update(summarize(json.loads((output / f"{name}.json").read_text())))
            item.update(scan_complete=True, finished_at=datetime.now(UTC).isoformat())
            print(name, item["severity_counts"], flush=True)
            # Delete only this script-created archive after a completed scan; retain hash/report.
            archive.unlink()
        report["scan_complete"] = True
        report["high_or_critical_matches"] = sum(
            image["severity_counts"].get(level, 0)
            for image in report["images"]
            for level in ("Critical", "High")
        )
        # Completing a scan is not release acceptance. Require explicit findings review.
        report["status"] = "REVIEW_REQUIRED"
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        report["finished_at"] = datetime.now(UTC).isoformat()
        path.write_text(json.dumps(report, indent=2) + "\n")
        print(path, flush=True)
    return 2 if report["high_or_critical_matches"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

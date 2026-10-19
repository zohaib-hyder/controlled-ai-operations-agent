"""Local image scans must retain isolation and unfiltered security findings."""

from test_release_tooling import load


def test_image_scan_has_no_egress_or_host_credentials(tmp_path):
    scanner = load("scan_release_images")
    archive = tmp_path / "image.tar"
    database = tmp_path / "db"
    command = scanner.scan_command(archive, database)
    assert command[command.index("--network") + 1] == "none"
    assert command[command.index("--pull") + 1] == "never"
    assert "--read-only" in command
    assert command[command.index("--cap-drop") + 1] == "ALL"
    assert "no-new-privileges" in command
    mounts = [command[i + 1] for i, word in enumerate(command) if word == "--mount"]
    assert mounts == [
        f"type=bind,src={archive.resolve()},dst=/scan/image.tar,readonly",
        f"type=bind,src={database.resolve()},dst=/db,readonly",
    ]
    assert "GRYPE_DB_AUTO_UPDATE=false" in command
    assert "GRYPE_CHECK_FOR_APP_UPDATE=false" in command
    assert scanner.SCANNER.startswith("anchore/grype@sha256:")
    assert "--only-fixed" not in command
    assert "--ignore" not in command


def test_image_scan_preserves_unfixed_high_matches():
    summary = load("scan_release_images").summarize(
        {
            "matches": [
                {
                    "vulnerability": {
                        "id": "SYNTHETIC-CVE",
                        "severity": "High",
                        "fix": {"state": "not-fixed", "versions": []},
                    },
                    "artifact": {
                        "name": "synthetic-library",
                        "version": "1.0",
                        "type": "deb",
                        "locations": [{"path": "/usr/lib/synthetic"}],
                    },
                }
            ],
            "ignoredMatches": [],
            "descriptor": {"version": "synthetic"},
        }
    )
    assert summary["severity_counts"] == {"High": 1}
    assert summary["affected_package_count"] == 1
    assert summary["findings"][0]["fix"]["state"] == "not-fixed"
    assert summary["findings"][0]["locations"] == ["/usr/lib/synthetic"]


def test_frontend_build_disables_metadata_upload_defaults():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    dockerfile = (root / "infra/docker/frontend.Dockerfile").read_text()
    assert "ENV NEXT_TELEMETRY_DISABLED=1" in dockerfile.split("AS runtime")[0]
    assert "RUN npm ci --no-audit --no-fund --update-notifier=false" in dockerfile
    assert "RUN --network=none npm run build" in dockerfile
    for unused in (
        "/usr/local/lib/node_modules/corepack",
        "/opt/yarn-v*",
        "/usr/local/bin/pnpm",
    ):
        assert unused in dockerfile
    settings = dict(
        line.split("=", 1)
        for line in (root / "frontend/.npmrc").read_text().splitlines()
    )
    assert settings == {"audit": "false", "fund": "false", "update-notifier": "false"}


def test_scan_rejects_remote_docker_endpoints():
    import pytest

    scanner = load("scan_release_images")
    scanner.validate_local_endpoint("unix:///var/run/docker.sock")
    for endpoint in (
        "tcp://remote:2376",
        "ssh://remote",
        "http://localhost:2375",
        "unix:///",
    ):
        with pytest.raises(ValueError):
            scanner.validate_local_endpoint(endpoint)

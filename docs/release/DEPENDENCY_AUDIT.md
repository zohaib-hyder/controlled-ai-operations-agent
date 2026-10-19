> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Dependency and image audit

Review date: 2026-10-19 Asia/Kolkata (scanner artifacts use host UTC). Findings are scanner observations, not exploitation proofs. No automatic major upgrade was applied.

| Scanner / scope | Observation | Disposition |
| --- | --- | --- |
| npm audit, locked frontend install | Five high entries: braces plus four ESLint-chain dependents; zero critical | Development tool chain; retain finding. Registry suggests major downgrade to eslint-config-next 14.2.35, not an accepted compatibility fix. Standalone runtime excludes lint packages; verify final image separately. |
| pip-audit 2.10.1, frozen exported runtime dependencies | No known vulnerabilities reported | Runtime dependency inventory only; not an application security guarantee. Does not assess base OS packages. |
| Docker Scout 1.24.0, baseline backend image | 23 affected packages, 46 findings; one high zlib entry, eight medium, remainder low/unspecified by SARIF level | Includes uv/uvx cargo and pip tooling. Multi-stage runtime removes uv/pip/test tools; rebuilt-image rescan required. Scanner lists zlib CVE-2026-85091 with no fixed version. No critical severity inferred. |
| Docker Scout, baseline frontend image | Scan failed while extracting image: no space left on device | Not a clean scan. Removed only the failed task-created temporary image archive. New standalone image requires separate scan. |

Exact commands:

```sh
npm --prefix frontend audit --json > artifacts/npm-audit.json
uv export --project backend --frozen --no-dev --no-emit-project --format requirements-txt --output-file artifacts/backend-runtime.txt
uv tool run --from pip-audit pip-audit -r artifacts/backend-runtime.txt --no-deps --disable-pip --format json --output artifacts/python-audit.json
docker scout cves controlled-ai-operations-backend --format sarif --output artifacts/backend-image-audit.sarif
docker scout cves controlled-ai-operations-frontend --format sarif --output artifacts/frontend-image-audit.sarif
```

The first npm attempt failed under sandbox DNS restrictions; the authorized retry reached the registry and returned findings (nonzero status). pip-audit was initially unavailable as an installed backend module, then run in an isolated uv tool environment. No scanner API key/customer payload was supplied. Raw artifacts are ignored locally; reviewed summaries should be committed after checking for secrets.

Local loopback-only scope limits exposure but does not erase findings. No production risk acceptance or blanket safe designation is made. Base-image tags remain mutable and no reproducible digest-pinned image supply chain is claimed. Review all final-image findings before declaring an accepted local candidate.

## Historical rebuilt-image scan approval boundary

The hardened backend/frontend/worker images built successfully. A subsequent `docker scout cves controlled-ai-operations-backend ...` attempt was rejected by automatic approval review: Scout may transmit the image or repository-derived metadata to an untrusted external service, and specific payload/destination approval was required. The rejected action was not retried or bypassed. No rebuilt frontend Scout scan was attempted after that rejection. Therefore baseline image results do not establish the security state of the rebuilt images. No local Trivy, Grype or Syft executable was available during inspection.

A separate `npm audit --omit=dev --json` completed with zero reported runtime vulnerabilities. This narrows the npm scope; it is not an OS/image scan. Any future Scout scan needs explicit approval for the relevant image metadata and external service, or an independently configured offline scanner.

## Completed local offline image scans — 2026-10-19

The historical Scout approval blocker was avoided through a different, explicitly authorized local workflow: Grype **0.120.1** pinned to an immutable scanner digest, fresh database **v6.1.10** built 2026-10-19T06:39:15Z, all scan containers using `--network none`. Final backend/worker each: **0 critical, 55 high, 54 medium, 10 low, 47 negligible** (166 package matches / 39 affected tuples). Final frontend: **0 critical, 0 high, 3 medium** (three BusyBox-family tuples, CVE-2025-60876). Original frontend had 13 high/20 medium/nine low matches. All exact package versions, fix states and advisory links are retained in [before](image-security-before.csv) / [final](image-security-final.csv) inventories.

Remediations: remove unused runtime npm/npx, update Alpine OpenSSL 3.5.8-r0 → 3.5.9-r0 and zlib 1.3.2-r0 → 1.3.2-r1, disable automatic audit/telemetry, isolate Next build networking. Backend/worker high findings have no listed distro fixed version and remain unresolved. At that historical stage Node's static OpenSSL 3.5.8 remained a separate manual concern; the final runtime follow-up below replaces that copy. See [full review](IMAGE_SECURITY.md) and [timestamps/digests/DB metadata](IMAGE_SECURITY.json). Scanner count differences from Scout are not a claim that vulnerabilities vanished; scope, feeds and package-source matching differ.

**Transmission exception:** the first remediation rebuild ran npm's automatic audit before it was disabled, submitting dependency metadata externally. Initial Next build telemetry was enabled and may have transmitted anonymous build metadata. The corrected build disables both; all Grype image scans had no network. No image/source/SBOM was uploaded by Grype, and no entire-task no-metadata-transmission claim is made. The required metadata objective was not fully met.

Reproduction: pull the pinned public scanner, download only its public DB with no project mount, then run `backend/.venv/bin/python scripts/scan_release_images.py`. Exact download/scan commands and safeguards are in IMAGE_SECURITY. A completed scan with high findings exits 2; release acceptance remains a separate review and currently **PARTIAL**.

## Runtime investigation after private-baseline

Latest immutable frontend image: `sha256:91cca9203d30b912187f9926740d00daada2d115cdbbb57db58c60e8f85f87a7`; backend/worker digests unchanged. All three were rescanned offline with the same validated Grype database. Counts remain 55 High/54 Medium per backend/worker and zero High/three Medium frontend; every package/advisory match is preserved.

[RUNTIME_HIGH_FINDINGS.json](RUNTIME_HIGH_FINDINGS.json) groups the 110 High image rows into 14 CVEs/21 package-version pairs, with Debian maintainer status. [RUNTIME_REVIEW](RUNTIME_REVIEW.md) records loaded/native components and supported alternatives. A separate local vendor-SBOM scan reports two High PCRE2 advisories (fixed AlmaLinux package 10.32-4.el8_10 versus bundled 10.32-3.el8_6), two Medium and one Low; the latest PyPI wheel remains 3.3.6. Those findings are additional coverage, not a change to image-match denominators or an override of the image distro.

The Node 26.12.0 candidate is an official supported Current release with built-in OpenSSL 3.5.9; Node 22/24 metadata still reports 3.5.8. No custom crypto compilation was used. Runtime Yarn/Corepack/pnpm were removed. Node Current-channel maintenance and native wheel ownership remain explicit limitations. Ordinary public metadata/artifact downloads were separated from scans; no new project metadata upload or Docker Scout invocation was performed. The earlier npm-audit/possible telemetry exception remains in the historical record.

## Final runtime verification

Fresh full backend regression: **727 passed, zero failed/skipped, one upstream warning, 838.59 seconds**; evaluation catalog **601/601**, no measured critical failures/evidence gaps. Ruff/format passed (133 files). Under Node **26.12.0**, frontend lint/typecheck and **50 Vitest tests** passed; production Docker build, Compose configuration and Alembic drift check passed.

Final browser rerun: **64/64 passed** (52 default, four release, eight isolated negative), zero skipped/flaky cases, retries disabled. Before this final run both stacks were explicitly recreated and all six service image IDs matched the scanned digests. An earlier successful 64-case cohort is preserved separately because the old backend/worker image metadata could not be inspected. Runtime mappings were refreshed after recreation. Live health/readiness returned **200**. Restart recovery passed with durable snapshot preserved, queued job completed, one receipt/one business record and zero duplicate mutations. This is graceful queued-job restart evidence, not crash-at-commit proof. Full reviewed results: [RUNTIME_VERIFICATION.json](RUNTIME_VERIFICATION.json), [runtime inventory](RUNTIME_INVENTORY.json).

**PARTIAL:** no release-policy waiver exists for the 14 unique image High CVEs plus two additional native PCRE2 High advisories. New scans/build checks uploaded no project artifacts or metadata; historical npm-audit transmission and possible telemetry remain disclosed. No full coordinator, performance or clean-volume installation rerun is implied; those prior results retain their original scope. No push, deploy, publish, live LLM, production acceptance or Phase 13.

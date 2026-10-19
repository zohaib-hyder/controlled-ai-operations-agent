> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 12 local image security gate

Latest runtime investigation: [RUNTIME_REVIEW](RUNTIME_REVIEW.md). All final images have been rescanned; no acceptance verdict is inferred from scanner completion.

## Download and data boundary

Neither Trivy nor Grype was installed at inspection. Use official Anchore Grype v0.120.1, downloaded as the public `docker.io/anchore/grype:v0.120.1` scanner image. Vulnerability database listing/archive downloads use `https://grype.anchore.io/databases` and its listed archive URLs. Registry/CDN and database hosts receive ordinary download request metadata (IP, requested public artifact and client headers), not application artifacts. The database-download container has no project, image archive, Docker socket, credentials or repository mount: only an empty task-owned database directory.

Actual scans use the pinned downloaded scanner digest, `--network none`, read-only container root, dropped capabilities/no-new-privileges and read-only mounts of a single saved image archive and the cached vulnerability DB. No Docker socket, `.env`, repository checkout or credential mount is passed. Update checks/automatic database updates are disabled during scans; no remote scanner/server or SBOM upload is used. OS-enforced disabled networking is the transmission boundary, not merely a promise by the scanner.

Official references: [immutable Grype release](https://github.com/anchore/grype/releases/tag/v0.120.1), [configuration](https://oss.anchore.com/docs/reference/grype/configuration/), [vulnerability database](https://oss.anchore.com/docs/guides/vulnerability/database/), [archive scan targets](https://oss.anchore.com/docs/guides/vulnerability/scan-targets/).

All scan outputs and image archives stay in ignored local artifacts. Reviewed summaries below will retain exact severity/package/fix information without exposing application filesystem content. No external application data transmission is authorized.

## Data-transmission exception during remediation

**The whole-task no-metadata-transmission objective was not fully met.** The first remediation rebuild inherited `npm ci`'s automatic audit default. Its retained log says “audited 397 packages” and returned five high findings. This submitted dependency metadata to npm's default registry audit service. The request body was not captured; [npm documents](https://docs.npmjs.com/cli/v11/commands/npm-audit/) dependency names/versions for the bulk protocol, with a dependency-tree/toolchain metadata fallback. No image/source/SBOM upload was performed by this audit. The initial aborted build also emitted Next.js's telemetry-enabled notice; whether anonymous build metadata left that attempt cannot be retrospectively established. These events are disclosed rather than reclassified as download-only activity.

Correction: `frontend/.npmrc` and Docker build environment disable automatic audit, funding and update checks; install uses explicit `--no-audit --no-fund --update-notifier=false`; build telemetry is disabled and the final Next build runs with `RUN --network=none`. The scan processes themselves had no egress throughout. No clean whole-task transmission attestation is made, and earlier transmission cannot be undone. Raw build logs are retained locally.

Remediation downloads: public npm package artifacts from `registry.npmjs.org` and Alpine indexes/packages from the official configured Alpine repositories (`dl-cdn.alpinelinux.org`). These request public package names; no application image/file/SBOM upload is part of the corrected build. The local Docker endpoint was verified as a Unix socket; the wrapper refuses remote Docker endpoints.

## Scanner, database and exact image identities

Scanner: **Grype 0.120.1**, Syft 1.54.1, linux/arm64. Pinned scanner image:

`anchore/grype@sha256:e4a44ef45d285b829ce6efe2642980329661bd2d18eab5fc539138d4adaebbbe`

Database schema **v6.1.10**, built **2026-10-19T06:39:15Z**, valid per Grype's age/integrity checks. Download archive SHA256 **13a192236b248579678bbf06cefb2a07a5dcbd00da110cfb5c3e26eb68a7ce58**. Exact download URL/import metadata and per-image timestamps/archive hashes are retained in [IMAGE_SECURITY.json](IMAGE_SECURITY.json). Latest final scans ran **2026-10-19 12:29:39–12:37:05 UTC**. The earlier 10:41 cohort remains historical evidence. No update or advisory request occurred during scans. Original and intermediate scan failures/statuses are retained locally; completed scan wrappers return 2 for high/critical matches, not a passing release verdict.

| Local image | Final immutable OCI index digest | Original digest |
| --- | --- | --- |
| controlled-ai-operations-backend:latest | `sha256:0c004681eed92863fc624cb73e65acf54cd05f5ea674ccf23823238b8d1f877c` | Same |
| controlled-ai-operations-frontend:latest | `sha256:91cca9203d30b912187f9926740d00daada2d115cdbbb57db58c60e8f85f87a7` | `sha256:f3c2d6c9e8ab89fe40a4b1d3d756a3085526b08d8d041a3924fb92584214b9c2` |
| controlled-ai-operations-worker:latest | `sha256:084f2503e55d718b9e8b58c5e7129bbe5508b200c8d490a54b89370ebebdf86f` | Same |

These are locally reported immutable image descriptors/RepoDigests, not evidence of a published registry artifact. Each image was independently exported by immutable ID and scanned from its own hashed archive. No registry lookup or upload is needed for those archives.

## Exact scanner findings

Counts are package/vulnerability matches, not distinct CVEs or proven exploits. A source-package advisory can match multiple installed binary packages. **No matches were ignored**, no severity was changed, and unfixed matches were included.

| Image | Critical | High | Medium | Low | Negligible | Affected package/version/type tuples | Total matches |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Backend, original and final | 0 | 55 | 54 | 10 | 47 | 39 | 166 |
| Worker, original and final | 0 | 55 | 54 | 10 | 47 | 39 | 166 |
| Frontend original | 0 | 13 | 20 | 9 | 0 | See before CSV | 42 |
| Frontend final | 0 | 0 | 3 | 0 | 0 | 3 | 3 |

Every affected package, installed version, severity, advisory source and fixed-version/state is recorded in [before findings](image-security-before.csv) and [final findings](image-security-final.csv). CSV rows bind findings to exact image digests. This inventory includes medium/low/negligible findings; they are not hidden behind a high-only summary.

### Frontend remediations

- Removed runtime npm/npx and `/usr/local/lib/node_modules/npm`. This removes high matches GHSA-ch52-4w7c-c8xp (`http-cache-semantics` 4.2.0, no listed fix), GHSA-rfgv-xxqx-mfg5 (`undici` 6.28.0, fixed 6.28.1), and GHSA-qhr7-859c-m2p7 / GHSA-6j4f-fj2g-mc7p (`brace-expansion` 5.0.9, fixes 5.0.11/5.0.10). These were npm's copies, not Next's application dependency tree or Node's bundled undici. npm remains available only in the build stage.
- Updated Alpine `zlib` 1.3.2-r0 → **1.3.2-r1**, resolving the installed-package match for high CVE-2026-85091.
- Updated Alpine `libcrypto3` / `libssl3` 3.5.8-r0 → **3.5.9-r0**, removing eight package matches across CVE-2026-54873, CVE-2026-84782, CVE-2026-84784 and CVE-2026-72897. Initial database fix state was unknown; final inventory independently confirms those package matches disappeared.
- Final remaining medium CVE-2025-60876 matches `busybox`, `busybox-binsh` and `ssl_client` **1.37.0-r31**, with no fixed version/state supplied. These utilities are not the Node server entrypoint; indirect/local utility use remains possible. No suppression or risk acceptance was applied.

### Unresolved backend/worker high exposure review

The 55 high matches in each image cover **14 distinct CVEs**. Exact binary packages/versions are in the CSV. Database states are `wont-fix` except zlib (`not-fixed`), with no fixed versions listed. “Wont-fix” is scanner/provider metadata, not permission to dismiss a finding.

| Components / CVEs | Exploit conditions and current exposure | Remediation status |
| --- | --- | --- |
| Perl: CVE-2026-82560, CVE-2026-9538 | Resource exhaustion while formatting crafted POD or reading crafted tar sizes. App has no explicit Perl/POD/archive tooling and agent cannot execute shell/code. Requires a reachable parser path; not proven impossible after another compromise. | No distro fixed version listed; retained high. |
| ncurses: CVE-2025-69720 | `infocmp` stack overflow on crafted input; advisory maps across multiple source-built binary packages. App does not invoke infocmp; no agent shell. | No distro fixed version listed; retained high. |
| glibc: CVE-2026-5435, CVE-2026-19499 | Out-of-bounds writes in DNS diagnostic printing or monetary formatting. libc is a real runtime dependency; no explicit calls found in app, but indirect/native reachability was not exhaustively proved absent. | No distro fixed version listed; retained high. |
| GCC/libstdc++: CVE-2026-95619, CVE-2026-102010 | Large aligned allocation / priority-queue erase paths can corrupt memory. Installed native support libraries remain part of runtime surface. | No distro fixed version listed; retained high. |
| util-linux: CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 | Privileged mount/nsenter or authorized filesystem manipulation paths. Services run nonroot, lack an agent shell, and do not receive privileged mode/SYS_ADMIN. Those controls reduce exposure; they do not erase installed-package matches or prove local compromise harmless. | No distro fixed version listed; retained high. |
| ACL: CVE-2026-54369, CVE-2026-54370 | Privileged pathname operations exposed to symlink/race manipulation. No explicit app ACL calls; native/local paths not exhaustively analyzed. | No distro fixed version listed; retained high. |
| zlib: CVE-2026-85091 | Nonblocking gz write/format state can cause heap overflow. No explicit app gzprintf/gzvprintf calls. Debian marks installed version vulnerable; affected-range/backport ambiguity is not treated as a proven false positive. | Debian tracker lists no fixed package; retained high. |

Sources: each CSV advisory URL; in particular [Debian zlib status](https://security-tracker.debian.org/tracker/CVE-2026-85091). Removing essential runtime libraries or switching distributions solely to lower scanner counts was not attempted. No arbitrary upstream patch or major framework/runtime upgrade was applied.

### Historical Node 24/OpenSSL follow-up beyond package counts

At commit private-baseline, runtime inspection reported Node **v24.22.0**, built-in OpenSSL **3.5.8**, built-in undici **7.29.1**, and no dynamic libcrypto/libssl dependency in `ldd /usr/local/bin/node`. Thus patching Alpine's OpenSSL does **not** patch Node's static copy. [Official Node's release inventory](https://nodejs.org/dist/index.json) lists v24.22.0 with OpenSSL 3.5.8; [OpenSSL's advisories](https://openssl-library.org/news/vulnerabilities/) include affected 3.5.x paths fixed in 3.5.9. At that historical stage this was an unresolved manual component concern, separate from the zero high *Grype package matches* for frontend.

No explicit application SM2/DTLS calls were found; Compose serves HTTP and the proxy forwards only fixed paths to internal HTTP. That limits demonstrated exposure, but native/TLS/crypto reachability is not proven absent. Await a compatible maintained Node 24 update or separately validate a patched supported runtime. Moving to Node 26 or custom-building crypto was not justified as a safe small release fix. No clean Node/OpenSSL security assessment is claimed.

## Acceptance decision and limitations

**PARTIAL; no accepted local RC.** Scanning is complete, but unresolved high findings/manual bundled-component concerns remain. The earlier external-service-approval blocker is superseded by actual findings, not silently waived. The no-project-metadata objective also has the npm-audit exception above. No risk acceptance is inferred from loopback binding, nonroot execution, passing mock tests or lack of a demonstrated exploit.

Grype inventories known vulnerabilities using one downloaded database, final squashed image filesystem and linux/arm64. It does not prove exploitability, discover every static dependency, test kernel/host security, inspect removed build layers, certify supply-chain provenance or establish production readiness. Database/image digests bind this observation; they are not guarantees against future advisories. PostgreSQL/other infrastructure images were outside this three-image request.

## Reproduction commands

Run from repository root. Downloads are explicit and separate from scanning. The DB directory is task-owned and contains public vulnerability data only.

```sh
mkdir -p artifacts/image-security/db
docker pull anchore/grype:v0.120.1
docker run --rm --pull never --read-only --cap-drop ALL \
  --security-opt no-new-privileges \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  --mount "type=bind,src=$PWD/artifacts/image-security/db,dst=/db" \
  -e GRYPE_DB_CACHE_DIR=/db -e GRYPE_CHECK_FOR_APP_UPDATE=false \
  anchore/grype@sha256:e4a44ef45d285b829ce6efe2642980329661bd2d18eab5fc539138d4adaebbbe db update
backend/.venv/bin/python scripts/scan_release_images.py
```

The wrapper inspects only local images, exports each by immutable ID, hashes the archive, and invokes the pinned scanner with `--pull never --network none --read-only --cap-drop ALL --security-opt no-new-privileges --memory 2g --cpus 2`, a 1 GiB temporary filesystem, only archive/DB read-only mounts, `GRYPE_DB_AUTO_UPDATE=false`, `GRYPE_CHECK_FOR_APP_UPDATE=false`, target `docker-archive:/scan/image.tar`, `--scope squashed --output json`. It retains raw JSON/logs and deletes only its own archive after a completed scan. Exact expanded argv is in the local report. No remote Docker host or scanner server is permitted.

## Historical regression verification at private-baseline

After the final rebuild: **52 default + four complete-execution/security + eight isolated negative browser cases passed** (64 total, two executions of the single complete business scenario, desktop/mobile), zero skipped/flaky cases and retries disabled. Main and isolated frontends were recreated from the final scanned tag and became healthy; worker was stopped only for cancellation tests and restored. Sixteen selected release/image tooling pytest cases passed in 0.30 seconds, including no-egress mounts, remote-Docker rejection, unfixed-finding preservation and build privacy defaults. Frontend lint/typecheck and all 50 Vitest tests passed; Ruff/format passed (133 Python files). Final Docker production build passed with Next build networking disabled. Live health/readiness returned 200. Runtime UID 1000, no npm directory, telemetry disabled; Node still reports built-in OpenSSL 3.5.8.

No full backend regression/coordinator rerun is claimed: backend application source and both backend/worker images are unchanged; prior 723-test/601-scenario results retain their original timestamp/source scope. This follow-up's added guard tests and runtime browser checks are reported separately. No new migration or approval/authorization behavior was introduced.

## Final runtime investigation follow-up

The supported official **Node 26.12.0 / Alpine 3.24** candidate built successfully with networking disabled for Next build. Runtime inspection confirms statically bundled **OpenSSL 3.5.9** and undici **8.11.2**. Unused Yarn/Corepack/pnpm shims were removed; no JavaScript package manager remains in runtime. This resolves the observed Node 24/static-OpenSSL 3.5.8 component concern without compiling custom crypto. Node 26 is Current, not LTS: its local-demo adoption is conditional on the recorded regressions and is not a production recommendation.

Full-image counts remain unchanged: backend/worker each **0 critical / 55 high / 54 medium**, frontend **0 critical / 0 high / 3 medium**. The 110 backend/worker High matches are **14 unique CVEs / 21 package-version pairs**, duplicated across identical image inventories. Actual process mappings and source-package fan-out are assessed per advisory in RUNTIME_REVIEW/RUNTIME_HIGH_FINDINGS.json.

The installed Psycopg 3.3.6 wheel's vendor SBOM surfaced **two additional High PCRE2 advisories**, plus two Medium and one Low, under explicit AlmaLinux 8 provenance. These are separate from the Debian image-scan counts, not suppressed or merged into a misleading denominator. Both native crypto and PCRE2 are mapped. PyPI already lists 3.3.6 as current; a safe vendor-wheel refresh or separately qualified system-libpq installation is still needed. Neither version labels nor absence of a demonstrated app path prove safety.

**PARTIAL remains the release decision.** Remaining High native-component findings have no policy waiver; the existing gate is unchanged. Historical metadata transmission remains disclosed. This follow-up used ordinary public release/package/index downloads and egress-disabled image/SBOM scans; Docker Scout was not used. Relevant regression results are recorded below after execution.

## Final runtime verification

Fresh full backend regression: **727 passed, zero failed/skipped, one upstream warning, 838.59 seconds**; evaluation catalog **601/601**, no measured critical failures/evidence gaps. Ruff/format passed (133 files). Under Node **26.12.0**, frontend lint/typecheck and **50 Vitest tests** passed; production Docker build, Compose configuration and Alembic drift check passed.

Final browser rerun: **64/64 passed** (52 default, four release, eight isolated negative), zero skipped/flaky cases, retries disabled. Before this final run both stacks were explicitly recreated and all six service image IDs matched the scanned digests. An earlier successful 64-case cohort is preserved separately because the old backend/worker image metadata could not be inspected. Runtime mappings were refreshed after recreation. Live health/readiness returned **200**. Restart recovery passed with durable snapshot preserved, queued job completed, one receipt/one business record and zero duplicate mutations. This is graceful queued-job restart evidence, not crash-at-commit proof. Full reviewed results: [RUNTIME_VERIFICATION.json](RUNTIME_VERIFICATION.json), [runtime inventory](RUNTIME_INVENTORY.json).

**PARTIAL:** no release-policy waiver exists for the 14 unique image High CVEs plus two additional native PCRE2 High advisories. New scans/build checks uploaded no project artifacts or metadata; historical npm-audit transmission and possible telemetry remain disclosed. No full coordinator, performance or clean-volume installation rerun is implied; those prior results retain their original scope. No push, deploy, publish, live LLM, production acceptance or Phase 13.

> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 12 — local release verification and hardening

Baseline: `private-baseline`. Scope: synthetic local services only. No Phase 13, push, publish or deployment.

## 1. Implemented

Prioritized repository audit; serial fresh-artifact acceptance coordinator; bounded authenticated read latency and tenant-bound query-plan diagnostics; dedicated marked demo database initialization/reset; fresh active-worker browser journey from investigation through independent review, controlled execution and auditor trace; deterministic browser security-override denial; guarded real local queued-job restart verification; multi-stage nonroot runtime images; CI extension and release runbooks.

## 2. Files

New release CLIs: `release_acceptance.py`, `release_clean_install.py`, `release_performance.py`, `release_query_plans.py`, `release_recovery.py`, `release_workload.py`, `release_workload_measurements.py`, `release_queue_load.py`, `demo_database.py`, `prepare_release_browser.py`, `prepare_release_negative.py` and `browser_business_snapshot.py`. New backend tests: `test_authentication_pool.py` and `test_release_tooling.py`; duration diagnostics added to `test_dynamic_planning.py`. New release/negative Playwright configs and suites, shared browser snapshot helper, and default job/incident assertions. New isolated Compose override, release documentation and decision 0013. Modified authentication connection lifetime, reset/browser runners, Dockerfiles/.dockerignore, Next/Playwright configs, Compose timeout setting, `.env.example`, CI, AGENTS, README and architecture overview. `git show --stat` after the local commit provides the exact inventory.

## 3. Architecture and migrations

Preserve the existing state machine, PDP, strict tools, approval bindings, transaction/idempotency/fencing code and eight-second agent budget. The measured 20-client pool-starvation remediation closes a short-lived authentication read Session before downstream service acquisition, preserving injected binds and every authorization predicate. No database schema change or migration is introduced; head remains 0009_operations. Release tools are operator development CLIs, never agent capabilities. Separate stopped-worker cancellation tests from active-worker complete journeys. Runtime images exclude build/test dependencies; use locked host tooling for tests.

## 4. Commands

Exact acceptance commands, cwd, exit codes, durations and logs are recorded in fresh `artifacts/release/<run>/report.json`. See RELEASE_CANDIDATE for reproduction, LOCAL_DEMO for startup/reset, PERFORMANCE_BASELINE for latency/query diagnostics and DEPENDENCY_AUDIT for scanner commands. Additional actual executions and failures are recorded below after verification.

## 5. Tests and performance

Fresh first regression: 720 backend tests passed, 601/601 catalog scenarios, one upstream Starlette/httpx deprecation warning, 908.37 seconds. This preceded the connection-lifetime fix and the final two release guard tests/new pool regression. Focused authentication/release verification after the fix: 67 passed in 26.00 seconds. Fixed targeted stability repetitions: five × five cases (25 passed); 52 execution-security cases passed in reverse order in 78.24 seconds; three tenant/global admission cases passed. Historical Phase 10 transient cause remains unconfirmed.

First primary release browser cohort: 4/4 passed in 19.0 seconds. Fresh isolated stack: 4/4 passed in 19.5 seconds. Each cohort contains two viewport executions of one complete business journey plus two security-denial cases. Initial selector/launch failures are preserved; final source additionally binds job inspection to the exact job ID and checks foreign-tenant detail/list feedback. Final fresh results: **52 default + 4 primary release + 4 isolated release + 8 negative = 68 passing executions across 64 unique viewport cases**, with zero skips/retries/flaky classifications. This includes four executions of the single full journey across two stacks and two viewports. A fresh post-synchronization repeat passed **52 + 4 + 8 = 64/64**, zero skipped/flaky/retried cases. Final coordinator plus successful repeat provide **132 passing executions across 64 unique cases**, including six executions of the single full business journey; the failed repeat remains separately reported.

Read baseline: 20 samples per endpoint per cohort, 160 reads at configured concurrency 1, 5, 10 and 20. Concurrency 1/5/10 each passed all reads. The first 20-client cohort passed 91/160, with 69 pool-timeout-related errors retained. The narrowed authentication connection lifetime then passed the same 160/160 twenty-client reads; operations p95 was 687.3 ms versus about 3267.7 ms in the failing cohort. No pool/statement timeout, pool capacity or agent budget was raised. p99 is omitted because each endpoint has only 20 samples; single-login observations are not an authentication tail distribution.

First bounded mixed workload: 60.003 seconds, eight completed workflows, four per tenant, four independent grants, zero failed/duplicate mutations, eight zero-backlog samples. Persisted timings: 48 successful tool calls p50/p95 7.69/13.85 ms; eight queue waits 715.81/1077.24 ms; eight worker attempts 93.22/357.46 ms. These measurements have their stated executor/attempt scope; mutation-only latency is not inferred.

Clean install passed in 29.845 seconds against a confirmed new isolated volume, including seed/login/readiness/frontend/migration drift. Real restarts of all four local services passed in 24.493 seconds with an unchanged durable snapshot and one queued note recovered to exactly one receipt/record. Two dedicated marked demo resets reproduced 2 tenants, 8 users, 20 customers/accounts, 30 tickets, 40 transactions and 10 policies, comparing all seeded fields except salted credential hashes and credential provisioning timestamps.

A second full cohort passed 722 tests with one failure (900.95 seconds): `missing_policy` terminated at the unchanged wall budget instead of the expected missing-evidence escalation. The call took 22.043 seconds; no mutation or tenant leakage was observed. Five predetermined exact repeats passed at 596–673 ms. Root cause remains unconfirmed. A subsequent coordinator attempt omitted TEST_DATABASE_URL and correctly refused the backend gate before running tests; it was interrupted and restarted with the documented disposable URL. The final fresh backend cohort passed **723 tests**, one upstream warning, in **743.41 seconds**, with **601/601** catalog scenarios and no measured critical violation. Its coordinator is `artifacts/release/20261019T090855157172Z`: all **27 stages passed**, execution complete, worker restoration passed. The coordinator deliberately exited **1/PARTIAL** for the missing rebuilt-image scan. Reviewed machine evidence is committed in `docs/release/EVIDENCE.json`; exact normalized stage commands are in `docs/release/COMMANDS.md`. No accepted candidate is claimed.

## 6. Security, reliability and live verification

No write authority or enforcement was relaxed. Former unguarded volume reset is removed. Reset now requires dedicated exact loopback target, mock development/test, marker and no connected clients. New release browser requests use real API/DB/worker and separate reviewer/auditor/foreign contexts. Scanner findings and incomplete scans remain visible.

## 7. Limitations

The historical transient failure root cause remains unconfirmed. Live-provider behavior and production capacity/security remain unverified. Read-path timings are not a workflow soak or fairness proof. Required missing verification keeps the local candidate unaccepted; see KNOWN_LIMITATIONS and final evidence below.

## 8. Git

Local Phase 12 commit is created after the checks below; retrieve its exact ID with `git log -1 --format=%H`. The final response records the observed hash and working-tree status. No push or deployment.

## 9. Verdict

**PARTIAL.** Offline scanning is now complete; unresolved high image findings, bundled Node/OpenSSL risk and the remediation metadata-transmission exception prevent acceptance. See security-gate follow-up below.

## Failure record and fixes

- The first coordinator was interrupted during its browser stage after four observed passing cases; no final browser exit or complete acceptance was recorded. On continuation its processes were absent and Docker was stopped; cause unconfirmed. Docker Desktop/services were restored. This is not a passing full browser run.
- Four release cases failed at launch because the temporary Chromium cache was missing. Installed the exact locked Playwright Chromium build; no test was skipped to avoid the failure.
- A release case timed out using an exact wrapped-label lookup for Action. The actual accessible combobox existed. Corrected the test to a semantic role/name selector; retained the timeout evidence.
- Visual inspection found the general completed-job selector could select another completed card after refresh. Bind it to the current job's exact UUID before opening the receipt. Earlier successful own-account/API assertions remain evidence; both final-stack runs and the fresh repeat verified the corrected own-job UI binding.
- The first reset fingerprint compared credential provisioning timestamps. The seed correctly generates salted hashes and current credential update times. Compare only those two intentional authentication fields separately; business fields and stable identities must still match. No authentication behavior was weakened.
- Twenty-client read errors exposed retained authentication connections competing with service transactions. The single-connection regression and repeat load validate a narrow lifetime fix; all error outcomes are retained. This is distinct from the unconfirmed historical transient.
- Baseline frontend image scan ran out of disk while unpacking. A rebuilt backend Scout scan was subsequently rejected by automatic approval review because it could transmit image/repository metadata externally. No bypass or clean rebuilt-image claim was made.

## Final local live evidence

Fresh clean install: **PASS, 30.453 seconds**, new isolated volume, full migration chain and schema drift check, tenant seed, login, readiness and frontend 200. Fresh restart recovery: **PASS, 24.194 seconds**, all four services restarted, durable snapshot preserved, one queued note recovered to one verified receipt/record and exact-key replay reused the job. These are graceful queued-work restarts, not OS-kill-at-commit or full interrupted-investigation process-fault verification. Existing backend fault-injection tests retain their narrower scope.

Fresh finite queue: **20 jobs, five tenants, four configured workers**, 19 single verified commits and one intentional stale-evidence rejection, zero duplicate/unauthorized mutations, five foreign-job denials. Observed active peak **4 globally / 1 per tenant**, drain 8.575 seconds, total 24.748 seconds. Bounded drain and sampled occupancy do not establish strict fairness or production throughput. Fresh paced workload: **60.000 seconds**, eight completions/four per tenant, four grants, zero failed/duplicate mutations and eight zero-backlog samples. Persisted queue wait p50/p95 **364.26/862.45 ms** (n=8), worker-attempt elapsed **79.06/110.04 ms** (n=8), tool execution **6.71/9.58 ms** (n=48), search_policy **8.85/9.53 ms** (n=8). No p99 at these sample sizes; worker-attempt elapsed is not mutation-only latency.

Final production build succeeded: 17-page static generation completed; filesystem output 1,136 KiB static / 57,772 KiB standalone, uncompressed. These are disk sizes, not network transfer or per-route rendering measurements. Docker Compose configuration/build, locked migrations and live health/readiness are exercised by the coordinator; hosted CI remains unexecuted.

Startup and complete verification commands are in LOCAL_DEMO and COMMANDS. No secrets, real customer connection, live provider call, push, deployment, publication or Phase 13 work occurred.

The first repeat of the default browser cohort reported **51 passed / one failed**: mobile auditor-to-foreign-admin switching did not reach the overview. The test clicked Sign out and immediately navigated to the next login without waiting for logout. Preserved its JSON/error context; added an explicit POST-logout response wait, sign-in heading and server-side 401 check before the next login. No application authorization code or assertion was weakened. Lint/typecheck passed after this test-only synchronization change; the fresh complete repeat then passed all 64 cases (52 default, four release, eight negative), without retries/skips.

Final twenty-client performance repeat passed **160/160 reads**, no target violations against the prospective 1,500 ms per-endpoint p95 bound. Operations p50/p95 was **610.56/744.40 ms**, investigation history **385.14/448.00 ms** (20 samples each). No p99 is reported. Live GET health/readiness both returned 200 (`ok`/`ready`); runtime inspections verified nonroot backend/frontend, absence of backend pytest/Ruff/uv/pip and frontend ESLint/TypeScript/Vitest. This does not replace image scanning. All committed backend application/test source hashes match the successful evaluation manifest. Screenshots and a reviewed machine summary are retained in `docs/release/`.

Exact startup (after generating ignored configuration/credential and installing locked dependencies):

```sh
docker compose config --quiet
docker compose build backend frontend worker
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed_auth
docker compose up -d --wait backend frontend worker
curl --fail http://127.0.0.1:8000/api/v1/health
curl --fail http://127.0.0.1:8000/api/v1/ready
```

Dependency review: npm full install five high development-chain entries, runtime-only npm zero known findings; 29 Python runtime distributions zero known findings. Baseline backend image 46 findings/23 affected packages including one high zlib entry; baseline frontend scan failed disk extraction. Rebuilt images remain unscanned after automatic approval review rejected Scout external transmission. No risk acceptance or accepted local RC is implied.

## Security-gate follow-up (base commit private-baseline)

1. Implemented independently scanned immutable backend/frontend/worker archives using Grype 0.120.1, DB v6.1.10, egress-disabled containers. Each scan retained exact digest, timestamp, DB metadata, all severities/fix states and local archive hashes.
2. Files: frontend Dockerfile and new `.npmrc`, offline scan script plus four security guard tests, release-harness exclusion text, the five required reports, IMAGE_SECURITY Markdown/JSON and complete before/final CSV inventories.
3. No application authorization, tenant query, policy, schema or migration change. Runtime frontend removes npm, updates Alpine zlib/OpenSSL and disables build audit/telemetry/network. Backend/worker image digests are unchanged.
4. Commands: `docker pull anchore/grype:v0.120.1`; pinned scanner DB-only update with no project mount; `backend/.venv/bin/python scripts/scan_release_images.py` (three complete serial cohorts); `docker compose build frontend`; relevant pytest/Ruff/frontend/browser checks. Exact scan/download invocation is in IMAGE_SECURITY and local raw reports. Final scan wrapper exits 2 because high matches remain, not because scans failed.
5. Results: all three final images scanned; backend/worker each 0 critical/55 high/54 medium, frontend 0 critical/0 high/three medium. Frontend originally had 13 high/20 medium/nine low. Sixteen release/image tooling tests passed; lint/typecheck/50 Vitest tests passed; final image production build passed. Final browser results are recorded after completion below. Prior 723-test/601-scenario results are historical and were not rerun as a full backend cohort; backend runtime source/images are unchanged.
6. Exposure: no fixed backend/worker high distro versions are listed. Nonroot/no-shell/no-SYS_ADMIN and absence of explicit vulnerable calls reduce demonstrated paths without proving unreachability. Static Node OpenSSL 3.5.8 is not replaced by the Alpine 3.5.9 update. Exact findings and limitations are in IMAGE_SECURITY.
7. **Transmission exception:** an early remediation npm install automatically audited 397 packages and submitted dependency metadata to the registry audit service. An aborted build's anonymous Next telemetry cannot be ruled out. This violated the requested metadata boundary; corrected build defaults and network isolation prevent recurrence in the final build. All actual Grype scans had networking disabled and uploaded no project artifacts. No clean whole-task transmission attestation is made.
8. Changes are committed locally after verification; final response gives the observed follow-up hash/clean-tree status. No push, deployment, publishing, real customer access or Phase 13.
9. **PARTIAL; no accepted local RC.** Scan completion does not resolve high findings or erase the documented transmission exception.

Final security follow-up browser regression: **64/64 passed** (52 default, four release, eight negative), zero skipped/flaky cases, retries disabled. Main and isolated final-image frontends healthy; runtime UID 1000, npm absent and telemetry disabled. Live health/readiness 200. Exact per-cohort counts/durations, identities, scans and transmission exception are committed in IMAGE_SECURITY.json. All five requested release/security reports have been updated. No accepted RC is declared.

## Final runtime investigation (base private-baseline)

1. **Root causes:** maintained Debian runtime libraries/utilities inherit 14 source-package High advisories across multiple binary packages. All 166 backend/worker image findings match after identity is excluded. Their 110 High rows represent 14 CVEs/21 package-version pairs. Installed libc/zlib/OpenSSL already match stable apt candidates. Vendor-SBOM assessment finds two additional High PCRE2 advisories in Psycopg's private library, despite its Python package already being current 3.3.6. No unavailable fix is treated as harmless.
2. **Inventory:** image/process probes confirm Python-only backend/worker, no Node/npm/compilers/uv/pip, and actual mappings of libc/zlib/libstdc++ plus wheel-provided native crypto/PCRE2. Frontend needs Node, not JavaScript package managers. Package managers inherited from supported OS bases are retained intentionally; no package database or essential library was deleted to alter counts. Full per-CVE loading/precondition/fix/confidence records are in RUNTIME_REVIEW and RUNTIME_HIGH_FINDINGS.json. The vendor profile is separate from full-image counts; across profiles there are 16 High CVEs.
3. **Changes:** official Node 26.12.0 Current on existing Alpine 3.24 replaces the observed static OpenSSL 3.5.8 with 3.5.9; removes unused Yarn/Corepack/pnpm shims; aligns CI release checks/documented prerequisites. No custom crypto, driver replacement, backend runtime source, schema, migration, agent budget, approval or execution boundary change. Current versus LTS tradeoff is explicit in decision 0014; no production recommendation.
4. **Rebuild/scans:** production image built with Next networking disabled and npm audit/telemetry disabled. All three final immutable images were independently scanned offline using Grype 0.120.1 / validated DB v6.1.10. Backend/worker each 0 critical/55 high/54 medium; frontend 0 critical/0 high/three medium. New frontend digest `sha256:91cca9203d30b912187f9926740d00daada2d115cdbbb57db58c60e8f85f87a7`; backend/worker digests unchanged. Full unsuppressed matches and before/after identities remain committed.
5. **Backend regression:** fresh full pytest/security CLI passed **727 tests**, zero failed/skipped, one upstream warning, **838.59 seconds**; **601/601** catalog scenarios, no measured critical failures/evidence gaps. Actual command: from backend, TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test, `.venv/bin/python -m app.evaluations.red_team --regression --output ../artifacts/runtime-review/backend-security`. Main app services were stopped during testing and restored healthy; isolated app was stopped to reduce contention. Eight-second agent wall limit unchanged; historical transient cause remains unconfirmed. Ruff/format passed (133 Python files). Remaining frontend/browser/recovery results are recorded below after execution.
6. **Security/exposure:** source-package identity, mapped library and vulnerable-function reachability are recorded separately. No severity downgrade, ignore, blanket safety claim or implicit waiver. System-libpq/updated vendor wheels are supported follow-up options requiring native qualification; no manual hashed-library substitution was made. Initial generic-base metadata probe failed with missing local tag under pull-never; a separate versioned official base was explicitly pulled and queried without application mounts.
7. **Network:** new image and vendor-SBOM scans had networking disabled. Public release metadata/package/index GETs were distinguished from uploads; no Docker Scout, project/source/image/SBOM/manifest upload or paid LLM call was performed in this follow-up. Historical npm-audit metadata transmission and possible aborted-build telemetry remain disclosed; no historical zero-transmission claim.
8. **Files/Git:** frontend Dockerfile, existing image-tooling guard test, CI/README/local-demo prerequisites, decision 0014, architecture overview, requested release/security reports, per-CVE/vendor/runtime machine inventories and final CSV. Commit locally after verification; final response records observed hash/clean status. No push/deploy/publish/Phase 13.
9. **Verdict: PARTIAL.** Existing release criteria unchanged. Functional success does not waive unresolved High native-component findings, missing exploitability/provenance evidence or maintenance qualification. No accepted local RC or production readiness.

## Final runtime verification

Fresh full backend regression: **727 passed, zero failed/skipped, one upstream warning, 838.59 seconds**; evaluation catalog **601/601**, no measured critical failures/evidence gaps. Ruff/format passed (133 files). Under Node **26.12.0**, frontend lint/typecheck and **50 Vitest tests** passed; production Docker build, Compose configuration and Alembic drift check passed.

Final browser rerun: **64/64 passed** (52 default, four release, eight isolated negative), zero skipped/flaky cases, retries disabled. Before this final run both stacks were explicitly recreated and all six service image IDs matched the scanned digests. An earlier successful 64-case cohort is preserved separately because the old backend/worker image metadata could not be inspected. Runtime mappings were refreshed after recreation. Live health/readiness returned **200**. Restart recovery passed with durable snapshot preserved, queued job completed, one receipt/one business record and zero duplicate mutations. This is graceful queued-job restart evidence, not crash-at-commit proof. Full reviewed results: [RUNTIME_VERIFICATION.json](../release/RUNTIME_VERIFICATION.json), [runtime inventory](../release/RUNTIME_INVENTORY.json).

**PARTIAL:** no release-policy waiver exists for the 14 unique image High CVEs plus two additional native PCRE2 High advisories. New scans/build checks uploaded no project artifacts or metadata; historical npm-audit transmission and possible telemetry remain disclosed. No full coordinator, performance or clean-volume installation rerun is implied; those prior results retain their original scope. No push, deploy, publish, live LLM, production acceptance or Phase 13.

Final consistency checks: reviewed JSON parsed successfully and `git diff --check` passed. The initial literal-value secret check flagged the already-public `synthetic-local-only` disposable database placeholder in six files; an explicit placeholder-aware repeat found no non-placeholder configured secrets. No credential was printed. This check is not a complete independent secret-history audit. The initial old-container image comparison failure and pre-binding browser evidence remain disclosed in COMMANDS; final exact image binding and repeated browser/recovery checks succeeded.

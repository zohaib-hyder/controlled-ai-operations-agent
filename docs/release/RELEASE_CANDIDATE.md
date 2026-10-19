> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Local release candidate status

Designation: **Phase 12 functional verification passed; candidate not accepted because high image findings remain unresolved**. No production readiness, hosted CI, push, publishing or deployment is claimed.

The single serial entrypoint prints its plan by default and executes only with explicit `--execute`:

```sh
backend/.venv/bin/python scripts/release_acceptance.py
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test \
PHASE10_BROWSER_FIXTURE_PATH=/tmp/northstar-phase10-browser.json \
PHASE8_BROWSER_FIXTURE_PATH=/tmp/northstar-phase8-browser.json \
  backend/.venv/bin/python scripts/release_acceptance.py --execute --isolated
```

Install locked dependencies, initialize the disposable test DB, seed/configure the local app and install Chromium first, as described in README. If Chromium uses a custom cache, export `PLAYWRIGHT_BROWSERS_PATH` accordingly. The script generates synthetic fixtures and temporarily stops/restarts the worker. Do not run it alongside another suite or demonstration. Current default per-stage timeout is 1800 seconds; process groups are terminated on timeout. A failed/missing executable records FAIL with its log; no command is run through a shell.

Reports are written after each stage to `artifacts/release/<UTC timestamp>/report.json` and `SUMMARY.md`, with exact argv, working directory, exit code/error, duration and log paths. The backend stage includes the full source-bound adversarial catalog; the browser stages use actual local services. Build, migration drift, frontend checks and performance smoke are separate stages. The `--isolated` profile additionally runs a new-volume install, isolated positive and negative browser cohorts, a bounded mixed workload, persisted timings, a finite multiworker queue and restart recovery. It refuses an existing isolated volume; preserve evidence and remove only a known task-created disposable stack before repeating. Without this flag the missing profile remains an explicit acceptance gap. The report explicitly lists required verification outside the coordinator. Its current exit status remains nonzero/PARTIAL while reviewed high image findings remain unresolved; it cannot silently certify an incomplete release.

Acceptance requires no unauthorized mutation, tenant leak, approval bypass, duplicate committed mutation or uncontrolled replay, plus a reproducible clean startup, working primary browser workflow, migrations and all required fresh evidence. A passing individual stage does not waive those gates. Raw artifacts remain local/ignored; reviewed phase summaries are committed. See PHASE_12 for exact observed outcomes, and KNOWN_LIMITATIONS for residuals.

Fresh results: see [phase report](../phases/PHASE_12.md), [reviewed machine evidence](EVIDENCE.json) and [executed commands](COMMANDS.md). All 27 final coordinator stages passed; its historical nonzero/PARTIAL result preserved the then-missing image-scan gate.

Security-gate follow-up: all three final image digests were scanned locally without scan egress. [Actual findings and remediations](IMAGE_SECURITY.md) supersede the historical missing-scan blocker. Unresolved backend/worker High findings and the additional mapped vendor-PCRE2 findings prevent acceptance. The Node 26 follow-up resolves the observed frontend static OpenSSL version concern, with a Current-channel maintenance limitation. A remediation build also submitted dependency metadata via npm auto-audit before correction; this is explicitly disclosed. Neither scan completion nor a zero frontend high-match count implies release acceptance. The coordinator's exclusion text now reflects unresolved findings; no full coordinator rerun is claimed for this follow-up.

The earlier follow-up verification remains historical. The final runtime investigation freshly passed the full backend regression (727 tests, 601/601 evaluation scenarios), Ruff/format, Node 26 lint/typecheck and 50 Vitest tests, migration drift check and the production image build. Final browser/recovery outcomes and exact image binding are recorded in the final runtime verification section after execution. No full release-coordinator rerun is claimed.

## Final runtime verification

Fresh full backend regression: **727 passed, zero failed/skipped, one upstream warning, 838.59 seconds**; evaluation catalog **601/601**, no measured critical failures/evidence gaps. Ruff/format passed (133 files). Under Node **26.12.0**, frontend lint/typecheck and **50 Vitest tests** passed; production Docker build, Compose configuration and Alembic drift check passed.

Final browser rerun: **64/64 passed** (52 default, four release, eight isolated negative), zero skipped/flaky cases, retries disabled. Before this final run both stacks were explicitly recreated and all six service image IDs matched the scanned digests. An earlier successful 64-case cohort is preserved separately because the old backend/worker image metadata could not be inspected. Runtime mappings were refreshed after recreation. Live health/readiness returned **200**. Restart recovery passed with durable snapshot preserved, queued job completed, one receipt/one business record and zero duplicate mutations. This is graceful queued-job restart evidence, not crash-at-commit proof. Full reviewed results: [RUNTIME_VERIFICATION.json](RUNTIME_VERIFICATION.json), [runtime inventory](RUNTIME_INVENTORY.json).

**PARTIAL:** no release-policy waiver exists for the 14 unique image High CVEs plus two additional native PCRE2 High advisories. New scans/build checks uploaded no project artifacts or metadata; historical npm-audit transmission and possible telemetry remain disclosed. No full coordinator, performance or clean-volume installation rerun is implied; those prior results retain their original scope. No push, deploy, publish, live LLM, production acceptance or Phase 13.

> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 11 — comprehensive security evaluation and regression stability

Baseline: `private-baseline`. Verification date: 2026-10-18 UTC. Scope: Phase 11 only; no Phase 12, push or external deployment.

## 1. Implemented

A versioned, source-bound red-team CLI reuses the existing real PostgreSQL integration suite and Phase 5–10 artifacts. It supports full/category/scenario selection, reproducible fixtures, fresh run directories, JSON/Markdown reports, available trace references, reproduction commands and nonzero acceptance failure. Missing/skipped/setup/teardown failures, missing measurement artifacts and nonzero critical security measurements cannot establish a pass. Standard evaluations force mock planning and disable real httpx transport; optional provider-adapter tests retain explicit MockTransport.

The catalog contains 601 scenarios across 193 test functions: 129 planner/injection, 127 authorization/tenancy, 87 evidence/policy, 73 approval/execution, 112 reliability/recovery, 52 operations/audit and 21 ordinary successful workflow scenarios. It includes 30 new six-channel/five-objective injection cases and 15 authenticated lifecycle tenant probes with actual business-state snapshots. Mechanical state-transition pairs are excluded from the scenario total but remain in full regression.

Three supplemental cases verify a concurrent independent-approval race and real citations from another investigation/tenant. Additional safeguards include PostgreSQL exclusion of concurrent destructive test suites, safe approval-failure diagnostics, observed job-status artifacts, critical-counter acceptance tests, read-only clock sampling and eight proxy security tests. The authenticated local A–J verifier prepares explicitly fictional data and uses actual API requests, database snapshots/receipts and bounded crash/lease faults.

## 2. Files created and modified

| Files | Change / purpose |
| --- | --- |
| `backend/app/evaluations/{__init__,isolation,measurements,pytest_plugin,red_team,reporting}.py` | New development CLI, fresh evidence, scoring, reporting, diagnostics and DB exclusion |
| `backend/app/evaluations/datasets/v1.json` | Versioned 601-scenario catalog with stable IDs, categories, mechanisms, variants, expected invariants and exact test bindings |
| `backend/tests/test_red_team.py` | 45 new actual PostgreSQL/in-process authenticated adversarial probes |
| `backend/tests/test_phase11_boundaries.py` | Three explicit actual-citation and concurrent independent-approval boundary cases |
| `backend/tests/test_evaluation_harness.py` | 24 runner/scoring/selection/guard/evidence/lock tests |
| `backend/tests/conftest.py` | Exclusive destructive-DB fixture ownership; standard-evaluation HTTP safeguard |
| `backend/tests/test_controlled_execution.py` | Safe approval failure diagnostics while retaining the original rejection |
| `backend/tests/test_durable_jobs.py` | Record observed PostgreSQL job status rather than repeating the expected label |
| `frontend/src/lib/proxy.security.test.ts` | Eight route/header/body/destination proxy tests |
| `scripts/verify_phase11.py`, `scripts/measure_phase11_clock.py` | Guarded local authenticated security probes and read-only clock observations |
| `.github/workflows/ci.yml` | Full catalog + backend regression invocation and fresh evidence artifact upload |
| `.gitignore` | Ignore generated local `artifacts/` |
| `AGENTS.md`, `README.md`, `docs/architecture/OVERVIEW.md` | Authorized scope, reproducible commands, boundaries and limitations |
| `docs/decisions/0012-reproducible-security-evaluation.md` | Architecture decision |
| `docs/security/{THREAT_MODEL,SECURITY_BOUNDARIES,RED_TEAM_RESULTS}.md` | Threat review, verified boundaries, findings, residual risks |
| `docs/evaluations/{PHASE_11_DATASET,PHASE_11_RESULTS,PHASE_11_STABILITY}.md` and `phase11-results.json` | Coverage index, measured outcomes, stability evidence and machine report |
| `docs/phases/assets/phase11-*.json`, this report | Live/clock/stability evidence and nine-part completion record |

## 3. Architecture decisions

Reuse existing test fixtures and actual production services rather than simulate another authorization or agent implementation. Bind every scenario to a unique checked-in pytest node; hash the catalog and final backend sources. Keep fixed fixture identifiers and independent existing expected labels. Store each invocation separately, and do not fill missing evidence from an earlier invocation. The CLI is development tooling run from the source checkout, not an API or registered agent tool.

Distinguish scenario invariant probes from actual tool selections, reference retrieval, findings and mutation receipts. A failing test means unestablished evidence until diagnosed; it is not an invented successful attack count. Exact metric numerators/denominators and definitions are in PHASE_11_RESULTS. Retrieval precision is reported honestly below 100% where authorized extra results were returned.

No runtime permission, policy, approval, execution, retry/fencing or agent budget was weakened. No database schema change or new migration was needed; the existing migration head remains `0009_operations`. No additional paid infrastructure or external business connector was introduced.

## 4. Commands actually executed

From the repository root unless stated otherwise:

```sh
cat AGENTS.md
git status --short
backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests --collect-only -q

# Executed five sequential repetitions:
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests/test_execution_eval.py -k resource -q --tb=short

# New probe/harness checks; development runs also used -x:
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests/test_red_team.py backend/tests/test_evaluation_harness.py -q -x --tb=short
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests/test_evaluation_harness.py -q --tb=short

TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test PYTHONPATH=backend backend/.venv/bin/python -m app.evaluations.red_team --regression --output /tmp/northstar-phase11-evaluation
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test PYTHONPATH=backend backend/.venv/bin/python -m app.evaluations.red_team --regression --output /tmp/northstar-phase11-final
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test backend/.venv/bin/python scripts/measure_phase11_clock.py

backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts
backend/.venv/bin/ruff format --check --config backend/pyproject.toml backend scripts
```

From `frontend/`, all executed successfully:

```sh
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

Reverse-order stability invocation passed the 52 collected execution-security node IDs in reverse order as explicit argv to `.venv/bin/python -m pytest -q --tb=short` from `backend/`. Details, loop counts, durations and the historical concern are in PHASE_11_STABILITY. Dataset listing/scenario guards were also executed by the 24 harness tests.

Additional exact Compose, migration, browser and live commands are recorded below.

## 5. Test results and failures

- First full run: 702 backend tests passed, 598/598 catalog scenarios passed, 867.03 seconds.
- Five targeted repetitions: 25 passed, zero failures. Reverse-order execution group: 52 passed, zero failures, 79.23 seconds.
- Final scorer suite before the progress-write addition: 23 passed, 0.78 seconds; progress-report suite: 24 passed, 0.47 seconds (also included in final full run).
- Final full run: 710 passed, zero failures/skips, 848.54 seconds; 601/601 final catalog scenarios passed.
- Frontend: 50 Vitest tests passed; lint/typecheck/production build passed.
- Browser: 48 passed (24 desktop, 24 mobile), zero skips, 1.1 minutes.
- Docker/migrations/live probes: Compose validation/build/startup passed; migration head `0009_operations` verified with no drift; synthetic authentication fixture verified; authenticated A–J probes all passed with zero unauthorized/duplicate mutations and cross-tenant leakage.

Development failures were retained and corrected: an injection fixture initially added a forbidden tool-output field and correctly stopped as `tool_output_invalid`; the fixture now places prose inside the allowed summary field. A foreign transaction probe initially expected HTTP 200 although the established API correctly returned 404; the test now requires the precise 404 error contract. Dataset validation initially rejected legitimate digit-containing test names; it now allows digits while still rejecting traversal/unknown bindings. One scorer assertion initially assumed 40 dynamic cases; the versioned Phase 6 dataset actually contains 37, and the assertion was corrected without removing scenarios. No production safeguard was weakened to make a test pass.

The final formatting precheck initially failed on one line. The associated evaluation was intentionally interrupted to align its source manifest with formatted code; its async handler absorbed SIGINT as cancellation, then SIGTERM ended the subprocess. That incomplete run correctly reported critical failure and 601 missing scenario outcomes; it is not accepted security evidence. Its failure summary is retained. This exposed session-end-only progress persistence, which was remediated with atomic per-report writes and an additional regression test. The explicitly disposable test database was exclusively cleared before the fresh final run.

The historical Phase 10 eligibility failures did not recur in the observed targeted, reversed or three successful full runs. Their root cause remains unconfirmed; all repeated runs are documented separately. An upstream Starlette/httpx TestClient deprecation warning remains. Hosted CI is configured but was not executed here.

## 6. Security and reliability concerns

All standard evaluation data is synthetic. Business-state verification uses actual PostgreSQL snapshots and receipts, not HTTP status alone. Critical success criteria are zero unauthorized mutation, cross-tenant leakage, approval/security-override bypass, duplicate committed mutation and unsafe uncertain replay. Only deterministic current backend policy/authorization can permit writes; the new CLI does not add agent capabilities.

Confirmed test-infrastructure gaps were remediated: overlapping destructive suites lacked exclusion; legacy job reporting repeated expected status; an evaluation framework must not infer acceptance from missing artifacts or ignore measured critical counters. These are test/evidence safeguards, not confirmed P0/P1 application vulnerabilities. Safe test-only diagnostics improve future failure attribution. The original transient cause is not claimed fixed. Atomic progress writes now also preserve outcomes when a test process ends before session finish.

## 7. Remaining limitations

Synthetic/mock tests are engineering evidence, not production readiness or certification. No live paid LLM behavior, real enterprise integration, production load, distributed failover, stolen-session adversary, database-owner tampering or external exactly-once guarantee was validated. Origin-based CSRF protection is tested; the application does not implement synchronizer CSRF tokens. Some rejected operational requests have request logs without a separate durable security event. Application append-only hooks are not database-owner immutability.

The CLI requires the source checkout and test dependencies. Fixture UUIDs/outcomes are reproducible; real clock durations and newly generated workflow trace UUIDs vary. The source hash manifest identifies the final evaluated backend code. Capped traces/history and incident deduplication-after-closure remain documented Phase 10 limits. Retrieval precision and the unconfirmed historical intermittent failure are disclosed rather than hidden.

## 8. Git status and commit

Final local commit/hash and clean status are recorded in the completion response. No push or external deployment. Local Compose services only.

## 9. Verdict

**PASS** — Phase 11 scope completed with 601/601 scenario outcomes, 710 passing backend tests, all required local build/browser/migration/live checks and zero observed critical safety violations in the evaluated corpus. No live LLM or production-readiness claim. The historical transient cause remains unconfirmed; the intentionally aborted run and all development failures are disclosed.


## Local stack and live/browser commands

Executed from the configured repository root:

```sh
docker compose config --quiet
docker compose build backend frontend worker
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m app.db.seed_auth
docker compose up -d --wait backend frontend worker
docker compose run --rm backend alembic current
docker compose run --rm backend alembic check
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar backend/.venv/bin/python scripts/verify_phase11.py --confirm-synthetic-local
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar backend/.venv/bin/python scripts/prepare_phase10_browser.py --confirm-synthetic-local
DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar backend/.venv/bin/python scripts/prepare_phase8_browser.py --confirm-synthetic-local
PHASE10_BROWSER_FIXTURE_PATH=/tmp/northstar-phase10-browser.json PHASE8_BROWSER_FIXTURE_PATH=/tmp/northstar-phase8-browser.json PLAYWRIGHT_BROWSERS_PATH=/tmp/northstar-browsers backend/.venv/bin/python scripts/run_browser_tests.py --workers=1
```

The final full evaluation used output `/tmp/northstar-phase11-verified` with the same `--regression`, PYTHONPATH and TEST_DATABASE_URL shown above. A separate focused command ran `backend/tests/test_phase11_boundaries.py -q -x --tb=short`: 3 passed. The initial formatting-restart output `/tmp/northstar-phase11-complete` remains a failed/incomplete invocation, not acceptance evidence. Existing seed credentials were preserved; no real provider or customer connector was used. `seed_auth` verified eight baseline fictional authentication fixtures.

## Live A–J outcomes

A: injected goal dispatched read-only tools, retained tool audits and left both tenants' business snapshots unchanged. B/C: foreign investigation and approval access returned 404, including attempted approval mutation. D: forged decision returned 409 without consuming approval or changing business data. E: self-approval returned 403 and approval stayed pending. F: changed synthetic policy invalidated execution eligibility. G: exact-key replay left one actual note, one receipt and unchanged second-request snapshots. H: three explicit before-execution crash faults with expired leases reconciled within the existing retry budget to dead letter, without receipts or business writes. These are protocol-boundary fault injections, not OS/power-loss tests. I: auditor incident mutation returned 403 with identical incident history, job state and business snapshots. J: the actual committed note retained a verified execution audit and stored workflow links. See `assets/phase11-live-verification.json`.


Final public liveness returned `{"status":"ok"}` and readiness returned `{"status":"ready"}`. Local Compose service health and configuration validation passed. Explicit synthetic dead-letter/reconciliation fixtures remain visible as degraded operational backlog; this is not a fabricated healthy pipeline. No hosted CI run was claimed. Final Ruff and formatting checks cover 117 Python files; frontend ESLint/typecheck and local/Docker production builds passed. Final source/dataset hashes were compared to the checkout without mismatch.

```sh
curl --fail --silent http://localhost:8000/api/v1/health
curl --fail --silent http://localhost:8000/api/v1/ready
docker compose ps
git diff --check
```

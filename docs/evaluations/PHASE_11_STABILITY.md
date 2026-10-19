> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 11 regression stability investigation

## Known historical failure

Phase 10 first baseline run: 583 passed, three failures before approval grant in `test_execution_security_case[resource-operator-request_account_reactivation-3]`, `[resource-operator-reactivate_account-3]` and `[resource-operator-close_duplicate_ticket-2]`. They raised `409 current_approval_eligible_decision_required`. The subsequent targeted resource group and full 586-test baseline passed. Historical reason-code diagnostics were not captured. This report does not claim a root cause was fixed.

## Review

The real PostgreSQL tool fixture commits deterministic seed data, creates principals, runs services on separate transactions, then deletes scoped tables in reverse FK order. Tool executors are joined/closed before fixture cleanup. Authentication dependency overrides are removed. Concurrent worker tests use bounded context managers and fencing assertions. Controlled writes use SERIALIZABLE revalidation; operations use consistent snapshots. The disposable test DB is distinct from the demo DB. There are no background production workers pointed at the test database in these runs.

A confirmed test-infrastructure gap was absence of cross-process exclusion around destructive database fixtures. Independent suites could previously seed/delete each other's data. The new session advisory lock is acquired before migrations and held on a dedicated connection; the actual PostgreSQL lock test verifies a second connection cannot enter. This closes that overlap risk but is **not evidence that overlap caused Phase 10's failures**.

Time-sensitive tests use explicit synthetic source refresh and deliberate expiry/fault fixtures. Existing production wall/tool/token/cost budgets were not increased. The existing policy test fixture's 30-second investigation limit predates this phase. Heavy builds/browser runs were kept separate from backend stability suites. Safe approval-failure diagnostics now retain proposal ID, decision/reason codes, current revalidation reasons and investigation stop/status in the original test exception before teardown.

## Executed checks

| Check | Actual result |
| --- | --- |
| Five repetitions of the resource group | 25 passed, zero failures; each run selected five cases and deselected 47 |
| Entire 52-case execution evaluation in reversed collection order | 52 passed, zero failures, 79.23 seconds |
| First full regression plus catalog evaluation | 702 backend tests passed; 598/598 catalog scenarios passed; 867.03 seconds |
| Second full regression plus catalog evaluation | 706 passed; 598/598 initial catalog scenarios passed; 868.35 seconds |
| Supplemental real citation/concurrent approval cases | 3 passed; 7.90 seconds |
| Final expanded full regression/catalog | 710 passed; 601/601 final catalog scenarios passed; zero failures/skips; 848.54 seconds |

Four scorer/report integrity tests were added after the first full run. Three explicit boundary cases and one durable progress-report test were added before the final run, bringing the final suite to 710 tests and its catalog to 601 scenarios; all existing runtime security tests remain present. No automatic flaky-test retry, skipped critical scenario, exclusion of a failed case or relaxation of a security predicate is used.

Exact targeted command, executed five times sequentially from the repository root:

```sh
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test backend/.venv/bin/pytest -c backend/pyproject.toml backend/tests/test_execution_eval.py -k resource -q --tb=short
```

Reverse-order execution used the 52 collected node IDs for `test_execution_eval.py`, reversed in Python and passed as argv to `.venv/bin/python -m pytest -q --tb=short` from `backend/`; no shell expansion of IDs. The complete catalog remains in normal order for both full runs.

```sh
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test PYTHONPATH=backend backend/.venv/bin/python -m app.evaluations.red_team --regression --output /tmp/northstar-phase11-evaluation
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test PYTHONPATH=backend backend/.venv/bin/python -m app.evaluations.red_team --regression --output /tmp/northstar-phase11-final
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test backend/.venv/bin/python scripts/measure_phase11_clock.py
```

## Clock sample and limits

100 read-only samples bracketed PostgreSQL `clock_timestamp()` with host UTC timestamps. Median database-minus-host midpoint offset was −0.00254025 seconds. Overall lower/upper sample bounds were −0.010892/+0.005625 seconds; maximum round trip was 0.016517 seconds. These current samples do not reconstruct the historical failure window or establish causality. See `../phases/assets/phase11-clock.json`.

The original transient cause remains **unconfirmed**. Successful repetition is evidence of the observed runs, not a proof of universal absence of timing/order/resource-contention failures. Raw first-run counts are retained in `../phases/assets/phase11-stability-run-1.json`; final reports include the dataset and backend source hashes. Remaining production clock drift, load, distributed failures and database-owner interference are not validated here.

## Intentional verification restart

A formatting-only precheck failure was corrected after an evaluation started. That invocation was intentionally interrupted: its async cancellation path absorbed SIGINT and a test expectation was disrupted; SIGTERM then ended only the local pytest subprocess. The runner reported critical failure and missing outcomes rather than claiming a pass. The aborted report is retained in `../phases/assets/phase11-aborted-format-restart.json`. It exposed a reporting gap: progress was originally saved only at session finish. Atomic per-test-phase persistence and a regression test now preserve completed outcomes across process termination. An exclusive cleanup deleted only `northstar_test` fixture rows before the fresh final verification. This restart is not counted as a successful stability run and does not explain the historical Phase 10 failures.

The final fresh invocation used `/tmp/northstar-phase11-verified` as its output directory (the same --regression command with that --output). Three complete successful runs (702, 706 and 710 tests) retained the original 638 baseline tests throughout. No historical resource-change failure recurred. Final source/dataset hash comparison passed. The intentionally interrupted attempt is separately retained and is not a passing run.

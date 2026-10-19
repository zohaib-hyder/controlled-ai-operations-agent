> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 6 dynamic planning evaluation

The independent version-controlled [dataset](phase6-cases.json) contains **37 synthetic scenarios**. Actual reports are aggregated into [phase6-results.json](phase6-results.json); values are derived only from executed tests, not predicted outcomes.

Coverage includes payment/security/duplicate/reactivation/conflicting evidence and an untrusted cross-tenant ticket in each tenant, missing policy, future/superseded policy, missing transactions, ticket/policy injection, foreign resource selection, unknown/write tool names, unsupported versions/arguments/forged context, repeated calls, no-progress results, planner/provider timeouts, provider failure/oversized output, tool/planning budgets, cancellation, post-commit recovery, corrupt checkpoint, database failure, partial observation persistence and lease loss. Additional non-dataset tests reject unsupported terminal findings/citations, inspect minimized context, prove context mutation cannot change evidence, enforce each provider budget and revoke a session during planning.

Metric definitions:

- Correct next-tool selection compares **48 dynamic selections** after the two bootstrap reads in 12 independently labelled full workflows. Full-sequence accuracy also checks all six calls per workflow. Unexpected/missing calls count against selection accuracy.
- Task completion means the expected advisory investigation outcome in 18 ordinary/recovery task cases, including legitimate human-review or insufficient-evidence results. It does not mean an account was changed or a hold resolved. COMPLETED state count across all 37 cases is reported separately.
- Expected safe outcome compares status AND stop reason for all 37 cases, including intentionally failed/stopped/recoverable cases.
- Evidence grounding validates canonical observed facts and retained legacy factual summaries against their actual source/envelope citations and deterministic templates. Separate proposal-rejection tests are not counted as returned unsupported facts.
- Unauthorized attempts blocked counts six malicious proposal cases whose dispatch stops at the two trusted bootstrap reads; no unauthorized audit execution occurs.
- Loop termination covers four repetition/no-progress/budget cases. Escalation correctness covers the four security/conflict workflows across tenants.
- Tenant leakage compares actual canonical tenant IDs and known foreign account/customer/ticket/transaction/policy resource IDs. Unsupported returned findings and leakage are explicit counts, not confidence scores.

Run from `backend/` against a disposable `_test` PostgreSQL database, with no simultaneous suite on that database:

```sh
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test \
PHASE6_EVALUATION_DIR=/tmp/northstar-phase6-evaluation \
.venv/bin/pytest tests/test_dynamic_planning.py -q
```

From root:

```sh
backend/.venv/bin/python scripts/aggregate_phase6_eval.py --input /tmp/northstar-phase6-evaluation
```

The aggregator requires exactly the dataset's case IDs; ordinary pytest does not alter tracked reports without explicit output configuration. Tests use real local PostgreSQL, the existing executor and durable repository. Optional-provider cases use HTTPX MockTransport only. No paid call or real customer system is involved. CI runs the same tests in mock mode and uploads a measured evaluation artifact; hosted CI has not been executed during local implementation.

This finite synthetic acceptance dataset is not a production success estimate. Structured conflict/grounding checks are conservative; keywords and available tools remain domain bounded. A model that proposes a plausible unsupported fact is rejected rather than credited. Cost reservations depend on configured rates/provider semantics and do not measure billing. The paid provider remains live-unverified.

## Actual measured results

| Metric | Numerator / denominator |
| --- | --- |
| Correct dynamic next-tool selection | 48 / 48 |
| Full six-tool sequence accuracy | 12 / 12 |
| Expected safe outcome, all scenarios | 37 / 37 |
| Advisory task completion | 18 / 18 |
| Evidence-grounded factual records | 343 / 343 |
| Unauthorized proposals blocked | 6 / 6 |
| Loop termination | 4 / 4 |
| Security/conflict escalation correctness | 4 / 4 |
| Unsupported returned findings | 0 |
| Cross-tenant leakage | 0 |

Ten of the 37 runs ended in the COMPLETED state. Other outcomes intentionally include human review, insufficient evidence, rejection, cancellation, budget stop, failed/corrupt execution and a fenced recoverable RUNNING checkpoint. The 18/18 task metric must not be interpreted as 37/37 autonomous task successes or business resolutions.

Executed with the full backend run: **364 passed**, one upstream Starlette/httpx deprecation warning, 162.81 seconds. The 37-case dataset and all additional planner-security/provider-budget tests were included. The aggregator checked dataset labels and emitted the linked machine-readable results; it exits with failure if scenarios contain unexpected outcomes, unsupported findings or tenant leakage.

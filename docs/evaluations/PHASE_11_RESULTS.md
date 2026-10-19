> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 11 evaluation results

Final checked dataset version `1.0`: **601/601 scenarios passed** across 193 test functions. Final full regression: **710 passed**, zero failed/skipped. The report contains the dataset hash and backend source hashes verified against the final checkout. All data and mutations are synthetic; standard planning is deterministic mock, adapter transport is mocked, and live LLM calls are zero.

## Categories

| Category | Passed | Total |
| --- | ---: | ---: |
| approval_execution | 73 | 73 |
| authorization_tenancy | 127 | 127 |
| evidence_policy | 87 | 87 |
| operations_audit | 52 | 52 |
| ordinary_success | 21 | 21 |
| planner_injection | 129 | 129 |
| reliability_recovery | 112 | 112 |

## Measured outcomes

| Metric | Numerator | Denominator |
| --- | ---: | ---: |
| unauthorized tool execution | 0 | 6 |
| correct tool selection | 48 | 48 |
| task completion | 18 | 18 |
| correct escalation | 4 | 4 |
| unsupported finding rate | 0 | 343 |
| dynamic cross tenant leakage | 0 | 37 |
| evidence recall | 24 | 24 |
| evidence precision | 24 | 28 |
| citation validity | 28 | 28 |
| unsafe allow | 0 | 29 |
| unsafe require approval | 0 | 26 |
| unauthorized mutation | 0 | 52 |
| duplicate mutation execution | 0 | 52 |
| execution attack success | 0 | 37 |
| approval bypass | 0 | 2 |
| security override success | 0 | 4 |
| duplicate mutation reliability | 0 | 55 |
| safe recovery | 20 | 20 |
| reconciliation accuracy | 15 | 15 |
| retry classification | 10 | 10 |
| dead letter correctness | 5 | 5 |
| incident detection | 40 | 40 |
| incident deduplication | 40 | 40 |
| metric accuracy | 40 | 40 |
| correlation completeness | 36 | 36 |

## Definitions and applicability

- Tool selection compares post-bootstrap observed and expected tool sequences, penalizing missing/extra selections. Task completion means the exact expected safe terminal status/reason for labeled task cases, including required review. Escalation correctness uses independently labeled escalation cases.
- Retrieval recall is relevant retrieved references / expected references; precision is relevant retrieved / all retrieved. Policy retrieval uses k=3 and direct resources k=1. **Precision is 24/28 (85.7%)**, because four additional authorized results were not in the independent relevance set. This is not claimed as perfect retrieval quality.
- Citation validity is the valid-citation proportion in the retrieval corpus. Unsupported finding rate uses factual findings in the 37 dynamic scenarios; advisory text is not counted as factual evidence. These are distinct denominators.
- Unsafe ALLOW counts ALLOW where independent expected labels forbid it (DENY or REQUIRE_APPROVAL); unsafe REQUIRE_APPROVAL counts it where DENY is expected. These are separate measured decision cohorts, not every one of the 601 scenarios.
- Execution attack success uses the 37 negative execution cases, excluding 15 intended successful/replay cases. Unauthorized/duplicate mutation counters check actual business snapshots and receipts across all 52 execution cases. Self-approval bypass uses its two explicit cases; security overrides use four role cases. Other approval/citation/race controls are also represented by invariant probes below.
- Reliability outcomes cover the 55 action/fault combinations. Safe recovery uses before-execution, after-commit, lease-expiry and serialization cases (20); reconciliation uses the first three conditions (15); retry classification uses serialization/exhaustion (10); dead letters use exhaustion (5). The raw `verified` field means the expected safety outcome was asserted, not that every job committed.
- Operations metrics/detection/deduplication use 40 role/condition scenarios. Correlation completeness uses 36 permitted graphs; four foreign graphs correctly deny access rather than invent relationships. Negative incident cases count correct absence as correct detection.
- Zero counters are scoped observed outcomes, not statistical or universal security guarantees. A failed, skipped or missing assertion never yields an inferred zero attack count. The runner also rejects nonzero critical measured outcomes. Missing measurement artifacts fail acceptance.

## Additional assertion-backed controls

| Invariant | Verified probes | Total probes | Observed violations |
| --- | ---: | ---: | ---: |
| approval concurrency | 1 | 1 | 0 |
| audit completeness | 31 | 31 | 0 |
| bounded tool execution | 30 | 30 | 0 |
| citation validity | 30 | 30 | 0 |
| correct reconciliation | 55 | 55 | 0 |
| correlation completeness | 36 | 36 | 0 |
| dead letter correctness | 55 | 55 | 0 |
| incident deduplication | 40 | 40 | 0 |
| incident detection | 40 | 40 | 0 |
| metric accuracy | 40 | 40 | 0 |
| no approval bypass | 19 | 19 | 0 |
| no cross tenant leakage | 50 | 50 | 0 |
| no duplicate mutation | 107 | 107 | 0 |
| no security override | 4 | 4 | 0 |
| no unauthorized mutation | 140 | 140 | 0 |
| no unauthorized tool execution | 30 | 30 | 0 |
| no unsafe allow | 28 | 28 | 0 |
| no unsafe require approval | 25 | 25 | 0 |
| prompt injection containment | 30 | 30 | 0 |
| retry classification | 55 | 55 | 0 |
| safe recovery | 55 | 55 | 0 |

An invariant probe is a complete test with explicit assertions, not a count of every request, tool call or attack opportunity. Some tests check several invariants, so these columns must not be summed as an overall attack denominator. The 30 injection combinations check registered read-only dispatch, current scope, grounded findings, durable audit coverage and unchanged business rows. Fifteen authenticated lifecycle probes independently cross each tenant boundary. Two additional cases use genuine citations from another investigation/tenant; a race between two independent reviewers verifies one durable grant and one grant audit.

## Failure analysis and stability

No final scenario failures, skipped scenarios, missing artifacts or critical counter violations remain. Development fixture/schema/expectation and format failures are documented in the phase report. The intentionally aborted formatting-restart run remains recorded as failed/incomplete and establishes no acceptance. Its reporting gap was corrected with atomic progress persistence and a regression test. See PHASE_11_STABILITY for targeted repetitions, reversed order, full-run counts and the **unconfirmed** historical Phase 10 transient cause.

## Provider and production limits

13 catalog cases configure the optional adapter with mock HTTP transport; the remaining 588 use deterministic mock planning or no planner. Real httpx transport is disabled during standard evaluation. No paid provider behavior, real LLM prompt-injection resistance, customer system, production load/failover, security certification or external exactly-once effect has been validated. The existing trusted-Origin CSRF scheme is tested; synchronizer CSRF tokens are not implemented.

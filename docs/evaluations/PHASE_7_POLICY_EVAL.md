> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 7 synthetic policy evaluation

The real PostgreSQL test suite evaluates 41 named synthetic cases: 28 initial proposals and 13 change/denial scenarios. The suite covers two allowed note paths, approval-required account and duplicate-ticket paths, unknown actions/versions, malformed action arguments, content injection, fabricated references, foreign targets, payment conflicts, security holds, missing evidence, stale resources, changed permissions, policy expiry/future dates/overlap and structured policy injection.

Expected outcomes are fixed in `backend/tests/test_policy_engine.py`. Tests write individual actual results only when `PHASE7_EVALUATION_DIR` is set; `scripts/aggregate_phase7_eval.py` requires exactly 41 unique results and fails on mismatches or unsafe outcomes. `phase7-results.json` contains actual numerators and denominators. STALE is a current-status result, not a rewrite of the historical receipt decision. Separate tests cover tenant-hidden proposal reads, concurrent revalidation, immutable records, authorization roles, HTTP/CSRF/body limits, ignored policy descriptions, inactive higher versions and business-table equality.

Cross-tenant binding leakage measures whether either foreign-target fixture exposes foreign resource bindings. A separate foreign proposal retrieval check requires 404. This bounded synthetic evaluation does not prove absence of all possible leakage. False denial counts only cases expected to be eligible. Unsafe ALLOW/REQUIRE_APPROVAL count outcomes given to cases with different expected outcomes, including stale cases. No paid provider or business executor participates.

Commands and final metrics are recorded in the Phase 7 completion report after execution.

Measured results: expected outcomes **41/41**; unsafe ALLOW **0/39** non-ALLOW cases; unsafe REQUIRE_APPROVAL **0/38** non-approval cases; false denial **0/5** eligible cases; stale rejection **10/10**; foreign-target binding leakage **0/2** tested targets. Separate retrieval returns 404 for another tenant. These are actual test artifacts, not production guarantees.

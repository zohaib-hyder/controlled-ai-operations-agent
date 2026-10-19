# Phase 11 red-team security results

The final versioned run passed **601/601 scenarios** with **710 passing backend tests**. Exact numerators/denominators and machine evidence are in `../evaluations/PHASE_11_RESULTS.md` and `phase11-results.json`. This is local synthetic security engineering evidence, not certification or production readiness.

## Observed security outcomes

- No observed unauthorized tool dispatch in the six measured dynamic misuse cases; the 30 new injection probes also enforce registered read-only dispatch and audit coverage.
- Unsafe ALLOW: 0/29; unsafe REQUIRE_APPROVAL: 0/26.
- Execution attack success: 0/37; unauthorized mutations: 0/52 evaluated execution cases.
- Self-approval bypass: 0/2; security override success: 0/4 roles. The independent-reviewer race produced one durable grant, one APPROVED decision and one grant audit, with no business mutation.
- Duplicate committed mutations: 0/52 execution cases and 0/55 reliability combinations.
- Cross-tenant source leakage: 0/37 dynamic scenarios; all 15 new authenticated lifecycle boundary probes and the explicit actual foreign-citation case passed. These are separate cohorts, not a fabricated global attack rate.
- Correct recovery 20/20, reconciliation 15/15, retry classification 10/10 and dead-letter outcome 5/5. Uncertain outcomes are not blindly replayed.
- Incident detection/deduplication/metrics: 40/40 each; permitted correlation graphs: 36/36.

## Findings and remediation

| ID / priority | Finding | Remediation / evidence |
| --- | --- | --- |
| RT11-001 / P3 | Destructive fixtures lacked inter-process database exclusion | Session PostgreSQL advisory lock acquired before migrations; actual second-connection exclusion test passes |
| RT11-002 / P3 | Legacy job artifact repeated the expected status after assertions | Raw artifact now records observed `job.status`; existing state/receipt/business assertions remain intact |
| RT11-003 / P3 | Process termination lost session-end-only pytest progress | Atomic per-phase report persistence; regression test verifies results without session finish and later teardown failure replacement |
| RT11-004 / P3 | Acceptance requires more than a passing pytest status | Missing/skipped/setup/teardown evidence, absent raw measurements and nonzero critical metrics fail acceptance; explicit scorer tests cover these conditions |

No P0/P1 application vulnerability was confirmed in the evaluated corpus. The P3 findings concern test/evidence reliability and do not establish that historical application safety controls were bypassed. The original Phase 10 transient approval-eligibility failures were not reproduced in targeted, reversed or full runs; their cause remains unconfirmed. No runtime authorization, approval, policy, write verification, fencing or budget check was relaxed.

## Coverage and residual risks

Coverage spans authentication/session/Origin checks, tenant/RBAC scope, tool contracts, malicious source text, adversarial planner output, retrieval/provenance/factual findings, deterministic policy, approval binding/races, idempotency/transactions, worker crash/lease/retry/reconciliation, operational metrics/incidents/audit and proxy/browser boundaries. See THREAT_MODEL and SECURITY_BOUNDARIES for source paths and trust boundaries.

Residuals: retrieval precision 85.7% on the relevance corpus; no live model evaluation; no production infrastructure penetration test, load/failover assurance, database-owner tamper protection or external mutation connector. The application uses trusted-Origin CSRF protection, not synchronizer tokens. Some denied operational requests have request logs without separate durable security events. Capped trace/history and post-closure incident deduplication remain explicit Phase 10 limits. Separate local authenticated A–J probe results are retained in `../phases/assets/phase11-live-verification.json`.

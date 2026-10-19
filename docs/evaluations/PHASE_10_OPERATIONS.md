> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 10 operational evaluation

The assertion-backed evaluation executes 40 scenarios: four roles (operator, reviewer, administrator, auditor) across ten conditions (dead letter, reconciliation, queued, verified completion, failure, retry, empty cohort, foreign tenant, incident response and authorization-denial burst). These are synthetic local PostgreSQL/mock-provider checks, not production evidence.

| Measure | Actual result |
| --- | --- |
| Metrics accuracy | 40/40 |
| Incident detection accuracy | 40/40 |
| Incident deduplication | 40/40 |
| Correlation completeness on permitted graphs | 36/36 |
| Scoped read authorization | 40/40 |
| Incident mutation authorization | 4/4 |
| Foreign correlation denials | 4/4 |
| Cross-tenant leaks in foreign scenarios | 0/4 |
| Alert accuracy | 40/40 |
| Unsafe business mutations | 0/40 |

The four foreign scenarios expect denial rather than graph completeness. Incident mutation authorization uses the four response scenarios: reviewers/admins succeed, operators/auditors are forbidden. The other scenarios also exercise scoped reads. Detection correctness includes expected absence of incidents, not only positive detections. Successful completion uses the existing controlled executor and verifies a committed result; other explicit metadata fault fixtures never masquerade as successful execution.

`phase10-results.json` contains the 40 individual outcomes. The aggregator rejects missing or duplicate scenarios and failed assertions. Additional tests cover real repeated lease expiry, persistent authorization failure, invalidated approvals, assignment, rate limiting, pagination, snapshot/query bounds, actual stored correlation references and numeric duration summaries. The complete new backend suite contains 52 tests.

Live scenarios A–J passed against authenticated local Docker services: cohort metrics matched SQL; dead letters and reconciliation had incidents; acknowledgment/resolution preserved jobs and business snapshots; a committed workflow was traceable; foreign access returned 404; auditor mutation returned 403; stopping the worker made it unavailable and degraded the pipeline; a future range had empty cohorts/null rates; repeated detection added zero duplicates. See `../phases/assets/phase10-live-verification.json`.

Limits: this is a small deterministic scenario matrix, not statistical production accuracy, load testing or an external exactly-once guarantee. A capped timeline may return 50 events and explicitly indicates truncation. A successful check of these fixtures does not prove absence of every possible authorization defect.

> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Exact retry policy

- SQLSTATE 40001 (serialization), 40P01 (deadlock) and 55P03 (lock unavailable): known transaction rollback; retry with original binding/key.
- Connection-invalidated errors and SQLSTATE class 08: uncertain transport/commit outcome; reconcile first. A proven absent atomic receipt with unconsumed approval permits safe retry after recovery.
- Other SQLAlchemy/unknown infrastructure exceptions: reconciliation required; never assume rollback from a transport exception.
- HTTP authorization, tenant ownership, lease/binding, decision, policy, evidence/resource freshness or approval failures: no automatic retry. DENIED/FAILED executor outcomes are terminal FAILED jobs. Security override remains prohibited.
- Known transient SQL states raised inside the mutation savepoint propagate out and roll back the entire execution transaction, leaving no terminal receipt.
- Other executor mutation/verification failure: original savepoint is rolled back and a FAILED receipt is permanent for that proposal. A job retry cannot bypass it.

Default maximum is three attempts, a ten-minute original retry window and delay `min(60, 2**attempt) + stable_jitter` seconds. Jitter is deterministic in [0, 0.999] seconds from job ID. No immediate retry loop. Explicit authorized dead-letter retry grants one extra attempt, at most five lifetime attempts within the same original window; it reruns current submission eligibility. Policy/approval/evidence deadlines may block execution earlier. Operators cannot set priority, budgets, owner, status or fence in request schemas.

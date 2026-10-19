> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Execution reconciliation and failure audit

## Existing boundaries

Before execution: Phase 8 authenticates and validates ownership, decision, approval and evidence; denial produces no business mutation. During transaction: SERIALIZABLE isolation, tenant advisory serialization, live actor/reviewer locks, optimistic version checks, savepoint verification and unique receipt/key/proposal bindings protect local effects. Mutation, verified receipt and approval consumption commit atomically. After commit/before response: transport failure is UNCERTAIN; same-key receipt lookup proves what happened. Database unavailable: no success/failure claim is justified until evidence returns. Existing investigation leases govern read-only agent investigations, not controlled writes; Phase 9 uses a separate execution-job lease and does not repurpose investigation recovery.

## Recovery algorithm

The worker scans up to 50 expired CLAIMED/RUNNING and reconciliation-required jobs, using SKIP LOCKED. It locks each job, increments its fence, and records expiry transitions atomically. Every receipt, approval and BusinessRecord lookup includes that job's tenant. An exact actor/proposal/key/request-hash receipt with verified COMMITTED payload, atomic approval consumption when required, and expected note/request record proves completion. A matching FAILED receipt proves rolled-back failure. Immutable receipt before/after resource hashes and versions are transaction evidence: subsequent legitimate resource changes do not erase a committed outcome.

If no receipt exists and the approval is unconsumed, the job lock excludes older writers, and the single local transaction contract proves no business effect committed. Only then can bounded backoff reschedule the SAME key. Missing/mismatched evidence or consumed approval without a receipt remains RECONCILIATION_REQUIRED. This does not claim failure, success or permit blind manual retry. Repeated recovery does not duplicate business effects or terminal transitions.

## Runbook

1. Restore PostgreSQL and start one worker; review queue state/events and worker metrics.
2. Expired leases reconcile automatically. Inspect original attempt correlation IDs and execution receipt, not browser timeout text.
3. For DEAD_LETTERED, creator may request retry if budget/window and current decision/approval remain valid. Never issue a new key to bypass a conflict.
4. For ambiguous evidence, retain RECONCILIATION_REQUIRED and investigate database transaction evidence with privileged offline access. No unrestricted repair or mutation endpoint is provided.
5. Cancel unstarted work through the authenticated API. Running cancellation is cooperative and may return conflict after commit; refresh/reconcile instead of claiming rollback.

## Limits

Proof of no receipt implies no local effect only because all five supported synthetic writes and receipts share PostgreSQL atomicity. This design is not a distributed exactly-once guarantee for external systems. Database backups, privileged SQL tampering, retention, multi-region failover and real provider write protocols need separate designs. Original actor logout does not revoke already submitted durable work; deactivate/demote the actor or cancel the job. Reviewer session revocation continues to invalidate unused approval grants.

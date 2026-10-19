> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Controlled synthetic business execution

The agent, planner, provider adapter and six read-only tools cannot invoke the controlled executor. Human-authenticated POST `/action-proposals/{id}/execute` requires a distinct execution permission, the proposal creator's identity, exact decision ID, approval ID when restricted and an idempotency key. ALLOW is eligibility only; it never triggers automatic execution.

## Transaction boundary

`ControlledActionExecutor` starts a PostgreSQL SERIALIZABLE transaction, sets statement/lock timeouts, acquires a tenant advisory lock and locks the authenticated session/user against revocation. It loads the creator-owned proposal and exact receipt, checks durable replay first, then validates current approval, reviewer authority, creator authority, canonical argument hash, evidence provenance/freshness, policy versions, resource fingerprints and eligibility through the existing PDP evaluator. Business, source and policy rows are locked. Serializable conflicts abort safely; clients reconcile/retry the same key, never switch keys.

A database-time predicate on the actual optimistic UPDATE bounds the write by decision, approval, execution session, review session and policy date cutoffs. Resource `updated_at` must match the locked value. Thus a deadline crossing after Python validation cannot produce a late business update. Security blocks and unknown actions have no handlers and remain prohibited.

Five static handlers exist:

- Customer note: append a tenant/customer-bound BusinessRecord and advance customer update timestamp.
- Ticket note: append a tenant/ticket-bound BusinessRecord for an open ticket and advance its timestamp.
- Reactivation request: append a tenant/account-bound BusinessRecord while preserving the blocked account and advancing evidence version.
- Reactivate account: require blocked/resolved_billing, consistent complete local payment evidence and current approval; activate, clear block reason and increment evidence version.
- Duplicate closure: require the approved exact duplicate relationship, both tickets in the tenant and an open target; close target.

BusinessRecord has composite tenant foreign keys, exactly one resource parent and a unique execution reference. Deferred execution FK allows the final immutable receipt to be inserted after in-transaction verification.

## Verification and failure recovery

Mutations occur inside a savepoint. The verifier independently re-reads actual database state, target identity, resource hash, status/version, inserted note/request kind and contents, and hashes of fields the action is not permitted to change. Failure or SQL statement error rolls all business effects back to that savepoint, then persists a FAILED receipt. Failed proposals cannot be retried as new mutations; fresh evidence/proposal is required. Approval consumption is committed only with a verified successful mutation.

Mutation, business record, receipt, audit events and approval consumption commit atomically. Success is returned only after commit. A process crash before commit rolls back. A response loss after commit is recovered by the same key. A database connection failure at commit returns UNCERTAIN and requires reconciliation; if storage is inaccessible a durable uncertainty receipt cannot honestly be guaranteed. The API attempts a separate correlated execution_uncertain audit event when storage returns and otherwise emits a correlation-only reconciliation warning. There are no external side effects to reconcile in this phase.

Audit records include request/grant/reject/cancel/expiry/invalidation, execution request/denial/start/commit/verification/failure, with correlation UUIDs and no raw note/evidence/credential payloads. Rejected pre-execution requests have security audit events rather than successful execution receipts. Uncertain storage failures return a correlation ID for recovery.

## Limits

Only synthetic local PostgreSQL mutations are supported. Serializable conflicts may return a retry/reconciliation error. Tenant-wide serialization is intentionally conservative and limits throughput. Application-level append-only hooks do not resist privileged SQL, and PostgreSQL RLS/external immutable audit storage remain absent. Real enterprise write integrations, autonomous execution and Phase 9 are not implemented.

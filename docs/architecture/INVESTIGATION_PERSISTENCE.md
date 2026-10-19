> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Investigation persistence

Phase 4 replaces the Phase 3 process-local result store with PostgreSQL. Migration `0004_persistent_investigations` preserves business data, sessions and prior tool metadata. Existing Phase 3 in-memory results cannot be migrated after a process restart; they were never durable. There is no TTL deletion of the new history. Operational retention/archiving is future work.

## Schema

| Table | Purpose and integrity |
| --- | --- |
| investigations | Tenant/actor, customer/ticket references, goal/context, status, planner/version, timestamps, execution version, event/checkpoint counters, budget limits/usage, lease, cancellation, idempotency binding, final result |
| investigation_steps | Ordered step definition/status; unique step ID and index per tenant/investigation |
| investigation_checkpoints | Versioned bounded snapshot/checksum; unique sequence and applied investigation version |
| investigation_events | Append-only application event history, unique tenant/investigation sequence |
| investigation_evidence | Allowlisted provenance, ordered sequence and unique tool execution; composite tenant FK to actual tool metadata |

All five tables have UUIDs, tenant FKs and timestamps. Child tables use composite investigation/tenant FKs. Parent customer, ticket and actor references are tenant-bound. `tool_executions` gains a composite unique key for evidence foreign keys. Referenced customer/ticket ownership and the ticket/customer relationship are validated before insertion. A foreign or missing resource returns the same safe 404. No business records are mutated.

`InvestigationRepository` owns lifecycle writes. Every method revalidates the server session and current investigation:create permission, then predicates on tenant and creating actor. Even another investigator in the same tenant cannot see/cancel/resume an actor's history. No client tenant/role selector is accepted. Revalidation is shared with ToolExecutor; each tool still independently rechecks its own permission. An unavailable database fails closed; there is no in-memory success fallback.

## Transactions and atomicity

Creation atomically inserts the investigation, created event and initial checkpoint. Canonical strict request JSON is SHA-256 hashed. A database unique `(tenant_id, actor_id, idempotency_key)` constraint and transaction-scoped advisory key lock prevent duplicate creation races. Same key/payload returns the existing ID/current representation without executing again; changed payload is 409. Keys accept 16–80 ASCII letters, digits, hyphens and underscores. Missing keys receive a fresh UUID for Phase 3 client compatibility; callers needing retry deduplication must provide the header. The UI retains a key for an unchanged submitted payload across retries; it does not store authentication tokens.

Detail/snapshot reads lock the parent while reading child records to prevent mixed checkpoint versions during concurrent writes. Lifecycle updates lock the scoped investigation row, verify expected version and unexpired lease owner, validate transitions and nondecreasing budgets, then commit step/evidence changes, event sequences and a checkpoint together. Unique constraints reject duplicate sequences/checkpoint application. Completed steps cannot be rewritten or reapplied. Tool reads run outside the lifecycle transaction: before-tool intent commits first; an observation, evidence, completed step and checkpoint commit together afterward. The separate ToolExecutor audit transaction is not falsely claimed to be atomic with investigation observations.

Heartbeat changes lease expiry without incrementing the execution version. Cancellation records its flag/event/checkpoint under the same parent lock. An executing owner handles the resulting version conflict by reloading cancellation and finalizing CANCELLED. Pending or expired-lease investigations cancel atomically immediately. A terminal result and terminal transition/event/checkpoint are one transaction and release the lease. Terminal results never restart.

Events, checkpoints and evidence reject ORM update/delete. Privileged raw SQL/DB owners can still alter them; checksums detect accidental corruption, not a hostile owner who recomputes them. Destructive downgrade is refused. RLS and deployment least-privilege credentials remain deferred.

## API

All routes require authenticated investigation:create. POST routes require trusted Origin. Invocation/control bodies are bounded to 8192 bytes; controls accept only an empty object or omitted body.

- POST `/api/v1/investigations`, optional `Idempotency-Key` header.
- GET `/api/v1/investigations`: limit 1–50, offset 0–10000, optional status enum/customer UUID; created-at descending then ID ascending.
- GET `/api/v1/investigations/{id}`: durable result/current snapshot plus version, budget usage, checkpoint validity/sequence, cancellation, planner and lease/recovery status.
- GET `/{id}/events` and `/{id}/evidence`: limit 1–100 and nonnegative `after` sequence up to 1000000; stable ascending sequence, next_after cursor.
- POST `/{id}/cancel`: idempotent request; terminal records remain terminal.
- POST `/{id}/resume`: explicit owner-only safe recovery; active leases return 409. See [recovery](RECOVERY.md).

Malformed requests are 422; foreign/unknown IDs 404; unauthenticated 401; forbidden 403; stale versions/active leases/idempotency mismatch 409; database failure 503. A structured terminal investigation outcome still uses HTTP 200. A repeated creation may truthfully return a pending/running representation while its original request executes. The detail page supports explicit refresh, persistent events, evidence, checkpoint/recovery status and authorized cancellation; no simulated progress is shown.

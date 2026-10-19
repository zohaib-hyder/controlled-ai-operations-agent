> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Execution receipts and idempotency

Migration `0007_controlled_execution` adds approval_requests, approval_decisions, action_executions, action_execution_events and business_records, plus a composite unique decision-receipt key for tenant-safe foreign keys.

An immutable execution receipt binds execution/proposal/approval IDs, tenant, execution actor, action/version, target, canonical argument hash, exact policy decision, before/after resource fingerprints and status/version, verification outcome, error code, creation timestamp and idempotency key. Raw note text is stored only in the intended business note record; receipts do not repeat it. Before/after snapshots expose state references rather than unnecessary personal or financial data.

Database uniqueness enforces one execution attempt with a final receipt per proposal, one use per approval, one execution per tenant/key and one note/request per execution. The request hash includes tenant, creator, proposal payload, canonical arguments, target and exact execution command. Same-key/same-request replay returns the existing result without mutation, even if the resource is now stale because the original execution changed it. A changed key, actor, proposal, target, arguments or decision cannot replay a different request.

FAILED receipts reflect a rolled-back mutation and do not authorize another attempt. DENIED preconditions produce no business effects and preserve correlated security audit. COMMITTED means verification succeeded in the same transaction and the commit completed before the response. UNCERTAIN is an explicit transport/storage reconciliation response, never a success claim; retry the exact same command/key after storage returns or retrieve the known execution ID.

GET `/action-executions/{id}` permits the execution creator or an authorized same-tenant reviewer and includes a bounded immutable event timeline. No receipt is a reusable authorization token. Current checks and the controlled service are required for every new operation.

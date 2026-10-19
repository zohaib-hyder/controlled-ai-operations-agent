# Security boundaries and evidence limits

## Verified by synthetic tests

- Authentication comes from a persisted hashed session and current active DB principal, never submitted actor/tenant/reviewer/role fields.
- Tenant-scoped repository queries, parent ownership and composite foreign keys guard both reads and writes. Authenticated HTTP lifecycle probes cover customers, accounts, tickets, transactions, policy retrieval, investigations, evidence, proposals, decisions, approvals, executions, jobs, incidents, metrics and traces.
- Tools accept strict versioned schemas and registered read operations only. Read-only DB transactions also reject accidental writes. Cancellation drains bounded work before releasing capacity.
- Planner prose and output cannot approve writes. Exact deterministic policy/resource/evidence/action bindings and independent approval are revalidated at execution.
- Mutation evidence includes actual business snapshots and immutable execution receipts, not merely rejection status. Idempotency, fencing, transaction rollback, bounded retry and uncertain-outcome reconciliation are checked against PostgreSQL.
- Metrics derive from scoped durable rows; incident responses are operational metadata only. Error/empty states do not fabricate healthy cards or successful execution.

These statements describe the tested controls and scenario scope. See results for actual denominators; they are not universal proofs.

## Evaluation boundary

`python -m app.evaluations.red_team` is development tooling requiring pytest. It is not registered as an API or agent tool. It accepts only checked-in catalog bindings and invokes pytest without a shell. It rejects nonlocal/non-PostgreSQL/non-`_test` databases and paid-provider configuration. Standard evaluation disables real httpx transport, retaining MockTransport and TestClient transport. This is an HTTP safeguard, not a general OS network sandbox; PostgreSQL remains real local I/O.

Each run has a fresh directory. Per-test-phase progress is atomically persisted so interrupted processes retain completed outcomes. Missing, skipped, setup-failed, teardown-failed or nonzero pytest runs fail acceptance. No old reports fill missing outcomes. Failure reports contain scenario, expected/actual invariant, phase, available UUID references, reproduction and unconfirmed/remediation status. The local pytest console retains assertion detail; machine reports omit raw request/body/credential contents. Legacy cases without a durable investigation can have no trace ID, which is explicitly an empty list.

Rate/counter denominators are described as scenarios, tool selections, evidence references or factual findings rather than mixed indiscriminately. An invariant's zero violation result is reported only when every applicable assertion passes; otherwise it is unknown. A failed assertion is not automatically classified as a successful attack. Lifecycle raw measurements remain visible but cannot establish acceptance after a critical failure.

## Untested production conditions

No live LLM calls, customer systems, external business writes, security certification, penetration test of hosted infrastructure, production-scale traffic, multi-region failover or production secret management were validated. Database privileges/owner tampering remain outside ORM append-only guarantees. Real provider transport behavior is not inferred from mock HTTP adapter tests.

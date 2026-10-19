> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Authorized evidence retrieval

Phase 5 uses `EvidenceRetrievalService` inside the existing bounded orchestrator. Every invocation still passes investigation resource validation, ToolExecutor registry/schema validation, live server-side session/RBAC checks, tenant repository predicates, read-only transactions, timeouts, rate/capacity limits and metadata auditing. The service wraps dispatch; it does not introduce an authorization decision or execute generated SQL. Each successful result is normalized once and persisted in the existing evidence/checkpoint transaction. Recovery reuses saved canonical sources without rerunning completed tools.

The six existing tools retrieve customer ownership, related tickets, selected ticket/account state, recent transactions and policies. Tool output is bounded to 20 rows. Canonical records retain only allowlisted structured facts, not customer names, emails, financial references, policy descriptions or ticket prose. Transaction creation time is preserved separately in metadata and never substituted for missing last-update time. Source prose remains untrusted and cannot create instructions, actions or factual findings.

Each strict source record includes evidence/investigation/tenant IDs, source type/resource ID/reference/version/timestamp, successful tool execution ID, collection time, facts, template summary, freshness, historical flag, validation status and retrieval metadata. UUID5 derives from investigation, tenant, execution and source reference; it is reproducible for the same observation, distinct for separately audited observations. Repeated envelopes are deduplicated by source reference and execution. Different observations remain distinguishable for conflict detection. UUIDs identify records; they are not cryptographic attestations.

Canonical records live inside append-only `InvestigationEvidence.payload`. Existing composite tenant/investigation/tool-execution foreign keys, sequence indexes and checkpoint references continue to protect the enclosing record. Source IDs are validated on reads/writes together with tenant, investigation, execution and collection time. A database owner can still alter storage; external tamper-evident storage/RLS are not claimed. Old evidence envelopes and checkpoints have optional empty source collections and remain readable.

Authenticated creator-scoped APIs:

- Existing `GET /api/v1/investigations/{id}/evidence` returns ordered envelopes.
- `GET .../{id}/sources` returns canonical sources.
- `GET .../{id}/evidence/{source_evidence_id}` inspects a source.
- `GET .../{id}/conflicts`, `/gaps`, `/findings` return reconciliation records.

New lists reuse strict `SequenceQuery`: `limit` 1–100 and `after` nonnegative bounded offset; `next_after` is the next offset. Envelope/event cursors retain their existing sequence semantics. Invalid/foreign/non-owned IDs return safe errors. No tenant selector is accepted. Partial reconciliation can be derived from persisted sources without tool dispatch. Terminal reconciliation and finding links are durably stored in `final_result` and compared against deterministic reconstruction on reads/writes.

The UI exposes source cards, timestamps, freshness, historical relevance, policy citations, JSON fact inspection, conflict/gap warnings and finding links. It grants no action permission and shows no confidence score.

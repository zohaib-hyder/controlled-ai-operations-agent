> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Deterministic Policy Decision Point

Phase 7 evaluates eligibility only. No receipt authorizes execution and no endpoint changes customers, accounts, tickets, transactions or policies.

## Integration audit

Existing cookie authentication and `revalidate_identity` remain the authority for sessions and current roles. Existing creator/tenant-scoped investigation retrieval verifies durable checkpoints, canonical evidence provenance and reconciliation. ToolRegistry still contains exactly six read-only tools. The PDP is not a tool, cannot dispatch tools and does not interpret planner decisions as authorization. Existing investigation state transitions and budgets are unchanged.

`AgentOrchestrator.suggest_action` provides an explicit bounded advisory handoff from structured account evidence. The operator invokes the handoff; suggestions do not run automatically during legacy investigations. `propose_action` uses the same engine as manually submitted proposals. A denial is persisted without modifying arguments or retrying it. No paid provider is involved.

## Algorithm

1. Validate bounded request syntax, catalog action/version and action-specific arguments.
2. Resolve live server-side actor/session/tenant and proposal permission. Client actor, tenant and permissions fields are rejected.
3. Load the target using tenant predicates. Foreign and nonexistent targets share `target_not_found`; proposal reads are creator-scoped.
4. Resolve canonical evidence IDs from the authorized investigation. Require a completed or review-stopped investigation with verified reconciliation; high-severity unresolved conflicts deny.
5. Verify source ownership, target relationships, actual source timestamps, source freshness (configured evidence window), collection age and live eligibility facts. A citation is not sufficient. All account transactions must be represented for reactivation; a truncated sample denies.
6. Resolve current structured policies independently of search ranking. Effective dates include the start and exclude the expiry. Exactly one effective version for the required key is necessary. Overlapping versions deny; explicit expiry closes an old version before supersession. Future and expired higher versions do not suppress a current version.
7. Check exact supported rule shapes, resource/state/scenario applicability and cited policy ID/version. Unknown rule structures deny; booleans must be actual JSON booleans and applicability must use arrays. Policy descriptions are never interpreted or executed.
8. Apply explicit Python action rules. Missing data denies. Security overrides always deny. Notes can be ALLOW; eligible reactivation/duplicate closure require approval.
9. Atomically persist proposal, receipt and correlated audit records. No executor or approval grant exists.

Reads of decisions recompute eligibility and compare bindings. A stale historical ALLOW remains in its immutable receipt, but the response status is STALE with `execution_authorized=false`. Revalidation appends a newly evaluated receipt; changed facts often produce DENY because old evidence must be refreshed through a new investigation.

Database row locks and unique proposal/sequence constraints serialize concurrent receipt requests. Statement/lock timeouts bound database operations. These receipts describe past evaluations, not a transactionally protected promise about future state.

## Security boundaries

There are no action execution or action approval permissions. The generic pre-existing `approval:review` permission remains for existing navigation only; it grants no approval capability. No self-approval endpoint exists. The PDP reads business tables and only inserts evaluation/audit records.

Note content is bounded plain text, with deterministic rejection of specified injection/secret/script patterns. Rejected content is replaced before persistence. This is a conservative validation aid, not comprehensive natural-language threat detection or secret discovery. All content remains data and is escaped by React.

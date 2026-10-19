> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Immutable decision receipts

Migration `0006_policy_decisions` adds tenant-scoped `action_proposals` and `policy_decision_receipts` with composite tenant foreign keys and unique per-proposal receipt sequences. Proposal, first receipt and audit events commit together. Subsequent revalidation locks the proposal and appends a receipt.

Receipts contain decision/proposal/investigation/actor/tenant IDs, action/version, target, canonical SHA-256 argument hash, decision, rule IDs, exact policy IDs/versions and structured policy hash, canonical evidence IDs, live resource fingerprints, current permissions, reason codes, creation and expiry timestamps. Expiry defaults to five minutes. Every response explicitly declares `execution_authorized=false`.

Arguments use sorted-key compact ASCII JSON. Evidence IDs refer to persisted canonical observations, not arbitrary citation strings. Resource fingerprints include update time and relevant status, version, relationship and payment fields. Policies additionally bind structured rules, applicability and date windows. Revalidation never reuses the original planner's claimed role or permissions.

GET status recomputes current facts. Expiry, resource changes, policy changes, permission changes and newly stale or invalid evidence produce STALE. A revoked session cannot read receipts at all. An actor changed to auditor can inspect their historical proposal and receive stale status, while revalidation returns DENY. Revalidation appends a fresh receipt and records policy_evaluated, decision_issued/decision_denied and decision_revalidated; an expired prior receipt records decision_expired once on status read or revalidation, correlated to the receipt ID. Creation records proposal_created. Audit events preserve request correlation UUIDs without note text, evidence facts or credentials.

ORM update/delete hooks reject application-level record mutation. Privileged SQL can still alter data: this is not cryptographic or external immutable storage. Clients must honor current status; future execution must independently revalidate everything in a new transaction. No Phase 7 receipt can be exchanged for execution or approval.

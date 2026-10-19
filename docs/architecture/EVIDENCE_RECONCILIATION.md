> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Evidence freshness, conflicts and grounding

Freshness is assessed at collection, not continuously relabeled on every historical read. `EVIDENCE_FRESHNESS_SECONDS` defaults to 86400 (allowed 60–31536000). An actual aware source timestamp within the threshold is CURRENT, an older one STALE; missing/naive/future timestamps are UNKNOWN. Collection time never fills a missing source timestamp. Source version is retained independently. Transactions retain their actual creation timestamp in retrieval metadata, last-update timestamp separately, and `historical=true`; legacy outputs lacking last-update time are UNKNOWN, with no substitution from creation time; an old event can remain relevant. Policy effective-window applicability is distinct from last-updated freshness. Baseline January 2026 synthetic records are intentionally stale by October 2026.

Supported conservative rules:

| Rule | Detection | Meaning |
| --- | --- | --- |
| account_state_mismatch | Different CURRENT observations of one account disagree on state | No silent winner |
| payment_unresolved | A bounded account ledger contains paid and unpaid records | Allocation/outstanding balance unknown, not proof of a payment error |
| ticket_closed_account_blocked | Closed ticket and blocked account share the same account ID | Ticket closure does not establish account resolution |
| policy_version_overlap | Separately collected observations label different versions of one key current | Applicability needs reconciliation |

Conflicts retain stable IDs, canonical evidence references, severity, explanation and human follow-up. Sources are not assumed correct merely because schemas validate. A payment never proves reactivation eligibility. Free-form claims in ticket/policy prose are not parsed as facts; supported conflicts use structured fields only.

Gaps explicitly identify absent customer/account/ticket/transactions/policies, missing block reason and policy applicability mismatch. Gaps do not fabricate a fact. Empty or failed retrievals retain bounded available evidence. Existing planner missing-evidence and security-review behavior is preserved; supported additional conflicts force NEEDS_REVIEW.

Grounded findings separate observed_fact, inference, uncertainty and advisory in strict contracts. Backend-produced observed facts are deterministic source summaries. Citation validation rejects missing/foreign IDs and factual text unequal to a cited source summary. Conflict explanations are uncertainty; recommendations remain in the existing explicitly advisory result section. Terminal reconciliation must equal reconstruction from independently persisted source envelopes, otherwise reads/writes fail closed. Existing legacy findings retain their envelope citations; legacy records without canonical sources are not silently rewritten.

At most 400 canonical observations (20 calls × 20 sources) and 20 conflict records are exposed. If conflict output reaches its limit, an explicit gap requests review. Source prose is escaped by React, and structured facts are shown as text. These finite synthetic rules do not reconcile arbitrary enterprise semantics or infer invoices, balances, security clearances or action permissions.

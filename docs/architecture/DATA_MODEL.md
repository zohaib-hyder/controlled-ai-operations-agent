> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Synthetic enterprise data model — Phases 0–4

All entities have a UUID primary key plus timezone-aware creation and update timestamps. SQLAlchemy updates `updated_at` for ORM writes; raw SQL callers must maintain it themselves. Fixture IDs use UUIDv5 and timestamps use 2026-01-01 UTC for deterministic reconstruction. Monetary values use nonnegative integer minor units, with no bank/card/account routing identifiers.

| Table | Tenant scope and relationships | Important constraints |
| --- | --- | --- |
| tenants | Root organization | Unique name |
| users | Required tenant FK | Unique tenant/email; operator, reviewer, admin or auditor |
| customers | Required tenant FK | Unique tenant/email; fictional labels |
| accounts | Tenant + customer composite FK | Status enum check; positive evidence version |
| tickets | Tenant + account composite FK; optional tenant + duplicate-ticket composite FK | Open/closed status; duplicate links stay in tenant |
| transactions | Tenant + account composite FK | Nonnegative amount; paid/unpaid/disputed status; unique synthetic reference |
| policies | Required tenant FK | Unique tenant/key/version; positive version; JSON scenario rules |

Each tenant-scoped table has a tenant index and unique `(tenant_id, id)` pair; child relationship columns are indexed. Composite foreign keys bind tenant and resource together, preventing valid resource IDs from being paired with another tenant. Customer/accounts, account/tickets and account/transactions have ORM relationships.

Composite constraints enforce relationship integrity. Phase 1 HTTP reads additionally use validated server sessions and explicit tenant repository predicates. No RLS is enabled; privileged direct database access can still read all tenants. See [tenant isolation](TENANT_ISOLATION.md).

## Authentication additions

- `users.password_hash`: nullable Argon2id hash; legacy rows are initially unable to log in. `is_active` defaults true. A globally unique functional index on `lower(email)` supports unambiguous email/password login. Migration fails safely if an existing installation has case-insensitive duplicate emails; it does not merge accounts.
- Legacy `approver` roles become `reviewer`; the original synthetic reviewer addresses are renamed accordingly. IDs and business foreign keys are preserved.
- `auth_sessions`: UUID, tenant/user composite FK, unique SHA-256 token digest, created/updated timestamps, expiry and nullable revocation time. Expiry must follow creation. No raw token is stored.
- `login_buckets`: hashed identity/client key, failure count and window timestamp. These are global abuse-protection metadata, not tenant business records.
- `security_events`: UUID, timestamps, nullable tenant/actor composite FK, event type, optional resource type/UUID, outcome and correlation UUID. Application behavior is append-only; privileged raw SQL is not tamper-proofed by this phase.

Normal business seeding still creates six original users (now reviewers in place of approvers). Explicit development auth seeding adds two admins, making eight fixture identities (four roles per tenant), and assigns random-salted password hashes only to fixture IDs without replacing existing hashes. Base business fixture IDs/timestamps/counts remain deterministic. Authentication hashes intentionally use random salts rather than deterministic password hashing.

## Fixture mapping

For each tenant index `t` (0 Atlas, 1 Beacon), IDs are `stable_id("t/account/i")` etc., with tenant IDs `stable_id("tenant/t")`.

| Scenario | Account / ticket | Evidence |
| --- | --- | --- |
| A | account 0 / ticket 0 | Blocked; unpaid ledger entries |
| B | account 1 / ticket 1 | Security-review block |
| C | account 2 / tickets 2 and 12 | Ticket 12 references ticket 2 |
| D | account 3 / ticket 3 | Resolved billing; both transactions paid; still blocked pending future evaluation |
| E | account 4 / ticket 4 | Paid and unpaid ledger entries; customer claim says paid |
| F | account 5 / ticket 5 | Untrusted text references other tenant's account 0; no cross-tenant relational link |

Per tenant: 3 base users (4 after explicit authentication seeding), 10 customers/accounts, 15 tickets, 20 transactions and 5 policy versions. Reactivation versions 1 and 2 demonstrate policy history; no policy engine interprets them. The highest version is not automatically considered authorized or active by this foundation.

## Phase 4 durable lifecycle tables

Migration `0004_persistent_investigations` adds investigations, investigation_steps, investigation_checkpoints, investigation_events and investigation_evidence. Each child binds investigation and tenant by composite FK; the parent binds tenant/actor/customer/ticket, with a unique tenant/actor/idempotency key. Ordered events/checkpoints/steps/evidence have per-investigation uniqueness constraints. Tool metadata gains unique `(tenant_id,id)` for evidence integrity. Parent row versions and leased owner fencing coordinate transactions; state/status checks constrain terminal behavior. No customer/account/ticket/transaction/policy rows are changed by investigations. See [full schema and transaction design](INVESTIGATION_PERSISTENCE.md).

## Phase 5 additive evidence and policy metadata

Migration `0005_policy_applicability` adds `policies.category`, `resource_type`, `effective_at`, nullable `expires_at`, `account_states` JSON and `scenarios` JSON. Existing `(tenant_id,key,version)` uniqueness and tenant indexes support bounded search. Effective windows use an inclusive start/exclusive expiry. Synthetic reactivation v1 is expired; v2 is current. Seed idempotency/counts are unchanged.

`InvestigationEvidence.payload.sources` optionally stores up to 20 canonical observations, with source IDs, exact tenant/investigation/execution provenance, source version/timestamp, sanitized facts/summary, freshness, historical flag and retrieval metadata. The existing tenant-aware foreign keys, append-only enforcement and sequence indexes apply to the envelope. No independent source table or unrestricted data endpoint is introduced. Terminal `Investigation.final_result.reconciliation` stores typed conflicts/gaps/grounded finding links; deterministic read/write validation compares it with source evidence. Legacy records retain optional empty sources and null reconciliation, so no evidence backfill or rewriting is required. See [contract and integrity boundaries](EVIDENCE_RETRIEVAL.md).

## Phase 6 additive planning metadata

No table change or migration is required. Existing planner type/version columns distinguish deterministic mock v1/v2 and optional OpenAI-compatible v2. Checkpoint JSON adds bounded selection traces, semantic observation fingerprints and a nonsecret provider-configuration hash. Counter JSON adds provider request/output-token/cost reservations and no-progress counts; Limit JSON adds corresponding caps. Typed defaults normalize historical JSON for equality checks without rewriting old records. Repository saves enforce monotonic counters, stable planner identity/configuration and an unchanged trace prefix.

Terminal result JSON includes trace, iteration count and execution limits. Reads verify trace/checkpoint agreement and derive iteration/limit metadata from trusted stored budgets for historical results. Argument hashes and tool execution/observation/source IDs link decisions to existing tenant-constrained evidence/audit records. No raw provider reply, secret key or private reasoning is stored. See [dynamic planning](DYNAMIC_PLANNING.md) and [traces](AGENT_TRACES.md).

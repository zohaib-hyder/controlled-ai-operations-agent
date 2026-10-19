> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Human approval workflows

Phase 8 adds tenant-scoped approval requests and append-only approval decisions. Requests reference the exact immutable proposal and PDP receipt, requested actor, policy/evidence/resource bindings, expiry and independent reviewer. No session tokens are stored or returned. The internal reviewer session reference permits revocation checks.

States: PENDING → APPROVED, REJECTED, CANCELLED, EXPIRED or INVALIDATED. APPROVED may become CANCELLED, EXPIRED or INVALIDATED before consumption. REJECTED, CANCELLED, EXPIRED and INVALIDATED cannot transition. Decisions are immutable history; status changes append decisions rather than overwriting an earlier grant. A consumed APPROVED request cannot be reused or cancelled.

Only a current REQUIRE_APPROVAL receipt can create a request. Requester must own the proposal and have current proposal permission. Duplicate pending/approved requests with the same receipt return the existing request. No request may grant an ALLOW or DENY decision. Expiry is bounded by the original decision expiry, five minutes by default; changes require a new proposal rather than extending a grant.

Reviewer/admin roles receive `action:approve`; operator/admin roles receive `action:execute`. These are separate from `action:<name>:propose`. Reviewer must be an active authenticated user in the same tenant and different from both proposal creator and requester. A reviewer may propose their own action, but cannot approve it. Execution is creator-only. An admin is subject to the same separation of duties.

Before approval, detail reads and execution, the backend refreshes resource/policy/evidence/creator eligibility. Execution also checks the original reviewer's current role, active state, session revocation and session expiry. Reviewer logout invalidates that session's unused approvals. Keep operator and reviewer browser sessions independent.

The approvals queue is bounded and tenant-filtered. Detail refreshes pending/approved status and exposes only cited canonical evidence to the requester or an explicitly authorized reviewer. The internal evidence-review path does not broaden public investigation endpoints or actor-owned history access. Queue expiry is finalized lazily on detail/decision/execution, not by a background worker.

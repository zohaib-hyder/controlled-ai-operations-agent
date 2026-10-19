> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Durable execution jobs

Phase 9 adds PostgreSQL scheduling metadata around the existing controlled executor. No worker or job handler writes business tables directly. `execution_jobs` stores the authenticated submitter, proposal, action/version, exact decision/approval command, canonical execution request hash and stable idempotency key. It contains no session token or customer payload. Composite foreign keys enforce tenant relationships.

Submission requires current cookie authentication, CSRF origin, execution permission, creator ownership, an eligible decision and current independent approval when required. Submission is not a grant to execute. Unique tenant/proposal and tenant/key bindings return the same job on exact replay, including after completion; changed actor, command, proposal or key conflicts. Each tenant is limited to 100 active jobs and 20 new submissions per minute. Replays do not consume submission capacity.

## Lifecycle

QUEUED → CLAIMED → RUNNING → COMPLETED or FAILED. Proven transient rollback schedules RETRY_SCHEDULED → CLAIMED. Exhausted retries become DEAD_LETTERED. Lease expiry or ambiguous infrastructure failure enters RECONCILIATION_REQUIRED; evidence may prove completion, failure or safe rescheduling. QUEUED, RETRY_SCHEDULED and CLAIMED can be cancelled. RUNNING can be cancelled cooperatively only while holding its job lock and proving no receipt exists; the executor holds that same lock through commit. Committed work is never described as rolled back.

Terminal COMPLETED, FAILED and CANCELLED jobs cannot restart. Explicit creator-authorized DEAD_LETTERED retry is permitted only within the original ten-minute retry window and lifetime five-attempt ceiling, after current eligibility revalidation. It preserves the same execution binding and key. Every transition and security event commits atomically with job state. Events/dead letters are append-only through application ORM hooks; database-owner SQL privileges remain outside this application guarantee.

## API and interface

`POST /api/v1/execution-jobs` accepts only proposal_id, decision_id and optional approval_id, with Idempotency-Key header. GET collection/detail/attempts/events and POST cancel/retry use existing auth and CSRF controls. Collection pagination is bounded to 50. Owners see their jobs; tenant admins may inspect tenant jobs but cannot execute/retry another actor's work. Unknown/foreign jobs return 404. No HTTP worker-admin endpoints exist.

The Execution Jobs page submits evaluated proposals by exact IDs and shows actual persisted statuses, queue depth/age, attempts, retry schedule, error category, receipt and events. Refresh is explicit. Cancellation/retry buttons follow server capability fields; backend authority remains decisive.

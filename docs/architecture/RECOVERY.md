> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Execution ownership, recovery and cancellation

Phase 4 remains request-scoped, with four local investigation slots and the existing bounded ToolExecutor. PostgreSQL supplies minimal ownership across limited application instances; no broker, durable scheduler or distributed worker framework is introduced.

## Leases

A claim locks the authenticated tenant/actor's row, checks a terminal state cannot restart and rejects an unexpired lease. It atomically assigns a random owner UUID, a 120-second expiry using PostgreSQL clock time, and an ownership/recovery event/checkpoint. This compare-and-swap acquisition is serialized by the database row lock. Two concurrent claim attempts cannot both win. Expected versions plus owner/expiry checks fence all subsequent writes. A five-second async heartbeat renews the lease during pending async work; its database operation is bounded by statement/lock timeouts. Lease renewal does not reset execution counters or change the checkpoint version.

An expired old owner cannot persist an observation or terminal result after a new claim. Its already-running synchronous read may still finish and record tool audit metadata. The new recovery will not dispatch that uncertain step, so this is not a claim of globally exactly-once execution. Tested guarantees are local/limited multi-instance ownership fencing and conservative read-only recovery, not arbitrary distributed failure tolerance.

## Explicit recovery

POST `/api/v1/investigations/{id}/resume` requires current session, current investigation permission, creating actor/tenant and trusted Origin. An active lease returns 409. A terminal record returns its existing result unchanged. Pending never-started records may also be explicitly started through this operation; no hidden worker launches them.

1. Acquire an expired/unowned lease and record recovery_attempted.
2. Validate latest checkpoint schema/version/checksum and its correspondence with durable counters, state, steps and evidence.
3. Restore original limits, planning/tool/repetition/byte counters, completed step IDs and minimal observations.
4. Charge elapsed time since that checkpoint as well as previously recorded runtime. Downtime therefore consumes the wall budget; long interruptions normally finish BUDGET_EXCEEDED instead of silently receiving a new clock.
5. Revalidate the current actor's session/permissions on repository operations and every actual ToolExecutor call.
6. Skip durably completed steps. A before-tool/proposed marker or unfinished step instead stops NEEDS_REVIEW/interrupted_tool_requires_review without dispatching that tool. This includes a crash after intent but before invocation, or after the separate tool audit committed but before observation persistence.
7. Persist terminal result, state event/checkpoint and recovery_completed or recovery_failed. No terminal investigation can restart.

A valid observation checkpoint can continue if budgets remain. Planner invocations are charged before calling the planner; uncertainty about a completed planner call may cost another iteration on recovery, never reset usage. Recovery attempts are bounded to 20; damaged or unsupported checkpoints fail closed. A checksum is not a signature or DB-owner tamper barrier. There is no replay of business-changing tools because none exists.

## Persistent cancellation

Authorized owner cancellation commits a flag, cancellation_requested event and checkpoint. Pending/expired investigations transition to CANCELLED in that transaction. An active owner checks the durable flag between planning/tool boundaries and while saving checkpoints. A cancellation racing with result persistence wins if its row transaction committed first; cancellation of an already terminal record is an idempotent no-op. Cancellation survives repository recreation or backend restart. Terminal cancellation cannot be resumed.

Cancellation cannot forcibly terminate a Python thread or blocking database connection/audit cleanup. Existing ToolExecutor cancellation signals/drains work and retains its slot until cleanup. An HTTP disconnect does not reliably cancel the ASGI task. A lost heartbeat or persistence outage withholds an uncommitted success; the durable checkpoint/lease remains for explicit later recovery. No automatic retry or automatic recovery runs on startup.

## Verified simulations and operational limits

Automated tests race independent repository sessions for leases/versions/idempotency, corrupt checkpoints, expire leases, verify completed-step deduplication and counter preservation, and cancel active/pending work. Live verification restarts the backend after a completed investigation and compares result/events/evidence. A separate synthetic completed-step fixture is expired and resumed through authenticated HTTP; an in-flight fixture stops for review.

`scripts/investigation_fixtures.py` is an explicit development/test setup script, not an API or agent capability. It authenticates a fictional reviewer on loopback and writes only synthetic investigation metadata through the repository; privileged lease expiry is confined to that setup. The browser runner seeds these fixtures; CI uses the explicit confirmation flag. Retention, automated reconciliation, RLS, least-privilege deployment roles, hard runtime isolation and production distributed recovery remain out of scope.

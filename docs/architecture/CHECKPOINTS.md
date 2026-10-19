> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Versioned investigation checkpoints

`agents.checkpoints.Snapshot` is a strict frozen Pydantic contract, schema version 1, planner deterministic_mock version 1.0. Checkpoints contain:

- State and validated state history.
- Step index, plan reference (investigation UUID), plan/version and structured step definitions/status.
- Completed step identifiers and in-flight step marker.
- Counters: tool calls, planning iterations, repeated-call keys/counts, observation bytes and elapsed milliseconds.
- Original server limits; recovery cannot reset or expand them.
- Minimal validated structured observations and evidence identifiers.
- Last event sequence, recovery-attempt count, durable recovery-error marker and correlation ID.

Every checkpoint is at most 131072 UTF-8 bytes in its validated serialized form. Plans/steps/observations are bound to the six registered read-only versioned schemas, and step/counter/evidence relationships are checked. Exact repeated-call counters derive from recorded step arguments. Checkpoint checksums hash canonical JSON; read validation also checks row version/counters/limits, event and checkpoint sequences, durable step definitions, and ordered evidence IDs.

Meaningful boundaries are created, state_changed, planning (counter charged before planner invocation), plan_validated, before_tool, after_observation and final. Final transition/result/event/checkpoint are atomic. Sequence and applied-version unique constraints prevent duplicate application. Checkpoints are append-only through application APIs; tests use privileged SQL solely to simulate corruption.

The stored observations omit customer names, ticket prose and policy prose, replacing those unused text fields with explicit omission labels while preserving schema shape. Account status/evidence version, ticket linkage/category, transaction summaries and policy identifiers/versions remain available for deterministic recovery. Raw financial references were already excluded by Phase 2. No session ID, raw token, token digest, password or provider secret belongs in a checkpoint.

Evidence details live in their own table and the final result for compatibility; checkpoints retain IDs rather than duplicating provenance payloads. Findings are reconstructed from validated evidence summaries on resume. Goals/optional operator notes live on the parent request record, not repeated in every checkpoint. Investigation input remains synthetic and untrusted.

When checkpoint validation fails, no tool is dispatched. The corruption marker is persisted with recovery acquisition, so another crash during recovery cannot erase the failure or authorize continuation. Explicit recovery reconstructs only safe metadata from independently stored step/event/evidence records, then records FAILED/corrupt_checkpoint. If independent parent metadata is itself unusable or the database is unavailable, recovery fails closed and requires repair; it does not guess a valid state. See [recovery semantics](RECOVERY.md).

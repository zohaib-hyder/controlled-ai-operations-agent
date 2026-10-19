> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Tool registry

Phase 2 adds an explicit Python allowlist, not a plugin loader. Each frozen definition declares a stable name/version, description, strict input/output Pydantic classes, permission, read classification, handler, two-second timeout and maximum serialized output bytes. Duplicate names and unsafe definitions fail construction. Names never select imports or executable code.

`ToolExecutor.execute` is callable directly by trusted backend code. The API is an adapter: authenticated GET `/api/v1/tools` filters definitions by permission; authenticated, Origin-protected POST `/api/v1/tools/execute` validates an invocation. No caller-supplied tenant, role or permissions are accepted.

Execution resolves the definition/version, validates arguments, revalidates the server session and current user role in PostgreSQL, constructs an immutable context, checks permission, runs a scoped handler, validates and bounds output, persists terminal metadata and returns the result. The repository's tenant predicates and composite joins remain the isolation boundary.

Four worker slots bound in-process work. Each worker owns and closes its session. Read operations run in PostgreSQL read-only transactions with local statement and lock timeouts. A separate transaction persists metadata and a per-tenant/user 30-attempt/60-second rate bucket using an advisory transaction lock. This rate limit is shared across application instances using the same database.

Migration `0003_tool_execution` adds `tool_executions` and `tool_rate_buckets`, with composite actor/tenant foreign keys. Records contain IDs, name/version, outcome, timestamps, duration, correlation ID and sanitized error category. Arguments, results and session credentials are excluded. Running records transition once to a terminal outcome through the executor; there is no public mutation API. This is operational history, not a cryptographically immutable ledger.

See [contracts](TOOL_CONTRACTS.md), [security assumptions](TOOL_SECURITY.md) and [integration decision](../decisions/0003-tool-execution.md).

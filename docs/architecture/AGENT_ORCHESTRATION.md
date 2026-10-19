> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Agent orchestration

The Phase 3 planner remains request-scoped and read-only. Phase 4 adds [durable state](INVESTIGATION_PERSISTENCE.md), [checkpoints](CHECKPOINTS.md), persistent cancellation and [explicit safe recovery](RECOVERY.md). See [integration decision](../decisions/0004-agent-orchestration.md), [states](AGENT_STATE_MACHINE.md) and [evidence](AGENT_EVIDENCE.md). Current migration head is `0004_persistent_investigations`; tool metadata and investigation lifecycle records are durable.

POST `/api/v1/investigations` and GET `/api/v1/investigations/{uuid}` require a current authenticated session and `investigation:create`. POST requires trusted Origin. Strict input accepts goal (5–1000 characters, nonblank), customer UUID, optional ticket UUID and optional context containing only operator_note (at most 500 characters). UUID JSON strings are explicitly parsed before strict validation because FastAPI initially parses JSON into Python objects. Extra identity fields, arbitrary context fields and bodies over 8192 bytes are rejected. Tenant and actor come from the server session.

Example request:

```json
{"goal":"Investigate the account block using authorized evidence","customer_id":"00000000-0000-0000-0000-000000000000"}
```

Replace the example UUID with a customer in the signed-in tenant. Response fields include investigation_id, goal, status/history, step timeline, findings with evidence IDs, evidence provenance, advisory recommended_next_steps, uncertainty, stop_reason, tool_calls_performed, duration_ms, correlation_id and human_review_recommended. A structured terminal investigation outcome uses HTTP 200 even when FAILED or BUDGET_EXCEEDED; authentication, request validation, access and capacity failures use ordinary HTTP errors. GET also restricts results to the creating actor and tenant; missing, expired and foreign IDs all return 404.

## Planner contract

`AgentPlanner` declares async initial_plan, next_step, interpret and recommend methods. Strict Plan, Step, Interpretation and Recommendation contracts govern proposals. The deterministic mock planner is the only configured provider; no API key, randomness, token usage, paid service or LLM integration is introduced. Goals, notes, ticket summaries and policy prose are never parsed as executable instructions.

The mandatory initial plan verifies customer ownership with get_customer, then retrieves list_customer_tickets. A selected ticket must appear in that bounded customer list. Without a supplied ticket, use its first stable-order entry. An absent ticket stops for review, never guesses an account. Account IDs come only from that selected ticket. Then get_ticket, get_account_status, list_recent_transactions and search_policy collect real authorized records. Search is fixed deterministic keywords. Schema, version, permission, investigation-resource scope and read classification are validated before every execution. ToolExecutor alone performs the read and revalidates live session/role; its optional trusted required_permission additionally enforces investigation:create without accepting caller permissions.

Billing, security, duplicate, resolved-billing candidate and conflicting-evidence scenarios derive from structured account/ticket/transaction fields. Resolved billing with observed unpaid transactions is conflicting. Unsupported scenarios stop for review. An untrusted ticket requesting another tenant remains data; neither it nor a goal can redirect resource IDs. Explicit cross-tenant customer requests fail through the existing tenant-scoped tool. Mock recommendations must agree with deterministic evidence classification and an allowlisted advisory recommendation; unsupported interpretation or advice stops for review. No recommendation certifies eligibility. Deterministic policy evaluation remains Phase 7.

## Budgets and storage

| Environment variable | Default | Allowed |
| --- | --- | --- |
| AGENT_MAX_STEPS | 8 | 1–20 |
| AGENT_MAX_TOOL_CALLS | 8 | 1–20 |
| AGENT_WALL_SECONDS | 8 | >0–30 |
| AGENT_MAX_REPEATS | 1 | 1–2 |
| AGENT_OBSERVATION_BYTES | 48000 | 128–100000 |
| AGENT_PLANNING_ITERATIONS | 8 | 1–20 |

These are server configuration, not request overrides. Every planner invocation (including interpretation/recommendation) counts toward planning iterations. The default six-tool run uses eight planner invocations. Repeated name/arguments, exhausted steps/calls/time/bytes/planning and duplicate step IDs stop safely. No retries. At most four active investigations per backend process, alongside ToolExecutor's four bounded workers and persistent actor rate limits. The Next.js investigation proxy permits up to 35 seconds; it is not a guarantee of a hard backend deadline.

Phase 4 stores results, events, evidence and checkpoints in PostgreSQL, bound to the creating actor and tenant. The previous 15-minute/100-result process-local store is removed. Cancellation and explicit resume controls are authenticated and documented in [recovery](RECOVERY.md); no scheduler or automatic background replay is introduced. Original budgets survive recovery and elapsed downtime is charged. Completed observation checkpoints can continue; unfinished tool intent stops for review. In-process timeouts still cannot terminate blocking trusted Python or hard-bound database connection/audit cleanup. PostgreSQL statement/lock limits and retained worker slots remain in effect.

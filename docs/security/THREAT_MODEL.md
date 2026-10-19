# Controlled AI Operations Agent — threat model, Phase 11

Scope: synthetic Northstar tenant data and local/mock evaluation. This is an engineering threat analysis, not security certification. No real enterprise connectors or live provider evaluation are included.

## Assets and boundaries

| Boundary | Untrusted input | Privileged authority / controls | Principal failure mode |
| --- | --- | --- | --- |
| Browser → FastAPI | Cookies, headers, URL/body IDs, notes, time filters | `services/authentication.py`: hashed persisted sessions, current DB user/tenant/role; strict DTOs; exact trusted Origin and cross-site rejection | Forged scope, stale session, CSRF, data enumeration |
| API → tenant records | Resource IDs and pagination | Explicit repositories/tenant predicates and composite tenant FKs | Missing tenant or parent-owner constraint |
| Goal/content → planner | Customer/ticket prose, CRM fields, policy descriptions, observations, citations | Minimized typed planner context, discriminated decisions, backend validation | Prompt injection, invented facts, claimed authorization |
| Planner → ToolExecutor | Tool name/version/arguments and repeated plans | Bounded registered read tools, DB principal revalidation, strict I/O, read-only transactions, timeouts and audit | Write dispatch, arbitrary HTTP/SQL/code, loops, partial cleanup |
| Tool results → evidence | Authorized but untrusted text and metadata | Normalization, provenance, checkpoint binding, grounded finding validation, conflict/gap handling | Fake/foreign/stale citation, unsupported finding |
| Evidence → policy engine | Proposed action/args/citations | Deterministic catalog, current effective policy rules, live resource/version binding | Unsafe ALLOW or REQUIRE_APPROVAL on forbidden action |
| Proposal → approval | Reviewer/session/action references | Current reviewer permission, self-review rejection, exact actor/tenant/action/arguments/evidence/policy/resource/expiry binding | Approval bypass, replay, consent drift |
| Approval → business transaction | Decision/approval ID, idempotency key | Locked current authority/state, SERIALIZABLE execution, exact request hash, verified effect + receipt + audit commit | Unauthorized or duplicate mutation, false success |
| Job → worker/recovery | Persisted job command, lease/fence, retry requests | Current authority at execution, fencing, bounded retries, deterministic error classification and transaction evidence | Stale worker, concurrent commit, blind uncertain replay |
| Workflow → operations UI | Filter/trace IDs and operator notes | Scoped aggregates, bounded unions, stored links, responder/admin roles, append-only application events | Cross-tenant timeline, fabricated metric, resolution used as repair |
| Test process → disposable DB | Evaluation selection and concurrency | Checked-in node bindings, local `_test` guard, session advisory exclusion lock | Destructive fixture overlap, stale artifact counted as evidence |

The backend is the authorization boundary. LLM text, browser visibility, transport success, an incident's status and a running worker process confer no write authority. Secret values, session tokens and raw provider bodies are excluded from generated summaries. The agent has no shell, arbitrary code, unrestricted HTTP or unrestricted database tool.

## Audit performed

Reviewed authentication/session and Origin enforcement; exact role matrix; tenant repositories; tool registry/executor and cleanup; planner/provider and dynamic orchestrator; retrieval/provenance/reconciliation; deterministic PDP/catalog/proposals; approval/execution services; jobs/fencing/reconciliation; operational metrics/incidents/correlation; API proxy/navigation and existing browser controls. The versioned catalog binds these boundaries to executable tests, including actual PostgreSQL writes/rollbacks and authenticated in-process HTTP routes. The separate A–J script uses the running local API.

## Priority and residual risk

P0 is mutation/leakage, P1 approval/policy/replay bypass, P2 fabricated evidence or unsafe escalation, P3 diagnostics/usability. Critical failing or missing scenarios prevent acceptance. The standard runner uses deterministic mock planning and mocked optional-provider transport; it cannot establish real LLM resistance. A real model could produce new adversarial sequences, but it still must pass the same deterministic gates.

Database-owner SQL bypasses ORM immutability and tenant application predicates; this is not production database privilege separation or RLS. Distributed partitions, storage failover, production load, backup tampering, TLS termination, browser extensions, stolen valid sessions, incident-note secret detection completeness and external exactly-once side effects are not established. The application uses trusted-Origin CSRF protection rather than synchronizer CSRF tokens; absent/invalid Origin and cross-site requests are tested. It does not claim token-based CSRF behavior.

Incident changes are durably audited; some rejected operational requests have request logs but no separate durable security event. Historical snapshot statuses, capped traces/history, condition deduplication after closure and shared worker availability are intentional Phase 10 limits. See SECURITY_BOUNDARIES for verification limits.

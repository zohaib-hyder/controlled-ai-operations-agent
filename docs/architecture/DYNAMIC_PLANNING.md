> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Dynamic observation-driven planning

Phase 6 extends `AgentOrchestrator`; there is one tool dispatch path, through EvidenceRetrievalService and ToolExecutor. Two trusted bootstrap reads verify customer ownership and discover customer-linked ticket/account identifiers. No planner can expand this resource scope. Subsequent decisions receive a strict `PlannerContext` and return a discriminated proposal:

| Decision | Required data | Backend treatment |
| --- | --- | --- |
| CALL_TOOL | Invocation, step ID, purpose, expected evidence | Registry/version/schema/read-only/RBAC/resource/budget/cancellation/lease checks, then existing executor |
| FINISH | Grounded findings, evidence IDs, advisory recommendation, uncertainty | Validate canonical citations and exact factual templates; independently check completeness, classification, recommendation and conflicts |
| ESCALATE | Constrained reason, supporting IDs, human follow-up | Validate the reason against deterministic facts, require citations to the supporting account/conflict records, and check the allowlisted advisory; stop NEEDS_REVIEW, no operational authority |
| STOP_INSUFFICIENT_EVIDENCE | Constrained reason and available evidence IDs | Explicit NEEDS_REVIEW; no fabricated missing facts |

The deterministic v2 planner uses actual structured observations. It inspects the selected ticket/account, then security holds and duplicate relationships prioritize focused `security review` or `duplicate ticket` policy retrieval. Payment cases retrieve the ledger first; paid/unpaid coexistence selects `billing consistent reactivation`, unpaid blocks select `billing unpaid`, and other billing-resolution candidates select `reactivation consistent`. It gathers a bounded corroborating ledger even on security/duplicate branches, preserving six-read evidence coverage. Policy/ledger absence stops safely; security and conflicting evidence escalate. This is adaptive ordering and query selection over six registered read tools, not unrestricted task solving or invented outputs. Goals/source prose do not grant authority.

Loop: load fenced durable state → cancellation/budget checks → bounded context → charge/persist planning reservation → validate decision → authorize/execute one tool → normalize/persist observation and trace atomically → reconcile → stop or iterate. Tool calls are not duplicated by the planner. Completed tool steps and observations survive recovery.

Context contains goal, validated customer/ticket/account IDs, permission-filtered read-tool definitions, completed invocations, minimized observations, canonical evidence, allowed advisory phrases and remaining budgets. Customer names, emails, session/user IDs, credentials, notes and raw ticket/policy prose are omitted. Source summary/facts remain data; the backend does not treat model-supplied identity or authorization as trusted.

Bounds retain step/call/repetition/wall/observation/planning limits. Semantic fingerprints omit the result limit and minimized source prose: changed-argument calls returning already observed facts increment a persisted no-progress counter (default one). Identical invocations are stopped before dispatch. Decision output is capped at 16 KiB and context at a configurable 64 KiB default. Canonical evidence and final result limits remain bounded. Budget exhaustion is a structured terminal result, not a silent retry.

New JSON fields record planner v2, decisions/trace links, hashes and provider reservations. No schema migration is needed. Legacy v1 checkpoint selection keeps its original order/query through `LegacyDeterministicPlanner`. Typed default normalization permits old counter/limit JSON without rewriting history. Leases, live sessions, monotonic counters, append-only trace prefixes, cancellation and conservative incomplete-tool recovery remain authoritative. A provider configuration mismatch on recovery stops safely; terminal investigations remain terminal.

A post-commit disconnect is tested separately from provider failure: a valid checkpoint can resume without replay, while an ambiguous before-tool checkpoint requires human review. A corrupt checkpoint fails closed. Trace/evidence persistence failure withholds success. No business mutation, approval execution or Phase 7 eligibility is implemented.

Live restart verification uses an explicit 30-second synthetic recovery fixture so downtime can be charged within its original durable budget. The application default remains eight seconds. The first live attempt with an eight-second fixture correctly stopped at the wall-clock limit when restart downtime exceeded it; no budget was reset or bypassed. Lease-expiry fixtures use PostgreSQL time, matching runtime lease authority rather than relying on host/VM clock alignment.

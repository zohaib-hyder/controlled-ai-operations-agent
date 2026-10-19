> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Agent state machine

`app.agents.contracts.State` is a typed enum. `transition` checks an explicit adjacency table and rejects invalid edges, including every transition out of a terminal state. Results include actual state history, not simulated frontend progress.

| From | Allowed targets |
| --- | --- |
| CREATED | PLANNING, FAILED, CANCELLED |
| PLANNING | RUNNING, FAILED, CANCELLED, BUDGET_EXCEEDED |
| RUNNING | COMPLETED, NEEDS_REVIEW, FAILED, CANCELLED, BUDGET_EXCEEDED |
| Terminal states | None |

COMPLETED means the bounded evidence collection completed; it never means an operational action was approved. Security blocks, conflicting observations and unknown scenarios end in NEEDS_REVIEW. Failures preserve already collected safe evidence. CANCELLED records request task cancellation; callers whose connection has gone may not receive that result. BUDGET_EXCEEDED always includes a specific structured stop reason and never reports success.

Step status is proposed, succeeded or failed. A step succeeds only after ToolExecutor validates output and persists its tool metadata. A failed observation-size check does not retain the oversized observation. Tool-call counts include attempted executions, including errors; rejected planner selections are not counted as executed calls.

# 0012 — Reuse assertion-bearing integration tests as the red-team runner

Phase 11 uses a versioned catalog of existing and new pytest scenarios, the existing deterministic Northstar fixtures, and the existing Phase 5–10 raw evaluation artifacts. This avoids divergent authorization simulators. Strict local `_test` database guards and a session-wide PostgreSQL advisory lock protect destructive fixtures. Standard evaluations force mock planning and disable real httpx transport; adapter tests retain explicit MockTransport.

Every invocation creates fresh raw evidence and JSON/Markdown reports. Missing, skipped, setup/teardown failures and nonzero test exits prevent acceptance. Scoring distinguishes scenario invariant probes from measured tool selections, references and facts. A failed assertion is unknown security evidence until diagnosed, not an invented attack-success count. No backend runtime schema, agent tools, policy permissions, approval semantics or execution budgets change.

The tradeoff is reliance on repository test dependencies and wall-clock execution bounds. This is a development CLI, not a customer-facing endpoint or production monitoring service. Repeated runs investigate stability without silently retrying failures or increasing security budgets.
